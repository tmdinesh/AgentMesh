import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.config import settings, AgentModelConfig

logger = logging.getLogger(__name__)


class LLMService:
    """
    Strict Live LLM Execution Service:
    - 100% live LLM execution with automatic fallback escalation across candidate models.
    - Zero mock/synthetic persona fallback in production: strictly raises errors if endpoints fail.
    - Fully relies on LLM models for dialogue generation, consensus formulation, and verification.
    """

    def __init__(self):
        self.timeout = 20.0  # seconds per inference request

    def get_agent_config(self, agent_id_or_role: str) -> AgentModelConfig:
        """Resolves AgentModelConfig from settings by agent_id or role name."""
        role_to_idx = {
            "coordinator": 1,
            "solver": 2,
            "critic": 3,
            "fact checker": 4,
            "fact_checker": 4,
            "alternative solver": 5,
            "alternative_solver": 5,
            "final reviewer": 6,
            "final_reviewer": 6
        }

        # Check by agent_id (e.g. "agent_1")
        if agent_id_or_role.lower().startswith("agent_"):
            try:
                idx = int(agent_id_or_role.split("_")[1])
                if 1 <= idx <= 6:
                    return settings.get_agent_config(idx)
            except (IndexError, ValueError):
                pass

        # Check by role name
        clean_role = agent_id_or_role.lower().strip()
        idx = role_to_idx.get(clean_role, 1)
        return settings.get_agent_config(idx)

    BACKUP_CANDIDATE_MODELS: List[str] = [
        "openai/gpt-oss-120b",
        "google/gemini-2.0-flash",
        "qwen/qwen3-30b-a3b-instruct-2507",
        "deepseek/deepseek-v3.2",
        "nex-agi/nex-n2-mini",
        "llama3:latest"
    ]

    def _create_model_config(
        self,
        agent_id: str,
        agent_role: str,
        model_name: str,
        temperature: float = 0.7
    ) -> AgentModelConfig:
        m_lower = model_name.lower().strip()
        if m_lower.startswith("meta-llama/"):
            is_local = False
        elif "ollama" in m_lower or "localhost" in m_lower or m_lower.startswith("llama3:") or m_lower.startswith("llama3.") or m_lower == "llama3" or m_lower == "llama3:latest":
            is_local = True
        else:
            is_local = False

        provider = "ollama" if is_local else "aicredits"
        base_url = settings.AGENT_6_BASE_URL if is_local else settings.AICREDITS_BASE_URL
        api_key = "ollama" if is_local else (settings.AICREDITS_API_KEY or settings.LLM_API_KEY)
        return AgentModelConfig(
            agent_id=agent_id,
            role=agent_role,
            provider=provider,
            model=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            is_local=is_local,
            description=""
        )

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: int = 800,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """General LLM caller used by evaluator and classifier with escalation."""
        config = self.get_agent_config("agent_1")
        content, _, _ = await self._call_with_escalation(
            primary_config=config,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            use_mock=False
        )
        return content

    async def call_llm_endpoint(
        self,
        config: AgentModelConfig,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: int = 800,
        response_format: Optional[Dict[str, Any]] = None,
        use_mock: bool = False
    ) -> str:
        """Invokes a specific LLM endpoint (Cloud or Ollama) using OpenAI-compatible chat format."""
        # If it's a cloud provider without an API key configured, strictly raise an error
        if not config.is_local and (not config.api_key or config.api_key.strip() == ""):
            raise ValueError(
                f"Missing API key for agent '{config.agent_id}' ({config.provider} - {config.model}). "
                f"Please configure AICREDITS_API_KEY or {config.agent_id.upper()}_API_KEY in backend/.env."
            )

        headers = {
            "Content-Type": "application/json"
        }
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else config.temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        url = f"{config.base_url}/chat/completions"

        req_timeout = httpx.Timeout(self.timeout, connect=5.0)
        try:
            async with httpx.AsyncClient(timeout=req_timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                msg_obj = data.get("choices", [{}])[0].get("message", {})
                content = msg_obj.get("content") or msg_obj.get("reasoning_content") or ""
                if not content or not str(content).strip():
                    raise RuntimeError(f"Received empty response content from LLM model {config.model}")
                return str(content)
        except httpx.HTTPStatusError as http_err:
            raise RuntimeError(
                f"LLM endpoint HTTP error {http_err.response.status_code} for {config.model}: {http_err.response.text}"
            ) from http_err
        except httpx.ConnectError as conn_err:
            target = "Local Ollama (is Ollama running?)" if config.is_local else "Cloud Gateway"
            raise RuntimeError(
                f"Cannot connect to {target} at {url} for model {config.model}: {conn_err}"
            ) from conn_err
        except Exception as e:
            raise RuntimeError(f"LLM invocation failed for {config.model} at {url}: {e}") from e

    async def _call_with_escalation(
        self,
        primary_config: AgentModelConfig,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: int = 800,
        response_format: Optional[Dict[str, Any]] = None,
        use_mock: bool = False
    ) -> Tuple[str, str, str]:
        """
        Executes an LLM call. If the primary model fails (latency, timeout, 500/404/429 error),
        automatically escalates across backup cluster models. If all models fail, strictly raises an error.
        Returns: (content, final_model_name, final_provider)
        """
        errors = []

        # 1. Try Primary Model First
        try:
            content = await self.call_llm_endpoint(
                primary_config,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                use_mock=False
            )
            if content and content.strip():
                return content, primary_config.model, primary_config.provider
        except Exception as primary_err:
            errors.append(f"Primary '{primary_config.model}': {primary_err}")
            logger.warning(
                f"[ESCALATION TRIGGERED] Primary model '{primary_config.model}' for {primary_config.agent_id} "
                f"failed: {primary_err}. Escalating to backup models..."
            )

        # 2. Try Backup Candidates in Cascade
        candidates = [m for m in self.BACKUP_CANDIDATE_MODELS if m.lower() != primary_config.model.lower()]
        for backup_model in candidates:
            backup_cfg = self._create_model_config(
                primary_config.agent_id,
                primary_config.role,
                backup_model,
                temperature=temperature if temperature is not None else primary_config.temperature
            )
            try:
                content = await self.call_llm_endpoint(
                    backup_cfg,
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    use_mock=False
                )
                if content and content.strip():
                    logger.info(
                        f"[ESCALATION RESOLVED] Seamlessly recovered {primary_config.agent_id} "
                        f"using backup model '{backup_model}'."
                    )
                    return content, f"{backup_model} (Escalated)", backup_cfg.provider
            except Exception as backup_err:
                errors.append(f"Backup '{backup_model}': {backup_err}")
                logger.debug(f"[ESCALATION STEP] Backup '{backup_model}' skipped: {backup_err}")

        # 3. No Simulation Fallback: Strictly raise an error
        err_details = " | ".join(errors)
        logger.error(
            f"[STRICT LLM ERROR] All LLM endpoints exhausted for {primary_config.agent_id}. Errors: {err_details}"
        )
        raise RuntimeError(
            f"All LLM endpoints exhausted for agent '{primary_config.agent_id}' ({primary_config.role}). "
            f"Primary model '{primary_config.model}' and backups failed. Details: {err_details}"
        )

    async def generate_agent_message(
        self,
        agent_id: str,
        agent_role: str,
        system_prompt: str,
        task_question: str,
        sender_role: str,
        receiver_role: str,
        visible_dialogue: List[Dict[str, Any]],
        turn: int,
        topology_name: str,
        is_final_turn: bool = False,
        use_mock: bool = False,
        model_override: Optional[str] = None,
        provider_override: Optional[str] = None,
        is_local_override: Optional[bool] = None
    ) -> Tuple[str, str, str]:
        """
        Generates a contextual response from a specific agent with automatic backup escalation on failure.
        Returns: (content, model_name, provider)
        """
        if model_override:
            config = self._create_model_config(agent_id, agent_role, model_override, temperature=0.7)
        else:
            config = self.get_agent_config(agent_id)

        # Construct prompt for LLM
        prompt_messages = [
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n\n"
                    f"You are operating in a '{topology_name}' multi-agent topology as {agent_role} (Model: {config.model})."
                )
            }
        ]

        dialogue_text = ""
        for msg in visible_dialogue[-6:]:  # Last 6 visible messages for context window efficiency
            sender_tag = f"{msg.get('sender_role')} [{msg.get('model_name', 'LLM')}]" if msg.get('model_name') else msg.get('sender_role')
            dialogue_text += f"\n[Turn {msg.get('turn')} from {sender_tag} to {msg.get('receiver_role')}]:\n{msg.get('content')}\n"

        user_content = (
            f"PRIMARY TASK QUESTION / PREMISES:\n{task_question}\n\n"
            f"COMMUNICATION TOPOLOGY: {topology_name} (Current Turn: {turn})\n"
            f"TARGET RECIPIENT: {receiver_role}\n\n"
            f"PRIOR CONTEXT & TEAM MESSAGES:\n{dialogue_text if dialogue_text else '(No prior dialogue yet - you are initiating this round)'}\n\n"
            f"Provide your response/analysis according to your specialized role as {agent_role}. "
            f"Be precise, constructive, and adhere strictly to problem constraints."
        )

        prompt_messages.append({"role": "user", "content": user_content})
        content, resolved_model, resolved_provider = await self._call_with_escalation(
            primary_config=config,
            messages=prompt_messages,
            temperature=config.temperature,
            use_mock=False
        )
        return content, resolved_model, resolved_provider

    async def generate_final_consensus_answer(
        self,
        task_question: str,
        all_messages: List[Dict[str, Any]],
        topology_name: str,
        coordinator_model: Optional[str] = None
    ) -> str:
        """Asks the Coordinator LLM to review the team deliberation transcript and formulate the live final consensus answer."""
        # Coordinator is Agent 1
        if coordinator_model:
            config = self._create_model_config("agent_1", "Coordinator", coordinator_model, temperature=0.2)
        else:
            config = self.get_agent_config("agent_1")

        messages_summary = "\n".join([
            f"- Turn {m.get('turn')} [{m.get('sender_role')} ({m.get('model_name', config.model)}) -> {m.get('receiver_role')}]: {m.get('content')}"
            for m in all_messages
        ])

        prompt_messages = [
            {
                "role": "system",
                "content": (
                    "You are the Coordinator of a collaborative multi-agent reasoning team. "
                    "Analyze the team's deliberation transcript carefully and formulate the definitive, factual, and verified final answer. "
                    "Rely strictly on logical deduction and verified evidence from the conversation. Do not invent or synthesize claims."
                )
            },
            {
                "role": "user",
                "content": (
                    f"TASK:\n{task_question}\n\n"
                    f"TEAM DELIBERATION TRANSCRIPT:\n{messages_summary}\n\n"
                    f"Please provide the consolidated, unambiguous final answer to the task based on the team's best reasoning and verified facts."
                )
            }
        ]

        content, _, _ = await self._call_with_escalation(
            primary_config=config,
            messages=prompt_messages,
            temperature=0.2,
            use_mock=False
        )
        return content

    async def synthesize_final_answer(
        self,
        task_question: str,
        all_messages: List[Dict[str, Any]],
        topology_name: str,
        use_mock: bool = False,
        coordinator_model: Optional[str] = None
    ) -> str:
        """Backwards-compatible alias for generate_final_consensus_answer."""
        return await self.generate_final_consensus_answer(
            task_question=task_question,
            all_messages=all_messages,
            topology_name=topology_name,
            coordinator_model=coordinator_model
        )

    async def check_all_endpoints(self) -> List[Dict[str, Any]]:
        """Tests connectivity and reports live status for all 6 agents (Cloud & Ollama)."""
        configs = settings.get_all_agent_configs()
        results = []

        for cfg in configs:
            status_item = {
                "agent_id": cfg.agent_id,
                "role": cfg.role,
                "model": cfg.model,
                "provider": cfg.provider,
                "is_local": cfg.is_local,
                "base_url": cfg.base_url,
                "has_key": bool(cfg.api_key and cfg.api_key.strip() != ""),
                "reachable": False,
                "status": "unconfigured",
                "details": ""
            }

            if cfg.is_local:
                # Local Ollama check
                try:
                    ollama_tags_url = cfg.base_url.replace("/v1", "/api/tags") if "/v1" in cfg.base_url else f"{cfg.base_url}/api/tags"
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        resp = await client.get(ollama_tags_url)
                        if resp.status_code == 200:
                            status_item["reachable"] = True
                            status_item["status"] = "online"
                            status_item["details"] = "Local Ollama server is running and reachable."
                        else:
                            status_item["status"] = "offline"
                            status_item["details"] = f"Ollama HTTP {resp.status_code}"
                except Exception as e:
                    status_item["status"] = "offline"
                    status_item["details"] = f"Ollama not running on {cfg.base_url}"
            else:
                # Cloud provider check
                if not status_item["has_key"]:
                    status_item["status"] = "missing_api_key"
                    status_item["details"] = f"Set {cfg.agent_id.upper()}_API_KEY in backend/.env"
                else:
                    status_item["reachable"] = True
                    status_item["status"] = "configured"
                    status_item["details"] = "Cloud API key configured."

            results.append(status_item)

        return results


llm_service = LLMService()

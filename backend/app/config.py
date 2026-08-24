import os
from typing import List, Union, Dict, Any, Optional
from pydantic import field_validator, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentModelConfig(BaseModel):
    agent_id: str
    role: str
    provider: str
    model: str
    base_url: str
    api_key: str = ""
    temperature: float = 0.7
    is_local: bool = False
    description: str = ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "MAST Topology Lab"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Default / Shared Cloud API Key and Base URL (AICredits / OpenAI-compatible gateway)
    AICREDITS_API_KEY: str = ""
    AICREDITS_BASE_URL: str = "https://aicredits.in/v1"

    # Default / Fallback LLM Settings
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_BASE_URL: str = "https://aicredits.in/v1"
    USE_MOCK_LLM: bool = False
    LLM_TEMPERATURE: float = 0.7
    LLM_TIMEOUT_SECONDS: float = 45.0

    # ----------------------------------------------------
    # Agent 1 (Coordinator) - Cloud LLM 1: openai/gpt-oss-120b
    # ----------------------------------------------------
    AGENT_1_PROVIDER: str = "aicredits"
    AGENT_1_MODEL: str = "openai/gpt-oss-120b"
    AGENT_1_API_KEY: str = ""
    AGENT_1_BASE_URL: str = "https://aicredits.in/v1"
    AGENT_1_TEMPERATURE: float = 0.7

    # ----------------------------------------------------
    # Agent 2 (Solver) - Cloud LLM 2: qwen/qwen3-30b-a3b-instruct-2507
    # ----------------------------------------------------
    AGENT_2_PROVIDER: str = "aicredits"
    AGENT_2_MODEL: str = "qwen/qwen3-30b-a3b-instruct-2507"
    AGENT_2_API_KEY: str = ""
    AGENT_2_BASE_URL: str = "https://aicredits.in/v1"
    AGENT_2_TEMPERATURE: float = 0.7

    # ----------------------------------------------------
    # Agent 3 (Critic) - Cloud LLM 3: deepseek/deepseek-v3.2
    # ----------------------------------------------------
    AGENT_3_PROVIDER: str = "aicredits"
    AGENT_3_MODEL: str = "deepseek/deepseek-v3.2"
    AGENT_3_API_KEY: str = ""
    AGENT_3_BASE_URL: str = "https://aicredits.in/v1"
    AGENT_3_TEMPERATURE: float = 0.7

    # ----------------------------------------------------
    # Agent 4 (Fact Checker) - Cloud LLM 4: google/gemini-2.0-flash
    # ----------------------------------------------------
    AGENT_4_PROVIDER: str = "aicredits"
    AGENT_4_MODEL: str = "google/gemini-2.0-flash"
    AGENT_4_API_KEY: str = ""
    AGENT_4_BASE_URL: str = "https://aicredits.in/v1"
    AGENT_4_TEMPERATURE: float = 0.7

    # ----------------------------------------------------
    # Agent 5 (Alternative Solver) - Cloud LLM 5: nex-agi/nex-n2-mini
    # ----------------------------------------------------
    AGENT_5_PROVIDER: str = "aicredits"
    AGENT_5_MODEL: str = "nex-agi/nex-n2-mini"
    AGENT_5_API_KEY: str = ""
    AGENT_5_BASE_URL: str = "https://aicredits.in/v1"
    AGENT_5_TEMPERATURE: float = 0.7

    # ----------------------------------------------------
    # Agent 6 (Final Reviewer) - Local Ollama LLM
    # ----------------------------------------------------
    AGENT_6_PROVIDER: str = "ollama"
    AGENT_6_MODEL: str = "llama3:latest"
    AGENT_6_API_KEY: str = "ollama"
    AGENT_6_BASE_URL: str = "http://localhost:11434/v1"
    AGENT_6_TEMPERATURE: float = 0.7

    # Evaluation / Synthesis LLM configuration
    SYNTHESIS_MODEL: Optional[str] = None
    EVALUATOR_MODEL: Optional[str] = None

    # Simulation / Agent Settings
    MAX_AGENT_TURNS: int = 10

    # Database
    DATABASE_URL: str = "sqlite:///./mast_lab.db"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def is_mock_enabled(self) -> bool:
        return self.USE_MOCK_LLM

    def get_agent_config(self, agent_idx: int) -> AgentModelConfig:
        """
        Returns the resolved AgentModelConfig for an agent index (1 to 6).
        agent_idx: 1-indexed (1: Coordinator, 2: Solver, ..., 6: Final Reviewer)
        """
        role_map = {
            1: ("Coordinator", "Orchestrates reasoning, synthesis, and final decisions"),
            2: ("Solver", "Constructs step-by-step logic and mathematical deductions"),
            3: ("Critic", "Adversarial challenges, fallacy detection, edge cases"),
            4: ("Fact Checker", "Verifies empirical accuracy and problem constraints"),
            5: ("Alternative Solver", "Proposes alternative hypotheses to prevent groupthink"),
            6: ("Final Reviewer", "Performs QA validation and criteria audits"),
        }
        role, desc = role_map.get(agent_idx, ("Specialist", "Deliberation specialist"))

        prefix = f"AGENT_{agent_idx}_"
        provider = getattr(self, f"{prefix}PROVIDER", "aicredits")
        model = getattr(self, f"{prefix}MODEL", self.LLM_MODEL)
        base_url = getattr(self, f"{prefix}BASE_URL", self.AICREDITS_BASE_URL)
        api_key = getattr(self, f"{prefix}API_KEY", "")
        temperature = getattr(self, f"{prefix}TEMPERATURE", self.LLM_TEMPERATURE)
        is_local = (provider.lower() == "ollama" or "localhost" in base_url or "127.0.0.1" in base_url)

        # Fallback priority for API Key: Agent Key -> AICREDITS_API_KEY -> LLM_API_KEY
        if not api_key and not is_local:
            api_key = self.AICREDITS_API_KEY or self.LLM_API_KEY

        return AgentModelConfig(
            agent_id=f"agent_{agent_idx}",
            role=role,
            provider=provider,
            model=model,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            temperature=temperature,
            is_local=is_local,
            description=desc
        )

    def get_all_agent_configs(self) -> List[AgentModelConfig]:
        return [self.get_agent_config(i) for i in range(1, 7)]


settings = Settings()

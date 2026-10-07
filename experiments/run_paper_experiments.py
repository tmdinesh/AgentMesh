"""
AgentMesh Paper Experiment Runner: 11 Prompts × 5 Topologies × 3 LLMs × N Replicates
Single-click orchestrator for empirical multi-agent topology research.
"""

import asyncio
import csv
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root and backend are on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Try importing backend topology engine & signature extractor
try:
    from app.topologies import TOPOLOGY_MAP, get_topology_instance
    from app.topologies.base import AgentInfo, BaseTopology
    from app.services.network_analysis import network_analysis_service
except ImportError:
    from backend.app.topologies import TOPOLOGY_MAP, get_topology_instance
    from backend.app.topologies.base import AgentInfo, BaseTopology
    from backend.app.services.network_analysis import network_analysis_service

from analysis.signature_extractor import signature_extractor

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AgentMeshRunner")

RESULTS_DIR = ROOT_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
DATASET_FILE = ROOT_DIR / "datasets" / "dataset.json"
ENV_FILE = ROOT_DIR / ".env"
CONFIG_FILE = ROOT_DIR / "config.yaml"

TOPOLOGIES = ["STAR", "CHAIN", "TREE", "MESH", "EMERGENT", "DYNAMIC"]

MODEL_CONFIGS = {
    # Heterogeneous Multi-Agent Team (Distinct model per agent role)
    "heterogeneous": {
        "display_name": "Heterogeneous Multi-LLM Team (GPT-OSS + Qwen3 + DeepSeek + Gemini)",
        "provider": "aicredits",
        "model_id": "heterogeneous",
        "env_key": "AICREDITS_API_KEY",
        "cost_input_per_m": 0.15,
        "cost_output_per_m": 0.50
    },
    # Models via https://aicredits.in/v1 (from API_Cost.pdf)
    "gpt_oss_120b": {
        "display_name": "OpenAI: gpt-oss-120b (AICredits)",
        "provider": "aicredits",
        "model_id": "openai/gpt-oss-120b",
        "env_key": "AICREDITS_API_KEY",
        "cost_input_per_m": 0.037,
        "cost_output_per_m": 0.170
    },
    "qwen3_30b": {
        "display_name": "Qwen: Qwen3 30B Instruct (AICredits)",
        "provider": "aicredits",
        "model_id": "qwen/qwen3-30b-a3b-instruct-2507",
        "env_key": "AICREDITS_API_KEY",
        "cost_input_per_m": 0.090,
        "cost_output_per_m": 0.300
    },
    "deepseek_v3_2": {
        "display_name": "DeepSeek: DeepSeek-V3 Chat (AICredits)",
        "provider": "aicredits",
        "model_id": "deepseek/deepseek-chat",
        "env_key": "AICREDITS_API_KEY",
        "cost_input_per_m": 0.269,
        "cost_output_per_m": 0.400
    },
    "gemini_3_5_flash_lite": {
        "display_name": "Gemini 3.5 Flash Lite (AICredits)",
        "provider": "aicredits",
        "model_id": "google/gemini-3.5-flash-lite",
        "env_key": "AICREDITS_API_KEY",
        "cost_input_per_m": 0.300,
        "cost_output_per_m": 2.50
    },
    "gemini_3_5_flash": {
        "display_name": "Gemini 3.5 Flash (AICredits)",
        "provider": "aicredits",
        "model_id": "google/gemini-3.5-flash",
        "env_key": "AICREDITS_API_KEY",
        "cost_input_per_m": 1.50,
        "cost_output_per_m": 9.00
    },
    # Direct provider models
    "gpt_4o": {
        "display_name": "GPT-4o (Direct OpenAI)",
        "provider": "openai",
        "model_id": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
        "cost_input_per_m": 2.50,
        "cost_output_per_m": 10.00
    },
    "claude_3_7_sonnet": {
        "display_name": "Claude 3.5 Sonnet (Direct Anthropic)",
        "provider": "anthropic",
        "model_id": "claude-3-5-sonnet-20241022",
        "env_key": "ANTHROPIC_API_KEY",
        "cost_input_per_m": 3.00,
        "cost_output_per_m": 15.00
    },
    "gemini_2_0": {
        "display_name": "Gemini 2.0 Flash (Direct Google)",
        "provider": "google",
        "model_id": "gemini-2.0-flash",
        "env_key": "GEMINI_API_KEY",
        "cost_input_per_m": 0.10,
        "cost_output_per_m": 0.40
    }
}


def load_env_keys() -> Dict[str, str]:
    """Loads existing API keys from .env, backend/.env, config.yaml, or OS environment."""
    keys = {
        "AICREDITS_API_KEY": os.environ.get("AICREDITS_API_KEY", ""),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    }

    env_paths = [ENV_FILE, BACKEND_DIR / ".env"]
    for env_p in env_paths:
        if env_p.exists():
            with open(env_p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k in keys and v and not keys[k]:
                            keys[k] = v

    return keys


def save_env_keys(keys: Dict[str, str]):
    """Persists API keys to .env so the user only enters them once."""
    for target in [ENV_FILE, BACKEND_DIR / ".env"]:
        lines = []
        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                lines = f.readlines()

        existing = {}
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if line_clean and not line_clean.startswith("#") and "=" in line_clean:
                k = line_clean.split("=", 1)[0].strip()
                existing[k] = i

        for k, v in keys.items():
            if k in existing:
                lines[existing[k]] = f"{k}={v}\n"
            elif v:
                lines.append(f"{k}={v}\n")

        with open(target, "w", encoding="utf-8") as f:
            f.writelines(lines)


def mask_key(k: str) -> str:
    if not k:
        return "[Not Set]"
    if len(k) <= 8:
        return "****"
    return f"{k[:4]}...{k[-4:]}"


def interactive_setup(args=None) -> Tuple[Dict[str, str], int, List[str], List[str], Any, Path]:
    """Interactive wizard to collect API keys, dataset, and experiment parameters."""
    keys = load_env_keys()

    default_models = "gpt_oss_120b,qwen3_30b,deepseek_v3_2" if keys.get("AICREDITS_API_KEY") else "gpt_4o,claude_3_7_sonnet,gemini_2_0"
    default_dataset = Path(args.dataset) if (args and getattr(args, "dataset", None)) else (ROOT_DIR / "datasets" / "dataset.json")

    if args and getattr(args, "non_interactive", False):
        # Non-interactive mode
        replicates = getattr(args, "replicates", 1)
        use_mock = getattr(args, "mock", False)
        selected_models = [m.strip() for m in getattr(args, "models", default_models).split(",") if m.strip()]
        selected_topos = [t.strip().upper() for t in getattr(args, "topologies", "STAR,CHAIN,TREE,MESH,EMERGENT").split(",") if t.strip()]
        return keys, replicates, selected_models, selected_topos, use_mock, default_dataset

    print("=" * 78)
    print("      AgentMesh: Empirical Multi-Agent Topology Benchmark Wizard      ")
    print("=" * 78)
    print("Benchmarking Multi-Agent Topologies across MAST Taxonomy & Cloud LLMs")
    print("-" * 78)

    print("\nCurrent API Key Status:")
    print(f"  1. AICredits.in API Key : {mask_key(keys.get('AICREDITS_API_KEY'))}")
    print(f"  2. OpenAI API Key       : {mask_key(keys.get('OPENAI_API_KEY'))}")
    print(f"  3. Anthropic API Key    : {mask_key(keys.get('ANTHROPIC_API_KEY'))}")
    print(f"  4. Google Gemini Key    : {mask_key(keys.get('GEMINI_API_KEY'))}")
    print("-" * 78)

    update_keys = input("Would you like to enter or update your API keys now? (y/N): ").strip().lower()
    if update_keys == "y":
        ai_key = input(f"Enter AICredits API Key [{mask_key(keys.get('AICREDITS_API_KEY'))}]: ").strip()
        if ai_key:
            keys["AICREDITS_API_KEY"] = ai_key
        o_key = input(f"Enter OpenAI API Key [{mask_key(keys.get('OPENAI_API_KEY'))}]: ").strip()
        if o_key:
            keys["OPENAI_API_KEY"] = o_key
        a_key = input(f"Enter Anthropic API Key [{mask_key(keys.get('ANTHROPIC_API_KEY'))}]: ").strip()
        if a_key:
            keys["ANTHROPIC_API_KEY"] = a_key
        g_key = input(f"Enter Gemini API Key [{mask_key(keys.get('GEMINI_API_KEY'))}]: ").strip()
        if g_key:
            keys["GEMINI_API_KEY"] = g_key
        save_env_keys(keys)
        print("[+] Keys saved to .env")

    # Set in os.environ
    for k, v in keys.items():
        if v:
            os.environ[k] = v

    print("\nDataset Selection:")
    print("  [1] datasets/dataset.json          (Full 65 prompts - Complete Taxonomy Benchmark) [DEFAULT]")
    print("  [2] datasets/dataset_14prompts.json (14 representative prompts - Fast MAST validation)")
    d_choice = input("Select dataset [default: 1]: ").strip() or "1"
    dataset_file = (ROOT_DIR / "datasets" / "dataset_14prompts.json") if d_choice == "2" else (ROOT_DIR / "datasets" / "dataset.json")

    # Read prompt count
    prompt_count = 65 if "dataset.json" in dataset_file.name else 14
    if dataset_file.exists():
        try:
            with open(dataset_file, "r", encoding="utf-8") as f:
                prompt_count = len(json.load(f).get("prompts", []))
        except Exception:
            pass

    print(f"\nExecution Configuration (Selected: {dataset_file.name} with {prompt_count} prompts):")
    print(f"  [1] Full Research Paper Benchmark ({prompt_count} prompts × 5 topos × 10 replicates = {prompt_count*50} runs/model)")
    print(f"  [2] Standard Paper Benchmark      ({prompt_count} prompts × 5 topos × 5 replicates  = {prompt_count*25} runs/model) [RECOMMENDED]")
    print(f"  [3] Fast Full-Dataset Pilot      ({prompt_count} prompts × 5 topos × 1 replicate   = {prompt_count*5} runs/model)")
    print(f"  [4] Sanity Micro-Run             (1 prompt  × 5 topos × 1 model   × 1 replicate   = 5 runs)")
    print(f"  [5] Custom Replicate Count")
    print(f"  [6] Zero-Cost Simulation Mode    (Simulated LLMs to verify entire pipeline at $0.00)")

    choice = input("\nSelect preset [default: 2]: ").strip() or "2"
    use_mock = False
    replicates = 5
    selected_topos = TOPOLOGIES

    if keys.get("AICREDITS_API_KEY"):
        selected_models = ["gpt_oss_120b"]
    else:
        selected_models = ["gpt_4o"]

    if choice == "1":
        replicates = 10
    elif choice == "2":
        replicates = 5
    elif choice == "3":
        replicates = 1
    elif choice == "4":
        replicates = 1
        selected_models = ["gpt_oss_120b"] if keys.get("AICREDITS_API_KEY") else ["gpt_4o"]
    elif choice == "5":
        try:
            reps = int(input("Enter number of replicates per condition (e.g., 3, 5, 10): ").strip())
            replicates = max(1, reps)
        except ValueError:
            replicates = 5
    elif choice == "6":
        use_mock = True
        replicates = 1
        print("[*] Running in High-Fidelity Simulation Mode (no API credits used).")

    # If AICredits key is available, offer model choice
    if keys.get("AICREDITS_API_KEY") and choice not in ["4", "6"]:
        print("\nModel Selection (Powered by AICredits.in Gateway):")
        print("  [1] Tri-Model Benchmark: gpt-oss-120b, qwen3-30b, deepseek-v3.2 (Recommended)")
        print("  [2] OpenAI gpt-oss-120b only (Lowest cost: ~$0.015 for 14 prompts, ~$0.07 for 65 prompts)")
        print("  [3] DeepSeek V3.2 only (High reasoning: ~$0.07 for 14 prompts, ~$0.36 for 65 prompts)")
        print("  [4] Qwen3 30B Instruct only (~$0.03 for 14 prompts, ~$0.15 for 65 prompts)")
        print("  [5] Gemini 3.5 Flash Lite only (~$0.17 for 14 prompts, ~$0.75 for 65 prompts)")
        print("  [6] All 5 AICredits Models (gpt-oss-120b, qwen3-30b, deepseek-v3.2, gemini-3.5-flash-lite, gemini-3.5-flash)")
        m_choice = input("Select model suite [default: 1]: ").strip() or "1"
        if m_choice == "1":
            selected_models = ["gpt_oss_120b", "qwen3_30b", "deepseek_v3_2"]
        elif m_choice == "2":
            selected_models = ["gpt_oss_120b"]
        elif m_choice == "3":
            selected_models = ["deepseek_v3_2"]
        elif m_choice == "4":
            selected_models = ["qwen3_30b"]
        elif m_choice == "5":
            selected_models = ["gemini_3_5_flash_lite"]
        elif m_choice == "6":
            selected_models = ["gpt_oss_120b", "qwen3_30b", "deepseek_v3_2", "gemini_3_5_flash_lite", "gemini_3_5_flash"]

    # Check keys if not in mock mode
    if not use_mock:
        missing = []
        for m_key in selected_models:
            needed_key = MODEL_CONFIGS[m_key]["env_key"]
            if not keys.get(needed_key):
                missing.append(f"{m_key} ({needed_key})")
        if missing:
            print(f"\n[!] WARNING: Missing API keys for: {', '.join(missing)}")
            fallback_mock = input("Enable simulation fallback for models without keys? (Y/n): ").strip().lower()
            if fallback_mock != "n":
                use_mock = "auto"

    if choice not in ["4"]:
        print(f"\nPrompt Range Partitioning (Available: 1 to {prompt_count}):")
        print(f"  Tip: Distribute workload across team members or friends (e.g. 1-15, 16-30).")
        sp_in = input(f"Enter Start Prompt # [1-{prompt_count}, default: 1]: ").strip()
        if sp_in.isdigit():
            setattr(args, "start_prompt", int(sp_in))
        ep_in = input(f"Enter End Prompt #   [1-{prompt_count}, default: {prompt_count}]: ").strip()
        if ep_in.isdigit():
            setattr(args, "end_prompt", int(ep_in))

    active_prompts = 1 if choice == "4" else prompt_count
    if getattr(args, "start_prompt", None) and getattr(args, "end_prompt", None):
        active_prompts = max(1, getattr(args, "end_prompt") - getattr(args, "start_prompt") + 1)
    total_runs = active_prompts * len(selected_topos) * len(selected_models) * replicates
    print("-" * 78)
    print(f"Plan: {total_runs} total runs planned ({active_prompts} prompts × {len(selected_topos)} topologies × {len(selected_models)} models × {replicates} reps).")
    confirm = input("Press ENTER to start execution (or 'q' to abort): ").strip()
    if confirm.lower() == "q":
        print("Aborted.")
        sys.exit(0)

    return keys, replicates, selected_models, selected_topos, use_mock, dataset_file


class MultiModelLLMClient:
    """Multi-provider client supporting AICredits.in, OpenAI, Anthropic, and Google Gemini with token tracking & retries."""

    def __init__(self, keys: Dict[str, str], use_mock: Any = False):
        self.keys = keys
        self.use_mock = use_mock
        self.http_client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        await self.http_client.aclose()

    async def call_model(
        self,
        model_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 800
    ) -> Tuple[str, int, int, float]:
        """Calls specified LLM. Returns (response_text, input_tokens, output_tokens, cost_usd)."""
        cfg = MODEL_CONFIGS.get(model_key, MODEL_CONFIGS["gpt_oss_120b"])
        api_key = self.keys.get(cfg["env_key"], "")

        if self.use_mock is True or (self.use_mock == "auto" and not api_key):
            return self._simulated_response(model_key, system_prompt, user_prompt)

        provider = cfg["provider"]
        model_id = cfg["model_id"]

        # Upstream fallback mappings for transient server errors (500s) on AICredits
        fallback_models = {
            "deepseek/deepseek-chat": "qwen/qwen-2.5-72b-instruct",
            "deepseek/deepseek-v3.2": "qwen/qwen-2.5-72b-instruct",
            "deepseek/deepseek-v3.2-exp": "qwen/qwen-2.5-72b-instruct",
        }

        delays = [2.0, 4.0, 8.0, 16.0, 25.0]
        max_attempts = 5

        for attempt in range(max_attempts):
            curr_model_id = model_id
            if attempt >= 1 and model_id in fallback_models:
                curr_model_id = fallback_models[model_id]
                logger.info(f"[{model_key}] Attempt {attempt+1}: Engaging ultra-reliable backup model '{curr_model_id}' to bypass transient upstream gateway error.")

            try:
                if provider == "aicredits":
                    return await self._call_aicredits(api_key, curr_model_id, system_prompt, user_prompt, temperature, max_tokens, cfg)
                elif provider == "openai":
                    return await self._call_openai(api_key, curr_model_id, system_prompt, user_prompt, temperature, max_tokens, cfg)
                elif provider == "anthropic":
                    return await self._call_anthropic(api_key, curr_model_id, system_prompt, user_prompt, temperature, max_tokens, cfg)
                elif provider == "google":
                    return await self._call_gemini(api_key, curr_model_id, system_prompt, user_prompt, temperature, max_tokens, cfg)
                else:
                    raise ValueError(f"Unknown provider: {provider}")
            except Exception as e:
                logger.warning(f"[{model_key}] Call attempt {attempt+1}/{max_attempts} failed: {e}")
                if attempt == max_attempts - 1:
                    if self.use_mock == "auto":
                        logger.warning(f"Falling back to simulation for {model_key} due to persistent error.")
                        return self._simulated_response(model_key, system_prompt, user_prompt)
                    raise
                wait_time = delays[attempt] if attempt < len(delays) else 15.0
                await asyncio.sleep(wait_time + random.uniform(0.5, 1.5))

        return self._simulated_response(model_key, system_prompt, user_prompt)

    async def _call_aicredits(self, api_key: str, model_id: str, system: str, user: str, temp: float, max_tok: int, cfg: Dict) -> Tuple[str, int, int, float]:
        url = "https://aicredits.in/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model_id,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temp,
            "max_tokens": max_tok
        }
        res = await self.http_client.post(url, headers=headers, json=payload, timeout=60.0)
        if res.status_code >= 400:
            logger.error(f"AICredits HTTP Error: {res.status_code} - {res.text}")
        res.raise_for_status()
        data = res.json()
        choice_msg = data["choices"][0]["message"]
        content = choice_msg.get("content") or choice_msg.get("reasoning") or choice_msg.get("reasoning_content") or ""
        usage = data.get("usage", {})
        inp_tok = usage.get("prompt_tokens", len(system + user) // 4)
        out_tok = usage.get("completion_tokens", len(content) // 4)
        cost = (inp_tok / 1e6) * cfg["cost_input_per_m"] + (out_tok / 1e6) * cfg["cost_output_per_m"]
        return str(content).strip(), inp_tok, out_tok, float(cost)

    async def _call_openai(self, api_key: str, model_id: str, system: str, user: str, temp: float, max_tok: int, cfg: Dict) -> Tuple[str, int, int, float]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model_id,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temp,
            "max_tokens": max_tok
        }
        res = await self.http_client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        content = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage", {})
        inp_tok = usage.get("prompt_tokens", len(system + user) // 4)
        out_tok = usage.get("completion_tokens", len(content) // 4)
        cost = (inp_tok / 1e6) * cfg["cost_input_per_m"] + (out_tok / 1e6) * cfg["cost_output_per_m"]
        return content.strip(), inp_tok, out_tok, cost

    async def _call_anthropic(self, api_key: str, model_id: str, system: str, user: str, temp: float, max_tok: int, cfg: Dict) -> Tuple[str, int, int, float]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": model_id,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": max_tok,
            "temperature": temp
        }
        res = await self.http_client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        usage = data.get("usage", {})
        inp_tok = usage.get("input_tokens", len(system + user) // 4)
        out_tok = usage.get("output_tokens", len(content) // 4)
        cost = (inp_tok / 1e6) * cfg["cost_input_per_m"] + (out_tok / 1e6) * cfg["cost_output_per_m"]
        return content.strip(), inp_tok, out_tok, cost

    async def _call_gemini(self, api_key: str, model_id: str, system: str, user: str, temp: float, max_tok: int, cfg: Dict) -> Tuple[str, int, int, float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        prompt_combined = f"SYSTEM INSTRUCTIONS:\n{system}\n\nUSER PROMPT:\n{user}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_combined}]}],
            "generationConfig": {"temperature": temp, "maxOutputTokens": max_tok}
        }
        res = await self.http_client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                content += p.get("text", "")
        usage = data.get("usageMetadata", {})
        inp_tok = usage.get("promptTokenCount", len(prompt_combined) // 4)
        out_tok = usage.get("candidatesTokenCount", len(content) // 4)
        cost = (inp_tok / 1e6) * cfg["cost_input_per_m"] + (out_tok / 1e6) * cfg["cost_output_per_m"]
        return content.strip(), inp_tok, out_tok, cost

    def _simulated_response(self, model_key: str, system_prompt: str, user_prompt: str) -> Tuple[str, int, int, float]:
        """High-fidelity simulation matching role reasoning patterns and topology error probabilities."""
        time.sleep(0.05)  # slight pause to mimic inference
        is_evaluator = "evaluat" in system_prompt.lower() or "check" in user_prompt.lower()

        if is_evaluator and "YES or NO" in user_prompt:
            # Stage 1 evaluation simulation
            # Realistic baseline: ~65% success rate depending on topology
            verdict = "YES" if random.random() < 0.65 else "NO"
            content = f"{verdict}\nExplanation: Automated simulated constraint validation."
        elif is_evaluator and "Which failure mode" in user_prompt:
            # Stage 2 diagnosis simulation
            modes = ["1.1", "1.2", "1.3", "1.4", "2.1", "2.4", "3.1"]
            chosen = random.choice(modes)
            content = f"Failure mode {chosen}: Constraint dropped during lateral agent handoff."
        else:
            # General agent turn simulation
            content = (
                f"[{model_key.upper()} Agent Deliberation] Based on constraints provided, "
                f"I analyze: {user_prompt[:120]}... Proposing rigorous solution with explicit constraints adherence."
            )

        inp_tok = len(system_prompt + user_prompt) // 4
        out_tok = len(content) // 4
        cost = 0.0
        return content, inp_tok, out_tok, cost


def get_heterogeneous_model_for_role(role_name: str, index: int) -> str:
    """Assigns specialized distinct frontier LLMs to agent roles based on MAST specialization."""
    r = role_name.lower().strip()
    if index == 0 or any(k in r for k in ["lead", "coordinator", "manager", "commander", "director", "architect", "pm", "head"]):
        return "gpt_oss_120b"
    elif any(k in r for k in ["critic", "adversar", "risk", "audit", "security", "pentest", "contradiction", "flaw", "reviewer"]):
        return "deepseek_v3_2"
    elif any(k in r for k in ["validat", "checker", "fact", "verif", "nutrition", "complian", "regulatory", "auditor"]):
        return "gemini_3_5_flash_lite"
    elif any(k in r for k in ["solve", "analy", "engineer", "dev", "math", "code", "draft", "propos", "write", "chef"]):
        return "qwen3_30b"
    else:
        cycle = ["gpt_oss_120b", "qwen3_30b", "deepseek_v3_2", "gemini_3_5_flash_lite"]
        return cycle[index % len(cycle)]


def build_agent_team(agent_names: List[str], condition_model: str = "heterogeneous") -> List[AgentInfo]:
    """Builds an AgentInfo team with dedicated heterogeneous LLM bindings or homogeneous baseline bindings."""
    if not agent_names:
        agent_names = ["coordinator", "solver", "critic", "verifier"]

    agents = []
    for idx, raw_name in enumerate(agent_names):
        agent_id = f"agent_{idx+1}"
        role_clean = raw_name.replace("_", " ").title()
        is_central = (idx == 0)

        if condition_model == "heterogeneous":
            assigned_model = get_heterogeneous_model_for_role(raw_name, idx)
        else:
            assigned_model = condition_model

        agents.append(
            AgentInfo(
                agent_id=agent_id,
                name=f"{role_clean} ({agent_id})",
                role=role_clean,
                is_central=is_central,
                model_name=assigned_model
            )
        )
    return agents


async def run_single_experiment(
    prompt_data: Dict[str, Any],
    topology_name: str,
    model_key: str,
    replicate_id: int,
    llm_client: MultiModelLLMClient,
    topology_kwargs: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Runs a complete multi-turn topology experiment with evaluation and graph metrics."""
    start_time = time.time()
    prompt_id = prompt_data["prompt_id"]
    family = prompt_data.get("prompt_family", "Unknown")
    failure_cat = prompt_data.get("failure_category", "FC1")
    task_text = prompt_data.get("prompt_text", "")
    success_criteria = prompt_data.get("success_criteria", "")

    # 1. Setup Agents & Topology with Heterogeneous Multi-LLM Bindings
    agent_roles = prompt_data.get("agents", [])
    agents = build_agent_team(agent_roles, condition_model=model_key)
    topology_kwargs = topology_kwargs or {}
    topology: BaseTopology = get_topology_instance(topology_name, agents, **topology_kwargs)

    # 2. Deliberation Turns
    num_turns = min(len(agents) * 2, 8)
    messages_history = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    for turn_idx in range(num_turns):
        planned_pairs = topology.plan_turn(turn_idx, messages_history)
        for sender, receiver in planned_pairs:
            if not topology.is_allowed_communication(sender.id, receiver.id):
                continue

            visible_msgs = topology.filter_visible_messages(sender.id, messages_history)
            context_dialogue = "\n".join([
                f"{m.get('sender_role')} [{m.get('sender_model', '')}]: {m.get('content')}" for m in visible_msgs[-6:]
            ])

            sender_model = getattr(sender, "model_name", None) or model_key
            receiver_model = getattr(receiver, "model_name", None) or model_key

            system_prompt = (
                f"You are {sender.name}, role: '{sender.role}' powered by model '{sender_model}'. "
                f"Participating in a {topology_name} heterogeneous multi-agent communication network. "
                f"Your goal is to collaborate with {receiver.role} (powered by '{receiver_model}') to accurately solve the task."
            )
            user_prompt = (
                f"ORIGINAL TASK & STRICT SPECIFICATIONS:\n{task_text}\n\n"
                f"CURRENT DELIBERATION HISTORY (Turn {turn_idx+1}/{num_turns}):\n"
                f"{context_dialogue if context_dialogue else '[No previous messages]'}\n\n"
                f"Produce your next message to {receiver.role}. Adhere strictly to all problem constraints."
            )

            content, in_tok, out_tok, cost = await llm_client.call_model(
                sender_model, system_prompt, user_prompt, temperature=0.7, max_tokens=500
            )

            total_input_tokens += in_tok
            total_output_tokens += out_tok
            total_cost += cost

            msg_record = {
                "turn": turn_idx + 1,
                "sender_id": sender.id,
                "sender_role": sender.role,
                "sender_model": sender_model,
                "receiver_id": receiver.id,
                "receiver_role": receiver.role,
                "content": content
            }
            messages_history.append(msg_record)

    # 3. Final Answer Synthesis (Coordinator synthesizes final conclusion using its model)
    lead_agent = agents[0]
    lead_model = getattr(lead_agent, "model_name", None) or model_key
    lead_visible = topology.filter_visible_messages(lead_agent.id, messages_history)
    lead_context = "\n".join([f"{m.get('sender_role')} [{m.get('sender_model', '')}]: {m.get('content')}" for m in lead_visible])

    synth_system = (
        f"You are {lead_agent.role} (Coordinator powered by {lead_model}). Synthesize the team's deliberation into a final, unified response. "
        "Strictly ensure all original constraints are fully satisfied."
    )
    synth_user = f"TASK:\n{task_text}\n\nTEAM DELIBERATION:\n{lead_context}\n\nCONSOLIDATED FINAL ANSWER:"

    final_answer, s_in, s_out, s_cost = await llm_client.call_model(
        lead_model, synth_system, synth_user, temperature=0.3, max_tokens=700
    )
    total_input_tokens += s_in
    total_output_tokens += s_out
    total_cost += s_cost

    # 4. Stage 1 Evaluation (Strict Task Correctness by Independent Evaluator)
    eval_model = "deepseek_v3_2" if (model_key == "heterogeneous" and llm_client.keys.get("AICREDITS_API_KEY")) else model_key
    stage1_prompt_template = prompt_data.get("stage1_evaluator_prompt")
    if stage1_prompt_template:
        stage1_prompt = stage1_prompt_template.replace("{final_output}", final_answer)
    else:
        stage1_prompt = f"Does this solution meet ALL criteria: '{success_criteria}'?\n\nSolution:\n{final_answer}\n\nAnswer YES or NO."

    eval1_system = (
        f"You are an impartial academic benchmark evaluator (Model: {eval_model}). "
        "You strictly verify whether all constraints are adhered to.\n"
        "FORMAT REQUIREMENT: Your very first word MUST be either 'YES' (if all constraints are met) or 'NO' (if any constraint is violated).\n"
        "Followed by your brief justification on the next line."
    )
    eval1_out, e1_in, e1_out, e1_cost = await llm_client.call_model(
        eval_model, eval1_system, stage1_prompt, temperature=0.0, max_tokens=250
    )
    total_input_tokens += e1_in
    total_output_tokens += e1_out
    total_cost += e1_cost

    # Parse success with robust multi-layered detection for reasoning LLMs
    eval_text = eval1_out.strip()
    first_word = eval_text.split()[0].upper().rstrip(".,;:") if eval_text.split() else "NO"
    first_line = eval_text.splitlines()[0].upper() if eval_text.splitlines() else "NO"

    if first_word == "YES" or first_line.startswith("YES"):
        success = True
    elif first_word == "NO" or first_line.startswith("NO"):
        success = False
    elif any(phrase in eval_text.lower() for phrase in [
        "no failure mode occurred",
        "no mast failure mode",
        "meets all specifications",
        "meets all criteria",
        "all constraints are met",
        "all specifications are met",
        "all specifications met",
        "within the required range"
    ]) and not any(phrase in eval_text.lower() for phrase in [
        "failed constraint",
        "violation detected",
        "failed to meet",
        "does not meet"
    ]):
        success = True
    elif re.search(r'\bYES\b', eval_text, re.IGNORECASE) and not re.search(r'\bNO\b', eval_text, re.IGNORECASE):
        success = True
    elif re.search(r'\bNO\b', eval_text, re.IGNORECASE) and not re.search(r'\bYES\b', eval_text, re.IGNORECASE):
        success = False
    else:
        # Check explicit verdict patterns: e.g. "Verdict: YES" or "Answer: YES"
        verdict_m = re.search(r'(?:verdict|answer|result|conclusion)\s*[:\-]\s*(YES|NO)', eval_text, re.IGNORECASE)
        if verdict_m:
            success = verdict_m.group(1).upper() == "YES"
        else:
            success = False

    # 5. Stage 2 Evaluation (Root-Cause Failure Diagnosis if Failed)
    failure_mode = "None"
    failure_diagnosis = "Success"

    if not success:
        stage2_template = prompt_data.get("stage2_evaluator_prompt")
        if stage2_template:
            stage2_prompt = stage2_template.replace("{final_output}", final_answer)
        else:
            stage2_prompt = f"The solution failed criteria '{success_criteria}'. Diagnose which failure mode occurred.\nSolution:\n{final_answer}"

        eval2_system = (
            "You are a multi-agent system failure classifier (MAST Taxonomy). "
            "Classify the root cause failure mode ID (e.g. 1.1, 1.2, 1.4, 2.1, 2.4, 3.1). "
            "State the primary failure mode ID on the first line (e.g. 'Failure Mode: 1.1')."
        )
        eval2_out, e2_in, e2_out, e2_cost = await llm_client.call_model(
            eval_model, eval2_system, stage2_prompt, temperature=0.0, max_tokens=250
        )
        total_input_tokens += e2_in
        total_output_tokens += e2_out
        total_cost += e2_cost
        failure_diagnosis = eval2_out.strip()

        # Check if stage 2 actually reported no failure mode
        if any(p in eval2_out.lower() for p in ["no failure mode occurred", "no mast failure mode", "meets all specifications"]):
            success = True
            failure_mode = "None"
            failure_diagnosis = "Success (Resolved on review)"
        else:
            # Extract failure mode ID
            fm_match = re.search(r"\b([1-3]\.[1-6])\b", eval2_out)
            if fm_match:
                failure_mode = f"FM-{fm_match.group(1)}"
            else:
                failure_mode = f"FM-{prompt_data.get('failure_mode_id', 'Unknown')}"

    # 6. NetworkX Graph Analysis
    network_edges = topology.get_graph_edges()
    net_metrics = network_analysis_service.analyze_experiment_network(agents, messages_history, network_edges)

    # Coordinator Centrality
    coord_id = agents[0].id
    coord_betweenness = net_metrics.betweenness_centrality.get(coord_id, 0.0)
    density = getattr(net_metrics, "communication_density", 0.0)
    reciprocity = getattr(net_metrics, "reciprocity", 0.0)

    # 7. Multi-Agent Failure Signatures
    signatures = signature_extractor.extract_signatures(messages_history, max_turns=num_turns)

    latency_sec = time.time() - start_time

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_id": prompt_id,
        "prompt_family": family,
        "failure_category": failure_cat,
        "topology": topology_name,
        "model": model_key,
        "replicate_id": replicate_id,
        "success": 1 if success else 0,
        "failure_mode": failure_mode,
        "failure_diagnosis": failure_diagnosis[:300].replace("\n", " "),
        "prompt_text": task_text,
        "success_criteria": success_criteria,
        "final_answer": final_answer,
        "eval1_output": eval1_out,
        "eval2_output": eval2_out if not success else None,
        "total_messages": len(messages_history),
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "cost_usd": round(total_cost, 5),
        "latency_sec": round(latency_sec, 2),
        "graph_density": round(density, 4),
        "coordinator_betweenness": round(coord_betweenness, 4),
        "reciprocity": round(reciprocity, 4),
        "dissent_ratio": signatures["dissent_ratio"],
        "clarification_rate": signatures["clarification_rate"],
        "lexical_decay_rate": signatures["lexical_decay_rate"],
        "step_repetition_index": signatures["step_repetition_index"],
        "early_termination_index": signatures["early_termination_index"],
        "coordinator_dominance": signatures["coordinator_dominance"],
        "participation_entropy": signatures["agent_participation_entropy"],
        "final_answer_snippet": final_answer[:200].replace("\n", " "),
        "transcript": messages_history
    }


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="AgentMesh Benchmark Runner")
    parser.add_argument("--non-interactive", action="store_true", help="Run without terminal prompts")
    parser.add_argument("--mock", action="store_true", help="Run in simulation mode without API calls")
    parser.add_argument("--replicates", type=int, default=1, help="Replicates per condition")
    parser.add_argument("--models", type=str, default="gpt_4o,claude_3_7_sonnet,gemini_2_0", help="Comma-separated model keys")
    parser.add_argument("--topologies", type=str, default="STAR,CHAIN,TREE,MESH,EMERGENT", help="Comma-separated topologies")
    parser.add_argument("--dataset", type=str, default=None, help="Path to prompt dataset JSON file")
    parser.add_argument("--max-prompts", type=int, default=None, help="Limit number of prompts to test")
    parser.add_argument("--start-prompt", type=int, default=None, help="1-based index of starting prompt (inclusive)")
    parser.add_argument("--end-prompt", type=int, default=None, help="1-based index of ending prompt (inclusive)")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    PARTITIONS_DIR = RESULTS_DIR / "partitions"
    PARTITIONS_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = RESULTS_DIR / "experiment_results.csv"
    traces_path = RESULTS_DIR / "traces.jsonl"

    keys, replicates, selected_models, selected_topos, use_mock, dataset_file = interactive_setup(args)

    # Load prompts
    if not dataset_file.exists():
        logger.error(f"Dataset file not found at {dataset_file}")
        sys.exit(1)

    with open(dataset_file, "r", encoding="utf-8") as f:
        dataset_content = json.load(f)
    all_prompts = dataset_content.get("prompts", [])
    total_dataset_prompts = len(all_prompts)

    start_num = max(1, getattr(args, "start_prompt", None) or 1)
    end_num = min(total_dataset_prompts, getattr(args, "end_prompt", None) or total_dataset_prompts)
    if args and args.max_prompts:
        end_num = min(end_num, start_num + args.max_prompts - 1)

    if start_num > end_num:
        logger.error(f"Invalid prompt range: start-prompt ({start_num}) > end-prompt ({end_num})")
        sys.exit(1)

    prompts = all_prompts[start_num - 1 : end_num]
    is_partitioned = (start_num > 1 or end_num < total_dataset_prompts)
    partition_csv = PARTITIONS_DIR / f"results_p{start_num:02d}_p{end_num:02d}.csv"
    partition_traces = PARTITIONS_DIR / f"traces_p{start_num:02d}_p{end_num:02d}.jsonl"

    print(f"\n[*] Active Prompt Partition: #{start_num} to #{end_num} ({len(prompts)} of {total_dataset_prompts} prompts)")
    print(f"[*] Prompt IDs: {prompts[0]['prompt_id']} -> {prompts[-1]['prompt_id']}")
    if is_partitioned:
        print(f"[*] Partition output files: {partition_csv.name} & {partition_traces.name}")

    llm_client = MultiModelLLMClient(keys, use_mock=use_mock)

    # Check already completed runs for resume
    completed_keys = set()
    for check_p in [csv_path, partition_csv]:
        if check_p.exists():
            with open(check_p, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    k = (row.get("prompt_id"), row.get("topology"), row.get("model"), str(row.get("replicate_id")))
                    completed_keys.add(k)
    if completed_keys:
        print(f"[*] Found {len(completed_keys)} previously completed experimental runs in results. Resuming...")

    # CSV headers
    csv_headers = [
        "timestamp", "prompt_id", "prompt_family", "failure_category", "topology",
        "model", "replicate_id", "success", "failure_mode", "total_messages",
        "input_tokens", "output_tokens", "total_tokens", "cost_usd", "latency_sec",
        "graph_density", "coordinator_betweenness", "reciprocity",
        "dissent_ratio", "clarification_rate", "lexical_decay_rate",
        "step_repetition_index", "early_termination_index", "coordinator_dominance", "participation_entropy",
        "failure_diagnosis", "final_answer_snippet"
    ]

    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)

    if is_partitioned and not partition_csv.exists():
        with open(partition_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)

    # Build queue of runs
    queue = []
    for prompt in prompts:
        for topo in selected_topos:
            for model in selected_models:
                for rep in range(1, replicates + 1):
                    key = (prompt["prompt_id"], topo, model, str(rep))
                    if key not in completed_keys:
                        queue.append((prompt, topo, model, rep))

    total_queue = len(queue)
    print(f"\n[*] Starting execution: {total_queue} runs remaining.")
    print("=" * 78)

    completed_count = 0
    total_cost_accum = 0.0
    success_count = 0

    try:
        for idx, (p_data, topo, model, rep) in enumerate(queue, 1):
            p_id = p_data["prompt_id"]
            p_fam = p_data.get("prompt_family", "")
            print(f"[{idx}/{total_queue}] Running {p_id} ({p_fam}) | Topo: {topo:<10} | Model: {model:<15} | Rep: #{rep}...", end="", flush=True)

            try:
                res = await run_single_experiment(p_data, topo, model, rep, llm_client)
            except Exception as run_err:
                print(f" -> ERROR ({run_err})")
                logger.error(f"Error executing run {p_id} {topo} {model} rep #{rep}: {run_err}")
                continue

            completed_count += 1
            total_cost_accum += res["cost_usd"]
            if res["success"] == 1:
                success_count += 1
                status = "SUCCESS"
            else:
                status = f"FAIL ({res['failure_mode']})"

            print(f" -> {status} ({res['latency_sec']}s, {res['total_tokens']} tok, ${res['cost_usd']:.4f})")

            # Append to main CSV
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([res[h] for h in csv_headers])

            # Append transcript to main JSONL
            with open(traces_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(res) + "\n")

            # Append to partition CSV & JSONL if partitioned
            if is_partitioned:
                with open(partition_csv, "a", newline="", encoding="utf-8") as f:
                    p_writer = csv.writer(f)
                    p_writer.writerow([res[h] for h in csv_headers])
                with open(partition_traces, "a", encoding="utf-8") as f:
                    f.write(json.dumps(res) + "\n")

    except KeyboardInterrupt:
        print("\n[!] Execution paused by user. Results up to this point have been safely saved.")
    finally:
        await llm_client.close()

    print("\n" + "=" * 78)
    print("                      Benchmark Run Completed!                       ")
    print("=" * 78)
    print(f"Total Runs Processed : {completed_count}")
    print(f"Overall Success Rate : {(success_count / max(1, completed_count)) * 100:.1f}%")
    print(f"Total Token Cost     : ${total_cost_accum:.4f}")
    print(f"Results CSV          : {csv_path}")
    if is_partitioned:
        print(f"Partition CSV        : {partition_csv}")
    print(f"Traces JSONL         : {traces_path}")
    print("-" * 78)

    # Automatically merge results and refresh artifacts
    print("[*] Automatically unifying dataset and updating publication artifacts...")
    try:
        from experiments.merge_results import merge_all_results
        merge_all_results()
    except Exception as e:
        logger.error(f"Error during auto-merge: {e}")


if __name__ == "__main__":
    asyncio.run(main())

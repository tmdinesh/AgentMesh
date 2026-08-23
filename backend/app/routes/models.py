from typing import List, Dict, Any
from fastapi import APIRouter
from app.config import settings
from app.services.llm_service import llm_service

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("/config")
def get_models_configuration() -> Dict[str, Any]:
    """Returns the active configuration and assigned LLMs for all 6 agents."""
    agent_configs = settings.get_all_agent_configs()
    return {
        "is_mock_enabled": settings.is_mock_enabled,
        "global_fallback_model": settings.LLM_MODEL,
        "agents": [
            {
                "agent_id": cfg.agent_id,
                "role": cfg.role,
                "provider": cfg.provider,
                "model": cfg.model,
                "base_url": cfg.base_url,
                "is_local": cfg.is_local,
                "has_api_key": bool(cfg.api_key and cfg.api_key.strip() != ""),
                "description": cfg.description,
                "temperature": cfg.temperature
            }
            for cfg in agent_configs
        ]
    }


@router.get("/status")
async def get_models_status() -> Dict[str, Any]:
    """Checks live connectivity to Ollama and reports readiness of all 6 agent endpoints."""
    endpoints_status = await llm_service.check_all_endpoints()
    ollama_ready = any(ep["is_local"] and ep.get("reachable") for ep in endpoints_status)
    cloud_configured_count = sum(1 for ep in endpoints_status if not ep["is_local"] and ep.get("has_key"))

    return {
        "mock_mode": settings.is_mock_enabled,
        "ollama_ready": ollama_ready,
        "cloud_configured_count": cloud_configured_count,
        "total_agents": len(endpoints_status),
        "agents": endpoints_status
    }

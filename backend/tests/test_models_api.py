import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest.mark.asyncio
async def test_models_config_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/models/config")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 6
        
        # Check Agent 1 (Coordinator) default
        agent_1 = data["agents"][0]
        assert agent_1["agent_id"] == "agent_1"
        assert agent_1["role"] == "Coordinator"
        assert agent_1["provider"] == "aicredits"
        assert agent_1["model"] == "deepseek/deepseek-v3.2"
        
        # Check Agent 6 (Final Reviewer - Ollama Local)
        agent_6 = data["agents"][5]
        assert agent_6["agent_id"] == "agent_6"
        assert agent_6["role"] == "Final Reviewer"
        assert agent_6["is_local"] is True
        assert agent_6["provider"] == "ollama"


@pytest.mark.asyncio
async def test_models_status_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/models/status")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 6
        assert "total_agents" in data
        assert data["total_agents"] == 6

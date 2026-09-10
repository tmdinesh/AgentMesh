import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db, SessionLocal
from app.models.task import Task

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_get_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) > 0
    assert any(t["category"] == "Reasoning" for t in tasks)


def test_run_star_experiment():
    payload = {
        "task_id": "reasoning_01_knights_knaves",
        "topology": "STAR",
        "num_agents": 4,
        "max_turns": 4,
        "use_mock": True
    }
    response = client.post("/api/experiments", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["topology"] == "STAR"
    assert data["num_agents"] == 4
    assert len(data["messages"]) > 0
    assert "network_metrics" in data

    exp_id = data["id"]
    # Test details endpoint
    detail_res = client.get(f"/api/experiments/{exp_id}")
    assert detail_res.status_code == 200

    # Test network endpoint
    net_res = client.get(f"/api/experiments/{exp_id}/network")
    assert net_res.status_code == 200
    assert "nodes" in net_res.json()


def test_run_chain_mesh_and_unconstrained_experiments():
    # Chain
    chain_res = client.post("/api/experiments", json={
        "task_id": "reasoning_02_river_crossing",
        "topology": "CHAIN",
        "num_agents": 5,
        "max_turns": 5,
        "use_mock": True
    })
    assert chain_res.status_code == 200
    assert chain_res.json()["topology"] == "CHAIN"

    # Mesh
    mesh_res = client.post("/api/experiments", json={
        "task_id": "qa_01_space_telescope",
        "topology": "MESH",
        "num_agents": 6,
        "max_turns": 6,
        "use_mock": True
    })
    assert mesh_res.status_code == 200
    assert mesh_res.json()["topology"] == "MESH"

    # Unconstrained / Emergent
    emergent_res = client.post("/api/experiments", json={
        "task_id": "reasoning_03_scheduling_constraint",
        "topology": "UNCONSTRAINED",
        "num_agents": 6,
        "max_turns": 6,
        "use_mock": True
    })
    assert emergent_res.status_code == 200
    assert emergent_res.json()["topology"] == "UNCONSTRAINED"
    assert len(emergent_res.json()["messages"]) > 0


def test_results_summary_and_statistics():
    summary_res = client.get("/api/results/summary")
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert data["total_experiments"] >= 4

    stats_res = client.get("/api/results/statistics")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "chi_square_analysis" in stats_data


def test_results_export_research_dataset():
    """Verify GET /api/results/export returns self-contained research paper dataset."""
    res = client.get("/api/results/export")
    assert res.status_code == 200
    data = res.json()
    assert "dataset_title" in data
    assert "schema_version" in data
    assert "generated_at" in data
    assert "total_experiments" in data
    assert "statistical_tests" in data
    assert "topology_summaries" in data
    assert "trials" in data
    assert data["total_experiments"] >= 4
    assert len(data["trials"]) >= 4

    first_exp = data["trials"][0]
    assert "experiment_id" in first_exp
    assert "topology" in first_exp
    assert "success" in first_exp
    assert "network_metrics" in first_exp
    assert "messages" in first_exp




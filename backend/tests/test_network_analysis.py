import pytest
from app.services.agent_service import create_agent_team
from app.services.network_analysis import network_analysis_service


def test_network_analysis_calculation():
    agents = create_agent_team(num_agents=4)
    messages = [
        {"sender_id": "agent_1", "receiver_id": "agent_2"},
        {"sender_id": "agent_2", "receiver_id": "agent_1"},
        {"sender_id": "agent_1", "receiver_id": "agent_3"},
        {"sender_id": "agent_3", "receiver_id": "agent_1"},
        {"sender_id": "agent_1", "receiver_id": "agent_4"},
    ]
    edges = [("agent_1", "agent_2"), ("agent_2", "agent_1"), ("agent_1", "agent_3"), ("agent_3", "agent_1"), ("agent_1", "agent_4"), ("agent_4", "agent_1")]

    metrics = network_analysis_service.analyze_experiment_network(
        agents=agents,
        messages=messages,
        topology_edges=edges
    )

    assert metrics.total_messages == 5
    assert metrics.messages_per_agent["agent_1"] == 3
    assert metrics.messages_per_agent["agent_2"] == 1
    assert metrics.degrees["agent_1"] > metrics.degrees["agent_4"]
    # Agent 1 (hub) should have highest betweenness centrality
    assert metrics.betweenness_centrality["agent_1"] >= metrics.betweenness_centrality["agent_2"]
    assert len(metrics.nodes) == 4

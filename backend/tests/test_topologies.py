import pytest
from app.services.agent_service import create_agent_team
from app.topologies import StarTopology, ChainTopology, MeshTopology, EmergentTopology


def test_star_topology_permissions():
    agents = create_agent_team(num_agents=5)
    star = StarTopology(agents)

    central_id = "agent_1"
    peripheral_1 = "agent_2"
    peripheral_2 = "agent_3"

    # Central can communicate with peripheral
    assert star.is_allowed_communication(central_id, peripheral_1) is True
    assert star.is_allowed_communication(peripheral_1, central_id) is True

    # Peripheral cannot communicate directly with another peripheral
    assert star.is_allowed_communication(peripheral_1, peripheral_2) is False
    assert star.is_allowed_communication(peripheral_2, peripheral_1) is False

    # Allowed receivers
    assert set(star.get_allowed_receivers(central_id)) == {"agent_2", "agent_3", "agent_4", "agent_5"}
    assert star.get_allowed_receivers(peripheral_1) == [central_id]


def test_chain_topology_permissions():
    agents = create_agent_team(num_agents=5)
    chain = ChainTopology(agents)

    # Sequential: agent_1 -> agent_2 -> agent_3 -> agent_4 -> agent_5 -> agent_1
    assert chain.is_allowed_communication("agent_1", "agent_2") is True
    assert chain.is_allowed_communication("agent_2", "agent_3") is True
    assert chain.is_allowed_communication("agent_5", "agent_1") is True

    # Non-sequential jumps disallowed
    assert chain.is_allowed_communication("agent_1", "agent_3") is False
    assert chain.is_allowed_communication("agent_2", "agent_1") is False

    assert chain.get_allowed_receivers("agent_2") == ["agent_3"]


def test_mesh_topology_permissions():
    agents = create_agent_team(num_agents=4)
    mesh = MeshTopology(agents)

    # All-to-all
    for a in agents:
        for b in agents:
            if a.id != b.id:
                assert mesh.is_allowed_communication(a.id, b.id) is True

    assert len(mesh.get_allowed_receivers("agent_1")) == 3


def test_emergent_topology_permissions():
    agents = create_agent_team(num_agents=6)
    emergent = EmergentTopology(agents)

    assert emergent.name == "UNCONSTRAINED"
    # Unconstrained communication across any distinct pair
    for a in agents:
        for b in agents:
            if a.id != b.id:
                assert emergent.is_allowed_communication(a.id, b.id) is True

    # Full visibility of dialogue
    history = [{"sender_id": "agent_2", "receiver_id": "agent_3", "content": "Proof"}]
    assert len(emergent.filter_visible_messages("agent_1", history)) == 1

    # Turn planning
    plan = emergent.plan_turn(0, [])
    assert len(plan) == 1
    assert plan[0][0].id == "agent_1"

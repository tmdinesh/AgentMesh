from typing import List, Dict, Any
import networkx as nx
from app.topologies.base import AgentInfo
from app.schemas.network import NetworkMetrics, NetworkNode, NetworkEdge


class NetworkAnalysisService:
    """
    Computes communication network metrics and graph structures using NetworkX.
    Calculates: Total messages, Messages per agent, Degree, Betweenness Centrality, Density.
    """

    def analyze_experiment_network(
        self,
        agents: List[AgentInfo],
        messages: List[Dict[str, Any]],
        topology_edges: List[tuple]
    ) -> NetworkMetrics:
        # Construct directed multigraph / weighted directed graph
        G = nx.DiGraph()

        # Add all agent nodes
        for a in agents:
            G.add_node(a.id, name=a.name, role=a.role, is_central=a.is_central)

        # Count message volume per agent and directed edge frequency
        messages_sent: Dict[str, int] = {a.id: 0 for a in agents}
        messages_received: Dict[str, int] = {a.id: 0 for a in agents}
        edge_counts: Dict[tuple, int] = {}

        for msg in messages:
            s = msg.get("sender_id")
            r = msg.get("receiver_id")
            if s in messages_sent:
                messages_sent[s] += 1

            if r in messages_received:
                messages_received[r] += 1
            elif r == "ALL":
                for a in agents:
                    if a.id != s:
                        messages_received[a.id] = messages_received.get(a.id, 0) + 1

            if s and r and s != r and r != "ALL":
                edge_counts[(s, r)] = edge_counts.get((s, r), 0) + 1
            elif s and r == "ALL":
                for a in agents:
                    if a.id != s:
                        edge_counts[(s, a.id)] = edge_counts.get((s, a.id), 0) + 1

        # Add weighted edges to NetworkX DiGraph
        for (u, v), weight in edge_counts.items():
            if G.has_node(u) and G.has_node(v):
                G.add_edge(u, v, weight=weight)

        # NetworkX Metric Calculations
        total_msgs = len(messages)
        n_nodes = len(agents)

        # Degree calculations
        in_degrees = {node: G.in_degree(node) for node in G.nodes()}
        out_degrees = {node: G.out_degree(node) for node in G.nodes()}
        total_degrees = {node: in_degrees[node] + out_degrees[node] for node in G.nodes()}

        # Betweenness Centrality
        try:
            betweenness = nx.betweenness_centrality(G, weight=None, normalized=True)
        except Exception:
            betweenness = {node: 0.0 for node in G.nodes()}

        # Communication Density
        try:
            density = float(nx.density(G))
        except Exception:
            density = 0.0

        # Build Node list for schemas
        nodes_list: List[NetworkNode] = []
        for a in agents:
            nodes_list.append(NetworkNode(
                id=a.id,
                label=a.name,
                role=a.role,
                model_name=a.model_name,
                provider=a.provider,
                is_local=a.is_local,
                degree=total_degrees.get(a.id, 0),
                in_degree=in_degrees.get(a.id, 0),
                out_degree=out_degrees.get(a.id, 0),
                betweenness_centrality=round(betweenness.get(a.id, 0.0), 4),
                messages_sent=messages_sent.get(a.id, 0),
                messages_received=messages_received.get(a.id, 0)
            ))

        # Build Edge list for schemas
        edges_list: List[NetworkEdge] = []
        for (u, v), weight in edge_counts.items():
            edges_list.append(NetworkEdge(
                source=u,
                target=v,
                weight=weight,
                label=f"{weight} msgs"
            ))

        # Also ensure static topology edges are visible even if message count is 0
        existing_edges = set((e.source, e.target) for e in edges_list)
        for (u, v) in topology_edges:
            if (u, v) not in existing_edges and u != v:
                edges_list.append(NetworkEdge(source=u, target=v, weight=0, label="0 msgs"))

        return NetworkMetrics(
            total_messages=total_msgs,
            messages_per_agent=messages_sent,
            degrees=total_degrees,
            in_degrees=in_degrees,
            out_degrees=out_degrees,
            betweenness_centrality={k: round(v, 4) for k, v in betweenness.items()},
            communication_density=round(density, 4),
            graph_type="DiGraph",
            nodes=nodes_list,
            edges=edges_list
        )


network_analysis_service = NetworkAnalysisService()

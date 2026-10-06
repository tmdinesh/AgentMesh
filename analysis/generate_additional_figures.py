"""
AgentMesh Additional Publication Figures Generator
Produces:
1. fig7_topology_architectures.png - Visual graph representation of all 5 communication topologies
2. fig8_evaluation_pipeline.png - The two-stage verification and MAST failure diagnosis framework
3. fig9_latency_token_distributions.png - Empirical token expenditure and latency distributions across topologies
"""

import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
import seaborn as sns
import networkx as nx

RESULTS_DIR = Path("results")
FIGURES_DIR = RESULTS_DIR / "figures"
CSV_PATH = RESULTS_DIR / "experiment_results.csv"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Publication aesthetic settings
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 300,
})


def generate_fig7_topology_architectures():
    """Generates a 5-panel graph diagram of the communication topologies."""
    fig, axes = plt.subplots(1, 5, figsize=(18, 3.8))
    nodes = ["A1\n(Coord)", "A2\n(Solver)", "A3\n(Critic)", "A4\n(Fact)", "A5\n(Alt)", "A6\n(QA)"]
    node_colors = ["#2b5c8f", "#3c8dbc", "#00a65a", "#f39c12", "#dd4b39", "#605ca8"]
    
    # 1. STAR
    ax = axes[0]
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n)
    for n in nodes[1:]:
        G.add_edge(nodes[0], n)
        G.add_edge(n, nodes[0])
    
    pos = {nodes[0]: (0, 0)}
    angles = np.linspace(0, 2*np.pi, 5, endpoint=False)
    for i, a in enumerate(angles):
        pos[nodes[i+1]] = (np.cos(a), np.sin(a))
    
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1100, edgecolors="black", linewidths=1.2)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#444444", width=1.5, arrowsize=14, arrowstyle="<->")
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7.5, font_color="white", font_weight="bold")
    ax.set_title("(a) Star (Hub-and-Spoke)\n$C_B \\to 1.0, D=0.034$", weight="bold", fontsize=11, pad=10)
    ax.axis("off")

    # 2. CHAIN
    ax = axes[1]
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n)
    for i in range(len(nodes) - 1):
        G.add_edge(nodes[i], nodes[i+1])
    
    pos = {nodes[i]: (0, -i * 0.7) for i in range(len(nodes))}
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1000, edgecolors="black", linewidths=1.2)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#444444", width=1.8, arrowsize=16, arrowstyle="-|>")
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7.5, font_color="white", font_weight="bold")
    ax.set_title("(b) Chain (Sequential)\n$\\mathcal{R} = 0, D=0.036$", weight="bold", fontsize=11, pad=10)
    ax.axis("off")

    # 3. TREE
    ax = axes[2]
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n)
    # A1 -> A2, A3; A2 -> A4, A5; A3 -> A6
    edges_tree = [
        (nodes[0], nodes[1]), (nodes[1], nodes[0]),
        (nodes[0], nodes[2]), (nodes[2], nodes[0]),
        (nodes[1], nodes[3]), (nodes[3], nodes[1]),
        (nodes[1], nodes[4]), (nodes[4], nodes[1]),
        (nodes[2], nodes[5]), (nodes[5], nodes[2]),
    ]
    G.add_edges_from(edges_tree)
    pos = {
        nodes[0]: (0.0, 1.0),
        nodes[1]: (-0.8, 0.0),
        nodes[2]: (0.8, 0.0),
        nodes[3]: (-1.3, -1.0),
        nodes[4]: (-0.3, -1.0),
        nodes[5]: (0.8, -1.0)
    }
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1000, edgecolors="black", linewidths=1.2)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#444444", width=1.5, arrowsize=14, arrowstyle="<->")
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7.5, font_color="white", font_weight="bold")
    ax.set_title("(c) Tree (Hierarchical)\nBranch Isolation, $D=0.057$", weight="bold", fontsize=11, pad=10)
    ax.axis("off")

    # 4. MESH
    ax = axes[3]
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n)
    for i in range(len(nodes)):
        for j in range(len(nodes)):
            if i != j:
                G.add_edge(nodes[i], nodes[j])
    angles = np.linspace(0, 2*np.pi, 6, endpoint=False)
    pos = {nodes[i]: (np.cos(angles[i]), np.sin(angles[i])) for i in range(6)}
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1000, edgecolors="black", linewidths=1.2)
    nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#888888", width=1.0, arrowsize=10, arrowstyle="<->", alpha=0.7)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7.5, font_color="white", font_weight="bold")
    ax.set_title("(d) Mesh (All-to-All)\n$O(N^2), D=0.086$", weight="bold", fontsize=11, pad=10)
    ax.axis("off")

    # 5. EMERGENT
    ax = axes[4]
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n)
    # Active on-demand routes
    active_edges = [
        (nodes[0], nodes[1]), (nodes[1], nodes[3]),
        (nodes[3], nodes[2]), (nodes[2], nodes[0]),
        (nodes[0], nodes[5])
    ]
    inactive_edges = [
        (nodes[1], nodes[4]), (nodes[4], nodes[5]),
        (nodes[2], nodes[4])
    ]
    G.add_edges_from(active_edges)
    pos = {nodes[i]: (np.cos(angles[i]), np.sin(angles[i])) for i in range(6)}
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=1000, edgecolors="black", linewidths=1.2)
    nx.draw_networkx_edges(G, pos, ax=ax, edgelist=active_edges, edge_color="#2b5c8f", width=2.0, arrowsize=15, arrowstyle="-|>")
    nx.draw_networkx_edges(G, pos, ax=ax, edgelist=inactive_edges, edge_color="#cccccc", width=1.0, style="dashed", arrowsize=10, arrowstyle="-|>")
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7.5, font_color="white", font_weight="bold")
    ax.set_title("(e) Emergent (Dynamic)\nAdaptive Routing, $D=0.062$", weight="bold", fontsize=11, pad=10)
    ax.axis("off")

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig7_topology_architectures.png"
    plt.savefig(out_path)
    plt.close()
    print(f"[+] Saved {out_path}")


def generate_fig8_evaluation_pipeline():
    """Generates a publication-grade flowchart diagram of the Two-Stage evaluation pipeline."""
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.5)
    ax.axis("off")

    # Style helper
    def draw_box(x, y, w, h, text, color, title="", title_color="black"):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15", facecolor=color, edgecolor="#222222", linewidth=1.2)
        ax.add_patch(rect)
        if title:
            ax.text(x + w/2, y + h - 0.25, title, ha="center", va="center", weight="bold", fontsize=9.5, color=title_color)
            ax.text(x + w/2, y + (h - 0.25)/2, text, ha="center", va="center", fontsize=8.2, color="#222222")
        else:
            ax.text(x + w/2, y + h/2, text, ha="center", va="center", weight="bold", fontsize=9, color="#222222")

    def draw_arrow(x1, y1, x2, y2, label=""):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=1.6, color="#333333", mutation_scale=14))
        if label:
            ax.text((x1 + x2)/2, (y1 + y2)/2 + 0.12, label, ha="center", va="bottom", fontsize=7.8, weight="bold", color="#444444")

    # 1. Benchmark Task Input
    draw_box(0.3, 1.4, 2.0, 1.8,
             "70 Curated Tasks\n- FC1 (Specification)\n- FC2 (Coordination)\n- FC3 (Verification)\n[Cemri et al., 2025]",
             "#e8f4f8", title="Benchmark Task ($T_k$)", title_color="#1a5276")

    # 2. Topology Graph Router
    draw_box(2.8, 1.4, 2.2, 1.8,
             "Enforces Graph $G=(V, E)$:\n- STAR, CHAIN\n- TREE, MESH\n- EMERGENT\nFilters message visibility",
             "#fcf3cf", title="Topology Router", title_color="#b7950b")

    # 3. Multi-Agent Ensemble
    draw_box(5.5, 1.4, 2.2, 1.8,
             "Heterogeneous Team:\nA1: Coordinator (GPT-OSS)\nA2: Solver (Qwen3)\nA3: Critic (DeepSeek-V3)\nA4-A6: Fact, Alt, QA",
             "#eafaf1", title="Agent Deliberation", title_color="#1e8449")

    # Connect pipeline stages
    draw_arrow(2.3, 2.3, 2.8, 2.3)
    draw_arrow(5.0, 2.3, 5.5, 2.3)

    # 4. Stage 1: Correctness Verification
    draw_box(8.2, 2.5, 2.5, 1.6,
             "Independent LLM Judge\n($T = 0.2$)\nStrict rubric matching\nPass ($S=1$) or Fail ($S=0$)",
             "#d5f5e3", title="Stage 1: Verification", title_color="#196f3d")
    draw_arrow(7.7, 2.6, 8.2, 3.2, label="Final Output")

    # 5. Stage 2: Diagnostic Taxonomy & Signatures
    draw_box(8.2, 0.4, 2.5, 1.8,
             "Multi-Turn MAST Classifier:\nDiagnoses FM-1.1 - FM-3.3\nExtracts 6 Failure Signatures:\nDissent, Clarif, Decay,\nRepetition, Dominance",
             "#fadbd8", title="Stage 2: Diagnosis", title_color="#922b21")
    draw_arrow(7.7, 2.0, 8.2, 1.3, label="If Fail ($S=0$)")

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig8_evaluation_pipeline.png"
    plt.savefig(out_path)
    plt.close()
    print(f"[+] Saved {out_path}")


def generate_fig9_latency_token_distributions():
    """Plots empirical token expenditure and execution latency distributions across topologies."""
    if not CSV_PATH.exists():
        print("[-] CSV not found for Figure 9.")
        return

    df = pd.read_csv(CSV_PATH)
    if len(df) == 0:
        return

    order_topos = ["TREE", "EMERGENT", "STAR", "MESH", "CHAIN"]
    present_topos = [t for t in order_topos if t in df["topology"].unique()]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    # Token expenditure boxplot
    palette = ["#2ecc71", "#3498db", "#f39c12", "#9b59b6", "#e74c3c"]
    sns.boxplot(data=df, x="topology", y="total_tokens", order=present_topos, ax=ax1, palette=palette, width=0.55)
    sns.stripplot(data=df, x="topology", y="total_tokens", order=present_topos, ax=ax1, color="black", alpha=0.3, jitter=0.2, size=3.5)
    ax1.set_title("(a) Communication Overhead (Tokens per Task)", weight="bold", fontsize=11)
    ax1.set_xlabel("Communication Network Topology")
    ax1.set_ylabel("Total Tokens Consumed")

    # Latency boxplot
    sns.boxplot(data=df, x="topology", y="latency_sec", order=present_topos, ax=ax2, palette=palette, width=0.55)
    sns.stripplot(data=df, x="topology", y="latency_sec", order=present_topos, ax=ax2, color="black", alpha=0.3, jitter=0.2, size=3.5)
    ax2.set_title("(b) Deliberation Wall-Clock Latency (Seconds)", weight="bold", fontsize=11)
    ax2.set_xlabel("Communication Network Topology")
    ax2.set_ylabel("Latency (Seconds)")

    plt.tight_layout()
    out_path = FIGURES_DIR / "fig9_latency_token_distributions.png"
    plt.savefig(out_path)
    plt.close()
    print(f"[+] Saved {out_path}")


def main():
    print("[*] Generating additional publication figures...")
    generate_fig7_topology_architectures()
    generate_fig8_evaluation_pipeline()
    generate_fig9_latency_token_distributions()
    print("[*] All additional figures successfully generated!")


if __name__ == "__main__":
    main()

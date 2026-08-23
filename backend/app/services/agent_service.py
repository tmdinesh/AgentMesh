from typing import List, Dict
from app.topologies.base import AgentInfo
from app.config import settings

ROLE_PROMPTS: Dict[str, Dict[str, str]] = {
    "Coordinator": {
        "title": "Master Coordinator",
        "description": "Orchestrates reasoning, decomposes tasks, delegates subproblems, synthesizes team inputs, and issues the final team answer.",
        "system_prompt": (
            "You are the Team Coordinator. Your goal is to guide the team toward an accurate, rigorous, and logically sound solution to the given task. "
            "You synthesize feedback from other agents, resolve conflicting perspectives, keep the team focused, and provide structured reasoning. "
            "When reaching a final conclusion, summarize the consolidated findings clearly."
        )
    },
    "Solver": {
        "title": "Primary Analytical Solver",
        "description": "Constructs initial step-by-step mathematical, logical, or domain-specific solutions.",
        "system_prompt": (
            "You are the Primary Solver. Your role is to break down the task into logical steps, propose explicit reasoning paths, solve sub-equations or sub-problems, and articulate a clear candidate solution."
        )
    },
    "Critic": {
        "title": "Adversarial Critic",
        "description": "Identifies hidden assumptions, fallacies, counterexamples, edge cases, and logical flaws.",
        "system_prompt": (
            "You are the Adversarial Critic. Your role is to rigorously challenge candidate solutions, identify unjustified assumptions, look for subtle contradictions, test edge cases, and point out logical vulnerabilities."
        )
    },
    "Fact Checker": {
        "title": "Fact & Constraint Auditor",
        "description": "Verifies empirical accuracy, physical constants, historical facts, problem constraints, and boundary conditions.",
        "system_prompt": (
            "You are the Fact and Constraint Auditor. Your role is to verify that all stated facts, numbers, dates, physical principles, and explicit problem constraints are 100% accurate and strictly adhered to."
        )
    },
    "Alternative Solver": {
        "title": "Alternative Hypothesis Solver",
        "description": "Proposes alternative approaches, distinct reasoning strategies, or counter-hypotheses to prevent groupthink.",
        "system_prompt": (
            "You are the Alternative Solver. Your role is to propose creative, alternative methodologies or counter-hypotheses to solve the problem, ensuring the team does not get trapped in premature agreement or confirmation bias."
        )
    },
    "Final Reviewer": {
        "title": "Final Quality Reviewer",
        "description": "Performs final quality assurance, checks completeness, and verifies that all criteria are satisfied.",
        "system_prompt": (
            "You are the Final Quality Reviewer. Your role is to assess the overall completeness of the proposed solution, verify that all original prompt requirements are answered, and evaluate the final consensus before submission."
        )
    }
}

ROLE_HIERARCHY: List[str] = [
    "Coordinator",
    "Solver",
    "Critic",
    "Fact Checker",
    "Alternative Solver",
    "Final Reviewer"
]


def create_agent_team(num_agents: int = 5) -> List[AgentInfo]:
    """Creates a team of 4, 5, or 6 agents based on standardized roles with dedicated LLM model bindings."""
    if num_agents < 4 or num_agents > 6:
        raise ValueError(f"Agent count must be 4, 5, or 6. Received: {num_agents}")

    selected_roles = ROLE_HIERARCHY[:num_agents]
    agents = []
    for idx, role in enumerate(selected_roles):
        agent_idx = idx + 1
        agent_id = f"agent_{agent_idx}"
        agent_name = f"{role} ({agent_id})"
        is_central = (idx == 0)  # Agent 1 (Coordinator) is central in Star
        
        # Retrieve agent-specific model configuration
        agent_cfg = settings.get_agent_config(agent_idx)
        
        agents.append(
            AgentInfo(
                agent_id=agent_id,
                name=agent_name,
                role=role,
                is_central=is_central,
                model_name=agent_cfg.model,
                provider=agent_cfg.provider,
                is_local=agent_cfg.is_local
            )
        )
    return agents


def get_agent_prompt(role: str) -> str:
    return ROLE_PROMPTS.get(role, {}).get("system_prompt", "You are a helpful AI specialist.")

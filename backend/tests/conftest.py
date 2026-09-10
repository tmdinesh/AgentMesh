import os
import sys
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

# Ensure backend directory is in sys.path
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


@pytest.fixture(autouse=True)
def mock_llm_for_tests(monkeypatch):
    """
    Ensures that LiveBackendLLMClient in actor_system and llm_service
    generate deterministic, specialized responses during test executions
    without making external paid API requests or failing on missing keys.
    """
    from app.topologies.actor_system import LiveBackendLLMClient
    from app.services.llm_service import llm_service

    def test_safe_call(self, system: str, user: str) -> str:
        s_lower = (system or "").lower()
        u_lower = (user or "").lower()

        # Routing decision prompt
        if "route this task" in s_lower:
            if any(k in u_lower for k in ["code", "python", "string", "function", "reverse", "fizzbuzz"]):
                return "coding"
            if any(k in u_lower for k in ["math", "equation", "differential", "integral", "calculate"]):
                return "math"
            if any(k in u_lower for k in ["critic", "audit", "contradiction"]):
                return "critic"
            if any(k in u_lower for k in ["fact", "premise", "deduction"]):
                return "fact_checker"
            return "reasoning"

        # Benchmark Judge prompt (expects JSON)
        if "judge" in s_lower or "is_correct" in s_lower or "academic benchmark" in s_lower:
            if "syntaxerror" in u_lower or "invalid" in u_lower or "contradiction" in u_lower or "wrong" in u_lower:
                return '{"is_correct": false, "reason": "Evaluation identified defect."}'
            return '{"is_correct": true, "reason": "All criteria satisfied."}'

        # Failure mode classification prompt (expects JSON)
        if "classify the primary failure" in s_lower or ("failure" in s_lower and "classifier" in s_lower):
            return '{"failure_type": "Wrong Final Answer", "reason": "Final answer failed criteria."}'

        # Actor / Stream Validator agent prompt
        if "validate" in s_lower or "validator" in s_lower or "verification" in s_lower:
            if "syntaxerror" in u_lower or "invalid" in u_lower or "contradiction" in u_lower or "wrong" in u_lower:
                return "NO: Evaluation identified defect."
            return "YES: The output logically satisfies all criteria."

        # Specialist generation prompt
        if "coding" in s_lower or "python" in u_lower or "fizzbuzz" in u_lower:
            return "```python\ndef solution(s):\n    return s[::-1]\n# Solution tested and verified\n```"
        if "math" in s_lower or "differential" in u_lower:
            return "y(t) = C * exp(-t). The differential equation is solved accurately."
        if "reasoning" in s_lower or "premise" in u_lower:
            return "Logical deduction: Premise entails conclusion without any contradiction."

        return f"Specialized deliberation step from {getattr(self, 'model', 'agent')} addressing: {user[:60]}"

    async def test_safe_call_async(self, system: str, user: str) -> str:
        return test_safe_call(self, system, user)

    async def mock_call_with_escalation(
        primary_config,
        messages,
        temperature=None,
        max_tokens=800,
        response_format=None,
        use_mock=False
    ):
        last_msg = messages[-1]["content"] if messages else ""
        sys_msg = messages[0]["content"] if len(messages) > 1 else ""
        text = test_safe_call(primary_config, sys_msg, last_msg)
        return text, primary_config.model, primary_config.provider

    monkeypatch.setattr(LiveBackendLLMClient, "call", test_safe_call)
    monkeypatch.setattr(LiveBackendLLMClient, "call_async", test_safe_call_async)
    monkeypatch.setattr(llm_service, "_call_with_escalation", mock_call_with_escalation)

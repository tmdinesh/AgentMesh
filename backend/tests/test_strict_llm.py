import pytest
from app.config import settings
from app.services.llm_service import LLMService, AgentModelConfig


@pytest.mark.asyncio
async def test_strict_mode_missing_api_key_raises_error():
    """Verify that cloud LLM invocations strictly fail when API keys are missing (no mock fallback)."""
    service = LLMService()
    cfg = AgentModelConfig(
        agent_id="test_strict_agent",
        role="Solver",
        provider="aicredits",
        model="openai/gpt-oss-120b",
        base_url="https://api.aicredits.com/v1",
        api_key="",
        is_local=False
    )
    messages = [{"role": "user", "content": "Solve 2+2"}]

    with pytest.raises(ValueError) as exc_info:
        await service.call_llm_endpoint(cfg, messages, use_mock=False)

    assert "Missing API key" in str(exc_info.value)
    assert "AICREDITS_API_KEY" in str(exc_info.value)


@pytest.mark.asyncio
async def test_strict_mode_unreachable_endpoint_raises_error():
    """Verify that unreachable LLM endpoints strictly raise an explicit error."""
    service = LLMService()
    cfg = AgentModelConfig(
        agent_id="test_offline_agent",
        role="Solver",
        provider="ollama",
        model="llama3:latest",
        base_url="http://127.0.0.1:99999",  # Non-existent port
        is_local=True
    )
    messages = [{"role": "user", "content": "Solve 2+2"}]

    with pytest.raises(RuntimeError) as exc_info:
        await service.call_llm_endpoint(cfg, messages, use_mock=False)

    assert "LLM invocation failed" in str(exc_info.value) or "Cannot connect" in str(exc_info.value)


def test_strict_mode_configuration_disabled():
    """Verify global config is_mock_enabled is strictly False."""
    assert settings.is_mock_enabled is False


@pytest.mark.asyncio
async def test_evaluator_strictly_raises_on_llm_failure(monkeypatch):
    """Verify evaluation_service raises RuntimeError if LLM judge fails (no keyword/heuristic bypass)."""
    from app.services.evaluation_service import evaluation_service
    from app.services.llm_service import llm_service

    async def broken_call_llm(*args, **kwargs):
        raise ConnectionError("LLM judge unreachable")

    monkeypatch.setattr(llm_service, "call_llm", broken_call_llm)

    with pytest.raises(RuntimeError) as exc_info:
        await evaluation_service.evaluate_experiment(
            task_question="What is 2+2?",
            expected_answer="4",
            evaluation_criteria="Answer must be 4.",
            final_answer="The answer is 4.",
            dialogue_history=[],
            topology_name="STAR"
        )

    assert "LLM correctness evaluation failed" in str(exc_info.value)
    assert "System strictly relies on LLM" in str(exc_info.value)


@pytest.mark.asyncio
async def test_failure_classifier_strictly_raises_on_llm_failure(monkeypatch):
    """Verify failure_classifier raises RuntimeError if LLM fails (no hardcoded topology fallback)."""
    from app.services.failure_classifier import failure_classifier
    from app.services.llm_service import llm_service

    async def broken_call_llm(*args, **kwargs):
        raise ConnectionError("LLM classifier unavailable")

    monkeypatch.setattr(llm_service, "call_llm", broken_call_llm)

    with pytest.raises(RuntimeError) as exc_info:
        await failure_classifier.classify_failure(
            task_question="What is 2+2?",
            expected_answer="4",
            evaluation_criteria="Answer must be 4.",
            final_answer="The answer is 5.",
            dialogue_history=[],
            topology_name="CHAIN"
        )

    assert "LLM failure classification failed" in str(exc_info.value)
    assert "does not generate synthesized fallback responses" in str(exc_info.value)

import json
import logging
import re
from typing import Dict, Any, Tuple
from app.services.llm_service import llm_service
from app.services.failure_classifier import failure_classifier

logger = logging.getLogger(__name__)


class EvaluationService:
    """
    Two-Stage Evaluation System:
    - Stage 1: Determines correctness (success = True / False) against expected answer and criteria.
    - Stage 2: If incorrect, invokes FailureClassifier to determine primary failure mode.
    """

    async def evaluate_experiment(
        self,
        task_question: str,
        expected_answer: str,
        evaluation_criteria: str,
        final_answer: str,
        dialogue_history: list[Dict[str, Any]],
        topology_name: str
    ) -> Tuple[bool, str, str]:
        """
        Returns:
            success (bool),
            failure_type (str),
            failure_reason (str or None)
        """
        # Stage 1: Evaluate correctness
        is_success = await self._check_correctness(
            task_question=task_question,
            expected_answer=expected_answer,
            evaluation_criteria=evaluation_criteria,
            final_answer=final_answer
        )

        if is_success:
            return True, "No Failure", "All evaluation criteria and expected conclusions were satisfied."

        # Stage 2: Failure classification
        failure_type, failure_reason = await failure_classifier.classify_failure(
            task_question=task_question,
            expected_answer=expected_answer,
            evaluation_criteria=evaluation_criteria,
            final_answer=final_answer,
            dialogue_history=dialogue_history,
            topology_name=topology_name
        )

        return False, failure_type, failure_reason

    async def _check_correctness(
        self,
        task_question: str,
        expected_answer: str,
        evaluation_criteria: str,
        final_answer: str
    ) -> bool:
        """Stage 1: Verify if final answer satisfies expected answer & criteria."""
        if not final_answer or final_answer.strip() == "":
            return False

        # Strict LLM Verification: Must fully rely on LLM judge (zero synthetic/keyword bypass)
        system_prompt = (
            "You are an academic benchmark judge evaluating whether an AI model's final response meets the required criteria.\n"
            "Respond ONLY with JSON in this format: {\"is_correct\": true} or {\"is_correct\": false}"
        )
        user_prompt = (
            f"QUESTION:\n{task_question}\n\n"
            f"EXPECTED ANSWER:\n{expected_answer}\n\n"
            f"EVALUATION CRITERIA:\n{evaluation_criteria}\n\n"
            f"SUBMITTED FINAL ANSWER:\n{final_answer}\n\n"
            "Does the submitted answer satisfy the key factual/logical claims and criteria?"
        )

        try:
            raw_response = await llm_service.call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\n?", "", clean_json)
                clean_json = re.sub(r"\n?```$", "", clean_json)
            data = json.loads(clean_json)
            return bool(data.get("is_correct", False))
        except Exception as e:
            logger.error(f"LLM correctness evaluation error: {e}")
            raise RuntimeError(
                f"LLM correctness evaluation failed: {e}. "
                "System strictly relies on LLM and does not generate simulated or heuristic responses."
            ) from e


evaluation_service = EvaluationService()

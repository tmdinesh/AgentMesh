import json
import logging
import re
from typing import Dict, Any, Tuple
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

ALLOWED_FAILURE_TYPES = [
    "Wrong Final Answer",
    "Hallucination / Unsupported Claim",
    "Contradiction",
    "Premature Agreement",
    "Information Loss"
]


class FailureClassifier:
    """
    Stage 2 Evaluator: Classifies the primary failure mode of an unsuccessful multi-agent run.
    """

    async def classify_failure(
        self,
        task_question: str,
        expected_answer: str,
        evaluation_criteria: str,
        final_answer: str,
        dialogue_history: list[Dict[str, Any]],
        topology_name: str
    ) -> Tuple[str, str]:
        """
        Returns (failure_type, failure_reason).
        """
        transcript_snippet = "\n".join([
            f"[Turn {m.get('turn')}] {m.get('sender_role')} -> {m.get('receiver_role')}: {m.get('content')[:200]}"
            for m in dialogue_history[-10:]
        ])

        system_prompt = (
            "You are an academic evaluator analyzing multi-agent system failures. "
            "Your job is to classify the PRIMARY failure mode into exactly ONE of the following 5 categories:\n"
            "1. 'Wrong Final Answer' - The answer has mathematical, arithmetic, or deduction errors not covered below.\n"
            "2. 'Hallucination / Unsupported Claim' - The team fabricated ungrounded facts, false constants, or nonexistent constraints.\n"
            "3. 'Contradiction' - The final answer or intermediate deductions directly contradict prior proven steps or explicit premises.\n"
            "4. 'Premature Agreement' - Agents hastily accepted an early flawed candidate solution without thorough critique or verification.\n"
            "5. 'Information Loss' - Critical constraints, premises, or intermediate findings were dropped or corrupted across communication hops.\n\n"
            "Respond ONLY with a valid JSON object in this exact format:\n"
            "{\n"
            '  "failure_type": "...",\n'
            '  "reason": "..."\n'
            "}"
        )

        user_prompt = (
            f"TOPOLOGY: {topology_name}\n\n"
            f"TASK QUESTION:\n{task_question}\n\n"
            f"EXPECTED ANSWER:\n{expected_answer}\n\n"
            f"EVALUATION CRITERIA:\n{evaluation_criteria}\n\n"
            f"SUBMITTED FINAL ANSWER:\n{final_answer}\n\n"
            f"RECENT DELIBERATION TRANSCRIPT:\n{transcript_snippet}\n\n"
            "Classify the primary failure mode and explain the root cause in the reason field."
        )

        try:
            raw_response = await llm_service.call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )

            # Clean JSON formatting if wrapped in markdown code blocks
            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\n?", "", clean_json)
                clean_json = re.sub(r"\n?```$", "", clean_json)

            data = json.loads(clean_json)
            f_type = data.get("failure_type", "Wrong Final Answer")
            reason = data.get("reason", "Answer failed to satisfy evaluation criteria.")

            # Validate against allowed types
            if f_type not in ALLOWED_FAILURE_TYPES:
                # Fuzzy match
                matched = next((t for t in ALLOWED_FAILURE_TYPES if t.lower() in f_type.lower()), "Wrong Final Answer")
                f_type = matched

            return f_type, reason

        except Exception as e:
            logger.error(f"Failure classification LLM invocation failed: {e}")
            raise RuntimeError(
                f"LLM failure classification failed: {e}. "
                "System strictly relies on LLM and does not generate synthesized fallback responses."
            ) from e


failure_classifier = FailureClassifier()

"""
AgentMesh Failure Signature Extractor
Extracts quantifiable behavioral, linguistic, and structural signatures
from multi-agent dialogue transcripts that predict and explain failure modes.
"""

import math
import re
from typing import Any, Dict, List


class FailureSignatureExtractor:
    """Extracts empirical signatures characterizing MAST multi-agent failure modes."""

    CRITIQUE_KEYWORDS = {
        "disagree", "incorrect", "wrong", "flaw", "contradiction", "violation",
        "however", "fails", "invalid", "error", "missing", "rejected", "mistake"
    }

    CLARIFICATION_KEYWORDS = {
        "clarify", "clarification", "ambiguous", "unclear", "define",
        "specify", "confirm", "what do you mean", "could you clarify", "?"
    }

    def extract_signatures(self, transcript: List[Dict[str, Any]], max_turns: int = 8) -> Dict[str, float]:
        """
        Extracts multi-agent failure signatures from conversation transcripts:
        - dissent_ratio: Frequency of critical auditing language (low in Premature Agreement)
        - clarification_rate: Density of questions and ambiguity inquiries (low in FC2.2)
        - lexical_decay_rate: Drop in constraint tokens across sequential hops (high in Information Loss)
        - step_repetition_index: Word overlap between consecutive agent messages (high in Step Repetition)
        - early_termination_index: Fraction of unconsumed turns (high in Premature Termination)
        - coordinator_dominance: Proportion of total words produced by agent_1
        """
        if not transcript:
            return {
                "dissent_ratio": 0.0,
                "clarification_rate": 0.0,
                "lexical_decay_rate": 0.0,
                "step_repetition_index": 0.0,
                "early_termination_index": 0.0,
                "coordinator_dominance": 0.0,
                "agent_participation_entropy": 0.0
            }

        total_words = 0
        total_dissent_matches = 0
        total_clarification_matches = 0
        agent_word_counts = {}
        consecutive_overlaps = []

        prev_words = None

        for idx, msg in enumerate(transcript):
            content = str(msg.get("content", "")).lower()
            words = re.findall(r"\b\w+\b", content)
            w_count = len(words)
            total_words += w_count

            sender = msg.get("sender_id", "unknown")
            agent_word_counts[sender] = agent_word_counts.get(sender, 0) + w_count

            # 1. Dissent & Critical Auditing
            for kw in self.CRITIQUE_KEYWORDS:
                total_dissent_matches += content.count(kw)

            # 2. Clarification & Questioning (FC2.2)
            for kw in self.CLARIFICATION_KEYWORDS:
                total_clarification_matches += content.count(kw)

            # 3. Step Repetition (Consecutive Turn Overlap)
            current_word_set = set(words)
            if prev_words and len(current_word_set) > 0 and len(prev_words) > 0:
                intersection = current_word_set.intersection(prev_words)
                union = current_word_set.union(prev_words)
                jaccard = len(intersection) / len(union) if union else 0.0
                consecutive_overlaps.append(jaccard)
            prev_words = current_word_set

        safe_total = max(1, total_words)
        dissent_ratio = round((total_dissent_matches / safe_total) * 100, 3)
        clarification_rate = round((total_clarification_matches / safe_total) * 100, 3)

        # 4. Lexical Decay Rate (first half vs second half message lengths)
        half_idx = len(transcript) // 2
        first_half_words = sum(len(re.findall(r"\b\w+\b", str(m.get("content", "")))) for m in transcript[:max(1, half_idx)])
        second_half_words = sum(len(re.findall(r"\b\w+\b", str(m.get("content", "")))) for m in transcript[half_idx:])
        decay_ratio = 1.0 - (second_half_words / max(1, first_half_words)) if first_half_words > 0 else 0.0
        lexical_decay_rate = round(max(-1.0, min(1.0, decay_ratio)), 3)

        # 5. Step Repetition Index
        step_repetition_index = round(float(sum(consecutive_overlaps) / max(1, len(consecutive_overlaps))), 3)

        # 6. Early Termination Index
        actual_turns = len(set(m.get("turn", 1) for m in transcript))
        early_termination_index = round(max(0.0, (max_turns - actual_turns) / max(1, max_turns)), 3)

        # 7. Coordinator Dominance
        coord_words = agent_word_counts.get("agent_1", 0)
        coordinator_dominance = round(coord_words / safe_total, 3)

        # 8. Shannon Participation Entropy across agents
        entropy = 0.0
        for count in agent_word_counts.values():
            if count > 0:
                p = count / safe_total
                entropy -= p * math.log2(p)
        max_entropy = math.log2(max(1, len(agent_word_counts))) if len(agent_word_counts) > 1 else 1.0
        normalized_entropy = round(entropy / max(1.0, max_entropy), 3)

        return {
            "dissent_ratio": dissent_ratio,
            "clarification_rate": clarification_rate,
            "lexical_decay_rate": lexical_decay_rate,
            "step_repetition_index": step_repetition_index,
            "early_termination_index": early_termination_index,
            "coordinator_dominance": coordinator_dominance,
            "agent_participation_entropy": normalized_entropy
        }


signature_extractor = FailureSignatureExtractor()

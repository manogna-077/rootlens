"""Disconfirmation evaluation module for assessing whether Evidence satisfies a Hypothesis's disconfirming condition."""

from dataclasses import dataclass
import re
from typing import Any, Dict, Optional, Set, Union
from backend.app.reasoning.evidence_evaluator import EvidenceInput, HypothesisInput


@dataclass
class DisconfirmationResult:
    """Structured result for disconfirmation evaluation."""
    evidence_id: str
    hypothesis_id: str
    disconfirms: bool
    reason: str

    def model_dump(self) -> Dict[str, Any]:
        """Provide model_dump for dictionary serialization."""
        return {
            "evidence_id": self.evidence_id,
            "hypothesis_id": self.hypothesis_id,
            "disconfirms": self.disconfirms,
            "reason": self.reason,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to plain dictionary."""
        return self.model_dump()


class DisconfirmationEvaluator:
    """Evaluates whether supplied evidence specifically satisfies a hypothesis's disconfirming condition."""

    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
        "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did", "not", "no",
        "this", "that", "these", "those", "it", "its", "they", "them", "their"
    }

    @classmethod
    def _tokenize(cls, text: str) -> Set[str]:
        """Extract generic content words (3+ chars, non-stopword)."""
        words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
        return {w for w in words if len(w) >= 3 and w not in cls.STOP_WORDS}

    @classmethod
    def evaluate(
        cls,
        evidence: Union[EvidenceInput, Dict[str, Any]],
        hypothesis: Union[HypothesisInput, Dict[str, Any]],
    ) -> DisconfirmationResult:
        """Evaluate evidence against hypothesis disconfirming condition generically."""
        if isinstance(evidence, dict):
            ev_id = str(evidence.get("id", ""))
            obs = str(evidence.get("observation", ""))
        else:
            ev_id = str(evidence.id)
            obs = str(evidence.observation)

        if isinstance(hypothesis, dict):
            hyp_id = str(hypothesis.get("id", ""))
            disconfirming = str(hypothesis.get("disconfirming_condition", "") or "")
        else:
            hyp_id = str(hypothesis.id)
            disconfirming = str(hypothesis.disconfirming_condition or "")

        disconfirming_clean = disconfirming.strip()

        # 1. Absence of disconfirming condition
        if not disconfirming_clean:
            return DisconfirmationResult(
                evidence_id=ev_id,
                hypothesis_id=hyp_id,
                disconfirms=False,
                reason="Hypothesis has no specified disconfirming condition."
            )

        obs_lower = obs.lower()
        disc_lower = disconfirming_clean.lower()

        # 2. Substring match / direct pattern match
        if disc_lower in obs_lower:
            return DisconfirmationResult(
                evidence_id=ev_id,
                hypothesis_id=hyp_id,
                disconfirms=True,
                reason=f"Observation '{obs}' directly satisfies disconfirming condition '{disconfirming_clean}'."
            )

        # 3. High token / semantic phrase overlap check with disconfirming condition
        disc_tokens = cls._tokenize(disc_lower)
        obs_tokens = cls._tokenize(obs_lower)

        if len(disc_tokens) > 0 and disc_tokens.issubset(obs_tokens):
            return DisconfirmationResult(
                evidence_id=ev_id,
                hypothesis_id=hyp_id,
                disconfirms=True,
                reason=f"Observation '{obs}' contains all key terms of disconfirming condition '{disconfirming_clean}'."
            )

        # 4. Fallback: Evidence does not satisfy disconfirming condition
        return DisconfirmationResult(
            evidence_id=ev_id,
            hypothesis_id=hyp_id,
            disconfirms=False,
            reason=f"Observation '{obs}' does not satisfy disconfirming condition '{disconfirming_clean}'."
        )


def evaluate_disconfirmation(
    evidence: Union[EvidenceInput, Dict[str, Any]],
    hypothesis: Union[HypothesisInput, Dict[str, Any]],
) -> DisconfirmationResult:
    """Convenience helper function for disconfirmation evaluation."""
    return DisconfirmationEvaluator.evaluate(evidence, hypothesis)

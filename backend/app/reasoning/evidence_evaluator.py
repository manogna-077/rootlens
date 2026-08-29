"""Generic evidence evaluation module for evaluating Evidence against Hypotheses."""

from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Union


class AssessmentType(str, Enum):
    """Allowed classification values for evidence assessment."""
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


@dataclass
class EvidenceAssessment:
    """Output contract for evidence evaluation against a hypothesis."""
    evidence_id: str
    hypothesis_id: str
    assessment: AssessmentType
    reason: str

    def model_dump(self) -> Dict[str, Any]:
        """Provide model_dump for compatibility with dict serialization."""
        return {
            "evidence_id": self.evidence_id,
            "hypothesis_id": self.hypothesis_id,
            "assessment": self.assessment.value if isinstance(self.assessment, Enum) else self.assessment,
            "reason": self.reason,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to plain dictionary."""
        return self.model_dump()


@dataclass
class EvidenceInput:
    """Schema representing evidence observed fact."""
    id: str
    incident_id: Optional[str] = None
    timestamp: Optional[str] = None
    source: Optional[str] = None
    event_type: Optional[str] = None
    service: Optional[str] = None
    version: Optional[str] = None
    observation: str = ""
    metadata: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None


@dataclass
class HypothesisInput:
    """Schema representing a hypothesis under evaluation."""
    id: str
    statement: str = ""
    status: Optional[str] = "GENERATED"
    score: Optional[float] = 0.0
    supporting_evidence_ids: Optional[List[str]] = None
    contradicting_evidence_ids: Optional[List[str]] = None
    missing_evidence: Optional[List[str]] = None
    disconfirming_condition: Optional[str] = None
    reasoning: Optional[str] = None


class EvidenceEvaluator:
    """Generic evaluator that assesses relationship between observed evidence and a hypothesis."""

    # Words to ignore when matching generic concepts across text
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
        "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did", "not", "no",
        "this", "that", "these", "those", "it", "its", "they", "them", "their"
    }

    # Generic negation phrases indicating non-occurrence or absence
    NEGATION_PATTERNS = [
        "not ", "no ", "never ", "remained unchanged", "did not", "was not",
        "were not", "failed to", "without", "no recent", "unchanged"
    ]

    @classmethod
    def _tokenize(cls, text: str) -> Set[str]:
        """Extract generic content words (3+ chars, non-stopword)."""
        words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
        return {w for w in words if len(w) >= 3 and w not in cls.STOP_WORDS}

    @classmethod
    def _extract_ngrams(cls, text: str, n: int = 2) -> Set[str]:
        """Extract multi-word sequences to capture generic phrases."""
        words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
        if len(words) < n:
            return set()
        return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}

    @classmethod
    def evaluate(
        cls,
        evidence: Union[EvidenceInput, Dict[str, Any]],
        hypothesis: Union[HypothesisInput, Dict[str, Any]],
    ) -> EvidenceAssessment:
        """Evaluate an Evidence object against a Hypothesis object without domain hardcoding."""
        if isinstance(evidence, dict):
            ev_id = str(evidence.get("id", ""))
            obs = str(evidence.get("observation", ""))
            service = str(evidence.get("service", "")) if evidence.get("service") else ""
        else:
            ev_id = str(evidence.id)
            obs = str(evidence.observation)
            service = str(evidence.service) if evidence.service else ""

        if isinstance(hypothesis, dict):
            hyp_id = str(hypothesis.get("id", ""))
            stmt = str(hypothesis.get("statement", ""))
            disconfirming = str(hypothesis.get("disconfirming_condition", "")) if hypothesis.get("disconfirming_condition") else ""
        else:
            hyp_id = str(hypothesis.id)
            stmt = str(hypothesis.statement)
            disconfirming = str(hypothesis.disconfirming_condition) if hypothesis.disconfirming_condition else ""

        obs_lower = obs.lower()
        stmt_lower = stmt.lower()
        service_lower = service.lower()
        disconfirming_lower = disconfirming.lower()

        # 1. Disconfirming condition check (generic substring / pattern check)
        if disconfirming_lower and disconfirming_lower in obs_lower:
            return EvidenceAssessment(
                evidence_id=ev_id,
                hypothesis_id=hyp_id,
                assessment=AssessmentType.CONTRADICTS,
                reason=f"Observation '{obs}' satisfies disconfirming condition '{disconfirming}'."
            )

        # 2. Tokenize and measure semantic overlap
        obs_tokens = cls._tokenize(obs_lower)
        stmt_tokens = cls._tokenize(stmt_lower)
        common_tokens = obs_tokens.intersection(stmt_tokens)

        # Include service check if specified
        service_match = bool(service_lower and (service_lower in stmt_lower or service_lower.replace("_", " ") in stmt_lower))

        # Check for 2-gram phrase matches between observation and statement
        obs_bigrams = cls._extract_ngrams(obs_lower, 2)
        stmt_bigrams = cls._extract_ngrams(stmt_lower, 2)
        common_bigrams = obs_bigrams.intersection(stmt_bigrams)

        # If there is no shared service, phrase, or term overlap, the evidence is NEUTRAL
        if not service_match and len(common_tokens) == 0 and len(common_bigrams) == 0:
            return EvidenceAssessment(
                evidence_id=ev_id,
                hypothesis_id=hyp_id,
                assessment=AssessmentType.NEUTRAL,
                reason=f"Observation '{obs}' shares no relevant terms or service context with hypothesis '{stmt}'."
            )

        # 3. Check for negation or contradiction in the observation regarding common concepts
        # If the observation asserts that a key concept/phrase in hypothesis did NOT occur or remained unchanged
        is_negated_observation = any(pattern in obs_lower for pattern in cls.NEGATION_PATTERNS)
        is_positive_hypothesis = not any(pattern in stmt_lower for pattern in cls.NEGATION_PATTERNS)

        if is_negated_observation and is_positive_hypothesis and (len(common_tokens) > 0 or len(common_bigrams) > 0):
            return EvidenceAssessment(
                evidence_id=ev_id,
                hypothesis_id=hyp_id,
                assessment=AssessmentType.CONTRADICTS,
                reason=f"Observation '{obs}' indicates non-occurrence or unchanged state for concepts in hypothesis '{stmt}'."
            )

        # 4. Shared context with consistent polarity -> SUPPORTS
        return EvidenceAssessment(
            evidence_id=ev_id,
            hypothesis_id=hyp_id,
            assessment=AssessmentType.SUPPORTS,
            reason=f"Observation '{obs}' aligns with hypothesis '{stmt}' on shared concepts: {sorted(list(common_tokens or common_bigrams))}."
        )


def evaluate_evidence(
    evidence: Union[EvidenceInput, Dict[str, Any]],
    hypothesis: Union[HypothesisInput, Dict[str, Any]],
) -> EvidenceAssessment:
    """Convenience function to evaluate evidence against hypothesis."""
    return EvidenceEvaluator.evaluate(evidence, hypothesis)

"""Evidence Score module implementing the RootLens Evidence Strength rubric.

Evidence Score represents Evidence Strength (NOT probability).

Rubric Weights:
- Temporal precedence: +20
- Mechanistic evidence: +25
- Independent supporting sources: +20
- Version/change correlation: +15
- Contradicting evidence: -20
- Strong alternative explanation: -15
- Historical similarity: +10

Normalized Final Score: 0 - 100
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set, Union
from backend.app.reasoning.evidence_evaluator import AssessmentType, EvidenceAssessment, EvidenceInput, HypothesisInput


@dataclass
class FactorScoreDetail:
    """Breakdown for an individual rubric factor."""
    factor_name: str
    points_awarded: float
    max_or_weight: float
    detected: bool
    explanation: str
    evidence_ids: List[str] = field(default_factory=list)


@dataclass
class EvidenceScoreResult:
    """Result container for Evidence Score calculation."""
    hypothesis_id: str
    raw_score: float
    normalized_score: float
    factors: Dict[str, FactorScoreDetail]
    explanation: str

    def model_dump(self) -> Dict[str, Any]:
        """Provide model_dump for dictionary serialization."""
        return {
            "hypothesis_id": self.hypothesis_id,
            "raw_score": self.raw_score,
            "normalized_score": self.normalized_score,
            "explanation": self.explanation,
            "factors": {
                name: {
                    "factor_name": detail.factor_name,
                    "points_awarded": detail.points_awarded,
                    "max_or_weight": detail.max_or_weight,
                    "detected": detail.detected,
                    "explanation": detail.explanation,
                    "evidence_ids": detail.evidence_ids,
                }
                for name, detail in self.factors.items()
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to plain dictionary."""
        return self.model_dump()


class EvidenceScoreCalculator:
    """Calculates Evidence Strength score based on the RootLens 7-factor rubric."""

    # Rubric Weights
    WEIGHT_TEMPORAL_PRECEDENCE = 20.0
    WEIGHT_MECHANISTIC_EVIDENCE = 25.0
    WEIGHT_INDEPENDENT_SOURCES = 20.0
    WEIGHT_VERSION_CHANGE_CORRELATION = 15.0
    WEIGHT_CONTRADICTING_EVIDENCE = -20.0
    WEIGHT_STRONG_ALTERNATIVE = -15.0
    WEIGHT_HISTORICAL_SIMILARITY = 10.0

    # Theoretical bounds for raw sum
    # Min raw sum: -20 (contradiction) - 15 (alternative) = -35.0
    # Max raw sum: 20 + 25 + 20 + 15 + 10 = +90.0
    MIN_RAW_BOUND = -35.0
    MAX_RAW_BOUND = 90.0

    # Generic keywords indicating mechanistic evidence
    MECHANISTIC_KEYWORDS = {
        "error", "exception", "failed", "failure", "timeout", "spike", "saturation",
        "overflow", "refused", "leak", "bottleneck", "deadlock", "crash", "corrupt",
        "degraded", "latency", "drop", "broken", "trace", "stack", "call"
    }

    # Generic keywords indicating temporal sequence / precedence
    TEMPORAL_KEYWORDS = {
        "before", "prior", "preceded", "preceding", "following", "after", "immediately",
        "timestamp", "sequence", "started at", "occurred at", "first", "timeline"
    }

    # Generic keywords indicating version or change correlation
    VERSION_CHANGE_KEYWORDS = {
        "deploy", "deployment", "version", "commit", "pr", "pull_request", "update",
        "upgrade", "release", "patch", "config", "configuration", "change", "changed"
    }

    # Generic keywords indicating historical similarity
    HISTORICAL_KEYWORDS = {
        "historical", "previous", "prior incident", "recurrence", "past", "known issue",
        "reappeared", "similar incident", "repeated"
    }

    @classmethod
    def _normalize_score(cls, raw_score: float) -> float:
        """Normalize raw score (-35 to +90) to 0-100 scale and clamp strictly."""
        if raw_score <= 0:
            # Shift 0..90 range, maps <=0 raw to proportional 0..20 floor
            normalized = max(0.0, 50.0 + (raw_score * (50.0 / 35.0)))
        else:
            normalized = 50.0 + (raw_score * (50.0 / cls.MAX_RAW_BOUND))
        
        return round(max(0.0, min(100.0, normalized)), 2)

    @classmethod
    def calculate(
        cls,
        hypothesis: Union[HypothesisInput, Dict[str, Any]],
        evidence_items: List[Union[EvidenceInput, Dict[str, Any]]],
        assessments: Optional[List[Union[EvidenceAssessment, Dict[str, Any]]]] = None,
        all_hypotheses: Optional[List[Union[HypothesisInput, Dict[str, Any]]]] = None,
    ) -> EvidenceScoreResult:
        """Calculate Evidence Strength score for a given hypothesis."""
        # Normalize inputs
        if isinstance(hypothesis, dict):
            hyp_id = str(hypothesis.get("id", ""))
            stmt = str(hypothesis.get("statement", ""))
            supp_ids = list(hypothesis.get("supporting_evidence_ids") or [])
            contra_ids = list(hypothesis.get("contradicting_evidence_ids") or [])
        else:
            hyp_id = str(hypothesis.id)
            stmt = str(hypothesis.statement)
            supp_ids = list(hypothesis.supporting_evidence_ids or [])
            contra_ids = list(hypothesis.contradicting_evidence_ids or [])

        ev_map: Dict[str, EvidenceInput] = {}
        for ev in evidence_items:
            if isinstance(ev, dict):
                ev_id = str(ev.get("id", ""))
                ev_obj = EvidenceInput(
                    id=ev_id,
                    source=ev.get("source"),
                    observation=str(ev.get("observation", "")),
                    timestamp=ev.get("timestamp"),
                    event_type=ev.get("event_type"),
                    service=ev.get("service"),
                )
            else:
                ev_id = str(ev.id)
                ev_obj = ev
            if ev_id:
                ev_map[ev_id] = ev_obj

        supp_ev_list = [ev_map[eid] for eid in supp_ids if eid in ev_map]
        contra_ev_list = [ev_map[eid] for eid in contra_ids if eid in ev_map]

        factors: Dict[str, FactorScoreDetail] = {}

        # 1. Temporal precedence (+20)
        temp_ev_ids = []
        for ev in supp_ev_list:
            obs_lower = ev.observation.lower()
            if any(tk in obs_lower for tk in cls.TEMPORAL_KEYWORDS) or ev.timestamp is not None:
                temp_ev_ids.append(ev.id)

        has_temporal = len(temp_ev_ids) > 0
        pts_temporal = cls.WEIGHT_TEMPORAL_PRECEDENCE if has_temporal else 0.0
        factors["temporal_precedence"] = FactorScoreDetail(
            factor_name="Temporal precedence",
            points_awarded=pts_temporal,
            max_or_weight=cls.WEIGHT_TEMPORAL_PRECEDENCE,
            detected=has_temporal,
            explanation=f"Detected temporal sequence evidence: {temp_ev_ids}" if has_temporal else "No temporal precedence evidence found.",
            evidence_ids=temp_ev_ids
        )

        # 2. Mechanistic evidence (+25)
        mech_ev_ids = []
        for ev in supp_ev_list:
            obs_lower = ev.observation.lower()
            if any(mk in obs_lower for mk in cls.MECHANISTIC_KEYWORDS):
                mech_ev_ids.append(ev.id)

        has_mech = len(mech_ev_ids) > 0
        pts_mech = cls.WEIGHT_MECHANISTIC_EVIDENCE if has_mech else 0.0
        factors["mechanistic_evidence"] = FactorScoreDetail(
            factor_name="Mechanistic evidence",
            points_awarded=pts_mech,
            max_or_weight=cls.WEIGHT_MECHANISTIC_EVIDENCE,
            detected=has_mech,
            explanation=f"Detected direct mechanistic evidence: {mech_ev_ids}" if has_mech else "No mechanistic evidence found.",
            evidence_ids=mech_ev_ids
        )

        # 3. Independent supporting sources (+20)
        sources = {ev.source for ev in supp_ev_list if ev.source}
        indep_ev_ids = [ev.id for ev in supp_ev_list if ev.source]
        has_indep = len(sources) >= 2
        pts_indep = cls.WEIGHT_INDEPENDENT_SOURCES if has_indep else (10.0 if len(sources) == 1 else 0.0)
        factors["independent_supporting_sources"] = FactorScoreDetail(
            factor_name="Independent supporting sources",
            points_awarded=pts_indep,
            max_or_weight=cls.WEIGHT_INDEPENDENT_SOURCES,
            detected=has_indep,
            explanation=f"Found {len(sources)} independent evidence sources: {sorted(list(sources))}" if sources else "No independent sources found.",
            evidence_ids=indep_ev_ids
        )

        # 4. Version/change correlation (+15)
        ver_ev_ids = []
        for ev in supp_ev_list:
            obs_lower = ev.observation.lower()
            if any(vk in obs_lower for vk in cls.VERSION_CHANGE_KEYWORDS) or (ev.event_type and "deploy" in ev.event_type.lower()):
                ver_ev_ids.append(ev.id)

        has_ver = len(ver_ev_ids) > 0
        pts_ver = cls.WEIGHT_VERSION_CHANGE_CORRELATION if has_ver else 0.0
        factors["version_change_correlation"] = FactorScoreDetail(
            factor_name="Version/change correlation",
            points_awarded=pts_ver,
            max_or_weight=cls.WEIGHT_VERSION_CHANGE_CORRELATION,
            detected=has_ver,
            explanation=f"Detected version or change correlation evidence: {ver_ev_ids}" if has_ver else "No version/change correlation found.",
            evidence_ids=ver_ev_ids
        )

        # 5. Contradicting evidence (-20)
        has_contra = len(contra_ev_list) > 0
        pts_contra = cls.WEIGHT_CONTRADICTING_EVIDENCE if has_contra else 0.0
        contra_ids_found = [ev.id for ev in contra_ev_list]
        factors["contradicting_evidence"] = FactorScoreDetail(
            factor_name="Contradicting evidence",
            points_awarded=pts_contra,
            max_or_weight=cls.WEIGHT_CONTRADICTING_EVIDENCE,
            detected=has_contra,
            explanation=f"Contradicting evidence detected: {contra_ids_found}" if has_contra else "No contradicting evidence.",
            evidence_ids=contra_ids_found
        )

        # 6. Strong alternative explanation (-15)
        alt_detected = False
        alt_explanation = "No strong alternative hypothesis detected."
        alt_ids = []
        if all_hypotheses:
            for alt in all_hypotheses:
                alt_h_id = alt.get("id") if isinstance(alt, dict) else alt.id
                alt_supp = alt.get("supporting_evidence_ids") if isinstance(alt, dict) else alt.supporting_evidence_ids
                if alt_h_id != hyp_id and alt_supp and len(alt_supp) >= 2:
                    alt_detected = True
                    alt_ids.append(alt_h_id)

        pts_alt = cls.WEIGHT_STRONG_ALTERNATIVE if alt_detected else 0.0
        factors["strong_alternative_explanation"] = FactorScoreDetail(
            factor_name="Strong alternative explanation",
            points_awarded=pts_alt,
            max_or_weight=cls.WEIGHT_STRONG_ALTERNATIVE,
            detected=alt_detected,
            explanation=f"Strong alternative hypotheses detected: {alt_ids}" if alt_detected else alt_explanation,
            evidence_ids=alt_ids
        )

        # 7. Historical similarity (+10)
        hist_ev_ids = []
        for ev in supp_ev_list:
            obs_lower = ev.observation.lower()
            if any(hk in obs_lower for hk in cls.HISTORICAL_KEYWORDS):
                hist_ev_ids.append(ev.id)

        has_hist = len(hist_ev_ids) > 0
        pts_hist = cls.WEIGHT_HISTORICAL_SIMILARITY if has_hist else 0.0
        factors["historical_similarity"] = FactorScoreDetail(
            factor_name="Historical similarity",
            points_awarded=pts_hist,
            max_or_weight=cls.WEIGHT_HISTORICAL_SIMILARITY,
            detected=has_hist,
            explanation=f"Historical similarity evidence detected: {hist_ev_ids}" if has_hist else "No historical similarity evidence found.",
            evidence_ids=hist_ev_ids
        )

        # Compute sum and normalized score
        raw_score = (
            pts_temporal + pts_mech + pts_indep + pts_ver +
            pts_contra + pts_alt + pts_hist
        )

        normalized_score = cls._normalize_score(raw_score)

        explanation = (
            f"Evidence Strength Score: {normalized_score}/100 (Raw points sum: {raw_score:+.1f}). "
            f"Evaluated {len(factors)} rubric factors across {len(supp_ids)} supporting and {len(contra_ids)} contradicting evidence IDs."
        )

        return EvidenceScoreResult(
            hypothesis_id=hyp_id,
            raw_score=raw_score,
            normalized_score=normalized_score,
            factors=factors,
            explanation=explanation
        )


def calculate_evidence_score(
    hypothesis: Union[HypothesisInput, Dict[str, Any]],
    evidence_items: List[Union[EvidenceInput, Dict[str, Any]]],
    assessments: Optional[List[Union[EvidenceAssessment, Dict[str, Any]]]] = None,
    all_hypotheses: Optional[List[Union[HypothesisInput, Dict[str, Any]]]] = None,
) -> EvidenceScoreResult:
    """Convenience function to calculate Evidence Strength score."""
    return EvidenceScoreCalculator.calculate(hypothesis, evidence_items, assessments, all_hypotheses)

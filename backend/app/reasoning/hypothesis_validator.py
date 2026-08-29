"""Hypothesis update validation logic for linking EvidenceAssessment results to Hypothesis state."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from backend.app.reasoning.evidence_evaluator import AssessmentType, EvidenceAssessment, HypothesisInput


class HypothesisStatus(str, Enum):
    """Allowed hypothesis statuses."""
    GENERATED = "GENERATED"
    INVESTIGATING = "INVESTIGATING"
    SUPPORTED = "SUPPORTED"
    WEAKENED = "WEAKENED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class ValidationError(ValueError):
    """Custom error raised when evidence-to-hypothesis update validation fails."""
    pass


class HypothesisValidator:
    """Validates and applies evidence assessment updates to hypotheses."""

    VALID_STATUSES = {status.value for status in HypothesisStatus}
    VALID_ASSESSMENTS = {assessment.value for assessment in AssessmentType}

    @classmethod
    def validate_assessment_update(
        cls,
        hypothesis: Union[HypothesisInput, Dict[str, Any]],
        assessment: Union[EvidenceAssessment, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate an assessment update against a hypothesis before applying.
        
        Raises ValidationError if:
        - evidence_id is missing or empty
        - assessment hypothesis_id does not match hypothesis.id
        - assessment type is invalid
        - hypothesis status is invalid
        """
        # Normalize hypothesis fields
        if isinstance(hypothesis, dict):
            hyp_id = str(hypothesis.get("id", ""))
            status = str(hypothesis.get("status", "GENERATED"))
        else:
            hyp_id = str(hypothesis.id)
            status = str(hypothesis.status or "GENERATED")

        # Normalize assessment fields
        if isinstance(assessment, dict):
            ev_id = str(assessment.get("evidence_id", ""))
            target_hyp_id = str(assessment.get("hypothesis_id", ""))
            asst_value = str(assessment.get("assessment", ""))
        else:
            ev_id = str(assessment.evidence_id)
            target_hyp_id = str(assessment.hypothesis_id)
            asst_value = assessment.assessment.value if isinstance(assessment.assessment, Enum) else str(assessment.assessment)

        # 1. Check evidence_id presence
        if not ev_id or not ev_id.strip():
            raise ValidationError("Assessment is missing a valid evidence_id.")

        # 2. Check hypothesis_id alignment
        if target_hyp_id != hyp_id:
            raise ValidationError(f"Assessment hypothesis_id '{target_hyp_id}' does not match hypothesis id '{hyp_id}'.")

        # 3. Check valid assessment type
        if asst_value not in cls.VALID_ASSESSMENTS:
            raise ValidationError(f"Invalid assessment type '{asst_value}'. Allowed: {cls.VALID_ASSESSMENTS}")

        # 4. Check valid hypothesis status
        if status not in cls.VALID_STATUSES:
            raise ValidationError(f"Invalid hypothesis status '{status}'. Allowed: {cls.VALID_STATUSES}")

        return {
            "evidence_id": ev_id,
            "hypothesis_id": hyp_id,
            "assessment": asst_value,
            "status": status,
        }

    @classmethod
    def apply_update(
        cls,
        hypothesis: Union[HypothesisInput, Dict[str, Any]],
        assessment: Union[EvidenceAssessment, Dict[str, Any]],
    ) -> HypothesisInput:
        """Validate and apply an EvidenceAssessment update to a Hypothesis, returning an updated copy.
        
        Rules:
        - Preserves existing supporting_evidence_ids, contradicting_evidence_ids, missing_evidence, disconfirming_condition.
        - SUPPORTS: adds evidence_id to supporting_evidence_ids (no duplicates). Updates status to SUPPORTED if not CONFIRMED/REJECTED.
        - CONTRADICTS: adds evidence_id to contradicting_evidence_ids (no duplicates). Updates status to WEAKENED if not CONFIRMED/REJECTED.
        - NEUTRAL: preserves state and strength without changing evidence links or score.
        - Does NOT force single-item CONFIRMED or REJECTED.
        """
        # Validate first
        cls.validate_assessment_update(hypothesis, assessment)

        if isinstance(hypothesis, dict):
            hyp_obj = HypothesisInput(
                id=str(hypothesis.get("id", "")),
                statement=str(hypothesis.get("statement", "")),
                status=str(hypothesis.get("status", "INVESTIGATING")),
                score=float(hypothesis.get("score", 0.0) or 0.0),
                supporting_evidence_ids=list(hypothesis.get("supporting_evidence_ids") or []),
                contradicting_evidence_ids=list(hypothesis.get("contradicting_evidence_ids") or []),
                missing_evidence=list(hypothesis.get("missing_evidence") or []),
                disconfirming_condition=hypothesis.get("disconfirming_condition"),
                reasoning=hypothesis.get("reasoning"),
            )
        else:
            hyp_obj = HypothesisInput(
                id=hypothesis.id,
                statement=hypothesis.statement,
                status=hypothesis.status or "INVESTIGATING",
                score=hypothesis.score or 0.0,
                supporting_evidence_ids=list(hypothesis.supporting_evidence_ids or []),
                contradicting_evidence_ids=list(hypothesis.contradicting_evidence_ids or []),
                missing_evidence=list(hypothesis.missing_evidence or []),
                disconfirming_condition=hypothesis.disconfirming_condition,
                reasoning=hypothesis.reasoning,
            )

        if isinstance(assessment, dict):
            ev_id = str(assessment["evidence_id"])
            asst_type = str(assessment["assessment"])
            reason = str(assessment.get("reason", ""))
        else:
            ev_id = str(assessment.evidence_id)
            asst_type = assessment.assessment.value if isinstance(assessment.assessment, Enum) else str(assessment.assessment)
            reason = str(assessment.reason)

        supp_list = hyp_obj.supporting_evidence_ids or []
        contra_list = hyp_obj.contradicting_evidence_ids or []

        # Prevent misplacement
        if asst_type == AssessmentType.SUPPORTS.value:
            if ev_id not in supp_list:
                supp_list.append(ev_id)
            # Update status if in normal active state
            if hyp_obj.status not in {HypothesisStatus.CONFIRMED.value, HypothesisStatus.REJECTED.value}:
                hyp_obj.status = HypothesisStatus.SUPPORTED.value

        elif asst_type == AssessmentType.CONTRADICTS.value:
            if ev_id not in contra_list:
                contra_list.append(ev_id)
            # Update status if in normal active state
            if hyp_obj.status not in {HypothesisStatus.CONFIRMED.value, HypothesisStatus.REJECTED.value}:
                hyp_obj.status = HypothesisStatus.WEAKENED.value

        elif asst_type == AssessmentType.NEUTRAL.value:
            # State and links remain unchanged
            pass

        hyp_obj.supporting_evidence_ids = supp_list
        hyp_obj.contradicting_evidence_ids = contra_list

        # Transparent reasoning update
        entry = f"[{asst_type}] Evidence {ev_id}: {reason}"
        if hyp_obj.reasoning:
            hyp_obj.reasoning = f"{hyp_obj.reasoning}\n{entry}"
        else:
            hyp_obj.reasoning = entry

        return hyp_obj

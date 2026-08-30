"""Verifier module for inspecting and validating investigation contexts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from backend.app.reasoning.disconfirmation import DisconfirmationEvaluator
from backend.app.reasoning.evidence_evaluator import AssessmentType, EvidenceAssessment, EvidenceInput, HypothesisInput
from backend.app.reasoning.hypothesis_validator import HypothesisStatus


class VerificationStatus(str, Enum):
    """Allowed status values for VerificationResult."""
    NOT_STARTED = "NOT_STARTED"
    PASS = "PASS"
    FAIL = "FAIL"


class CausalRelationship(str, Enum):
    """Allowed causal relationship types."""
    PRECEDES = "PRECEDES"
    CORRELATES_WITH = "CORRELATES_WITH"
    SUPPORTS = "SUPPORTS"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    CAUSES = "CAUSES"


@dataclass
class VerificationResult:
    """Output structure returned by the Verifier."""
    status: VerificationStatus
    invalid_claims: List[str] = field(default_factory=list)
    missing_support: List[str] = field(default_factory=list)
    reason: str = ""

    def model_dump(self) -> Dict[str, Any]:
        """Provide model_dump for compatibility with dict serialization."""
        return {
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
            "invalid_claims": list(self.invalid_claims),
            "missing_support": list(self.missing_support),
            "reason": self.reason,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to plain dictionary."""
        return self.model_dump()


@dataclass
class VerificationContext:
    """Input structure representing structured investigation facts under verification."""
    evidence_items: List[Union[EvidenceInput, Dict[str, Any]]] = field(default_factory=list)
    hypotheses: List[Union[HypothesisInput, Dict[str, Any]]] = field(default_factory=list)
    assessments: List[Union[EvidenceAssessment, Dict[str, Any]]] = field(default_factory=list)
    causal_claims: Optional[List[Dict[str, Any]]] = None
    selected_hypothesis_id: Optional[str] = None
    scores: Optional[Dict[str, float]] = None


class Verifier:
    """Deterministic, non-mutating Verifier for RootLens investigation contexts."""

    VALID_ASSESSMENTS = {a.value for a in AssessmentType}
    VALID_STATUSES = {s.value for s in HypothesisStatus} | {f"HypothesisStatus.{s.value}" for s in HypothesisStatus}
    VALID_CAUSAL_RELATIONSHIPS = {c.value for c in CausalRelationship}

    @classmethod
    def verify(cls, context: Union[VerificationContext, Dict[str, Any]]) -> VerificationResult:
        """Inspect and validate an investigation context without mutating input state."""
        # Normalize context fields
        if isinstance(context, dict):
            evidence_raw = context.get("evidence_items") or []
            hypotheses_raw = context.get("hypotheses") or []
            assessments_raw = context.get("assessments") or []
            causal_claims_raw = context.get("causal_claims") or []
            selected_hyp_id = context.get("selected_hypothesis_id")
            scores_raw = context.get("scores")
        else:
            evidence_raw = context.evidence_items or []
            hypotheses_raw = context.hypotheses or []
            assessments_raw = context.assessments or []
            causal_claims_raw = context.causal_claims or []
            selected_hyp_id = context.selected_hypothesis_id
            scores_raw = context.scores

        invalid_claims: List[str] = []
        missing_support: List[str] = []

        # Map evidence items by ID
        evidence_map: Dict[str, EvidenceInput] = {}
        for ev in evidence_raw:
            if isinstance(ev, dict):
                ev_id = str(ev.get("id", ""))
                ev_obj = EvidenceInput(
                    id=ev_id,
                    service=ev.get("service"),
                    observation=str(ev.get("observation", "")),
                )
            else:
                ev_id = str(ev.id)
                ev_obj = ev
            if ev_id:
                evidence_map[ev_id] = ev_obj

        # Map hypotheses by ID
        hypothesis_map: Dict[str, HypothesisInput] = {}
        for hyp in hypotheses_raw:
            if isinstance(hyp, dict):
                hyp_id = str(hyp.get("id", ""))
                hyp_obj = HypothesisInput(
                    id=hyp_id,
                    statement=str(hyp.get("statement", "")),
                    status=str(hyp.get("status", "GENERATED")),
                    score=float(hyp.get("score", 0.0) or 0.0),
                    supporting_evidence_ids=list(hyp.get("supporting_evidence_ids") or []),
                    contradicting_evidence_ids=list(hyp.get("contradicting_evidence_ids") or []),
                    missing_evidence=list(hyp.get("missing_evidence") or []),
                    disconfirming_condition=hyp.get("disconfirming_condition"),
                    reasoning=hyp.get("reasoning"),
                )
            else:
                hyp_id = str(hyp.id)
                hyp_obj = hyp
            if hyp_id:
                hypothesis_map[hyp_id] = hyp_obj

        # Map assessments
        assessment_objs: List[EvidenceAssessment] = []
        for asst in assessments_raw:
            if isinstance(asst, dict):
                asst_ev_id = str(asst.get("evidence_id", ""))
                asst_hyp_id = str(asst.get("hypothesis_id", ""))
                asst_val = str(asst.get("assessment", ""))
                reason = str(asst.get("reason", ""))
            else:
                asst_ev_id = str(asst.evidence_id)
                asst_hyp_id = str(asst.hypothesis_id)
                asst_val = asst.assessment.value if isinstance(asst.assessment, Enum) else str(asst.assessment)
                reason = str(asst.reason)

            # Check assessment value validity
            if asst_val not in cls.VALID_ASSESSMENTS:
                invalid_claims.append(f"Assessment references invalid type '{asst_val}'. Allowed: {cls.VALID_ASSESSMENTS}")
            else:
                assessment_objs.append(EvidenceAssessment(
                    evidence_id=asst_ev_id,
                    hypothesis_id=asst_hyp_id,
                    assessment=AssessmentType(asst_val),
                    reason=reason
                ))

        # 1. Evidence Existence & Status Validation for Hypotheses
        for hyp_id, hyp in hypothesis_map.items():
            # Validate status
            if hyp.status not in cls.VALID_STATUSES:
                invalid_claims.append(f"Hypothesis '{hyp_id}' contains invalid status '{hyp.status}'.")

            # Validate supporting evidence existence
            for ev_id in (hyp.supporting_evidence_ids or []):
                if ev_id not in evidence_map:
                    invalid_claims.append(f"Hypothesis '{hyp_id}' references nonexistent supporting evidence ID '{ev_id}'.")

            # Validate contradicting evidence existence
            for ev_id in (hyp.contradicting_evidence_ids or []):
                if ev_id not in evidence_map:
                    invalid_claims.append(f"Hypothesis '{hyp_id}' references nonexistent contradicting evidence ID '{ev_id}'.")

            # Unsupported claims check: CONFIRMED without supporting evidence
            if hyp.status == HypothesisStatus.CONFIRMED.value and not (hyp.supporting_evidence_ids or []):
                missing_support.append(f"Hypothesis '{hyp_id}' is marked CONFIRMED but has no supporting evidence IDs.")

        # 2. Assessment Alignment Check
        for asst in assessment_objs:
            hyp = hypothesis_map.get(asst.hypothesis_id)
            if not hyp:
                invalid_claims.append(f"Assessment references nonexistent hypothesis ID '{asst.hypothesis_id}'.")
                continue

            if asst.evidence_id not in evidence_map:
                invalid_claims.append(f"Assessment references nonexistent evidence ID '{asst.evidence_id}'.")
                continue

            # Mismatch checks
            if asst.assessment == AssessmentType.SUPPORTS:
                if asst.evidence_id not in (hyp.supporting_evidence_ids or []):
                    missing_support.append(f"Assessment SUPPORTS evidence '{asst.evidence_id}' for hypothesis '{hyp.id}' but it is missing from supporting_evidence_ids.")
            elif asst.assessment == AssessmentType.CONTRADICTS:
                if asst.evidence_id not in (hyp.contradicting_evidence_ids or []):
                    missing_support.append(f"Assessment CONTRADICTS evidence '{asst.evidence_id}' for hypothesis '{hyp.id}' but it is missing from contradicting_evidence_ids.")
            elif asst.assessment == AssessmentType.NEUTRAL:
                if asst.evidence_id in (hyp.supporting_evidence_ids or []):
                    invalid_claims.append(f"NEUTRAL assessment evidence '{asst.evidence_id}' incorrectly placed in supporting_evidence_ids for hypothesis '{hyp.id}'.")
                if asst.evidence_id in (hyp.contradicting_evidence_ids or []):
                    invalid_claims.append(f"NEUTRAL assessment evidence '{asst.evidence_id}' incorrectly placed in contradicting_evidence_ids for hypothesis '{hyp.id}'.")

        # 3. Selected Hypothesis & Alternatives Check
        if selected_hyp_id is not None:
            if selected_hyp_id not in hypothesis_map:
                invalid_claims.append(f"Selected hypothesis ID '{selected_hyp_id}' does not exist in investigation context.")
            else:
                selected_hyp = hypothesis_map[selected_hyp_id]
                if selected_hyp.status == HypothesisStatus.CONFIRMED.value and not (selected_hyp.supporting_evidence_ids or []):
                    missing_support.append(f"Selected hypothesis '{selected_hyp_id}' claims CONFIRMED conclusion but has zero supporting evidence.")

                # Alternatives check: If selected hypothesis claims CONFIRMED certainty, verify other hypotheses were considered
                if selected_hyp.status == HypothesisStatus.CONFIRMED.value and len(hypothesis_map) == 1:
                    missing_support.append(f"Selected hypothesis '{selected_hyp_id}' was CONFIRMED without considering alternative hypotheses.")

        # 4. Disconfirmation Coverage Check
        for hyp_id, hyp in hypothesis_map.items():
            if hyp.disconfirming_condition:
                for ev_id, ev in evidence_map.items():
                    disc_res = DisconfirmationEvaluator.evaluate(ev, hyp)
                    if disc_res.disconfirms:
                        # Material conflict check: Disconfirming evidence exists but hypothesis is CONFIRMED without addressing in reasoning
                        reasoning_text = hyp.reasoning or ""
                        if hyp.status == HypothesisStatus.CONFIRMED.value and ev_id not in reasoning_text:
                            invalid_claims.append(f"Hypothesis '{hyp_id}' is marked CONFIRMED despite satisfying disconfirming condition with evidence '{ev_id}' without addressing it in reasoning.")

        # 5. Causal Claims Validation
        for claim in causal_claims_raw:
            rel = str(claim.get("relationship", ""))
            src_id = str(claim.get("source_id", ""))
            tgt_id = str(claim.get("target_id", ""))
            ev_ids = list(claim.get("evidence_ids") or [])

            if rel not in cls.VALID_CAUSAL_RELATIONSHIPS:
                invalid_claims.append(f"Causal claim from '{src_id}' to '{tgt_id}' contains invalid relationship type '{rel}'.")

            # Check evidence IDs in causal claim exist
            for ev_id in ev_ids:
                if ev_id not in evidence_map:
                    invalid_claims.append(f"Causal claim references nonexistent evidence ID '{ev_id}'.")

            # PRECEDES or CORRELATES_WITH cannot alone prove CAUSES without supporting evidence
            if rel == CausalRelationship.CAUSES.value and not ev_ids:
                missing_support.append(f"Causal claim '{src_id}' CAUSES '{tgt_id}' lacks supporting evidence IDs.")

            if rel in {CausalRelationship.PRECEDES.value, CausalRelationship.CORRELATES_WITH.value}:
                # If a claim asserts PRECEDES or CORRELATES_WITH, ensure it is not treated as CAUSES
                if claim.get("asserts_causation", False):
                    invalid_claims.append(f"Causal claim '{src_id}' to '{tgt_id}' with relationship '{rel}' cannot be treated as proof of CAUSES.")

        # 6. Structural Scores Check (Phase 5: Only basic structural checks)
        if scores_raw is not None:
            if not isinstance(scores_raw, dict):
                invalid_claims.append("Scores structure must be a dictionary mapping hypothesis IDs to float scores.")
            else:
                for hyp_id, score_val in scores_raw.items():
                    if hyp_id not in hypothesis_map:
                        invalid_claims.append(f"Score entry references nonexistent hypothesis ID '{hyp_id}'.")
                    if not isinstance(score_val, (int, float)):
                        invalid_claims.append(f"Score for hypothesis '{hyp_id}' must be numeric.")

        # Final Status Determination
        if invalid_claims or missing_support:
            status = VerificationStatus.FAIL
            reason = f"Verification failed with {len(invalid_claims)} invalid claim(s) and {len(missing_support)} missing support issue(s)."
        else:
            status = VerificationStatus.PASS
            reason = "Verification passed cleanly with all evidence traceable and supported."

        return VerificationResult(
            status=status,
            invalid_claims=invalid_claims,
            missing_support=missing_support,
            reason=reason
        )


def verify_investigation(context: Union[VerificationContext, Dict[str, Any]]) -> VerificationResult:
    """Convenience helper function for investigation context verification."""
    return Verifier.verify(context)

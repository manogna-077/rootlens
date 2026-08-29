"""Unit tests for Verifier component."""

import unittest
from backend.app.reasoning.evidence_evaluator import AssessmentType, EvidenceAssessment, EvidenceInput, HypothesisInput
from backend.app.reasoning.hypothesis_validator import HypothesisStatus
from backend.app.reasoning.verifier import CausalRelationship, VerificationContext, VerificationResult, VerificationStatus, Verifier, verify_investigation


class TestVerifier(unittest.TestCase):
    """Test suite covering Phase 5 Verifier requirements."""

    def test_pass_for_valid_investigation_context(self):
        """1. PASS for a valid investigation context with traceable evidence and supported hypotheses."""
        ev1 = EvidenceInput(id="EVD-101", observation="Memory usage exceeded 95%.", service="cache_service")
        ev2 = EvidenceInput(id="EVD-102", observation="GC pause duration reached 12 seconds.", service="cache_service")
        hyp1 = HypothesisInput(id="HYP-1", statement="GC pause caused memory saturation.", status="SUPPORTED", supporting_evidence_ids=["EVD-101", "EVD-102"])
        hyp2 = HypothesisInput(id="HYP-2", statement="External attack caused memory saturation.", status="WEAKENED", contradicting_evidence_ids=["EVD-101"])

        asst1 = EvidenceAssessment(evidence_id="EVD-101", hypothesis_id="HYP-1", assessment=AssessmentType.SUPPORTS, reason="Memory spike aligns.")
        asst2 = EvidenceAssessment(evidence_id="EVD-102", hypothesis_id="HYP-1", assessment=AssessmentType.SUPPORTS, reason="GC pause aligns.")

        ctx = VerificationContext(
            evidence_items=[ev1, ev2],
            hypotheses=[hyp1, hyp2],
            assessments=[asst1, asst2],
            selected_hypothesis_id="HYP-1"
        )

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.PASS)
        self.assertEqual(len(result.invalid_claims), 0)
        self.assertEqual(len(result.missing_support), 0)

    def test_fail_for_nonexistent_evidence_id(self):
        """2. FAIL for nonexistent evidence ID in hypothesis evidence lists."""
        hyp = HypothesisInput(id="HYP-1", statement="Issue A", status="SUPPORTED", supporting_evidence_ids=["EVD-NONEXISTENT"])
        ctx = VerificationContext(evidence_items=[], hypotheses=[hyp])

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("nonexistent supporting evidence ID 'EVD-NONEXISTENT'" in claim for claim in result.invalid_claims))

    def test_fail_for_assessment_evidence_list_mismatch(self):
        """3. FAIL for assessment/evidence-list mismatch (e.g., SUPPORTS assessment missing from supporting_evidence_ids)."""
        ev = EvidenceInput(id="EVD-101", observation="Obs A")
        hyp = HypothesisInput(id="HYP-1", statement="Issue A", status="SUPPORTED", supporting_evidence_ids=[])
        asst = EvidenceAssessment(evidence_id="EVD-101", hypothesis_id="HYP-1", assessment=AssessmentType.SUPPORTS, reason="Supports")

        ctx = VerificationContext(evidence_items=[ev], hypotheses=[hyp], assessments=[asst])

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("missing from supporting_evidence_ids" in supp for supp in result.missing_support))

    def test_fail_for_invalid_assessment_value(self):
        """4. FAIL for invalid assessment type."""
        ev = EvidenceInput(id="EVD-101", observation="Obs A")
        hyp = HypothesisInput(id="HYP-1", statement="Issue A")
        asst = {"evidence_id": "EVD-101", "hypothesis_id": "HYP-1", "assessment": "INVALID_ASST_TYPE", "reason": "Test"}

        ctx = {"evidence_items": [ev], "hypotheses": [hyp], "assessments": [asst]}

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("invalid type 'INVALID_ASST_TYPE'" in claim for claim in result.invalid_claims))

    def test_fail_for_invalid_hypothesis_status(self):
        """5. FAIL for invalid hypothesis status (including 'unverified')."""
        ev = EvidenceInput(id="EVD-101", observation="Obs A")
        hyp = {"id": "HYP-1", "statement": "Issue A", "status": "unverified", "supporting_evidence_ids": ["EVD-101"]}

        ctx = {"evidence_items": [ev], "hypotheses": [hyp]}

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("invalid status 'unverified'" in claim for claim in result.invalid_claims))

    def test_fail_for_nonexistent_selected_hypothesis_id(self):
        """6. FAIL for selected_hypothesis_id that does not exist."""
        ctx = VerificationContext(evidence_items=[], hypotheses=[], selected_hypothesis_id="HYP-MISSING")

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("Selected hypothesis ID 'HYP-MISSING' does not exist" in claim for claim in result.invalid_claims))

    def test_fail_for_confirmed_hypothesis_with_no_supporting_evidence(self):
        """7. FAIL for confirmed hypothesis with no supporting evidence."""
        hyp = HypothesisInput(id="HYP-1", statement="Issue A", status="CONFIRMED", supporting_evidence_ids=[])
        ctx = VerificationContext(evidence_items=[], hypotheses=[hyp])

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("marked CONFIRMED but has no supporting evidence" in supp for supp in result.missing_support))

    def test_detect_conflicting_evidence_against_confirmed_conclusion(self):
        """8 & 11. Detect disconfirming condition satisfied on CONFIRMED hypothesis without reasoning address."""
        ev = EvidenceInput(id="EVD-101", observation="voltage level remained at 0V continuously")
        hyp = HypothesisInput(
            id="HYP-1",
            statement="Voltage spike destroyed component.",
            status="CONFIRMED",
            supporting_evidence_ids=["EVD-101"],
            disconfirming_condition="voltage level remained at 0V",
            reasoning="Confirmed after observation."
        )
        asst = EvidenceAssessment(evidence_id="EVD-101", hypothesis_id="HYP-1", assessment=AssessmentType.SUPPORTS, reason="Observed.")

        ctx = VerificationContext(evidence_items=[ev], hypotheses=[hyp], assessments=[asst])

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("satisfying disconfirming condition" in claim for claim in result.invalid_claims))

    def test_alternatives_are_considered_appropriately(self):
        """9. Alternatives check: Warns if a single hypothesis is CONFIRMED without alternative options."""
        ev = EvidenceInput(id="EVD-101", observation="Obs A")
        hyp = HypothesisInput(id="HYP-1", statement="Issue A", status="CONFIRMED", supporting_evidence_ids=["EVD-101"])
        asst = EvidenceAssessment(evidence_id="EVD-101", hypothesis_id="HYP-1", assessment=AssessmentType.SUPPORTS, reason="Supports")

        ctx = VerificationContext(evidence_items=[ev], hypotheses=[hyp], assessments=[asst], selected_hypothesis_id="HYP-1")

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("without considering alternative hypotheses" in supp for supp in result.missing_support))

    def test_invalid_causal_relationship_rejected(self):
        """12. Invalid causal relationship is rejected."""
        ev = EvidenceInput(id="EVD-101", observation="Obs A")
        causal = [{"source_id": "EVD-101", "target_id": "HYP-1", "relationship": "INVALID_REL"}]

        ctx = VerificationContext(evidence_items=[ev], causal_claims=causal)

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("invalid relationship type 'INVALID_REL'" in claim for claim in result.invalid_claims))

    def test_precedes_is_not_treated_as_causes(self):
        """13. PRECEDES cannot be asserted as proof of CAUSES."""
        ev = EvidenceInput(id="EVD-101", observation="Obs A")
        causal = [{"source_id": "EVD-101", "target_id": "HYP-1", "relationship": "PRECEDES", "asserts_causation": True}]

        ctx = VerificationContext(evidence_items=[ev], causal_claims=causal)

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("cannot be treated as proof of CAUSES" in claim for claim in result.invalid_claims))

    def test_unsupported_causes_claim_rejected(self):
        """14. Unsupported CAUSES claim lacking evidence IDs is reported in missing_support."""
        causal = [{"source_id": "HYP-1", "target_id": "HYP-2", "relationship": "CAUSES", "evidence_ids": []}]

        ctx = VerificationContext(causal_claims=causal)

        result = verify_investigation(ctx)

        self.assertEqual(result.status, VerificationStatus.FAIL)
        self.assertTrue(any("lacks supporting evidence IDs" in supp for supp in result.missing_support))

    def test_evidence_ids_remain_traceable(self):
        """15. Evidence IDs remain traceable in error messages."""
        hyp = HypothesisInput(id="HYP-1", statement="Issue A", status="SUPPORTED", supporting_evidence_ids=["EVD-TRACE-MISSING-123"])
        ctx = VerificationContext(hypotheses=[hyp])

        result = verify_investigation(ctx)

        self.assertIn("EVD-TRACE-MISSING-123", result.invalid_claims[0])

    def test_verifier_does_not_mutate_input_state(self):
        """16. Verifier does not mutate input state or hypotheses."""
        ev = EvidenceInput(id="EVD-101", observation="Obs A")
        hyp = HypothesisInput(id="HYP-1", statement="Issue A", status="INVESTIGATING", supporting_evidence_ids=["EVD-101"])
        orig_status = hyp.status
        orig_supp = list(hyp.supporting_evidence_ids)

        ctx = VerificationContext(evidence_items=[ev], hypotheses=[hyp])
        result = verify_investigation(ctx)

        self.assertEqual(hyp.status, orig_status)
        self.assertEqual(hyp.supporting_evidence_ids, orig_supp)

    def test_optional_scores_structurally_validated_only(self):
        """17. Optional scores are structurally checked without applying Phase 6 math."""
        hyp = HypothesisInput(id="HYP-1", statement="Issue A", status="INVESTIGATING")
        ctx_valid = VerificationContext(hypotheses=[hyp], scores={"HYP-1": 0.75})
        ctx_invalid_id = VerificationContext(hypotheses=[hyp], scores={"NONEXISTENT_HYP": 0.75})
        ctx_invalid_type = VerificationContext(hypotheses=[hyp], scores={"HYP-1": "NOT_A_FLOAT"})

        self.assertEqual(verify_investigation(ctx_valid).status, VerificationStatus.PASS)
        self.assertEqual(verify_investigation(ctx_invalid_id).status, VerificationStatus.FAIL)
        self.assertEqual(verify_investigation(ctx_invalid_type).status, VerificationStatus.FAIL)

    def test_no_scenario_hardcoding_and_arbitrary_concepts(self):
        """18. Verify generic arbitrary concept handling without scenario hardcoding."""
        ev = EvidenceInput(id="EVD-GALAXIES", observation="Redshift factor measured at z=2.4.")
        hyp1 = HypothesisInput(id="HYP-COSMOLOGY", statement="Cosmological redshift expansion.", status="SUPPORTED", supporting_evidence_ids=["EVD-GALAXIES"])
        hyp2 = HypothesisInput(id="HYP-TIRED-LIGHT", statement="Tired light hypothesis.", status="WEAKENED", contradicting_evidence_ids=["EVD-GALAXIES"])
        asst = EvidenceAssessment(evidence_id="EVD-GALAXIES", hypothesis_id="HYP-COSMOLOGY", assessment=AssessmentType.SUPPORTS, reason="Redshift aligns.")

        ctx = VerificationContext(
            evidence_items=[ev],
            hypotheses=[hyp1, hyp2],
            assessments=[asst],
            selected_hypothesis_id="HYP-COSMOLOGY"
        )

        result = verify_investigation(ctx)
        self.assertEqual(result.status, VerificationStatus.PASS)


if __name__ == "__main__":
    unittest.main()

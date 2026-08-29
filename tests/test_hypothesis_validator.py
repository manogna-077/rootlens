"""Unit tests for HypothesisValidator and evidence-to-hypothesis updates."""

import unittest
from backend.app.reasoning.evidence_evaluator import AssessmentType, EvidenceAssessment, HypothesisInput
from backend.app.reasoning.hypothesis_validator import HypothesisStatus, HypothesisValidator, ValidationError


class TestHypothesisValidator(unittest.TestCase):
    """Test suite covering Phase 3 hypothesis update validation requirements."""

    def test_supports_adds_to_supporting_evidence_ids(self):
        """1. SUPPORTS adds evidence to supporting_evidence_ids and updates status to SUPPORTED."""
        hyp = HypothesisInput(id="H100", statement="Config update broke auth service.", status="INVESTIGATING")
        asst = EvidenceAssessment(evidence_id="EVD-001", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="Config change logged.")

        updated_hyp = HypothesisValidator.apply_update(hyp, asst)

        self.assertIn("EVD-001", updated_hyp.supporting_evidence_ids)
        self.assertEqual(updated_hyp.status, HypothesisStatus.SUPPORTED.value)
        self.assertNotEqual(updated_hyp.status, HypothesisStatus.CONFIRMED.value)

    def test_contradicts_adds_to_contradicting_evidence_ids(self):
        """2. CONTRADICTS adds evidence to contradicting_evidence_ids and updates status to WEAKENED."""
        hyp = HypothesisInput(id="H100", statement="Config update broke auth service.", status="INVESTIGATING")
        asst = EvidenceAssessment(evidence_id="EVD-002", hypothesis_id="H100", assessment=AssessmentType.CONTRADICTS, reason="No config change found.")

        updated_hyp = HypothesisValidator.apply_update(hyp, asst)

        self.assertIn("EVD-002", updated_hyp.contradicting_evidence_ids)
        self.assertEqual(updated_hyp.status, HypothesisStatus.WEAKENED.value)
        self.assertNotEqual(updated_hyp.status, HypothesisStatus.REJECTED.value)

    def test_neutral_does_not_artificially_change_hypothesis_strength(self):
        """3. NEUTRAL does not add to supporting/contradicting or artificially change status."""
        hyp = HypothesisInput(id="H100", statement="Config update broke auth service.", status="INVESTIGATING", score=0.5)
        asst = EvidenceAssessment(evidence_id="EVD-003", hypothesis_id="H100", assessment=AssessmentType.NEUTRAL, reason="Office door unlocked.")

        updated_hyp = HypothesisValidator.apply_update(hyp, asst)

        self.assertNotIn("EVD-003", updated_hyp.supporting_evidence_ids or [])
        self.assertNotIn("EVD-003", updated_hyp.contradicting_evidence_ids or [])
        self.assertEqual(updated_hyp.status, "INVESTIGATING")
        self.assertEqual(updated_hyp.score, 0.5)

    def test_existing_supporting_evidence_is_preserved(self):
        """4. Existing supporting evidence is preserved."""
        hyp = HypothesisInput(id="H100", statement="Network drop", supporting_evidence_ids=["EVD-PREV-SUPP"])
        asst = EvidenceAssessment(evidence_id="EVD-NEW-SUPP", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="Packet loss logged.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertIn("EVD-PREV-SUPP", updated.supporting_evidence_ids)
        self.assertIn("EVD-NEW-SUPP", updated.supporting_evidence_ids)

    def test_existing_contradicting_evidence_is_preserved(self):
        """5. Existing contradicting evidence is preserved."""
        hyp = HypothesisInput(id="H100", statement="Network drop", contradicting_evidence_ids=["EVD-PREV-CONTRA"])
        asst = EvidenceAssessment(evidence_id="EVD-NEW-SUPP", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="Packet loss logged.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertIn("EVD-PREV-CONTRA", updated.contradicting_evidence_ids)

    def test_existing_missing_evidence_is_preserved(self):
        """6. Existing missing evidence is preserved."""
        hyp = HypothesisInput(id="H100", statement="Disk failure", missing_evidence=["SMART_LOGS"])
        asst = EvidenceAssessment(evidence_id="EVD-001", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="IO error.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertIn("SMART_LOGS", updated.missing_evidence)

    def test_disconfirming_condition_is_preserved(self):
        """7. Disconfirming condition is preserved."""
        hyp = HypothesisInput(id="H100", statement="Overheating", disconfirming_condition="temp < 30C")
        asst = EvidenceAssessment(evidence_id="EVD-001", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="High temp.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertEqual(updated.disconfirming_condition, "temp < 30C")

    def test_evidence_ids_remain_traceable(self):
        """8. Evidence IDs remain traceable in lists and reasoning audit log."""
        hyp = HypothesisInput(id="H100", statement="Cache issue")
        asst = EvidenceAssessment(evidence_id="EVD-TRACE-99", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="Cache miss rate 90%.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertIn("EVD-TRACE-99", updated.supporting_evidence_ids)
        self.assertIn("EVD-TRACE-99", updated.reasoning)

    def test_wrong_hypothesis_id_is_rejected(self):
        """9. Assessment referencing wrong hypothesis_id raises ValidationError."""
        hyp = HypothesisInput(id="H_CORRECT", statement="Issue A")
        asst = EvidenceAssessment(evidence_id="EVD-001", hypothesis_id="H_WRONG", assessment=AssessmentType.SUPPORTS, reason="Test")

        with self.assertRaises(ValidationError):
            HypothesisValidator.validate_assessment_update(hyp, asst)

    def test_missing_evidence_id_is_rejected(self):
        """10. Missing or empty evidence_id raises ValidationError."""
        hyp = HypothesisInput(id="H100", statement="Issue A")
        asst = EvidenceAssessment(evidence_id="", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="Test")

        with self.assertRaises(ValidationError):
            HypothesisValidator.validate_assessment_update(hyp, asst)

    def test_duplicate_evidence_links_handled_safely(self):
        """11. Duplicate evidence ID updates do not create duplicate entries in list."""
        hyp = HypothesisInput(id="H100", statement="Issue A", supporting_evidence_ids=["EVD-001"])
        asst = EvidenceAssessment(evidence_id="EVD-001", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="Duplicate run.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertEqual(updated.supporting_evidence_ids.count("EVD-001"), 1)

    def test_invalid_status_is_rejected(self):
        """12. Invalid hypothesis status (such as 'unverified' or any unrecognized string) raises ValidationError."""
        hyp_unverified = {"id": "H100", "statement": "Issue A", "status": "unverified"}
        hyp_invalid = {"id": "H100", "statement": "Issue A", "status": "INVALID_STATUS_XYZ"}
        asst = {"evidence_id": "EVD-001", "hypothesis_id": "H100", "assessment": "SUPPORTS", "reason": "Test"}

        with self.assertRaises(ValidationError):
            HypothesisValidator.validate_assessment_update(hyp_unverified, asst)

        with self.assertRaises(ValidationError):
            HypothesisValidator.validate_assessment_update(hyp_invalid, asst)

    def test_all_six_valid_statuses_accepted(self):
        """16. Verify that all 6 allowed RootLens statuses are accepted by validator."""
        asst = EvidenceAssessment(evidence_id="EVD-001", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="Valid status test.")
        valid_statuses = ["GENERATED", "INVESTIGATING", "SUPPORTED", "WEAKENED", "CONFIRMED", "REJECTED"]

        for st in valid_statuses:
            hyp = HypothesisInput(id="H100", statement="Issue A", status=st)
            validated = HypothesisValidator.validate_assessment_update(hyp, asst)
            self.assertEqual(validated["status"], st)

    def test_invalid_assessment_is_rejected(self):
        """13. Invalid assessment string raises ValidationError."""
        hyp = HypothesisInput(id="H100", statement="Issue A")
        asst = {"evidence_id": "EVD-001", "hypothesis_id": "H100", "assessment": "INVALID_ASSESSMENT", "reason": "Test"}

        with self.assertRaises(ValidationError):
            HypothesisValidator.validate_assessment_update(hyp, asst)

    def test_single_contradiction_does_not_automatically_force_rejected(self):
        """14. A single contradiction sets status to WEAKENED, not REJECTED."""
        hyp = HypothesisInput(id="H100", statement="Issue A", status="INVESTIGATING")
        asst = EvidenceAssessment(evidence_id="EVD-CONTRA-1", hypothesis_id="H100", assessment=AssessmentType.CONTRADICTS, reason="One contradiction.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertEqual(updated.status, HypothesisStatus.WEAKENED.value)
        self.assertNotEqual(updated.status, HypothesisStatus.REJECTED.value)

    def test_single_supporting_item_does_not_automatically_force_confirmed(self):
        """15. A single supporting item sets status to SUPPORTED, not CONFIRMED."""
        hyp = HypothesisInput(id="H100", statement="Issue A", status="INVESTIGATING")
        asst = EvidenceAssessment(evidence_id="EVD-SUPP-1", hypothesis_id="H100", assessment=AssessmentType.SUPPORTS, reason="One supporting evidence.")

        updated = HypothesisValidator.apply_update(hyp, asst)

        self.assertEqual(updated.status, HypothesisStatus.SUPPORTED.value)
        self.assertNotEqual(updated.status, HypothesisStatus.CONFIRMED.value)


if __name__ == "__main__":
    unittest.main()

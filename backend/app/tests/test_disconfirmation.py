"""Unit tests for DisconfirmationEvaluator."""

import unittest
from backend.app.reasoning.disconfirmation import DisconfirmationEvaluator, DisconfirmationResult, evaluate_disconfirmation
from backend.app.reasoning.evidence_evaluator import EvidenceInput, HypothesisInput
from backend.app.reasoning.hypothesis_validator import HypothesisStatus, HypothesisValidator


class TestDisconfirmation(unittest.TestCase):
    """Test suite covering Phase 4 disconfirmation evaluation requirements."""

    def test_evidence_satisfies_disconfirming_condition(self):
        """1. Evidence satisfies disconfirming condition -> disconfirms=True."""
        evidence = EvidenceInput(
            id="EV-DIS-001",
            observation="The configuration value remained unchanged during the incident."
        )
        hypothesis = HypothesisInput(
            id="HYP-CONFIG-1",
            statement="The configuration change caused the failures.",
            disconfirming_condition="configuration value remained unchanged"
        )

        result = evaluate_disconfirmation(evidence, hypothesis)

        self.assertEqual(result.evidence_id, "EV-DIS-001")
        self.assertEqual(result.hypothesis_id, "HYP-CONFIG-1")
        self.assertTrue(result.disconfirms)
        self.assertIn("disconfirming condition", result.reason)

    def test_evidence_does_not_satisfy_disconfirming_condition(self):
        """2. Evidence does not satisfy disconfirming condition -> disconfirms=False."""
        evidence = EvidenceInput(
            id="EV-DIS-002",
            observation="Network traffic volume reached 10 Gbps peak."
        )
        hypothesis = HypothesisInput(
            id="HYP-CONFIG-1",
            statement="The configuration change caused the failures.",
            disconfirming_condition="configuration value remained unchanged"
        )

        result = evaluate_disconfirmation(evidence, hypothesis)

        self.assertEqual(result.evidence_id, "EV-DIS-002")
        self.assertEqual(result.hypothesis_id, "HYP-CONFIG-1")
        self.assertFalse(result.disconfirms)

    def test_hypothesis_has_no_disconfirming_condition(self):
        """3. Hypothesis has no disconfirming condition -> disconfirms=False with clear reason."""
        evidence = EvidenceInput(
            id="EV-DIS-003",
            observation="System reboot logged at 10:00 AM."
        )
        hypothesis = HypothesisInput(
            id="HYP-NODISC-1",
            statement="System reboot caused memory corruption.",
            disconfirming_condition=None
        )

        result = evaluate_disconfirmation(evidence, hypothesis)

        self.assertFalse(result.disconfirms)
        self.assertIn("no specified disconfirming condition", result.reason)

    def test_evidence_and_hypothesis_ids_preserved(self):
        """4 & 5. Evidence ID and Hypothesis ID are preserved in output."""
        evidence = {"id": "CUSTOM_EVD_987", "observation": "sensor voltage remained below 5V"}
        hypothesis = {"id": "CUSTOM_HYP_654", "disconfirming_condition": "voltage remained below 5V"}

        result = evaluate_disconfirmation(evidence, hypothesis)

        self.assertEqual(result.evidence_id, "CUSTOM_EVD_987")
        self.assertEqual(result.hypothesis_id, "CUSTOM_HYP_654")

    def test_reason_is_present_and_grounded(self):
        """6. Reason is present, grounded in supplied observation and disconfirming condition."""
        evidence = EvidenceInput(id="EV-001", observation="ambient humidity was 45%")
        hypothesis = HypothesisInput(id="HYP-001", disconfirming_condition="ambient humidity was 45%")

        result = evaluate_disconfirmation(evidence, hypothesis)

        self.assertIsInstance(result.reason, str)
        self.assertIn("ambient humidity was 45%", result.reason)

    def test_arbitrary_concepts_work(self):
        """7. Test disconfirmation with arbitrary non-domain concepts."""
        evidence = EvidenceInput(id="EV-ASTRONOMY", observation="telescope optical focus remained locked at zero focal shift")
        hypothesis = HypothesisInput(id="HYP-ASTRONOMY", disconfirming_condition="focus remained locked")

        result = evaluate_disconfirmation(evidence, hypothesis)

        self.assertTrue(result.disconfirms)

    def test_disconfirmation_does_not_force_rejected_status(self):
        """10. Disconfirmation identification does not automatically set hypothesis status to REJECTED."""
        evidence = EvidenceInput(id="EV-DIS-010", observation="disk queue length stayed zero")
        hypothesis = HypothesisInput(id="HYP-010", statement="Disk queue saturation caused latency", status="INVESTIGATING", disconfirming_condition="queue length stayed zero")

        disconf_res = evaluate_disconfirmation(evidence, hypothesis)
        self.assertTrue(disconf_res.disconfirms)

        # Applying assessment based on disconfirmation updates status to WEAKENED, not REJECTED
        assessment = {
            "evidence_id": evidence.id,
            "hypothesis_id": hypothesis.id,
            "assessment": "CONTRADICTS",
            "reason": disconf_res.reason
        }
        updated_hyp = HypothesisValidator.apply_update(hypothesis, assessment)

        self.assertEqual(updated_hyp.status, HypothesisStatus.WEAKENED.value)
        self.assertNotEqual(updated_hyp.status, HypothesisStatus.REJECTED.value)

    def test_existing_hypothesis_history_not_destroyed(self):
        """11. Existing evidence history and fields are preserved when disconfirmation is evaluated."""
        hypothesis = HypothesisInput(
            id="HYP-HIST-1",
            statement="Sensor malfunction",
            status="INVESTIGATING",
            supporting_evidence_ids=["EVD-SUPP-PREV"],
            contradicting_evidence_ids=["EVD-CONTRA-PREV"],
            missing_evidence=["LOG-CALIBRATION"],
            disconfirming_condition="calibration log verified ok"
        )
        evidence = EvidenceInput(id="EVD-DIS-NEW", observation="calibration log verified ok")

        disconf_res = evaluate_disconfirmation(evidence, hypothesis)
        assessment = {
            "evidence_id": evidence.id,
            "hypothesis_id": hypothesis.id,
            "assessment": "CONTRADICTS",
            "reason": disconf_res.reason
        }
        updated = HypothesisValidator.apply_update(hypothesis, assessment)

        self.assertIn("EVD-SUPP-PREV", updated.supporting_evidence_ids)
        self.assertIn("EVD-CONTRA-PREV", updated.contradicting_evidence_ids)
        self.assertIn("EVD-DIS-NEW", updated.contradicting_evidence_ids)
        self.assertIn("LOG-CALIBRATION", updated.missing_evidence)


if __name__ == "__main__":
    unittest.main()

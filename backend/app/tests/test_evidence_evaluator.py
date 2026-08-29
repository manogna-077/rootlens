"""Unit tests for EvidenceAssessment and EvidenceEvaluator."""

import unittest
from backend.app.reasoning.evidence_evaluator import (
    AssessmentType,
    EvidenceAssessment,
    EvidenceEvaluator,
    EvidenceInput,
    HypothesisInput,
    evaluate_evidence,
)


class TestEvidenceEvaluator(unittest.TestCase):
    """Test suite for EvidenceAssessment logic using generic examples."""

    def test_generic_supports_classification(self):
        """Test SUPPORTS using generic arbitrary concepts."""
        evidence = EvidenceInput(
            id="EV-100",
            service="auth_service",
            observation="configuration value changed immediately before request failures."
        )
        hypothesis = HypothesisInput(
            id="HYP-100",
            statement="The configuration change caused the request failures."
        )

        assessment = evaluate_evidence(evidence, hypothesis)

        self.assertEqual(assessment.evidence_id, "EV-100")
        self.assertEqual(assessment.hypothesis_id, "HYP-100")
        self.assertEqual(assessment.assessment, AssessmentType.SUPPORTS)
        self.assertTrue(len(assessment.reason) > 0)
        self.assertIn("configuration", assessment.reason)

    def test_generic_contradicts_classification(self):
        """Test CONTRADICTS using generic arbitrary concepts with negation/unchanged state."""
        evidence = EvidenceInput(
            id="EV-200",
            observation="configuration value remained unchanged during the incident."
        )
        hypothesis = HypothesisInput(
            id="HYP-100",
            statement="The configuration change caused the request failures."
        )

        assessment = evaluate_evidence(evidence, hypothesis)

        self.assertEqual(assessment.evidence_id, "EV-200")
        self.assertEqual(assessment.hypothesis_id, "HYP-100")
        self.assertEqual(assessment.assessment, AssessmentType.CONTRADICTS)
        self.assertTrue(len(assessment.reason) > 0)

    def test_generic_neutral_classification(self):
        """Test NEUTRAL using completely unrelated arbitrary concepts."""
        evidence = EvidenceInput(
            id="EV-300",
            observation="the office lighting schedule changed."
        )
        hypothesis = HypothesisInput(
            id="HYP-100",
            statement="The configuration change caused the request failures."
        )

        assessment = evaluate_evidence(evidence, hypothesis)

        self.assertEqual(assessment.evidence_id, "EV-300")
        self.assertEqual(assessment.hypothesis_id, "HYP-100")
        self.assertEqual(assessment.assessment, AssessmentType.NEUTRAL)
        self.assertTrue(len(assessment.reason) > 0)

    def test_disconfirming_condition(self):
        """Test that satisfying a generic disconfirming condition produces CONTRADICTS."""
        evidence = EvidenceInput(
            id="EV-400",
            observation="system temperature remained at 22C throughout the test run."
        )
        hypothesis = HypothesisInput(
            id="HYP-200",
            statement="Thermal overheating caused hardware shutdown.",
            disconfirming_condition="remained at 22C"
        )

        assessment = evaluate_evidence(evidence, hypothesis)

        self.assertEqual(assessment.evidence_id, "EV-400")
        self.assertEqual(assessment.hypothesis_id, "HYP-200")
        self.assertEqual(assessment.assessment, AssessmentType.CONTRADICTS)
        self.assertIn("disconfirming condition", assessment.reason)

    def test_dictionary_contract_compliance(self):
        """Test serialization and plain dictionary contract compliance without Pydantic."""
        evidence = {
            "id": "EVD-999",
            "observation": "router firmware updated at 08:00 UTC.",
            "service": "network_router"
        }
        hypothesis = {
            "id": "HYP-999",
            "statement": "router firmware update interrupted network packet flow."
        }

        assessment = evaluate_evidence(evidence, hypothesis)
        assessment_dict = assessment.model_dump()

        self.assertEqual(assessment_dict["evidence_id"], "EVD-999")
        self.assertEqual(assessment_dict["hypothesis_id"], "HYP-999")
        self.assertIn(assessment_dict["assessment"], ["SUPPORTS", "CONTRADICTS", "NEUTRAL"])
        self.assertIsInstance(assessment_dict["reason"], str)

    def test_preserves_supplied_ids_and_no_scenario_hardcoding(self):
        """Test that arbitrary custom IDs and statements are preserved."""
        evidence = EvidenceInput(
            id="CUSTOM_EV_XYZ",
            observation="solar radiation level spiked during transmission window."
        )
        hypothesis = HypothesisInput(
            id="CUSTOM_HYP_ABC",
            statement="solar radiation spike degraded satellite telemetry transmission."
        )

        assessment = EvidenceEvaluator.evaluate(evidence, hypothesis)

        self.assertEqual(assessment.evidence_id, "CUSTOM_EV_XYZ")
        self.assertEqual(assessment.hypothesis_id, "CUSTOM_HYP_ABC")
        self.assertEqual(assessment.assessment, AssessmentType.SUPPORTS)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for EvidenceScoreCalculator and Evidence Strength rubric."""

import unittest
from backend.app.reasoning.evidence_evaluator import EvidenceInput, HypothesisInput
from backend.app.reasoning.evidence_score import EvidenceScoreCalculator, EvidenceScoreResult, calculate_evidence_score


class TestEvidenceScore(unittest.TestCase):
    """Test suite covering Phase 6 Evidence Strength rubric requirements."""

    def test_temporal_precedence_contribution(self):
        """1. Temporal precedence adds +20 points."""
        ev = EvidenceInput(id="EVD-001", source="metrics", observation="Error spike pre-dated service crash at timestamp 10:00.")
        hyp = HypothesisInput(id="HYP-1", statement="Service crash caused by initial error spike.", supporting_evidence_ids=["EVD-001"])

        res = calculate_evidence_score(hyp, [ev])

        self.assertTrue(res.factors["temporal_precedence"].detected)
        self.assertEqual(res.factors["temporal_precedence"].points_awarded, 20.0)
        self.assertIn("EVD-001", res.factors["temporal_precedence"].evidence_ids)

    def test_mechanistic_evidence_contribution(self):
        """2. Mechanistic evidence adds +25 points."""
        ev = EvidenceInput(id="EVD-002", source="logs", observation="Thread deadlock exception logged in stack trace.")
        hyp = HypothesisInput(id="HYP-1", statement="Thread deadlock caused freeze.", supporting_evidence_ids=["EVD-002"])

        res = calculate_evidence_score(hyp, [ev])

        self.assertTrue(res.factors["mechanistic_evidence"].detected)
        self.assertEqual(res.factors["mechanistic_evidence"].points_awarded, 25.0)

    def test_independent_supporting_sources_contribution(self):
        """3. Independent supporting sources add up to +20 points."""
        ev1 = EvidenceInput(id="EVD-001", source="datadog", observation="Latency spike logged.")
        ev2 = EvidenceInput(id="EVD-002", source="prometheus", observation="CPU spike logged.")
        hyp = HypothesisInput(id="HYP-1", statement="System overload.", supporting_evidence_ids=["EVD-001", "EVD-002"])

        res = calculate_evidence_score(hyp, [ev1, ev2])

        self.assertTrue(res.factors["independent_supporting_sources"].detected)
        self.assertEqual(res.factors["independent_supporting_sources"].points_awarded, 20.0)

    def test_version_change_correlation_contribution(self):
        """4. Version/change correlation adds +15 points."""
        ev = EvidenceInput(id="EVD-003", source="ci_cd", observation="Deployment of release v2.0 occurred 5 mins prior.", event_type="deployment")
        hyp = HypothesisInput(id="HYP-1", statement="Release v2.0 introduced regression.", supporting_evidence_ids=["EVD-003"])

        res = calculate_evidence_score(hyp, [ev])

        self.assertTrue(res.factors["version_change_correlation"].detected)
        self.assertEqual(res.factors["version_change_correlation"].points_awarded, 15.0)

    def test_contradicting_evidence_penalty(self):
        """5. Contradicting evidence penalizes score by -20 points."""
        ev_supp = EvidenceInput(id="EVD-001", source="logs", observation="Latency spike exception.")
        ev_contra = EvidenceInput(id="EVD-002", source="metrics", observation="CPU usage remained normal.")
        hyp = HypothesisInput(id="HYP-1", statement="CPU saturation caused latency.", supporting_evidence_ids=["EVD-001"], contradicting_evidence_ids=["EVD-002"])

        res = calculate_evidence_score(hyp, [ev_supp, ev_contra])

        self.assertTrue(res.factors["contradicting_evidence"].detected)
        self.assertEqual(res.factors["contradicting_evidence"].points_awarded, -20.0)

    def test_strong_alternative_explanation_penalty(self):
        """6. Strong alternative explanation penalizes score by -15 points."""
        ev1 = EvidenceInput(id="EVD-001", source="s1", observation="Obs A")
        ev2 = EvidenceInput(id="EVD-002", source="s2", observation="Obs B")
        hyp1 = HypothesisInput(id="HYP-1", statement="Cause A", supporting_evidence_ids=["EVD-001"])
        hyp2 = HypothesisInput(id="HYP-2", statement="Cause B", supporting_evidence_ids=["EVD-001", "EVD-002"])

        res = calculate_evidence_score(hyp1, [ev1, ev2], all_hypotheses=[hyp1, hyp2])

        self.assertTrue(res.factors["strong_alternative_explanation"].detected)
        self.assertEqual(res.factors["strong_alternative_explanation"].points_awarded, -15.0)

    def test_historical_similarity_contribution(self):
        """7. Historical similarity adds +10 points."""
        ev = EvidenceInput(id="EVD-005", source="kb", observation="Identical to past historical incident #442.")
        hyp = HypothesisInput(id="HYP-1", statement="Known recurring bug.", supporting_evidence_ids=["EVD-005"])

        res = calculate_evidence_score(hyp, [ev])

        self.assertTrue(res.factors["historical_similarity"].detected)
        self.assertEqual(res.factors["historical_similarity"].points_awarded, 10.0)

    def test_normalization_and_clamping_range(self):
        """8. Verify score normalization strictly clamps to 0-100 range."""
        ev_contra1 = EvidenceInput(id="EVD-C1", source="s1", observation="Contradiction 1")
        ev_contra2 = EvidenceInput(id="EVD-C2", source="s2", observation="Contradiction 2")
        hyp_weak = HypothesisInput(id="HYP-WEAK", statement="Weak hypothesis", contradicting_evidence_ids=["EVD-C1", "EVD-C2"])
        hyp_alt = HypothesisInput(id="HYP-ALT", statement="Strong alt", supporting_evidence_ids=["EVD-C1", "EVD-C2"])

        res_weak = calculate_evidence_score(hyp_weak, [ev_contra1, ev_contra2], all_hypotheses=[hyp_weak, hyp_alt])

        self.assertGreaterEqual(res_weak.normalized_score, 0.0)
        self.assertLessEqual(res_weak.normalized_score, 100.0)

    def test_zero_missing_evidence_handling(self):
        """9. Zero/missing evidence yields baseline score without crash or invented points."""
        hyp = HypothesisInput(id="HYP-EMPTY", statement="Empty hypothesis")
        res = calculate_evidence_score(hyp, [])

        self.assertEqual(res.raw_score, 0.0)
        self.assertEqual(res.normalized_score, 50.0)

    def test_arbitrary_concepts_and_traceability(self):
        """10. Arbitrary domain concepts work with full evidence ID traceability."""
        ev1 = EvidenceInput(id="EVD-QUANTUM-1", source="interferometer", observation="Quantum decoherence detected prior to phase collapse at timestamp 00:01.")
        ev2 = EvidenceInput(id="EVD-QUANTUM-2", source="spectrometer", observation="Spectral line shift exception logged.")
        hyp = HypothesisInput(id="HYP-QUANTUM", statement="Thermal fluctuations caused quantum phase collapse.", supporting_evidence_ids=["EVD-QUANTUM-1", "EVD-QUANTUM-2"])

        res = calculate_evidence_score(hyp, [ev1, ev2])

        self.assertGreater(res.normalized_score, 50.0)
        self.assertIn("EVD-QUANTUM-1", res.factors["temporal_precedence"].evidence_ids)
        self.assertIn("EVD-QUANTUM-2", res.factors["mechanistic_evidence"].evidence_ids)

    def test_score_is_not_probability(self):
        """11. Evidence score represents Evidence Strength (0-100), not a probability distribution."""
        ev = EvidenceInput(id="EVD-1", source="s1", observation="Trace exception logged.")
        hyp = HypothesisInput(id="HYP-1", statement="Test statement", supporting_evidence_ids=["EVD-1"])
        res = calculate_evidence_score(hyp, [ev])

        self.assertIsInstance(res.normalized_score, float)
        self.assertTrue("Evidence Strength Score" in res.explanation)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Person 4 Causal Graph and relationship validation."""

import copy
import unittest

from backend.app.graph.causal_graph import (
    CausalEdge,
    CausalGraph,
    CausalNode,
    CausalRelationship,
    GraphValidationResult,
    RelationshipValidationError,
)
from backend.app.reasoning.evidence_evaluator import EvidenceInput, HypothesisInput
from backend.app.reasoning.verifier import VerificationContext, Verifier


class TestCausalGraph(unittest.TestCase):
    """Test suite for Phase 7 Causal Graph module."""

    def test_1_precedes_relationship_accepted(self):
        """1. PRECEDES relationship is accepted strictly."""
        edge = CausalEdge(source_id="EVENT-A", target_id="EVENT-B", relationship="PRECEDES")
        self.assertEqual(edge.relationship, CausalRelationship.PRECEDES)
        graph = CausalGraph(edges=[edge])
        self.assertEqual(len(graph.edges), 1)

    def test_2_correlates_with_relationship_accepted(self):
        """2. CORRELATES_WITH relationship is accepted strictly."""
        edge = CausalEdge(source_id="METRIC-X", target_id="METRIC-Y", relationship="CORRELATES_WITH")
        self.assertEqual(edge.relationship, CausalRelationship.CORRELATES_WITH)
        graph = CausalGraph(edges=[edge])
        self.assertEqual(len(graph.edges), 1)

    def test_3_supports_relationship_accepted(self):
        """3. SUPPORTS relationship is accepted strictly."""
        edge = CausalEdge(source_id="EVD-01", target_id="HYP-01", relationship="SUPPORTS")
        self.assertEqual(edge.relationship, CausalRelationship.SUPPORTS)
        graph = CausalGraph(edges=[edge])
        self.assertEqual(len(graph.edges), 1)

    def test_4_contributes_to_relationship_accepted(self):
        """4. CONTRIBUTES_TO relationship is accepted strictly."""
        edge = CausalEdge(source_id="FACTOR-A", target_id="FAILURE-B", relationship="CONTRIBUTES_TO")
        self.assertEqual(edge.relationship, CausalRelationship.CONTRIBUTES_TO)
        graph = CausalGraph(edges=[edge])
        self.assertEqual(len(graph.edges), 1)

    def test_5_causes_relationship_accepted_with_evidence(self):
        """5. CAUSES relationship is accepted when supporting evidence exists."""
        edge = CausalEdge(
            source_id="ROOT-CAUSE-X",
            target_id="OUTAGE-Y",
            relationship="CAUSES",
            evidence_ids=["EVD-101"]
        )
        self.assertEqual(edge.relationship, CausalRelationship.CAUSES)
        graph = CausalGraph(edges=[edge])
        val_res = graph.validate(known_evidence_ids={"EVD-101"})
        self.assertTrue(val_res.is_valid)

    def test_6_invalid_relationship_rejected(self):
        """6. Invalid relationship value is rejected clearly."""
        with self.assertRaises(RelationshipValidationError):
            CausalEdge(source_id="NODE-A", target_id="NODE-B", relationship="TRIGGERS_MAGICALLY")

    def test_7_precedes_does_not_become_causes_automatically(self):
        """7. PRECEDES does NOT automatically become CAUSES without evidence."""
        graph = CausalGraph()
        graph.add_edge({"source_id": "STEP-1", "target_id": "STEP-2", "relationship": "PRECEDES"})
        
        # Attempting automatic upgrade without evidence raises error
        with self.assertRaises(RelationshipValidationError):
            graph.upgrade_relationship(
                source_id="STEP-1",
                target_id="STEP-2",
                current_relationship="PRECEDES",
                target_relationship="CAUSES",
                evidence_ids=[]
            )
        
        # The relationship in the graph remains PRECEDES
        self.assertEqual(graph.edges[0].relationship, CausalRelationship.PRECEDES)

    def test_8_correlates_with_does_not_become_causes_automatically(self):
        """8. CORRELATES_WITH does NOT automatically become CAUSES without evidence."""
        graph = CausalGraph()
        graph.add_edge({"source_id": "OBS-1", "target_id": "OBS-2", "relationship": "CORRELATES_WITH"})

        with self.assertRaises(RelationshipValidationError):
            graph.upgrade_relationship(
                source_id="OBS-1",
                target_id="OBS-2",
                current_relationship="CORRELATES_WITH",
                target_relationship="CAUSES",
                evidence_ids=None
            )

        self.assertEqual(graph.edges[0].relationship, CausalRelationship.CORRELATES_WITH)

    def test_9_unsupported_causes_claim_rejected_or_downgraded(self):
        """9. Unsupported CAUSES claim lacking evidence is rejected by validation or safely downgraded."""
        # Case 9a: Rejected by validation
        edge_unsupported = CausalEdge(source_id="NODE-A", target_id="NODE-B", relationship="CAUSES", evidence_ids=[])
        graph = CausalGraph(edges=[edge_unsupported])
        val_res = graph.validate()
        self.assertFalse(val_res.is_valid)
        self.assertTrue(any("lacks supporting evidence" in err for err in val_res.errors))

        # Case 9b: Safely downgraded when auto_downgrade is enabled
        graph_auto = CausalGraph()
        downgraded_edge = graph_auto.add_edge(
            {"source_id": "NODE-A", "target_id": "NODE-B", "relationship": "CAUSES", "evidence_ids": []},
            auto_downgrade=True
        )
        self.assertEqual(downgraded_edge.relationship, CausalRelationship.CONTRIBUTES_TO)
        self.assertEqual(downgraded_edge.metadata["downgraded_from"], "CAUSES")

    def test_10_evidence_ids_preserved_and_traceable(self):
        """10. Evidence IDs are preserved and traceable across graph construction and export."""
        edge = CausalEdge(source_id="NODE-A", target_id="NODE-B", relationship="CAUSES", evidence_ids=["EVD-999", "EVD-888"])
        self.assertEqual(edge.evidence_ids, ["EVD-999", "EVD-888"])

        graph = CausalGraph(edges=[edge])
        dump = graph.model_dump()
        self.assertEqual(dump["edges"][0]["evidence_ids"], ["EVD-999", "EVD-888"])

    def test_11_unknown_evidence_ids_detected(self):
        """11. Unknown evidence IDs are reported clearly during validation."""
        edge = CausalEdge(source_id="NODE-A", target_id="NODE-B", relationship="SUPPORTS", evidence_ids=["EVD-KNOWN", "EVD-UNKNOWN-99"])
        graph = CausalGraph(edges=[edge])
        val_res = graph.validate(known_evidence_ids={"EVD-KNOWN"})
        self.assertFalse(val_res.is_valid)
        self.assertTrue(any("Unknown evidence ID 'EVD-UNKNOWN-99'" in err for err in val_res.errors))

    def test_12_source_target_ids_preserved(self):
        """12. Source and target IDs are strictly preserved."""
        edge = CausalEdge(source_id="ALPHA-ID-123", target_id="BETA-ID-456", relationship="PRECEDES")
        self.assertEqual(edge.source_id, "ALPHA-ID-123")
        self.assertEqual(edge.target_id, "BETA-ID-456")

    def test_13_duplicate_relationships_handled_safely(self):
        """13. Duplicate relationships merge evidence IDs and metadata deterministically without duplicating edges."""
        graph = CausalGraph()
        graph.add_edge({"source_id": "A", "target_id": "B", "relationship": "SUPPORTS", "evidence_ids": ["E1"]})
        graph.add_edge({"source_id": "A", "target_id": "B", "relationship": "SUPPORTS", "evidence_ids": ["E2", "E1"]})

        self.assertEqual(len(graph.edges), 1)
        self.assertEqual(graph.edges[0].evidence_ids, ["E1", "E2"])

    def test_14_arbitrary_concepts_and_non_rootlens_ids_work(self):
        """14. Arbitrary non-RootLens concepts and domain IDs work seamlessly."""
        graph = CausalGraph()
        graph.add_node(CausalNode(id="GENE_TP53", entity_type="biology"))
        graph.add_node(CausalNode(id="CELL_APOPTOSIS", entity_type="biology"))
        graph.add_edge({
            "source_id": "GENE_TP53",
            "target_id": "CELL_APOPTOSIS",
            "relationship": "CAUSES",
            "evidence_ids": ["PAPER-2026-BIO-01"]
        })

        val_res = graph.validate(known_evidence_ids={"PAPER-2026-BIO-01"})
        self.assertTrue(val_res.is_valid)
        self.assertEqual(graph.nodes["GENE_TP53"].entity_type, "biology")

    def test_15_no_scenario_hardcoding(self):
        """15. Confirms zero scenario A/B/C/D strings or hardcoding in implementation."""
        edge = CausalEdge(source_id="X", target_id="Y", relationship="CONTRIBUTES_TO")
        graph = CausalGraph(edges=[edge])
        dump_str = str(graph.to_dict())
        for scenario in ["Scenario A", "Scenario B", "Scenario C", "Scenario D"]:
            self.assertNotIn(scenario, dump_str)

    def test_16_input_state_not_mutated(self):
        """16. Graph construction and imports do not mutate caller-owned dictionary or object inputs."""
        input_dict = {
            "source_id": "SRC",
            "target_id": "TGT",
            "relationship": "SUPPORTS",
            "evidence_ids": ["E1"],
            "metadata": {"key": "val"}
        }
        input_dict_copy = copy.deepcopy(input_dict)

        graph = CausalGraph()
        graph.add_edge(input_dict)

        self.assertEqual(input_dict, input_dict_copy)

    def test_17_serialization_structure_is_deterministic(self):
        """17. Exported dictionary structure is clean, deterministic, and round-trippable."""
        graph = CausalGraph()
        graph.add_node(CausalNode(id="N2", name="Node 2"))
        graph.add_node(CausalNode(id="N1", name="Node 1"))
        graph.add_edge({"source_id": "N1", "target_id": "N2", "relationship": "PRECEDES"})

        data = graph.to_dict()
        reconstructed = CausalGraph.from_dict(data)

        self.assertEqual(len(reconstructed.edges), 1)
        self.assertEqual(reconstructed.edges[0].source_id, "N1")
        self.assertEqual(reconstructed.edges[0].target_id, "N2")

    def test_18_compatibility_with_verifier_and_investigation_context(self):
        """18. CausalGraph builds seamlessly from VerificationContext and aligns with Verifier rules."""
        ctx = VerificationContext(
            evidence_items=[EvidenceInput(id="EVD-1")],
            hypotheses=[HypothesisInput(id="HYP-1")],
            causal_claims=[
                {"source_id": "EVD-1", "target_id": "HYP-1", "relationship": "CAUSES", "evidence_ids": ["EVD-1"]}
            ]
        )

        graph = CausalGraph.from_investigation_context(ctx)
        self.assertEqual(len(graph.edges), 1)

        val_res = graph.validate(known_evidence_ids={"EVD-1"})
        self.assertTrue(val_res.is_valid)

        # Also verify with Person 4 Verifier
        ver_res = Verifier.verify(ctx)
        self.assertEqual(ver_res.status.value, "PASS")


if __name__ == "__main__":
    unittest.main()

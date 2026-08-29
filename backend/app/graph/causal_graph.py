"""Causal graph and relationship validation module for RootLens pipeline."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from backend.app.reasoning.verifier import CausalRelationship


class RelationshipValidationError(ValueError):
    """Exception raised when causal relationship validation fails."""
    pass


@dataclass
class CausalNode:
    """Represents a node (entity or concept) in the causal graph."""
    id: str
    name: Optional[str] = None
    entity_type: str = "concept"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id or not str(self.id).strip():
            raise ValueError("Node ID cannot be empty.")
        self.id = str(self.id)
        if self.name is None:
            self.name = self.id
        if self.metadata is None:
            self.metadata = {}

    def model_dump(self) -> Dict[str, Any]:
        """Provide model_dump for dictionary serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "metadata": dict(self.metadata),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to plain dictionary."""
        return self.model_dump()


@dataclass
class CausalEdge:
    """Represents a directional relationship/edge between two nodes in the causal graph."""
    source_id: str
    target_id: str
    relationship: Union[CausalRelationship, str]
    evidence_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.source_id or not str(self.source_id).strip():
            raise ValueError("Edge source_id cannot be empty.")
        if not self.target_id or not str(self.target_id).strip():
            raise ValueError("Edge target_id cannot be empty.")

        self.source_id = str(self.source_id)
        self.target_id = str(self.target_id)

        # Validate relationship strictly
        rel_str = self.relationship.value if isinstance(self.relationship, Enum) else str(self.relationship)
        valid_rels = {r.value for r in CausalRelationship}
        if rel_str not in valid_rels:
            raise RelationshipValidationError(
                f"Invalid relationship type '{rel_str}'. Allowed: {sorted(list(valid_rels))}"
            )
        self.relationship = CausalRelationship(rel_str)

        # Ensure evidence_ids is a unique, deterministic list of non-empty strings
        raw_evidence = self.evidence_ids or []
        seen = set()
        clean_ev = []
        for ev in raw_evidence:
            ev_str = str(ev).strip()
            if ev_str and ev_str not in seen:
                seen.add(ev_str)
                clean_ev.append(ev_str)
        self.evidence_ids = clean_ev

        if self.metadata is None:
            self.metadata = {}

    def model_dump(self) -> Dict[str, Any]:
        """Provide model_dump for dictionary serialization."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship.value if isinstance(self.relationship, Enum) else str(self.relationship),
            "evidence_ids": list(self.evidence_ids),
            "metadata": dict(self.metadata),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to plain dictionary."""
        return self.model_dump()


@dataclass
class GraphValidationResult:
    """Validation output for a CausalGraph."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    downgraded_claims: List[Dict[str, Any]] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        """Provide model_dump for dictionary serialization."""
        return {
            "is_valid": self.is_valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "downgraded_claims": [dict(c) for c in self.downgraded_claims],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to plain dictionary."""
        return self.model_dump()


class CausalGraph:
    """Directed causal graph representing relationships between investigation entities and evidence."""

    def __init__(
        self,
        nodes: Optional[List[Union[CausalNode, Dict[str, Any]]]] = None,
        edges: Optional[List[Union[CausalEdge, Dict[str, Any]]]] = None,
    ):
        self._nodes: Dict[str, CausalNode] = {}
        self._edges: Dict[tuple, CausalEdge] = {}

        if nodes:
            for n in nodes:
                self.add_node(n)

        if edges:
            for e in edges:
                self.add_edge(e)

    def add_node(self, node: Union[CausalNode, Dict[str, Any], str]) -> CausalNode:
        """Add a node to the graph without mutating caller input."""
        if isinstance(node, str):
            node_obj = CausalNode(id=node)
        elif isinstance(node, dict):
            node_obj = CausalNode(
                id=str(node.get("id", "")),
                name=node.get("name"),
                entity_type=str(node.get("entity_type", "concept")),
                metadata=dict(node.get("metadata") or {}),
            )
        elif isinstance(node, CausalNode):
            node_obj = CausalNode(
                id=node.id,
                name=node.name,
                entity_type=node.entity_type,
                metadata=dict(node.metadata),
            )
        else:
            raise TypeError(f"Invalid node type: {type(node)}")

        self._nodes[node_obj.id] = node_obj
        return node_obj

    def get_node(self, node_id: str) -> Optional[CausalNode]:
        """Retrieve a node by ID."""
        return self._nodes.get(str(node_id))

    @property
    def nodes(self) -> Dict[str, CausalNode]:
        """Return a copy of nodes dictionary."""
        return {nid: CausalNode(n.id, n.name, n.entity_type, dict(n.metadata)) for nid, n in self._nodes.items()}

    @property
    def edges(self) -> List[CausalEdge]:
        """Return a deterministic list of edges."""
        sorted_keys = sorted(self._edges.keys())
        res = []
        for k in sorted_keys:
            e = self._edges[k]
            res.append(CausalEdge(
                source_id=e.source_id,
                target_id=e.target_id,
                relationship=e.relationship,
                evidence_ids=list(e.evidence_ids),
                metadata=dict(e.metadata),
            ))
        return res

    def add_edge(
        self,
        edge: Union[CausalEdge, Dict[str, Any]],
        auto_downgrade: bool = False,
        auto_create_nodes: bool = True,
    ) -> CausalEdge:
        """Add an edge to the graph deterministically.
        
        Handles duplicate edges by merging evidence IDs deterministically.
        If auto_downgrade is True and a CAUSES claim lacks supporting evidence,
        it is safely downgraded to CONTRIBUTES_TO.
        """
        if isinstance(edge, dict):
            src_id = str(edge.get("source_id", ""))
            tgt_id = str(edge.get("target_id", ""))
            rel_val = edge.get("relationship", "")
            ev_ids = list(edge.get("evidence_ids") or [])
            meta = dict(edge.get("metadata") or {})
        elif isinstance(edge, CausalEdge):
            src_id = edge.source_id
            tgt_id = edge.target_id
            rel_val = edge.relationship
            ev_ids = list(edge.evidence_ids)
            meta = dict(edge.metadata)
        else:
            raise TypeError(f"Invalid edge type: {type(edge)}")

        rel_enum = rel_val if isinstance(rel_val, CausalRelationship) else CausalRelationship(str(rel_val))

        # Check CAUSES evidence requirement if auto_downgrade requested
        if rel_enum == CausalRelationship.CAUSES and not ev_ids and auto_downgrade:
            rel_enum = CausalRelationship.CONTRIBUTES_TO
            meta["downgraded_from"] = CausalRelationship.CAUSES.value
            meta["downgrade_reason"] = "CAUSES relationship lacked supporting evidence."

        edge_obj = CausalEdge(
            source_id=src_id,
            target_id=tgt_id,
            relationship=rel_enum,
            evidence_ids=ev_ids,
            metadata=meta,
        )

        if auto_create_nodes:
            if edge_obj.source_id not in self._nodes:
                self.add_node(edge_obj.source_id)
            if edge_obj.target_id not in self._nodes:
                self.add_node(edge_obj.target_id)

        key = (edge_obj.source_id, edge_obj.target_id, edge_obj.relationship.value)
        if key in self._edges:
            existing = self._edges[key]
            # Merge evidence_ids deterministically
            combined_ev = list(existing.evidence_ids)
            for eid in edge_obj.evidence_ids:
                if eid not in combined_ev:
                    combined_ev.append(eid)
            merged_meta = dict(existing.metadata)
            merged_meta.update(edge_obj.metadata)

            updated = CausalEdge(
                source_id=existing.source_id,
                target_id=existing.target_id,
                relationship=existing.relationship,
                evidence_ids=combined_ev,
                metadata=merged_meta,
            )
            self._edges[key] = updated
            return updated
        else:
            self._edges[key] = edge_obj
            return edge_obj

    def upgrade_relationship(
        self,
        source_id: str,
        target_id: str,
        current_relationship: Union[CausalRelationship, str],
        target_relationship: Union[CausalRelationship, str],
        evidence_ids: Optional[List[str]] = None,
    ) -> CausalEdge:
        """Attempt to upgrade a relationship.
        
        Strictly prevents automatic conversion of PRECEDES or CORRELATES_WITH to CAUSES
        unless sufficient supporting evidence is supplied.
        """
        curr_rel = current_relationship if isinstance(current_relationship, CausalRelationship) else CausalRelationship(str(current_relationship))
        tgt_rel = target_relationship if isinstance(target_relationship, CausalRelationship) else CausalRelationship(str(target_relationship))

        ev_ids = list(evidence_ids or [])

        # Check for PRECEDES / CORRELATES_WITH -> CAUSES automatic conversion attempt
        if curr_rel in {CausalRelationship.PRECEDES, CausalRelationship.CORRELATES_WITH} and tgt_rel == CausalRelationship.CAUSES:
            if not ev_ids:
                raise RelationshipValidationError(
                    f"Cannot automatically convert '{curr_rel.value}' to '{tgt_rel.value}' without supporting evidence."
                )

        # Remove existing edge key if present
        old_key = (str(source_id), str(target_id), curr_rel.value)
        existing_meta = {}
        if old_key in self._edges:
            existing_meta = dict(self._edges[old_key].metadata)
            del self._edges[old_key]

        return self.add_edge({
            "source_id": source_id,
            "target_id": target_id,
            "relationship": tgt_rel,
            "evidence_ids": ev_ids,
            "metadata": existing_meta,
        })

    def validate(
        self,
        known_evidence_ids: Optional[Union[Set[str], List[str], List[Any], Dict[str, Any]]] = None,
    ) -> GraphValidationResult:
        """Validate causal graph integrity, relationship semantics, and evidence traceability."""
        errors: List[str] = []
        warnings: List[str] = []
        downgraded: List[Dict[str, Any]] = []

        # Extract known evidence set if provided
        known_ev_set: Optional[Set[str]] = None
        if known_evidence_ids is not None:
            known_ev_set = set()
            if isinstance(known_evidence_ids, (set, list, tuple)):
                for item in known_evidence_ids:
                    if isinstance(item, str):
                        known_ev_set.add(item)
                    elif isinstance(item, dict):
                        if "id" in item:
                            known_ev_set.add(str(item["id"]))
                    elif hasattr(item, "id"):
                        known_ev_set.add(str(getattr(item, "id")))
            elif isinstance(known_evidence_ids, dict):
                for k in known_evidence_ids.keys():
                    known_ev_set.add(str(k))

        for key, edge in sorted(self._edges.items()):
            # 1. Node existence check
            if edge.source_id not in self._nodes:
                errors.append(f"Edge source node '{edge.source_id}' does not exist in graph.")
            if edge.target_id not in self._nodes:
                errors.append(f"Edge target node '{edge.target_id}' does not exist in graph.")

            # 2. Traceability check
            if known_ev_set is not None:
                for eid in edge.evidence_ids:
                    if eid not in known_ev_set:
                        errors.append(
                            f"Unknown evidence ID '{eid}' referenced in relationship from '{edge.source_id}' to '{edge.target_id}'."
                        )

            # 3. CAUSES evidence requirement check
            if edge.relationship == CausalRelationship.CAUSES:
                if not edge.evidence_ids:
                    errors.append(
                        f"CAUSES relationship from '{edge.source_id}' to '{edge.target_id}' lacks supporting evidence."
                    )

            # 4. PRECEDES and CORRELATES_WITH check
            if edge.relationship in {CausalRelationship.PRECEDES, CausalRelationship.CORRELATES_WITH}:
                if edge.metadata.get("asserts_causation", False):
                    errors.append(
                        f"Relationship '{edge.relationship.value}' from '{edge.source_id}' to '{edge.target_id}' cannot assert causation automatically."
                    )

            # Track downgraded edges in result
            if "downgraded_from" in edge.metadata:
                downgraded.append({
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "original_relationship": edge.metadata["downgraded_from"],
                    "current_relationship": edge.relationship.value,
                    "reason": edge.metadata.get("downgrade_reason", ""),
                })

        is_valid = len(errors) == 0
        return GraphValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            downgraded_claims=downgraded,
        )

    def model_dump(self) -> Dict[str, Any]:
        """Serialize graph to deterministic plain dictionary."""
        return {
            "nodes": [n.model_dump() for n in self.nodes.values()],
            "edges": [e.model_dump() for e in self.edges],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to plain dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalGraph":
        """Reconstruct CausalGraph from dictionary without mutating input."""
        nodes = data.get("nodes") or []
        edges = data.get("edges") or []
        return cls(nodes=nodes, edges=edges)

    @classmethod
    def from_investigation_context(
        cls,
        context: Any,
        auto_downgrade: bool = False,
    ) -> "CausalGraph":
        """Build a CausalGraph from a VerificationContext or dict containing causal_claims."""
        graph = cls()
        causal_claims = []
        evidence_items = []

        if isinstance(context, dict):
            causal_claims = context.get("causal_claims") or []
            evidence_items = context.get("evidence_items") or []
            hypotheses = context.get("hypotheses") or []
        elif hasattr(context, "causal_claims"):
            causal_claims = getattr(context, "causal_claims") or []
            evidence_items = getattr(context, "evidence_items") or []
            hypotheses = getattr(context, "hypotheses") or []

        # Add evidence nodes
        for ev in evidence_items:
            ev_id = str(ev.get("id") if isinstance(ev, dict) else getattr(ev, "id", ""))
            if ev_id:
                graph.add_node(CausalNode(id=ev_id, entity_type="evidence"))

        # Add hypothesis nodes
        for hyp in hypotheses:
            hyp_id = str(hyp.get("id") if isinstance(hyp, dict) else getattr(hyp, "id", ""))
            if hyp_id:
                graph.add_node(CausalNode(id=hyp_id, entity_type="hypothesis"))

        # Add causal claims as edges
        for claim in causal_claims:
            graph.add_edge(claim, auto_downgrade=auto_downgrade)

        return graph

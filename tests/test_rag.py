import pytest
from pathlib import Path

from backend.app.rag.knowledge_base import KnowledgeBase, KnowledgeDocument, KnowledgeChunk, chunk_text
from backend.app.rag.retriever import LexicalRetriever, RetrievalResult, tokenize
from backend.tools.executor import ToolExecutor
from backend.tools.registry import ToolRegistry, search_past_incidents, search_runbooks
from backend.app.agent.controller import InvestigationController
from backend.app.agent.planner import Planner, AgentAction
from backend.app.agent.state import InvestigationState, InvestigationStatus
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus
from backend.app.agent.evaluator_bridge import bridge_evidence_evaluator


def test_chunking_logic():
    text = "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10"
    chunks = chunk_text(text, chunk_size=4, overlap=2)
    assert len(chunks) > 1
    assert chunks[0][0] == "Word1 Word2 Word3 Word4"
    assert "Word3 Word4" in chunks[1][0]


def test_knowledge_base_loading():
    kb = KnowledgeBase()
    kb.load_all()
    assert len(kb.documents) >= 5
    assert len(kb.chunks) >= 5
    doc_ids = list(kb.documents.keys())
    assert "INC-HIST-001" in doc_ids
    assert "RB-001" in doc_ids


def test_lexical_retriever_ranking_and_top_k():
    kb = KnowledgeBase()
    kb.load_all()
    retriever = LexicalRetriever(kb)
    
    results = retriever.retrieve(query="Connection Pool Exhaustion api_gateway", top_k=2)
    assert len(results) <= 2
    assert len(results) >= 1
    top_hit = results[0]
    assert top_hit.document_id == "INC-HIST-001"
    assert top_hit.score > 0.1
    assert top_hit.source_type == "historical_incident"


def test_retriever_service_filtering():
    kb = KnowledgeBase()
    kb.load_all()
    retriever = LexicalRetriever(kb)

    results = retriever.retrieve(query="504 gateway timeout", service="api_gateway", top_k=5)
    for r in results:
        assert r.service == "api_gateway"


def test_retriever_no_data_threshold():
    kb = KnowledgeBase()
    kb.load_all()
    retriever = LexicalRetriever(kb)

    results = retriever.retrieve(query="nonexistent_xyz_term_12345", min_score=0.5)
    assert len(results) == 0


def test_search_past_incidents_tool_executor():
    executor = ToolExecutor()
    action = {
        "tool": "search_past_incidents",
        "arguments": {"query": "Connection Pool Exhaustion", "service": "api_gateway", "top_k": 2}
    }
    result = executor.execute(action)
    assert result.status == "success"
    assert len(result.evidence_ids) >= 1
    assert "KB-INC-HIST-001" in result.evidence_ids
    assert len(result.provenance) >= 1
    prov = result.provenance[0]
    assert prov["document_id"] == "INC-HIST-001"
    assert "source_path" in prov
    assert "snippet" in prov


def test_search_runbooks_tool_executor():
    executor = ToolExecutor()
    action = {
        "tool": "search_runbooks",
        "arguments": {"query": "Diagnosing 504 Gateway Timeouts", "service": "api_gateway", "top_k": 2}
    }
    result = executor.execute(action)
    assert result.status == "success"
    assert len(result.evidence_ids) >= 1
    assert "KB-RB-001" in result.evidence_ids
    assert result.provenance[0]["source_type"] == "runbook"


def test_search_no_match_behavior():
    executor = ToolExecutor()
    action = {
        "tool": "search_past_incidents",
        "arguments": {"query": "completely_unrelated_query_phrase_zzxx"}
    }
    result = executor.execute(action)
    assert result.status == "no_data"
    assert result.evidence_ids == []
    assert len(result.observations) == 1
    assert result.provenance == []


def test_historical_knowledge_vs_evidence_distinction():
    executor = ToolExecutor()
    res = executor.execute({
        "tool": "search_past_incidents",
        "arguments": {"query": "Connection Pool Exhaustion"}
    })
    prov = res.provenance[0]
    assert prov["source_type"] == "historical_incident"
    # Ensure source_type is explicit, distinguishing it from live telemetry evidence
    assert prov["source_type"] != "elastic"
    assert prov["source_type"] != "prometheus"


def test_rag_changes_planner_next_action_flow():
    """
    Deterministic flow test:
    1. Initial state has missing_evidence = ["runbooks", "active_connections"]
    2. Planner selects search_runbooks action first because runbooks is in missing_evidence.
    3. Controller executes search_runbooks, retrieving RB-001.
    4. Runbook observation addresses 'runbooks' missing_evidence, removing it from state.missing_evidence.
    5. In next iteration, state.missing_evidence now only contains 'active_connections'.
    6. Planner now selects query_metrics to address 'active_connections'.
    """
    state = InvestigationState(
        incident={"id": "sc_rag_1", "description": "504 Gateway Timeout on api_gateway", "service": "api_gateway"},
        goal="Determine root cause",
        missing_evidence=["runbooks", "active_connections"],
    )
    hypotheses = [
        Hypothesis(id="hyp-1", statement="Connection pool exhaustion in api_gateway", status=HypothesisStatus.GENERATED)
    ]
    available_tools = [
        {"name": "search_runbooks", "required_params": []},
        {"name": "query_metrics", "required_params": []},
    ]

    controller = InvestigationController()
    executor = ToolExecutor()

    # Iteration 1
    state = controller.run_iteration(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=executor,
        evidence_evaluator=bridge_evidence_evaluator,
    )

    # Verify search_runbooks was selected and executed in iteration 1
    assert state.actions_taken[0]["tool"] == "search_runbooks"
    assert "runbooks" not in state.missing_evidence
    assert "active_connections" in state.missing_evidence

    # Iteration 2
    state = controller.run_iteration(
        state=state,
        hypotheses=hypotheses,
        available_tools=available_tools,
        executor=executor,
        evidence_evaluator=bridge_evidence_evaluator,
    )

    # Verify planner's next action shifted to query_metrics based on updated state
    assert state.actions_taken[1]["tool"] == "query_metrics"


def test_rag_evaluation_fixture():
    """Deterministic evaluation benchmark for RAG retrieval performance."""
    kb = KnowledgeBase()
    kb.load_all()
    retriever = LexicalRetriever(kb)

    eval_queries = [
        {"query": "Connection Pool Exhaustion", "service": "api_gateway", "expected_doc": "INC-HIST-001"},
        {"query": "Rate Limit Cascade", "service": "payment_service", "expected_doc": "INC-HIST-002"},
        {"query": "Database Lock Contention", "service": "user_service", "expected_doc": "RB-003"},
    ]

    top_1_hits = 0
    top_k_hits = 0
    total = len(eval_queries)

    for item in eval_queries:
        results = retriever.retrieve(query=item["query"], service=item["service"], top_k=3)
        doc_ids = [r.document_id for r in results]
        
        if doc_ids and doc_ids[0] == item["expected_doc"]:
            top_1_hits += 1
        if item["expected_doc"] in doc_ids:
            top_k_hits += 1

        # Check provenance completeness
        for r in results:
            prov = r.to_provenance()
            assert "document_id" in prov
            assert "chunk_id" in prov
            assert "source_path" in prov
            assert "score" in prov

    assert top_1_hits == total
    assert top_k_hits == total

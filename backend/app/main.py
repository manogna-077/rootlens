import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone
from backend.app.schemas import (
    ApprovalRequest,
    ApprovalResponse,
    EvidenceModel,
    HealthResponse,
    IncidentModel,
)
from backend.app.agent.controller import InvestigationController
from backend.app.agent.evaluator_bridge import bridge_evidence_evaluator
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus, build_initial_hypotheses
from backend.app.agent.state import InvestigationState
from backend.app.reasoning.verifier import Verifier, VerificationContext
from backend.app.reasoning.evidence_score import calculate_evidence_score
from backend.app.reasoning.disconfirmation import evaluate_disconfirmation
from backend.tools.executor import ToolExecutor
from backend.tools.registry import ToolRegistry, load_evidence

app = FastAPI(title="RootLens API", version="0.1.0")

# In-memory store for investigation states, hypotheses, and approvals
investigations_store: Dict[str, InvestigationState] = {}
hypotheses_store: Dict[str, List[Hypothesis]] = {}
approvals_store: Dict[str, Dict[str, Any]] = {}


def _get_data_dir() -> Path:
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data" / "incidents"
    if not data_dir.exists():
        data_dir = Path("data/incidents").resolve()
    return data_dir


def _load_incident_data(id: str) -> dict:
    incidents_dir = _get_data_dir()
    file_path = incidents_dir / f"{id}.json"
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Incident '{id}' not found")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Error reading incident data")


def _get_incident_evidence(id: str) -> List[dict]:
    evidence_files = [
        "code_changes.json",
        "dependencies.json",
        "deployments.json",
        "logs.json",
        "metrics.json",
    ]
    matched_evidence = []
    collected_ids = set()
    if id in investigations_store:
        collected_ids = set(investigations_store[id].evidence_ids)

    for filename in evidence_files:
        items = load_evidence(filename)
        for item in items:
            ev_id = item.get("id")
            inc_id = item.get("incident_id")
            if (inc_id and inc_id == id) or (ev_id and ev_id in collected_ids):
                matched_evidence.append(item)
    return matched_evidence


@app.get("/api/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/incidents", response_model=List[IncidentModel])
def list_incidents() -> List[IncidentModel]:
    incidents_dir = _get_data_dir()
    incidents: List[IncidentModel] = []
    if incidents_dir.exists():
        for file_path in sorted(incidents_dir.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    incidents.append(IncidentModel(**data))
            except Exception:
                continue
    return incidents


@app.get("/api/incidents/{id}", response_model=IncidentModel)
def get_incident(id: str) -> IncidentModel:
    data = _load_incident_data(id)
    return IncidentModel(**data)


@app.get("/api/incidents/{id}/evidence", response_model=List[EvidenceModel])
def get_incident_evidence_endpoint(id: str) -> List[EvidenceModel]:
    _load_incident_data(id)
    evidence_items = _get_incident_evidence(id)
    return [EvidenceModel(**item) for item in evidence_items]


@app.get("/api/incidents/{id}/timeline")
def get_incident_timeline_endpoint(id: str) -> List[Dict[str, Any]]:
    _load_incident_data(id)
    if id in investigations_store:
        state = investigations_store[id]
        if state.audit_events:
            return state.audit_events
        if state.actions_taken:
            return state.actions_taken

    evidence_items = _get_incident_evidence(id)
    sorted_evidence = sorted(evidence_items, key=lambda x: x.get("timestamp", ""))
    return sorted_evidence


@app.post("/api/incidents/{id}/investigate", response_model=InvestigationState)
def run_incident_investigation(id: str) -> InvestigationState:
    incident_data = _load_incident_data(id)

    # Prepare initial state
    initial_state = InvestigationState(
        incident=incident_data,
        goal=f"Determine root cause for incident {id}",
        missing_evidence=(
            ["deployments", "logs", "metrics"]
            if "Deployment regression" in incident_data.get("description", "")
            else ["metrics", "logs", "deployments"]
            if "Database failure" in incident_data.get("description", "")
            else ["check_dependency_health", "logs"]
            if "External dependency" in incident_data.get("description", "")
            else ["deployments", "logs"]
        ),
    )

    # Initial hypotheses constructed via general builder
    initial_hypotheses = build_initial_hypotheses(incident_data)

    available_tools = [
        {"name": "get_deployments", "required_params": []},
        {"name": "search_logs", "required_params": []},
        {"name": "query_metrics", "required_params": []},
        {"name": "compare_versions", "required_params": []},
        {"name": "check_dependency_health", "required_params": []},
        {"name": "search_past_incidents", "required_params": []},
        {"name": "search_runbooks", "required_params": []},
    ]

    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry)
    controller = InvestigationController()

    final_state = controller.run_investigation(
        state=initial_state,
        hypotheses=initial_hypotheses,
        available_tools=available_tools,
        executor=executor,
        evidence_evaluator=bridge_evidence_evaluator,
    )

    investigations_store[id] = final_state
    hypotheses_store[id] = initial_hypotheses

    return final_state


@app.get("/api/incidents/{id}/investigation", response_model=InvestigationState)
def get_incident_investigation(id: str) -> InvestigationState:
    _load_incident_data(id)
    if id not in investigations_store:
        raise HTTPException(status_code=404, detail=f"No investigation found for incident '{id}'")
    return investigations_store[id]


@app.get("/api/incidents/{id}/hypotheses", response_model=List[Hypothesis])
def get_incident_hypotheses(id: str) -> List[Hypothesis]:
    _load_incident_data(id)
    if id not in hypotheses_store:
        raise HTTPException(status_code=404, detail=f"No hypotheses found for incident '{id}'")
    return hypotheses_store[id]


@app.get("/api/incidents/{id}/graph")
def get_incident_graph(id: str) -> Dict[str, Any]:
    incident_data = _load_incident_data(id)
    evidence_items = _get_incident_evidence(id)
    state = investigations_store.get(id)
    hypotheses = hypotheses_store.get(id, [])

    context = VerificationContext(
        evidence_items=evidence_items,
        hypotheses=[h.model_dump() for h in hypotheses],
    )
    verification_result = Verifier.verify(context)

    nodes = [{"id": incident_data["id"], "type": "incident", "label": incident_data.get("description", id)}]
    edges = []

    for hyp in hypotheses:
        nodes.append({"id": hyp.id, "type": "hypothesis", "label": hyp.statement, "status": hyp.status})
        edges.append({"source": incident_data["id"], "target": hyp.id, "relationship": "investigates"})

    for ev in evidence_items:
        nodes.append({"id": ev["id"], "type": "evidence", "label": ev.get("observation", "")})

    if verification_result and hasattr(verification_result, "causal_links"):
        for link in getattr(verification_result, "causal_links", []):
            edges.append(link)

    return {
        "incident_id": id,
        "nodes": nodes,
        "edges": edges,
        "verification_status": verification_result.status if verification_result else "UNKNOWN",
    }


@app.get("/api/incidents/{id}/report")
def get_incident_report(id: str) -> Dict[str, Any]:
    incident_data = _load_incident_data(id)
    evidence_items = _get_incident_evidence(id)
    state = investigations_store.get(id)
    hypotheses = hypotheses_store.get(id, [])

    context = VerificationContext(
        evidence_items=evidence_items,
        hypotheses=[h.model_dump() for h in hypotheses],
    )
    verification_result = Verifier.verify(context)

    score_results = []
    hypotheses_dicts = [h.model_dump() for h in hypotheses]
    for hyp_dict in hypotheses_dicts:
        score_res = calculate_evidence_score(
            hypothesis=hyp_dict,
            evidence_items=evidence_items,
            all_hypotheses=hypotheses_dicts,
        )
        score_results.append(score_res.model_dump() if hasattr(score_res, "model_dump") else str(score_res))

    disconfirmation_results = []
    for hyp in hypotheses:
        if hyp.disconfirming_condition:
            for ev in evidence_items:
                disc_res = evaluate_disconfirmation(ev, hyp)
                if disc_res.disconfirms:
                    disconfirmation_results.append({
                        "hypothesis_id": hyp.id,
                        "evidence_id": disc_res.evidence_id,
                        "disconfirmed": True,
                        "reason": disc_res.reason,
                    })

    return {
        "incident_id": id,
        "incident": incident_data,
        "verification": verification_result.model_dump() if hasattr(verification_result, "model_dump") else str(verification_result),
        "evidence_scores": score_results,
        "disconfirmation_evaluations": disconfirmation_results,
        "investigation_status": state.status if state else "NOT_STARTED",
        "hypotheses_count": len(hypotheses),
        "evidence_count": len(evidence_items),
        "approval": approvals_store.get(id, {"approved": False, "status": "pending"}),
    }

@app.get("/api/incidents/{id}/audit")
def get_incident_audit(id: str) -> List[Dict[str, Any]]:
    _load_incident_data(id)
    if id not in investigations_store:
        raise HTTPException(
            status_code=404,
            detail=f"No investigation found for incident '{id}'"
        )

    events: List[Dict[str, Any]] = []

    if id in investigations_store:
        events.extend(investigations_store[id].audit_events)

    if id in approvals_store:
        approval = approvals_store[id]
        events.append({
            "id": f"approval-{id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": approval.get("approver") or "admin",
            "action": "approval_update",
            "details": {
                "approved": approval.get("approved"),
                "comments": approval.get("comments"),
                "status": approval.get("status"),
            },
        })

    return events

@app.post("/api/incidents/{id}/approval", response_model=ApprovalResponse)
def post_incident_approval(id: str, request: ApprovalRequest) -> ApprovalResponse:
    _load_incident_data(id)
    status_str = "approved" if request.approved else "rejected"
    approval_data = {
        "incident_id": id,
        "approved": request.approved,
        "approver": request.approver,
        "comments": request.comments,
        "status": status_str,
    }
    approvals_store[id] = approval_data

    # If investigation state exists, record an audit event for approval
    if id in investigations_store:
        investigations_store[id].audit_events.append({
            "event": "approval_update",
            "approved": request.approved,
            "approver": request.approver,
            "comments": request.comments,
        })

    return ApprovalResponse(
        incident_id=id,
        approved=request.approved,
        status=status_str,
        message=f"Investigation approval for incident '{id}' updated to {status_str}.",
    )


import json
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException

from backend.app.schemas import HealthResponse, IncidentModel
from backend.app.agent.controller import InvestigationController
from backend.app.agent.evaluator_bridge import bridge_evidence_evaluator
from backend.app.agent.hypotheses import Hypothesis, HypothesisStatus
from backend.app.agent.state import InvestigationState
from backend.tools.executor import ToolExecutor
from backend.tools.registry import ToolRegistry

app = FastAPI(title="RootLens API", version="0.1.0")

# In-memory store for investigation states and associated hypotheses
investigations_store: Dict[str, InvestigationState] = {}
hypotheses_store: Dict[str, List[Hypothesis]] = {}


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


@app.post("/api/incidents/{id}/investigate", response_model=InvestigationState)
def run_incident_investigation(id: str) -> InvestigationState:
    incident_data = _load_incident_data(id)

    # Prepare initial state
    initial_state = InvestigationState(
        incident=incident_data,
        goal=f"Determine root cause for incident {id}",
        missing_evidence=["deployments", "logs", "metrics"],
    )

    # Initial default hypothesis
    initial_hypotheses = [
        Hypothesis(
            id=f"hyp-{id}-1",
            statement=f"Investigating root cause for {incident_data.get('description', id)}",
            status=HypothesisStatus.GENERATED,
        )
    ]

    available_tools = [
        {"name": "get_deployments", "required_params": []},
        {"name": "search_logs", "required_params": []},
        {"name": "query_metrics", "required_params": []},
        {"name": "compare_versions", "required_params": []},
        {"name": "check_dependency_health", "required_params": []},
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
    # Ensure incident exists
    _load_incident_data(id)
    if id not in investigations_store:
        raise HTTPException(status_code=404, detail=f"No investigation found for incident '{id}'")
    return investigations_store[id]


@app.get("/api/incidents/{id}/hypotheses", response_model=List[Hypothesis])
def get_incident_hypotheses(id: str) -> List[Hypothesis]:
    # Ensure incident exists
    _load_incident_data(id)
    if id not in hypotheses_store:
        raise HTTPException(status_code=404, detail=f"No hypotheses found for incident '{id}'")
    return hypotheses_store[id]

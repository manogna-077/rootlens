import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / 'data' / 'evidence'

class ToolResult:
    def __init__(self, tool: str, status: str, evidence_ids: list, observations: list, provenance: list):
        self.tool = tool
        self.status = status
        self.evidence_ids = evidence_ids
        self.observations = observations
        self.provenance = provenance
        
    def to_dict(self):
        return {
            "tool": self.tool,
            "status": self.status,
            "evidence_ids": self.evidence_ids,
            "observations": self.observations,
            "provenance": self.provenance
        }

def load_evidence(filename: str):
    file_path = DATA_DIR / filename
    if not file_path.exists():
        return []
    with open(file_path, 'r') as f:
        return json.load(f)

def get_deployments(service: str = None, time_range: str = None):
    deployments = load_evidence('deployments.json')
    if service:
        deployments = [d for d in deployments if d.get('service') == service]
    
    evidence_ids = [d['id'] for d in deployments]
    observations = [
        {"summary": d['observation'], "service": d.get('service'), "incident_id": d.get('incident_id')}
        for d in deployments
    ]
    provenance = [d['provenance'] for d in deployments]
    
    return ToolResult(
        tool="get_deployments",
        status="success" if deployments else "no_data",
        evidence_ids=evidence_ids,
        observations=observations,
        provenance=provenance
    )

def search_logs(service: str = None, query: str = None):
    logs = load_evidence('logs.json')
    if service:
        logs = [l for l in logs if l.get('service') == service]
    if query:
        logs = [l for l in logs if query.lower() in l.get('observation', '').lower()]
        
    evidence_ids = [l['id'] for l in logs]
    observations = [
        {"summary": l['observation'], "service": l.get('service'), "incident_id": l.get('incident_id')}
        for l in logs
    ]
    provenance = [l['provenance'] for l in logs]
    
    return ToolResult(
        tool="search_logs",
        status="success" if logs else "no_data",
        evidence_ids=evidence_ids,
        observations=observations,
        provenance=provenance
    )

def query_metrics(service: str = None, metric_name: str = None):
    metrics = load_evidence('metrics.json')
    if service:
        metrics = [m for m in metrics if m.get('service') == service]
    if metric_name:
        metrics = [m for m in metrics if m.get('metadata', {}).get('metric_name') == metric_name]
        
    evidence_ids = [m['id'] for m in metrics]
    observations = [
        {"summary": m['observation'], "service": m.get('service'), "incident_id": m.get('incident_id')}
        for m in metrics
    ]
    provenance = [m['provenance'] for m in metrics]
    
    return ToolResult(
        tool="query_metrics",
        status="success" if metrics else "no_data",
        evidence_ids=evidence_ids,
        observations=observations,
        provenance=provenance
    )

def compare_versions(service: str = None):
    code_changes = load_evidence('code_changes.json')
    if service:
        code_changes = [c for c in code_changes if c.get('service') == service]
        
    evidence_ids = [c['id'] for c in code_changes]
    observations = [
        {"summary": c['observation'], "service": c.get('service'), "incident_id": c.get('incident_id')}
        for c in code_changes
    ]
    provenance = [c['provenance'] for c in code_changes]
    
    return ToolResult(
        tool="compare_versions",
        status="success" if code_changes else "no_data",
        evidence_ids=evidence_ids,
        observations=observations,
        provenance=provenance
    )

def check_dependency_health(service: str = None):
    deps = load_evidence('dependencies.json')
    if service:
        deps = [d for d in deps if d.get('service') == service or d.get('metadata', {}).get('provider', '').lower() == service.lower()]
        
    evidence_ids = [d['id'] for d in deps]
    observations = [
        {"summary": d['observation'], "service": d.get('service'), "incident_id": d.get('incident_id')}
        for d in deps
    ]
    provenance = [d['provenance'] for d in deps]
    
    return ToolResult(
        tool="check_dependency_health",
        status="success" if deps else "no_data",
        evidence_ids=evidence_ids,
        observations=observations,
        provenance=provenance
    )

_RAG_RETRIEVER = None

def _get_rag_retriever():
    global _RAG_RETRIEVER
    if _RAG_RETRIEVER is None:
        from backend.app.rag.knowledge_base import KnowledgeBase
        from backend.app.rag.retriever import LexicalRetriever
        kb = KnowledgeBase()
        kb.load_all()
        _RAG_RETRIEVER = LexicalRetriever(kb)
    return _RAG_RETRIEVER

def search_past_incidents(query: str = "", service: str = None, top_k: int = 3):
    retriever = _get_rag_retriever()
    results = retriever.retrieve(
        query=query,
        source_type="historical_incident",
        service=service,
        top_k=top_k,
        min_score=0.05
    )
    if not results:
        return ToolResult(
            tool="search_past_incidents",
            status="no_data",
            evidence_ids=[],
            observations=[{"summary": f"No relevant historical incidents found for query '{query}'"}],
            provenance=[]
        )
    
    evidence_ids = [f"KB-{res.document_id}" for res in results]
    observations = [
        {
            "summary": f"[Historical Incident] {res.title}: {res.snippet}",
            "service": res.service,
            "source_type": res.source_type,
            "document_id": res.document_id,
            "score": round(res.score, 4)
        }
        for res in results
    ]
    provenance = [res.to_provenance() for res in results]

    return ToolResult(
        tool="search_past_incidents",
        status="success",
        evidence_ids=evidence_ids,
        observations=observations,
        provenance=provenance
    )

def search_runbooks(query: str = "", service: str = None, top_k: int = 3):
    retriever = _get_rag_retriever()
    results = retriever.retrieve(
        query=query,
        source_type="runbook",
        service=service,
        top_k=top_k,
        min_score=0.05
    )
    if not results:
        return ToolResult(
            tool="search_runbooks",
            status="no_data",
            evidence_ids=[],
            observations=[{"summary": f"No relevant runbooks found for query '{query}'"}],
            provenance=[]
        )
    
    evidence_ids = [f"KB-{res.document_id}" for res in results]
    observations = [
        {
            "summary": f"[Runbook] {res.title}: {res.snippet}",
            "service": res.service,
            "source_type": res.source_type,
            "document_id": res.document_id,
            "score": round(res.score, 4)
        }
        for res in results
    ]
    provenance = [res.to_provenance() for res in results]

    return ToolResult(
        tool="search_runbooks",
        status="success",
        evidence_ids=evidence_ids,
        observations=observations,
        provenance=provenance
    )

class ToolRegistry:
    def __init__(self):
        self.tools = {
            "get_deployments": get_deployments,
            "search_logs": search_logs,
            "query_metrics": query_metrics,
            "compare_versions": compare_versions,
            "check_dependency_health": check_dependency_health,
            "search_past_incidents": search_past_incidents,
            "search_runbooks": search_runbooks
        }
        
    def execute(self, tool_name: str, **kwargs):
        if tool_name not in self.tools:
            return ToolResult(
                tool=tool_name,
                status="error_invalid_tool",
                evidence_ids=[],
                observations=[f"Unknown tool: {tool_name}"],
                provenance=[]
            )
        try:
            return self.tools[tool_name](**kwargs)
        except Exception as e:
            return ToolResult(
                tool=tool_name,
                status="error_execution_failed",
                evidence_ids=[],
                observations=[f"Tool execution failed: {str(e)}"],
                provenance=[]
            )

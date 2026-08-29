from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_incidents():
    response = client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    incident_ids = [inc["id"] for inc in data]
    assert "scenario_a" in incident_ids
    assert "scenario_b" in incident_ids


def test_get_incident_success():
    response = client.get("/api/incidents/scenario_a")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "scenario_a"
    assert "description" in data
    assert "signal" in data


def test_get_incident_not_found():
    response = client.get("/api/incidents/non_existent_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_investigation_flow():
    incident_id = "scenario_a"

    # Before investigation, GET investigation & GET hypotheses should return 404
    res_inv_before = client.get(f"/api/incidents/{incident_id}/investigation")
    assert res_inv_before.status_code == 404

    res_hyp_before = client.get(f"/api/incidents/{incident_id}/hypotheses")
    assert res_hyp_before.status_code == 404

    # Trigger investigation
    res_post = client.post(f"/api/incidents/{incident_id}/investigate")
    assert res_post.status_code == 200
    post_data = res_post.json()
    assert post_data["incident"]["id"] == incident_id
    assert post_data["status"] in ["RUNNING", "COMPLETED", "INSUFFICIENT_EVIDENCE", "FAILED"]
    assert post_data["iteration"] >= 1

    # Now GET investigation should return 200 and saved state
    res_inv_after = client.get(f"/api/incidents/{incident_id}/investigation")
    assert res_inv_after.status_code == 200
    inv_data = res_inv_after.json()
    assert inv_data["incident"]["id"] == incident_id
    assert inv_data["iteration"] == post_data["iteration"]

    # Now GET hypotheses should return 200 and hypotheses array
    res_hyp_after = client.get(f"/api/incidents/{incident_id}/hypotheses")
    assert res_hyp_after.status_code == 200
    hyp_data = res_hyp_after.json()
    assert isinstance(hyp_data, list)
    assert len(hyp_data) > 0
    assert hyp_data[0]["id"].startswith(f"hyp-{incident_id}")


def test_investigation_endpoints_invalid_incident():
    invalid_id = "unknown_incident_xyz"

    res_post = client.post(f"/api/incidents/{invalid_id}/investigate")
    assert res_post.status_code == 404

    res_inv = client.get(f"/api/incidents/{invalid_id}/investigation")
    assert res_inv.status_code == 404

    res_hyp = client.get(f"/api/incidents/{invalid_id}/hypotheses")
    assert res_hyp.status_code == 404


def test_get_evidence():
    response = client.get("/api/incidents/scenario_a/evidence")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["incident_id"] == "scenario_a"


def test_get_timeline():
    # Test timeline before investigation (returns evidence timeline)
    response = client.get("/api/incidents/scenario_a/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Trigger investigation
    client.post("/api/incidents/scenario_a/investigate")

    # Test timeline after investigation (returns audit events/actions taken)
    response_after = client.get("/api/incidents/scenario_a/timeline")
    assert response_after.status_code == 200
    data_after = response_after.json()
    assert isinstance(data_after, list)


def test_get_graph():
    response = client.get("/api/incidents/scenario_a/graph")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "scenario_a"
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_get_report():
    response = client.get("/api/incidents/scenario_a/report")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "scenario_a"
    assert "verification" in data
    assert "evidence_scores" in data
    assert "disconfirmation_evaluations" in data


def test_get_audit():
    # Before investigation -> 404
    res_before = client.get("/api/incidents/scenario_b/audit")
    assert res_before.status_code == 404

    # Trigger investigation
    client.post("/api/incidents/scenario_b/investigate")

    # After investigation -> 200
    res_after = client.get("/api/incidents/scenario_b/audit")
    assert res_after.status_code == 200
    data = res_after.json()
    assert isinstance(data, list)


def test_post_approval():
    # Post approval for valid incident
    res = client.post(
        "/api/incidents/scenario_a/approval",
        json={"approved": True, "approver": "lead_engineer", "comments": "Approved RCA"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == "scenario_a"
    assert data["approved"] is True
    assert data["status"] == "approved"

    # Verify approval state reflects in report
    res_rep = client.get("/api/incidents/scenario_a/report")
    assert res_rep.status_code == 200
    report_data = res_rep.json()
    assert report_data["approval"]["approved"] is True


def test_stage_3_endpoints_invalid_incident():
    invalid_id = "non_existent_123"

    assert client.get(f"/api/incidents/{invalid_id}/evidence").status_code == 404
    assert client.get(f"/api/incidents/{invalid_id}/timeline").status_code == 404
    assert client.get(f"/api/incidents/{invalid_id}/graph").status_code == 404
    assert client.get(f"/api/incidents/{invalid_id}/report").status_code == 404
    assert client.get(f"/api/incidents/{invalid_id}/audit").status_code == 404
    assert client.post(f"/api/incidents/{invalid_id}/approval", json={"approved": True}).status_code == 404



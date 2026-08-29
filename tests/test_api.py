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


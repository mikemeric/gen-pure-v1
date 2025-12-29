"""Integration tests"""
import pytest

def test_health_check(test_client):
    response = test_client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_login_flow(test_client):
    response = test_client.post(
        "/auth/login",
        json={"username": "demo", "password": "DemoPassword123!"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

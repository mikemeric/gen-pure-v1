"""Basic tests"""
import pytest

def test_import_core():
    from core import config, exceptions, models
    assert True

def test_config():
    from core.config import get_config
    cfg = get_config()
    assert cfg.environment in ["development", "production", "testing"]

def test_api():
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

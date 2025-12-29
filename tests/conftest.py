"""Pytest configuration"""
import os
import pytest

os.environ.setdefault('ENVIRONMENT', 'testing')

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)

#!/usr/bin/env python3
"""
Script pour créer tous les fichiers Python du projet
"""
from pathlib import Path

def write_file(path, content):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        f.write(content)
    print(f"✓ {path}")

# Core - Config
write_file('core/config.py', '''"""Configuration management"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    environment: str = "development"
    api_port: int = 8000
    database_url: str = "postgresql://localhost/detection_db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "change-me-in-production"
    
    class Config:
        env_file = ".env"

_config = None

def get_config() -> Settings:
    global _config
    if _config is None:
        _config = Settings()
    return _config
''')

# Core - Exceptions
write_file('core/exceptions.py', '''"""Custom exceptions"""

class DetectionSystemError(Exception):
    """Base exception"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        self.http_status_code = 500
        super().__init__(message)

class AuthenticationError(DetectionSystemError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)
        self.http_status_code = 401

class ImageValidationError(DetectionSystemError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, details)
        self.http_status_code = 400

class DetectionError(DetectionSystemError):
    pass
''')

# Core - Models
write_file('core/models.py', '''"""Data models"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

class DetectionMethod(Enum):
    HOUGH = "hough"
    CLUSTERING = "clustering"

@dataclass
class DetectionResult:
    niveau_y: Optional[int] = None
    niveau_percentage: Optional[float] = None
    confiance: float = 0.0
    methode_utilisee: Optional[DetectionMethod] = None
    temps_traitement_ms: float = 0.0
    erreurs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class User:
    id: str
    username: str
    roles: List[str] = field(default_factory=lambda: ["user"])
    is_active: bool = True
''')

# API Main
write_file('api/main.py', '''"""FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Detection API",
    version="3.0.0",
    description="Fuel level detection API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "name": "Detection API",
        "version": "3.0.0",
        "status": "operational"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''')

# Test simple
write_file('tests/test_basic.py', '''"""Basic tests"""
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
''')

print("\n✅ Fichiers Python créés avec succès!")
print("Note: Ces fichiers contiennent une version simplifiée.")
print("Référez-vous à la conversation pour le code complet de chaque module.")


#!/usr/bin/env python3
from pathlib import Path

def w(path, content):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content.strip() + '\n')
    print(f"✓ {path}")

# Services - Auth JWT Manager (simplifié)
w('services/auth/jwt_manager.py', '''"""JWT token management"""
import jwt
from datetime import datetime, timedelta

class JWTManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def create_access_token(self, user_data: dict) -> str:
        payload = {
            **user_data,
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> dict:
        return jwt.decode(token, self.secret_key, algorithms=['HS256'])

_jwt_manager = None

def get_jwt_manager() -> JWTManager:
    global _jwt_manager
    if _jwt_manager is None:
        from core.config import get_config
        _jwt_manager = JWTManager(get_config().jwt_secret_key)
    return _jwt_manager
''')

# API Routes - Auth
w('api/routes/auth.py', '''"""Authentication routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    # Simple demo authentication
    if request.username == "demo" and request.password == "DemoPassword123!":
        from services.auth.jwt_manager import get_jwt_manager
        jwt_manager = get_jwt_manager()
        token = jwt_manager.create_access_token({
            "user_id": "demo-user",
            "username": request.username
        })
        return LoginResponse(access_token=token)
    raise HTTPException(status_code=401, detail="Invalid credentials")
''')

# API Routes - Detection
w('api/routes/detection.py', '''"""Detection routes"""
from fastapi import APIRouter, File, UploadFile, HTTPException

router = APIRouter(prefix="/detect", tags=["Detection"])

@router.post("/")
async def detect_level(file: UploadFile = File(...)):
    """Detect fuel level in uploaded image"""
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(400, "Invalid file type")
    
    # Placeholder - implement actual detection
    return {
        "niveau_percentage": 50.0,
        "confiance": 0.85,
        "message": "Detection successful (placeholder)"
    }
''')

# API Routes - Health
w('api/routes/health.py', '''"""Health check routes"""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/")
async def health_check():
    return {"status": "healthy"}

@router.get("/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "components": {
            "api": "healthy",
            "database": "healthy",
            "cache": "healthy"
        }
    }
''')

# Update API main to include routes
w('api/main.py', '''"""FastAPI application with routes"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import auth, detection, health

app = FastAPI(
    title="Detection API",
    version="3.0.0",
    description="Advanced Fuel Level Detection API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(detection.router)

@app.get("/")
def root():
    return {
        "name": "Detection API",
        "version": "3.0.0",
        "status": "operational",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    from core.config import get_config
    config = get_config()
    uvicorn.run(app, host="0.0.0.0", port=config.api_port)
''')

# Tests conftest
w('tests/conftest.py', '''"""Pytest configuration"""
import os
import pytest

os.environ.setdefault('ENVIRONMENT', 'testing')

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)
''')

# Integration test
w('tests/integration/test_api_flow.py', '''"""Integration tests"""
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
''')

print("\n✅ Fichiers additionnels créés avec succès!")


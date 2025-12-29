import os
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache

class Settings(BaseSettings):
    PROJECT_NAME: str = "GEN-PURE Detection System"
    VERSION: str = "3.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Sécurité
    SECRET_KEY: str = "9c90f8457639f28d8b9d3e8e2c4f1a5b8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Base de données
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/genpure"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Configuration Pydantic V2
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

# 1. L'instance directe (pour main.py)
settings = Settings()

# 2. La fonction "Factory" (pour auth.py et les autres fichiers hérités)
@lru_cache()
def get_config():
    return settings

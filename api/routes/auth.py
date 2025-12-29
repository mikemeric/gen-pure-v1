from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from core.config import get_config
from core.security import create_access_token, verify_password
from api.schemas.token import Token

router = APIRouter()
settings = get_config()

@router.post("/login/access-token", response_model=Token)
async def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Simulation d'authentification pour le démarrage (A remplacer par DB check)
    # Pour l'instant, accepte n'importe quel login pour que le dashboard s'affiche
    if not form_data.username:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            subject=form_data.username, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.config import get_config
from api.routes import auth, detection

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

config = get_config()

# CORRECTIF ICI : On met le titre en dur pour éviter l'erreur
app = FastAPI(
    title="GEN-PURE API",
    version="3.0.0",
    description="GEN-PURE API v3 - Detection & Monitoring System"
)

# Configuration CORS (Ouvert pour le mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(detection.router)

# --- WEB APP MOBILE ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Detection API v3.0.0")
    if config.environment == "development":
        logger.warning("⚠️  Running in DEVELOPMENT mode")

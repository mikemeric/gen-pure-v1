import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Imports de votre structure
from api.routes import auth, detection, health
from api.middleware.auth_middleware import AuthMiddleware
from core.config import settings
from infrastructure.database.postgresql import init_db
from services.health.startup import setup_health_checker

app = FastAPI(title="GEN-PURE v3.0", version="3.0.0")

# --- 1. CONFIGURATION DES DOSSIERS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Montage des fichiers statiques
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configuration du moteur de templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- 2. MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. ROUTES API ---
app.include_router(auth.router, prefix="/auth", tags=["Security"])
app.include_router(detection.router, prefix="/api/detection", tags=["Detection"])
app.include_router(health.router, prefix="/health", tags=["Monitoring"])

# --- 4. GESTION DU DÉMARRAGE (STARTUP) ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Tentative de démarrage du service...")
    
    # Initialisation de la base de données avec sécurité
    try:
        await init_db()
        print("✅ Base de données initialisée (ou déjà connectée)")
    except Exception as e:
        print(f"⚠️ Attention : Échec de connexion DB au démarrage : {e}")
        print("ℹ️ Le service continue de tourner sans DB pour l'instant.")

    # Configuration du Health Checker
    try:
        await setup_health_checker(app)
        print("✅ Health Checker activé")
    except Exception as e:
        print(f"⚠️ Attention : Impossible de démarrer le Health Checker : {e}")

# --- 5. ROUTES D'INTERFACE ---

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/admin")
async def read_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/manager")
async def read_manager(request: Request):
    # Vérifie si le fichier existe pour éviter une erreur 500
    if not os.path.exists(os.path.join(TEMPLATES_DIR, "manager.html")):
        return {"error": "Le fichier templates/manager.html est introuvable"}
    return templates.TemplateResponse("manager.html", {"request": request})

# --- 6. LANCEMENT ---
if __name__ == "__main__":
    import uvicorn
    # Render utilise la variable d'environnement PORT
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
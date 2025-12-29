import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Imports de votre structure
from api.routes import auth, detection, health
from infrastructure.database.postgresql import init_db
from services.health.startup import setup_health_checker

app = FastAPI(title="GEN-PURE v3.0", version="3.0.0")

# --- 1. CONFIGURATION DES DOSSIERS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Création des dossiers s'ils n'existent pas pour éviter les erreurs au lancement
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Montage des fichiers statiques (CSS, JS, Images)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Configuration du moteur de templates (HTML)
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

# --- 4. GESTION DU STARTUP ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Démarrage de GEN-PURE...")
    
    # 1. Initialisation Base de données (Mock ou réelle)
    try:
        await init_db()
        print("✅ Base de données initialisée")
    except Exception as e:
        print(f"⚠️ Erreur DB: {e}")

    # 2. Lancement du Health Checker (Surveillance système)
    try:
        await setup_health_checker(app)
        print("✅ Health Checker actif")
    except Exception as e:
        print(f"⚠️ Warning: Le Health Checker n'a pas pu démarrer: {e}")

# --- 5. ROUTES D'INTERFACE ---

# Route Accueil (Login)
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route Manager
@app.get("/manager")
async def read_manager(request: Request):
    if not os.path.exists(os.path.join(TEMPLATES_DIR, "manager.html")):
        return {"error": "Le fichier templates/manager.html est introuvable."}
    return templates.TemplateResponse("manager.html", {"request": request})

# Route Admin
@app.get("/admin")
async def read_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    # Le port est récupéré depuis l'environnement pour Render (défaut 10000)
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
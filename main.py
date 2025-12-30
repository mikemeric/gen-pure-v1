import os
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Form, File, UploadFile, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse

# --- IMPORTATION DES UNITÉS D'ÉLITE ---
from services.detection.fuel_detector import GlobalIntelligenceUnit
from services.database.memory_unit import MemoryUnit
from services.reporting.legiste_agent import LegisteAgent
from services.reporting.bi_generator import BIGenerator
from services.analytics.vision_agent import VisionAgent
from services.security.gardien_agent import GardienAgent

# --- INITIALISATION DU SYSTÈME ---
app = FastAPI(title="GEN-PURE OMEGA V2.5 - SOUVERAINETÉ TOTALE")

# Activation des Unités de Commandement
memory = MemoryUnit()
intelligence_unit = GlobalIntelligenceUnit()
legiste = LegisteAgent()
bi_gen = BIGenerator()
vision_agent = VisionAgent()
gardien = GardienAgent()

# Configuration des Chemins et Dossiers Critiques
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Création des répertoires pour éviter les erreurs d'écriture
os.makedirs("data", exist_ok=True)
os.makedirs("static/reports/bi", exist_ok=True)

# --- ROUTES D'ACCÈS ET SÉCURITÉ ---

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == "Idriss" and password == "OMEGA123":
        token = gardien.create_access_token({"sub": username})
        resp = RedirectResponse(url="/manager", status_code=status.HTTP_302_FOUND)
        # Sécurisation du cookie pour le Dashboard
        resp.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        return resp
    return templates.TemplateResponse("login.html", {"request": {}, "error": "ACCÈS REFUSÉ"})

# --- POSTE DE COMMANDEMENT (DASHBOARD) ---

@app.get("/manager")
async def manager_dashboard(request: Request, source_filter: str = "ALL", category: str = "ALL"):
    """Dashboard Central avec Filtrage BI et Chronos"""
    all_scans = memory.get_all_scans()
    
    # Ré-entraînement automatique de l'IA avec les données existantes
    intelligence_unit.train_model(all_scans)
    
    # Logique de filtrage BI
    filtered = [s for s in all_scans if 
                (source_filter == "ALL" or source_filter.upper() in s['station'].upper()) and 
                (category == "ALL" or s.get('category') == category)]
    
    # Données pour le Graphique Chronos (10 derniers points chronologiques)
    chronos_data = sorted(filtered, key=lambda x: x['timestamp'])[-10:]
    chart_labels = [s['timestamp'].split(' ')[0] for s in chronos_data]
    chart_values = [s['turbidity'] for s in chronos_data]

    return templates.TemplateResponse("manager.html", {
        "request": request,
        "scans": filtered,
        "rejections": memory.get_all_rejections(),
        "fleet": memory.get_fleet(),
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "system_status": "IA_SOUVERAINE_ACTIVE"
    })

# --- GESTION DE LA FLOTTE (ASSETS) ---

@app.post("/api/fleet/register")
async def register_asset(asset_id: str = Form(...), category: str = Form(...)):
    """Enregistre un Camion, GE ou Station dans le registre"""
    new_asset = {
        "id": asset_id,
        "category": category,
        "timestamp": datetime.now().strftime("%Y-%m-%d")
    }
    memory.register_asset(new_asset)
    return RedirectResponse(url="/manager", status_code=status.HTTP_302_FOUND)

# --- UNITÉ DE DÉTECTION ET IA ---

@app.post("/api/detection/detect")
async def api_detect(file: UploadFile = File(...), station: str = Form(...), category: str = Form(...)):
    """Analyse IA, Archivage et Certification"""
    img_bytes = await file.read()
    
    # Analyse Vision Souveraine (ML Local)
    diag = await intelligence_unit.analyze_with_turbo_mode(img_bytes, station)
    
    # Traitement des Rejets (Discipline)
    if diag['risk_level'] == 'REJET':
        memory.archive_rejection({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "station": station,
            "reason": diag['diagnostic']
        })
        return JSONResponse(content=diag)
    
    # Préparation du rapport complet
    diag.update({
        "report_id": f"GP-{uuid.uuid4().hex[:8].upper()}",
        "station": station,
        "category": category,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "manual_validation": diag['risk_level']
    })
    
    # Archivage et génération du Certificat PDF individuel
    memory.archive_diagnostic(diag)
    legiste.generate_certificate(diag)
    
    return JSONResponse(content=diag)

@app.post("/api/ia/correct")
async def correct_ia(report_id: str = Form(...), verdict: str = Form(...)):
    """Protocole de Supervision Manuelle : Le Général éduque l'IA"""
    scans = memory.get_all_scans()
    updated = False
    for s in scans:
        if s['report_id'] == report_id:
            s.update({"manual_validation": verdict, "risk_level": verdict})
            updated = True
            break
    
    if updated:
        memory.overwrite_scans(scans)
        intelligence_unit.train_model(scans) # Ré-entraînement immédiat
        return {"status": "IA_TRAINED_SUCCESSFULLY"}
    
    raise HTTPException(status_code=404, detail="Rapport non identifié")

# --- ANALYSE BI ET VISION ---

@app.get("/manager/compare")
async def compare_view(request: Request, id1: str, id2: str):
    """Analyse différentielle entre deux prélèvements"""
    scan_a = memory.get_scan_by_id(id1)
    scan_b = memory.get_scan_by_id(id2)
    data = vision_agent.prepare_comparison(scan_a, scan_b)
    return templates.TemplateResponse("compare.html", {"request": request, "data": data})

@app.get("/api/bi/generate-monthly")
async def gen_bi(month: str = "DECEMBRE"):
    """Génération du Rapport BI Consolidé (PDF)"""
    scans = memory.get_all_scans()
    path = bi_gen.generate_monthly_report(scans, month)
    return JSONResponse(content={"status": "SUCCESS", "report_url": f"/{path}"})

# --- SCAN MOBILE ---

@app.get("/scan")
async def scan_page(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

# --- DÉMARRAGE ---

if __name__ == "__main__":
    import uvicorn
    # Configuration pour Render ou Local
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
import os
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse

# --- IMPORTATION DE L'ÉTAT-MAJOR (UNITÉS D'ÉLITE) ---
from services.detection.fuel_detector import GlobalIntelligenceUnit
from services.database.memory_unit import MemoryUnit
from services.reporting.legiste_agent import LegisteAgent
from services.logistics.flux_agent import FluxAgent
from services.security.gardien_agent import GardienAgent
from services.notifications.spectre_agent import SpectreAgent
from services.analytics.vision_agent import VisionAgent

# --- INITIALISATION DU QUARTIER GÉNÉRAL ---
app = FastAPI(title="GEN-PURE OMEGA - Système de Défense Intégral")

# Activation des Unités
memory = MemoryUnit()
intelligence_unit = GlobalIntelligenceUnit()
legiste = LegisteAgent()
flux_agent = FluxAgent()
gardien = GardienAgent()
spectre = SpectreAgent()
vision_agent = VisionAgent()

# Configuration Infrastructure
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
os.makedirs("static/reports", exist_ok=True)

# --- ACCÈS ET SÉCURITÉ (AGENT GARDIEN) ---

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == "Idriss" and password == "OMEGA123":
        token = gardien.create_access_token({"sub": username, "role": "GENERAL"})
        response = RedirectResponse(url="/manager", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        return response
    return templates.TemplateResponse("login.html", {"request": {}, "error": "ACCÈS REFUSÉ"})

# --- POSTE DE COMMANDEMENT (FLUX & VISION) ---

@app.get("/manager")
async def manager_dashboard(request: Request):
    all_history = memory.get_all_scans()
    map_data = flux_agent.get_geo_map_data(all_history)
    # On passe également les alertes réseaux détectées par FLUX
    network_alerts = flux_agent.identify_network_threats(all_history[0] if all_history else {}, all_history)
    
    return templates.TemplateResponse("manager.html", {
        "request": request,
        "map_points": map_data,
        "active_alerts": network_alerts,
        "system_status": "PROTOCOLE_VISION_ACTIF"
    })

@app.get("/manager/compare")
async def compare_scans(request: Request, id1: str, id2: str):
    """Phase 6 : Agent VISION en action"""
    scan_a = memory.get_scan_by_id(id1)
    scan_b = memory.get_scan_by_id(id2)
    
    if not scan_a or not scan_b:
        raise HTTPException(status_code=404, detail="Rapports introuvables pour comparaison")
        
    comparison = vision_agent.prepare_comparison(scan_a, scan_b)
    return templates.TemplateResponse("compare.html", {"request": request, "data": comparison})

# --- UNITÉ DE SCAN ET DÉTECTION (SENTINELLE / SPECTRE) ---

@app.get("/scan")
async def scan_page(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

@app.post("/api/detection/detect")
async def api_detect(file: UploadFile = File(...), station: str = Form(...)):
    try:
        # 1. Analyse IA
        image_bytes = await file.read()
        history = memory.get_station_trend(station, limit=5)
        diag = await intelligence_unit.analyze_with_turbo_mode(image_bytes, station, history)
        
        # 2. Sceaux et Archivage
        report_id = f"GP-{uuid.uuid4().hex[:8].upper()}"
        diag.update({
            "report_id": report_id, 
            "station": station, 
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signature_scellee": gardien.seal_report(report_id, "IDRISS")
        })
        memory.archive_diagnostic(diag)
        
        # 3. Certification et Alerte Spectre
        pdf_path = legiste.generate_certificate(diag)
        diag["pdf_link"] = f"/{pdf_path}"
        
        if diag.get('risk_level') == 'DANGER':
            spectre.send_critical_alert(diag)
            
        return JSONResponse(content=diag)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "ERREUR_SYSTEME", "detail": str(e)})

# --- DOCUMENTATION ---
@app.get("/guide")
async def operational_guide(request: Request):
    return templates.TemplateResponse("guide.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
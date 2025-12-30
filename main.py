import os
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, Form, File, UploadFile, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse

# --- SERVICES CERTIFIÉS ---
from services.detection.fuel_detector import GlobalIntelligenceUnit
from services.database.memory_unit import MemoryUnit
from services.reporting.legiste_agent import LegisteAgent
from services.reporting.bi_generator import BIGenerator
from services.analytics.vision_agent import VisionAgent
from services.security.gardien_agent import GardienAgent

app = FastAPI(title="GEN-PURE OMEGA - CAMEROUN EDITION")

# Initialisation
memory = MemoryUnit()
intelligence_unit = GlobalIntelligenceUnit()
legiste = LegisteAgent()
bi_gen = BIGenerator()
vision_agent = VisionAgent()
gardien = GardienAgent()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
os.makedirs("data", exist_ok=True)
os.makedirs("static/reports/bi", exist_ok=True)

# --- ACCÈS ---
@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == "Idriss" and password == "OMEGA123":
        token = gardien.create_access_token({"sub": username})
        resp = RedirectResponse(url="/manager", status_code=status.HTTP_302_FOUND)
        resp.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
        return resp
    return templates.TemplateResponse("login.html", {"request": {}, "error": "ACCÈS REFUSÉ"})

# --- DASHBOARD & BI ---
@app.get("/manager")
async def manager_dashboard(request: Request, source_filter: str = "ALL", category: str = "ALL"):
    all_scans = memory.get_all_scans()
    
    # Entraînement continu
    intelligence_unit.train_model(all_scans)
    
    # Filtrage
    filtered = [s for s in all_scans if 
                (source_filter == "ALL" or source_filter.upper() in s['station'].upper()) and 
                (category == "ALL" or s.get('category') == category)]
    
    # Chronos Data
    chronos_data = sorted(filtered, key=lambda x: x['timestamp'])[-10:]
    
    return templates.TemplateResponse("manager.html", {
        "request": request,
        "scans": filtered,
        "rejections": memory.get_all_rejections(),
        "fleet": memory.get_fleet(),
        "chart_labels": [s['timestamp'].split(' ')[0] for s in chronos_data],
        "chart_values": [s['turbidity'] for s in chronos_data]
    })

# --- COMPARAISON VISION ---
@app.get("/manager/compare")
async def compare_view(request: Request, id1: str, id2: str):
    scan_a = memory.get_scan_by_id(id1)
    scan_b = memory.get_scan_by_id(id2)
    data = vision_agent.prepare_comparison(scan_a, scan_b)
    return templates.TemplateResponse("compare.html", {"request": request, "data": data})

# --- API FLOTTE (RESTORED) ---
@app.post("/api/fleet/register")
async def register_asset(asset_id: str = Form(...), category: str = Form(...)):
    memory.register_asset({
        "id": asset_id, "category": category, 
        "timestamp": datetime.now().strftime("%Y-%m-%d")
    })
    return RedirectResponse(url="/manager", status_code=status.HTTP_302_FOUND)

# --- API DÉTECTION (UPDATED WITH GPS) ---
@app.post("/api/detection/detect")
async def api_detect(
    file: UploadFile = File(...), 
    station: str = Form(...), 
    category: str = Form(...),
    lat: str = Form(None),
    lng: str = Form(None)
):
    img_bytes = await file.read()
    diag = await intelligence_unit.analyze_with_turbo_mode(img_bytes, station)
    
    # Enrichissement contextuel
    diag.update({
        "report_id": f"GP-{uuid.uuid4().hex[:6].upper()}",
        "station": station,
        "category": category,
        "lat": lat, "lng": lng,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "manual_validation": diag['risk_level']
    })

    if diag['risk_level'] == 'REJET': # Rejet technique (image noire, flou total)
        memory.archive_rejection(diag)
        return JSONResponse(content=diag)

    # Archivage complet (Même si DANGER, on garde la preuve pour le ROI)
    memory.archive_diagnostic(diag)
    
    # Si c'est un mauvais carburant, on le log aussi dans les incidents pour stats rapides
    if diag['risk_level'] != "NORMAL":
        memory.archive_rejection(diag) 

    legiste.generate_certificate(diag)
    return JSONResponse(content=diag)

# --- SUPERVISION ---
@app.post("/api/ia/correct")
async def correct_ia(report_id: str = Form(...), verdict: str = Form(...)):
    scans = memory.get_all_scans()
    updated = False
    for s in scans:
        if s['report_id'] == report_id:
            s.update({"manual_validation": verdict, "risk_level": verdict})
            updated = True
    if updated:
        memory.overwrite_scans(scans)
        intelligence_unit.train_model(scans)
        return {"status": "OK"}
    raise HTTPException(404, "Scan introuvable")

@app.get("/api/bi/generate-monthly")
async def gen_bi(month: str = "COURANT"):
    path = bi_gen.generate_monthly_report(memory.get_all_scans(), month)
    return JSONResponse(content={"status": "SUCCESS", "report_url": f"/{path}"})

@app.get("/scan")
async def scan_page(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
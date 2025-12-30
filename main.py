import os
import uuid
from datetime import datetime
from typing import Optional

# Framework Web & Sécurité
from fastapi import FastAPI, Request, Form, File, UploadFile, status, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse

# --- IMPORTS DES SERVICES (Vos Agents) ---
# Assurez-vous que les fichiers services/... existent bien
from services.detection.fuel_detector import GlobalIntelligenceUnit
from services.database.memory_unit import MemoryUnit
from services.reporting.legiste_agent import LegisteAgent
from services.reporting.bi_generator import BIGenerator
from services.analytics.vision_agent import VisionAgent
from services.security.gardien_agent import GardienAgent

# --- CONFIGURATION INITIALE ---
app = FastAPI(title="GEN-PURE V3.4 - PLATEFORME SaaS SOUVERAINE")

# Instanciation des Agents (Démarrage des Services)
memory = MemoryUnit()
intelligence_unit = GlobalIntelligenceUnit()
legiste = LegisteAgent()
bi_gen = BIGenerator()
vision_agent = VisionAgent()
gardien = GardienAgent()

# Montage des dossiers statiques (CSS, JS, Images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration du moteur de templates (HTML)
templates = Jinja2Templates(directory="templates")

# Création des répertoires critiques au démarrage
os.makedirs("data", exist_ok=True)
os.makedirs("static/reports/bi", exist_ok=True)
os.makedirs("static/certificates", exist_ok=True)

# ---------------------------------------------------------
# SÉCURITÉ & AUTHENTIFICATION (MIDDLEWARE)
# ---------------------------------------------------------

async def get_current_user(request: Request):
    """
    Vérifie le cookie 'access_token'.
    Retourne le profil utilisateur ou None si non connecté.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        # Le token est souvent préfixé par "Bearer "
        scheme, _, param = token.partition(" ")
        payload = gardien.verify_token(param)
        return payload # Contient {sub, role, company_id}
    except Exception:
        return None

# ---------------------------------------------------------
# ROUTES D'AUTHENTIFICATION (LOGIN / LOGOUT)
# ---------------------------------------------------------

@app.get("/")
async def login_page(request: Request):
    """Page d'accueil (Formulaire de connexion)"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """
    Hub de connexion unique.
    Redirige vers le bon tableau de bord selon le Rôle (SuperAdmin, Manager, Driver).
    """
    user = memory.verify_user(username, password)
    
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "IDENTIFIANT OU MOT DE PASSE INCORRECT"
        })
    
    # Création du Token enrichi (Identité + Rôle + Entreprise)
    token_data = {
        "sub": user['username'],
        "role": user['role'],
        "company_id": user['company_id']
    }
    token = gardien.create_access_token(token_data)
    
    # Aiguillage selon le grade
    if user['role'] == 'SUPERADMIN':
        url = "/superadmin"
    elif user['role'] == 'MANAGER': # Client Licence Fleet Defense
        url = "/manager"
    else: # DRIVER (Chauffeur) ou AUDITOR (Expert) -> Scan direct
        url = "/scan"
        
    resp = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    resp.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return resp

@app.get("/logout")
async def logout():
    """Déconnexion et suppression du cookie"""
    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie("access_token")
    return resp

# ---------------------------------------------------------
# PORTAIL SUPER-ADMIN (GESTION DES LICENCES)
# ---------------------------------------------------------

@app.get("/superadmin")
async def superadmin_panel(request: Request):
    """Interface de Dieu (Idriss) pour gérer les clients"""
    user = await get_current_user(request)
    if not user or user['role'] != 'SUPERADMIN':
        return RedirectResponse("/") # Éjection des intrus
    
    return templates.TemplateResponse("superadmin.html", {
        "request": request,
        "licenses": memory.get_licenses(),
        "users": memory.get_users()
    })

@app.post("/api/admin/create-client")
async def create_client(
    request: Request,
    company_name: str = Form(...),
    license_type: str = Form(...), # FLEET ou AUDITOR
    admin_name: str = Form(...),
    admin_pass: str = Form(...)
):
    """Génération d'une nouvelle Licence Entreprise + Admin associé"""
    user = await get_current_user(request)
    if not user or user['role'] != 'SUPERADMIN': raise HTTPException(403)

    # 1. Créer la licence (Valable 1 an par défaut)
    expiry = (datetime.now().replace(year=datetime.now().year + 1)).strftime("%Y-%m-%d")
    licence = memory.create_license(company_name, license_type, expiry)
    
    # 2. Créer l'utilisateur Admin du client (MANAGER ou AUDITOR selon licence)
    role = "MANAGER" if license_type == "FLEET" else "AUDITOR"
    memory.create_user(admin_name, admin_pass, role, licence['company_id'])
    
    return RedirectResponse("/superadmin", status_code=302)

# ---------------------------------------------------------
# DASHBOARD MANAGER (CLOISONNÉ PAR ENTREPRISE)
# ---------------------------------------------------------

@app.get("/manager")
async def manager_dashboard(request: Request, source_filter: str = "ALL", category: str = "ALL"):
    """Le Cockpit du client (Licence Fleet Defense)"""
    user = await get_current_user(request)
    # Sécurité : Seuls les Managers et le SuperAdmin entrent ici
    if not user or user['role'] not in ['MANAGER', 'SUPERADMIN']:
        return RedirectResponse("/scan") 
    
    # Récupération des données FILTRÉES par Company_ID
    company_id = user['company_id']
    
    all_scans = memory.get_all_scans(company_id)
    fleet = memory.get_fleet(company_id)
    drivers = memory.get_company_drivers(company_id) # Liste des chauffeurs pour la gestion RH
    
    # Logique de filtrage (Barre de recherche)
    filtered = [s for s in all_scans if 
                (source_filter == "ALL" or source_filter.upper() in s['station'].upper()) and 
                (category == "ALL" or s.get('category') == category)]
    
    # Données pour le graphiques (10 derniers scans)
    chronos_data = sorted(filtered, key=lambda x: x['timestamp'])[-10:]

    return templates.TemplateResponse("manager.html", {
        "request": request,
        "scans": filtered,
        "rejections": [r for r in memory.get_all_rejections() if r.get('company_id') == company_id],
        "fleet": fleet,
        "drivers": drivers, # Passé au template pour le modal "Chauffeurs"
        "chart_labels": [s['timestamp'].split(' ')[0] for s in chronos_data],
        "chart_values": [s['turbidity'] for s in chronos_data],
        "company_id": company_id,
        "user_role": user['role']
    })

# ---------------------------------------------------------
# API : GESTION FLOTTE & RH (Ajout/Suppression)
# ---------------------------------------------------------

@app.post("/api/manager/add-driver")
async def add_driver(request: Request, username: str = Form(...), password: str = Form(...)):
    """Le Manager crée ses propres chauffeurs"""
    user = await get_current_user(request)
    if not user or user['role'] != 'MANAGER': raise HTTPException(403)
    
    # Le chauffeur hérite du Company_ID du Manager
    success = memory.create_user(username, password, "DRIVER", user['company_id'])
    return RedirectResponse("/manager", status_code=302)

@app.post("/api/manager/delete-driver")
async def delete_driver(request: Request, username: str = Form(...)):
    """Le Manager supprime un de ses chauffeurs"""
    user = await get_current_user(request)
    if not user or user['role'] != 'MANAGER': raise HTTPException(403)
    
    if username == user['sub']: # Interdiction de se supprimer soi-même
        return JSONResponse({"error": "Action impossible sur son propre compte"}, status_code=400)

    memory.delete_user(username, user['company_id'])
    return RedirectResponse("/manager", status_code=302)

@app.post("/api/fleet/register")
async def register_asset(request: Request, asset_id: str = Form(...), category: str = Form(...)):
    """Ajout d'un véhicule/GE à la flotte"""
    user = await get_current_user(request)
    if not user or user['role'] != 'MANAGER': raise HTTPException(403)
    
    new_asset = {
        "id": asset_id,
        "category": category,
        "company_id": user['company_id'],
        "timestamp": datetime.now().strftime("%Y-%m-%d")
    }
    memory.register_asset(new_asset)
    return RedirectResponse(url="/manager", status_code=status.HTTP_302_FOUND)

@app.post("/api/fleet/delete")
async def delete_asset(request: Request, asset_id: str = Form(...)):
    """Suppression d'un véhicule/GE de la flotte"""
    user = await get_current_user(request)
    if not user or user['role'] != 'MANAGER': raise HTTPException(403)
    
    memory.delete_asset(asset_id, user['company_id'])
    return RedirectResponse(url="/manager", status_code=status.HTTP_302_FOUND)

# ---------------------------------------------------------
# API : SCAN & DÉTECTION (Cœur du Système)
# ---------------------------------------------------------

@app.get("/scan")
async def scan_page(request: Request):
    """Interface Mobile pour les chauffeurs"""
    user = await get_current_user(request)
    if not user: return RedirectResponse("/")
    return templates.TemplateResponse("scan.html", {"request": request, "user": user})

@app.post("/api/detection/detect")
async def api_detect(
    request: Request,
    file: UploadFile = File(...), 
    station: str = Form(...), 
    category: str = Form(...),
    lat: str = Form(None),
    lng: str = Form(None)
):
    """Réception photo, Analyse IA, Archivage"""
    user = await get_current_user(request)
    
    # Identification contextuelle
    company_id = user['company_id'] if user else "ANONYMOUS"
    user_sub = user['sub'] if user else "Guest"

    img_bytes = await file.read()
    
    # 1. Analyse IA (Détection Anti-Fraude + Physique)
    diag = await intelligence_unit.analyze_with_turbo_mode(img_bytes, station)
    
    # 2. Enrichissement des métadonnées
    diag.update({
        "report_id": f"GP-{uuid.uuid4().hex[:6].upper()}",
        "station": station,
        "category": category,
        "lat": lat, "lng": lng,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "manual_validation": diag['risk_level'],
        "company_id": company_id,
        "scanned_by": user_sub
    })

    # 3. Traitement du verdict
    if diag['risk_level'] == 'REJET':
        memory.archive_rejection(diag) # On garde trace des tentatives de fraude
        return JSONResponse(content=diag)

    memory.archive_diagnostic(diag)
    
    # Si anormal, on ajoute aussi aux rejets pour le calcul ROI
    if diag['risk_level'] != "NORMAL":
        memory.archive_rejection(diag)

    # Génération Certificat PDF (Pour Licence Auditor)
    legiste.generate_certificate(diag)
    
    return JSONResponse(content=diag)

# ---------------------------------------------------------
# API : FEEDBACK LOOP (Amélioration IA)
# ---------------------------------------------------------

@app.post("/api/ia/correct")
async def correct_ia(request: Request, report_id: str = Form(...), verdict: str = Form(...)):
    """Le superviseur corrige un verdict IA"""
    user = await get_current_user(request)
    if not user or user['role'] not in ['MANAGER', 'SUPERADMIN']: raise HTTPException(403)

    scans = memory.get_all_scans(user['company_id'])
    updated = False
    for s in scans:
        if s['report_id'] == report_id:
            s.update({"manual_validation": verdict, "risk_level": verdict})
            updated = True
            break
    
    if updated:
        memory.overwrite_scans(scans)
        intelligence_unit.train_model(scans)
        return {"status": "OK"}
    
    raise HTTPException(404, "Scan introuvable")

# ---------------------------------------------------------
# POINT D'ENTRÉE (Serveur)
# ---------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # Le port est dynamique pour Render, sinon 10000 par défaut
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
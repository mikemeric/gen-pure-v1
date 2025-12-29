from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.detection.fuel_detector import FuelLevelDetector
import os

app = FastAPI(title="GEN-PURE v3.0")
detector = FuelLevelDetector()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scan")
async def scan(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

@app.post("/api/detection/detect")
async def detect(
    file: UploadFile = File(...), 
    station: str = Form(...) # Reçoit l'origine sélectionnée ou saisie
):
    image_bytes = await file.read()
    
    # Analyse par l'IA (Eau, Turbidité, Particules)
    result = await detector.analyze(image_bytes)
    
    # Ajout du contexte pour le Manager
    result["station_origin"] = station
    
    # Simulation de sauvegarde (pourrait être envoyé vers PostgreSQL)
    print(f"--- NOUVEAU SCAN ---")
    print(f"Station: {station} | Statut: {result['status']}")
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
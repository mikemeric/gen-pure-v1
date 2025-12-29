import os
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.detection.fuel_detector import FuelLevelDetector

app = FastAPI()
detector = FuelLevelDetector()

# IMPORTANT: Vérifiez que ces dossiers existent à la racine
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scan")
async def scan_page(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

@app.get("/manager")
async def manager_page(request: Request):
    # On force le rendu du template manager.html
    return templates.TemplateResponse("manager.html", {"request": request, "fleet_status": "Active"})

@app.post("/api/detection/detect")
async def detect(file: UploadFile = File(...), station: str = Form(...)):
    image_bytes = await file.read()
    result = await detector.analyze(image_bytes)
    result["station"] = station
    return result
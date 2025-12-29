import os
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.detection.fuel_detector import FuelLevelDetector

app = FastAPI(title="GEN-PURE PROD")
detector = FuelLevelDetector()

# Configuration
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scan")
async def scan(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

@app.get("/manager")
async def manager(request: Request):
    # Données simulées pour le dashboard (à lier à la DB plus tard)
    return templates.TemplateResponse("manager.html", {
        "request": request,
        "fleet_health": "85%",
        "risk_stations": 2,
        "last_update": "Maintenant"
    })

@app.post("/api/detection/detect")
async def detect(file: UploadFile = File(...)):
    image_bytes = await file.read()
    result = await detector.analyze(image_bytes)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
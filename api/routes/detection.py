import sqlite3
from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid, os, cv2, numpy as np, io
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
from api.middleware.auth_middleware import get_current_user

# --- CONFIGURATION BASE DE DONNEES ---
DB_PATH = "genpure.db"
engine = create_engine(f'sqlite:///{DB_PATH}')
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class ScanRecord(Base):
    __tablename__ = "scans"
    id = Column(String, primary_key=True)
    user = Column(String)
    timestamp = Column(DateTime, default=datetime.now)
    is_compliant = Column(Boolean)
    turbidity = Column(Float)
    water_pct = Column(Float)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    fournisseur = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/api/v2/detect", tags=["Detection"])

# --- PDF AVEC GPS ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'DI-SOLUTIONS : RAPPORT D\'EXPERTISE GEN-PURE', 0, 1, 'L')
        self.ln(5)

@router.post("")
async def detect(
    file: UploadFile = File(...), 
    lat: float = None, 
    lon: float = None, 
    provider: str = "Inconnu",
    token: dict = Depends(get_current_user)
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Algo V5
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    turbidity = round(min(100.0, (cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0) * 100.0), 2)
    is_compliant = turbidity > 20.0
    
    scan_id = str(uuid.uuid4())[:8]
    
    # SAUVEGARDE SQL (HISTORIQUE 30 JOURS)
    db = SessionLocal()
    new_scan = ScanRecord(
        id=scan_id, user=token.get("username"), is_compliant=is_compliant,
        turbidity=turbidity, water_pct=0.0, latitude=lat, longitude=lon, fournisseur=provider
    )
    db.add(new_scan)
    db.commit()
    db.close()
    
    return {
        "scan_id": scan_id, "success": True, "is_compliant": is_compliant,
        "turbidity_score": turbidity, "message": "ANALYSE TERMINEE",
        "timestamp": datetime.now()
    }

@router.get("/report/{scan_id}")
async def get_report(scan_id: str):
    db = SessionLocal()
    res = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
    db.close()
    if not res: raise HTTPException(status_code=404)
    
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"ID SCAN : {res.id}", ln=1)
    pdf.cell(0, 10, f"DATE : {res.timestamp}", ln=1)
    pdf.cell(0, 10, f"POSITION : Lat {res.latitude}, Lon {res.longitude}", ln=1)
    pdf.cell(0, 10, f"RESULTAT : {'CONFORME' if res.is_compliant else 'ALERTE'}", ln=1)
    
    return StreamingResponse(io.BytesIO(pdf.output(dest='S').encode('latin-1')), media_type="application/pdf")

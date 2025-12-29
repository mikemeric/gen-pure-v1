import io
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fpdf import FPDF
import sqlite3

router = APIRouter(prefix="/api/v2/manager", tags=["Manager"])

class MonthlyPDF(FPDF):
    def header(self):
        self.set_fill_color(0, 51, 102) # Bleu DI-SOLUTIONS
        self.rect(0, 0, 210, 40, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 20)
        self.cell(0, 20, 'DI-SOLUTIONS : BILAN MENSUEL', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, 'Rapport de Surveillance Qualite Carburant - GEN-PURE', 0, 1, 'C')
        self.ln(20)

@router.get("/monthly-report")
async def generate_monthly_report():
    # 1. Simulation de données (En V3 ce sera lié à la DB SQL)
    stats = {
        "total_scans": 145,
        "alerts": 12,
        "savings": "24 000 000 FCFA",
        "worst_station": "Station X - Bonaberi"
    }
    
    pdf = MonthlyPDF()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    # Section 1 : Résumé Exécutif
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Periode : Decembre 2025", ln=1)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"- Nombre total de controles effectues : {stats['total_scans']}", ln=1)
    pdf.set_text_color(255, 75, 75) # Orange/Rouge
    pdf.cell(0, 10, f"- Alertes de contamination detectees : {stats['alerts']}", ln=1)
    pdf.set_text_color(0, 51, 102) # Bleu
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"- ESTIMATION DES SINISTRES EVITES : {stats['savings']}", ln=1)
    
    # Section 2 : Analyse Fournisseur
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Analyse Critique des Fournisseurs", ln=1)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"Le point de ravitaillement ayant presente le plus haut taux d'impurete ce mois-ci est : {stats['worst_station']}. Une inspection de leurs cuves est recommandee.")
    
    # Conclusion
    pdf.ln(20)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 8, "Ce rapport est genere automatiquement par la technologie GEN-PURE de DI-SOLUTIONS. Il constitue une preuve d'audit pour vos polices d'assurance et votre maintenance preventive.", 1, 'L', fill=True)

    return StreamingResponse(io.BytesIO(pdf.output(dest='S').encode('latin-1')), media_type="application/pdf")

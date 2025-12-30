import os
from fpdf import FPDF
import qrcode
from datetime import datetime

class LegisteAgent:
    """Agent LÉGISTE : Expert en certification et scellés numériques"""

    def __init__(self):
        self.output_dir = "static/reports"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_certificate(self, diag):
        """Génère un certificat PDF haute sécurité avec QR Code"""
        report_id = diag.get('report_id', 'INCONNU')
        filename = f"CERT-{report_id}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        # 1. Génération du QR Code de traçabilité
        qr_data = f"GEN-PURE|ID:{report_id}|STATION:{diag.get('station')}|STATUS:{diag.get('risk_level')}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_path = os.path.join(self.output_dir, f"QR-{report_id}.png")
        qr_img.save(qr_path)

        # 2. Construction du PDF avec FPDF2
        pdf = FPDF()
        pdf.add_page()
        
        # En-tête de sécurité
        pdf.set_fill_color(30, 64, 175) # Bleu OMEGA
        pdf.rect(0, 0, 210, 40, 'F')
        
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 20, "CERTIFICAT DE CONFORMITE OMEGA", ln=True, align='C')
        
        pdf.set_font("Helvetica", "I", 10)
        pdf.cell(0, 10, f"Document Officiel GEN-PURE - Délivré le {diag.get('timestamp')}", ln=True, align='C')
        
        pdf.ln(20)
        pdf.set_text_color(0, 0, 0)

        # Corps du rapport
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Rapport d'Analyse : #{report_id}", ln=True)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)

        # Détails techniques
        pdf.set_font("Helvetica", "", 12)
        data = [
            ["Source / Station :", diag.get('station')],
            ["Catégorie :", diag.get('category', 'STATION')],
            ["Indice de Turbidité :", f"{diag.get('turbidity')} NTU"],
            ["Verdict IA :", diag.get('risk_level')]
        ]

        for item in data:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(50, 10, item[0])
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(0, 10, str(item[1]), ln=True)

        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "Diagnostic de l'Agent Sentinelle :", ln=True)
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 8, diag.get('diagnostic', 'Aucun détail fourni.'))

        # Insertion du QR Code
        pdf.image(qr_path, x=150, y=50, w=40)

        # Pied de page et Signature
        pdf.set_y(-50)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 10, "SIGNATURE ELECTRONIQUE CERTIFIEE", ln=True, align='R')
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(0, 5, f"Scellé numérique : {diag.get('signature_scellee', 'IDRISS-OMEGA-VERIFIED')}", ln=True, align='R')

        pdf.output(filepath)
        
        # Nettoyage du QR Code temporaire
        if os.path.exists(qr_path):
            os.remove(qr_path)
            
        return filepath
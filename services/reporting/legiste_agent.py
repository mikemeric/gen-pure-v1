from fpdf import FPDF
import qrcode
import os
from datetime import datetime

class LegisteAgent:
    """Agent LÉGISTE : Production de Certificats de Conformité Infalsifiables"""

    def generate_certificate(self, diag_data):
        report_id = diag_data['report_id']
        filename = f"static/reports/CERT-{report_id}.pdf"
        
        # S'assurer que le dossier de stockage existe
        os.makedirs("static/reports", exist_ok=True)

        # 1. Génération du QR Code de Sécurité (Lien vers la Mémoire Centrale)
        qr_data = f"https://gen-pure.onrender.com/verify/{report_id}"
        qr = qrcode.make(qr_data)
        qr_path = f"static/reports/QR-{report_id}.png"
        qr.save(qr_path)

        # 2. Construction du Document PDF
        pdf = FPDF()
        pdf.add_page()
        
        # En-tête Industriel
        pdf.set_font("Arial", 'B', 20)
        pdf.set_text_color(30, 58, 138) # Bleu Marine GEN-PURE
        pdf.cell(0, 15, "CERTIFICAT DE PURETÉ GASOIL", ln=True, align='C')
        
        pdf.set_font("Arial", '', 10)
        pdf.set_text_color(100)
        pdf.cell(0, 10, f"Rapport ID : {report_id} | Date : {diag_data['timestamp']}", ln=True, align='C')
        pdf.ln(10)

        # Section Données de Terrain
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f" ORIGINE : {diag_data['station'].upper()}", ln=True, fill=True)
        pdf.ln(5)

        # Résultats de l'État-Major
        pdf.set_font("Arial", '', 12)
        pdf.set_text_color(0)
        pdf.cell(90, 10, f"Indice de Turbidité : {diag_data['metrics']['turbidity']}%")
        pdf.cell(90, 10, f"Présence d'Eau : {'OUI (CRITIQUE)' if diag_data['metrics']['water'] else 'NON'}", ln=True)
        
        pdf.set_font("Arial", 'B', 14)
        status_color = (220, 38, 38) if "CRITIQUE" in diag_data['status'] else (22, 163, 74)
        pdf.set_text_color(*status_color)
        pdf.cell(0, 15, f"VERDICT : {diag_data['status']}", ln=True)

        # Recommandation Stratégique
        pdf.set_font("Arial", 'I', 11)
        pdf.set_text_color(50)
        pdf.multi_cell(0, 10, f"Note de l'Expert : {diag_data['recommendation']}")

        # Insertion du Sceau QR Code
        pdf.image(qr_path, x=150, y=230, w=40)
        pdf.set_font("Arial", '', 8)
        pdf.text(150, 275, "Scannez pour vérifier l'authenticité")

        pdf.output(filename)
        return filename
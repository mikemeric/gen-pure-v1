import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

class BIGenerator:
    """Agent BI-GENERATOR : Unité d'Élite pour la Synthèse Stratégique OMEGA"""

    def __init__(self):
        self.output_dir = "static/reports/bi"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_monthly_report(self, scans, month_name):
        """Génère un rapport PDF consolidé de haute précision"""
        filename = f"RAPPORT_BI_{month_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        elements = []

        # --- STYLE PERSONNALISÉ ---
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.hexColor("#1e40af"), spaceAfter=10, fontName='Helvetica-Bold')
        sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, textColor=colors.grey, spaceAfter=20)

        # --- ENTÊTE DU RAPPORT ---
        elements.append(Paragraph(f"GEN-PURE OMEGA : BILAN OPÉRATIONNEL", header_style))
        elements.append(Paragraph(f"Période d'Analyse : {month_name} | Rapport généré le {datetime.now().strftime('%d/%m/%Y')}", sub_style))
        elements.append(Spacer(1, 12))

        # --- CALCUL DES KPIs ---
        total = len(scans)
        dangers = len([s for s in scans if s.get('risk_level') == 'DANGER'])
        rejets = len([s for s in scans if s.get('risk_level') == 'REJET'])
        conformes = total - dangers
        purete_index = (conformes / total * 100) if total > 0 else 100

        # --- TABLEAU DES KPI ---
        data_kpi = [
            [Paragraph("<b>INDICATEUR TACTIQUE</b>", styles['Normal']), Paragraph("<b>RÉSULTAT</b>", styles['Normal'])],
            ["Volume total des analyses", str(total)],
            ["Alertes Critiques (DANGER)", str(dangers)],
            ["Analyses Conformes", str(conformes)],
            ["Indice de Pureté Réseau", f"{round(purete_index, 2)}%"]
        ]

        table_kpi = Table(data_kpi, colWidths=[300, 150])
        table_kpi.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.hexColor("#eff6ff")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.hexColor("#1e40af")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(Paragraph("1. RÉSUMÉ EXÉCUTIF DES FLUX", styles['Heading2']))
        elements.append(Spacer(1, 10))
        elements.append(table_kpi)
        elements.append(Spacer(1, 20))

        # --- RÉPARTITION PAR CATÉGORIE ---
        elements.append(Paragraph("2. PERFORMANCE PAR TYPE D'ACTIF", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        cat_counts = {"STATION": 0, "CAMION": 0, "GE": 0}
        for s in scans:
            cat = s.get('category', 'STATION')
            if cat in cat_counts: cat_counts[cat] += 1
        
        data_cat = [
            ["CATÉGORIE", "NOMBRE D'ANALYSES", "STATUT"],
            ["STATIONS SERVICE", str(cat_counts["STATION"]), "ACTIF"],
            ["FLOTTE CAMIONS", str(cat_counts["CAMION"]), "SOUS SURVEILLANCE"],
            ["GROUPES ÉLECTROGÈNES", str(cat_counts["GE"]), "OPTIMISÉ"]
        ]
        
        table_cat = Table(data_cat, colWidths=[180, 150, 120])
        table_cat.setStyle(TableStyle([
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ]))
        elements.append(table_cat)
        elements.append(Spacer(1, 25))

        # --- JOURNAL DES INCIDENTS CRITIQUES ---
        elements.append(Paragraph("3. REGISTRE DES ALERTES DANGER", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        incidents = [["ID", "STATION / SOURCE", "DATE", "TURBIDITÉ"]]
        for s in scans:
            if s.get('risk_level') == 'DANGER':
                incidents.append([s.get('report_id', 'N/A'), s.get('station', 'N/A'), s.get('timestamp', 'N/A'), f"{s.get('turbidity', 0)} NTU"])

        if len(incidents) > 1:
            table_inc = Table(incidents, colWidths=[80, 160, 130, 80])
            table_inc.setStyle(TableStyle([
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.red),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            elements.append(table_inc)
        else:
            elements.append(Paragraph("Aucun incident critique détecté sur cette période.", styles['Italic']))

        # --- PIED DE PAGE ---
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Document certifié par l'Intelligence Artificielle GEN-PURE OMEGA. Toute altération rend le certificat invalide.", styles['Normal']))

        doc.build(elements)
        return filepath
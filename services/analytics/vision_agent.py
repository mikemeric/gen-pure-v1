import numpy as np

class VisionAgent:
    """Agent VISION : Unité d'Analyse Différentielle et de Comparaison"""

    def __init__(self):
        self.thresholds = {
            "turbidity": 15.0,  # Écart NTU max toléré avant alerte
            "color": 25.0,      # Écart de chromie max
            "purity": 1000.0    # Écart de texture/sédimentation
        }

    def prepare_comparison(self, scan_a, scan_b):
        """Calcule les deltas et prépare les données pour l'interface compare.html"""
        if not scan_a or not scan_b:
            return None

        # Extraction des caractéristiques (Features issues de l'IA locale)
        feat_a = np.array(scan_a.get('features', [0, 0, 0, 0, 0]))
        feat_b = np.array(scan_b.get('features', [0, 0, 0, 0, 0]))

        # Calcul des écarts absolus (Delta)
        # feat = [B, G, R, Turbidity, Purity]
        delta_color = np.linalg.norm(feat_a[:3] - feat_b[:3])
        delta_turbidity = abs(feat_a[3] - feat_b[3])
        delta_purity = abs(feat_a[4] - feat_b[4])

        # Diagnostic de l'écart
        status = "STABLE"
        diagnostic = "Les deux échantillons présentent des signatures similaires."
        
        if delta_turbidity > self.thresholds["turbidity"] or delta_color > self.thresholds["color"]:
            status = "DÉGRADATION"
            diagnostic = "Écart significatif détecté. Risque de contamination ou de mélange suspect entre les deux points."
        
        if scan_a['risk_level'] != scan_b['risk_level']:
            status = "ALERTE"
            diagnostic = "Incohérence majeure : l'un des points est conforme tandis que l'autre est à risque."

        return {
            "scan_a": {
                "report_id": scan_a['report_id'],
                "station": scan_a['station'],
                "values": [round(feat_a[3], 2), round(feat_a[4], 2), scan_a['risk_level']],
                "timestamp": scan_a['timestamp']
            },
            "scan_b": {
                "report_id": scan_b['report_id'],
                "station": scan_b['station'],
                "values": [round(feat_b[3], 2), round(feat_b[4], 2), scan_b['risk_level']],
                "timestamp": scan_b['timestamp']
            },
            "analysis": {
                "delta_turbidity": round(delta_turbidity, 2),
                "delta_color": round(delta_color, 2),
                "status": status,
                "diagnostic": diagnostic,
                "delta": round(delta_turbidity, 2) # Pour l'affichage rapide
            }
        }
        
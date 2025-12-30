class VisionAgent:
    """Agent VISION : Analyse comparative et différentielle"""

    def prepare_comparison(self, scan_a, scan_b):
        """Calcule les deltas entre deux rapports"""
        delta_turbidity = round(scan_a['turbidity'] - scan_b['turbidity'], 2)
        
        comparison = {
            "labels": ["Turbidité", "Pureté", "Risque"],
            "scan_a": {
                "id": scan_a['report_id'],
                "station": scan_a['station'],
                "values": [scan_a['turbidity'], 100 - scan_a['turbidity'], scan_a['risk_level']]
            },
            "scan_b": {
                "id": scan_b['report_id'],
                "station": scan_b['station'],
                "values": [scan_b['turbidity'], 100 - scan_b['turbidity'], scan_b['risk_level']]
            },
            "analysis": {
                "delta": delta_turbidity,
                "status": "DÉGRADATION" if delta_turbidity > 0 else "AMÉLIORATION"
            }
        }
        return comparison
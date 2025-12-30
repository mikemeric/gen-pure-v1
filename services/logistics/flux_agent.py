import json

class FluxAgent:
    """Agent FLUX : Intelligence Logistique et Cartographie des Risques"""

    def identify_network_threats(self, current_scan, history_records):
        """
        Analyse la propagation du risque à travers le réseau.
        Détermine si un incident local est le signe d'une faille logistique globale.
        """
        alerts = []
        
        if not current_scan:
            return alerts

        # 1. Analyse de l'incident immédiat
        if current_scan.get('risk_level') == 'DANGER':
            alerts.append({
                "title": "ALERTE SOURCE",
                "message": f"Contamination critique détectée à {current_scan.get('station')}. Blocage recommandé.",
                "severity": "CRITICAL"
            })

        # 2. Analyse de corrélation (Historique récent)
        danger_nodes = [s for s in history_records if s.get('risk_level') == 'DANGER']
        if len(danger_nodes) > 2:
            alerts.append({
                "title": "ALERTE RÉSEAU SYSTÉMIQUE",
                "message": f"{len(danger_nodes)} stations rapportent une eau libre. Faille probable au dépôt central.",
                "severity": "HIGH"
            })
            
        return alerts

    def get_geo_map_data(self, all_scans):
        """
        Formate les données de la Mémoire Centrale pour l'Agent PIXEL-ELITE (Frontend).
        Assure la correspondance exacte avec les variables JS du Manager.
        """
        map_points = []
        for scan in all_scans:
            # On s'assure que chaque point possède la structure requise par manager.html
            map_points.append({
                "report_id": scan.get('report_id', 'INCONNU'),
                "station": scan.get('station', 'Unité Mobile'),
                "status": scan.get('status', 'ANALYSE EN COURS'),
                "risk": scan.get('risk_level', 'NORMAL'), # DANGER, VIGILANCE, NORMAL
                "timestamp": scan.get('timestamp', ''),
                "turbidity": scan.get('turbidity', 0)
            })
        return map_points
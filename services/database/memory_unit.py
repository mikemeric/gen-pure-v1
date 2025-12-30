import json
import os

class MemoryUnit:
    """Agent ARCHIVISTE : Gestionnaire de la Mémoire Centrale OMEGA"""

    def __init__(self):
        self.db_path = "data/omega_history.json"
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w') as f:
                json.dump([], f)

    def archive_diagnostic(self, diagnostic):
        """Enregistre un nouveau scan dans la mémoire"""
        history = self.get_all_scans()
        history.insert(0, diagnostic)  # Le plus récent en premier
        with open(self.db_path, 'w') as f:
            json.dump(history, f, indent=4)

    def get_all_scans(self):
        """Récupère l'intégralité des rapports"""
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    # --- FONCTION CRITIQUE POUR L'AGENT VISION ---
    def get_scan_by_id(self, report_id):
        """
        Recherche un rapport spécifique par son identifiant unique.
        Essentiel pour la comparaison Phase 6.
        """
        history = self.get_all_scans()
        # On cherche l'ID dans la liste des dictionnaires
        for scan in history:
            if scan.get('report_id') == report_id:
                return scan
        return None

    def get_station_trend(self, station_name, limit=5):
        """Récupère les derniers scans d'une station précise"""
        history = self.get_all_scans()
        return [s for s in history if s.get('station') == station_name][:limit]
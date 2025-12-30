import json
import os

class MemoryUnit:
    """Agent ARCHIVISTE : Gardien de la base de données et de la flotte OMEGA"""

    def __init__(self):
        self.base_dir = "data"
        self.paths = {
            "scans": os.path.join(self.base_dir, "omega_history.json"),
            "rejections": os.path.join(self.base_dir, "omega_rejections.json"),
            "fleet": os.path.join(self.base_dir, "fleet_registry.json")
        }
        # Création du périmètre de stockage
        os.makedirs(self.base_dir, exist_ok=True)
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialise les fichiers JSON s'ils n'existent pas"""
        for key in self.paths:
            if not os.path.exists(self.paths[key]):
                with open(self.paths[key], 'w', encoding='utf-8') as f:
                    json.dump([], f)

    # --- GESTION DES SCANS (HISTORIQUE) ---

    def archive_diagnostic(self, diag):
        """Enregistre un nouveau scan certifié"""
        history = self.get_all_scans()
        history.insert(0, diag)  # Le plus récent en premier
        with open(self.paths["scans"], 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def get_all_scans(self):
        """Récupère l'intégralité des analyses"""
        try:
            with open(self.paths["scans"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def overwrite_scans(self, scans_list):
        """Écrase l'historique (utilisé après une correction manuelle de l'IA)"""
        with open(self.paths["scans"], 'w', encoding='utf-8') as f:
            json.dump(scans_list, f, indent=4, ensure_ascii=False)

    def get_scan_by_id(self, report_id):
        """Recherche un scan spécifique pour comparaison ou audit"""
        scans = self.get_all_scans()
        for s in scans:
            if s.get('report_id') == report_id:
                return s
        return None

    # --- GESTION DES REJETS (DISCIPLINE) ---

    def archive_rejection(self, rej):
        """Enregistre une tentative de fraude ou erreur technique"""
        rejections = self.get_all_rejections()
        rejections.insert(0, rej)
        with open(self.paths["rejections"], 'w', encoding='utf-8') as f:
            json.dump(rejections, f, indent=4, ensure_ascii=False)

    def get_all_rejections(self):
        try:
            with open(self.paths["rejections"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    # --- GESTION DE LA FLOTTE (ACTIFS) ---

    def register_asset(self, asset):
        """Ajoute un Camion, GE ou Station au registre de flotte"""
        fleet = self.get_fleet()
        # Éviter les doublons d'ID
        if not any(item['id'] == asset['id'] for item in fleet):
            fleet.append(asset)
            with open(self.paths["fleet"], 'w', encoding='utf-8') as f:
                json.dump(fleet, f, indent=4, ensure_ascii=False)
            return True
        return False

    def get_fleet(self):
        """Récupère la liste des actifs pour l'affichage dans le Dashboard"""
        try:
            with open(self.paths["fleet"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
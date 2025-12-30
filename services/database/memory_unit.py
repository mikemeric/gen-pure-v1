import json
import os
import uuid
from datetime import datetime
from passlib.context import CryptContext

# Configuration du hachage sécurisé pour les mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class MemoryUnit:
    """Agent ARCHIVISTE V3.4 : Gestion de la persistance SaaS et CRUD complet"""

    def __init__(self):
        self.base_dir = "data"
        # Définition des chemins vers les fichiers JSON
        self.paths = {
            "scans": os.path.join(self.base_dir, "scans.json"),
            "users": os.path.join(self.base_dir, "users.json"),
            "licenses": os.path.join(self.base_dir, "licenses.json"),
            "fleet": os.path.join(self.base_dir, "fleet_registry.json"),
            "rejections": os.path.join(self.base_dir, "rejections.json")
        }
        os.makedirs(self.base_dir, exist_ok=True)
        self._initialize_storage()

    def _initialize_storage(self):
        """Crée les fichiers JSON s'ils n'existent pas"""
        for key in self.paths:
            if not os.path.exists(self.paths[key]):
                with open(self.paths[key], 'w', encoding='utf-8') as f:
                    json.dump([], f)
        
        # Création du SuperAdmin fondateur si la base est vide
        users = self.get_users()
        if not any(u.get('role') == 'SUPERADMIN' for u in users):
            self.create_user("Idriss", "OMEGA123", "SUPERADMIN", "GEN-PURE-HQ")

    # --- GESTION DES UTILISATEURS ---

    def get_users(self):
        with open(self.paths["users"], 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_company_drivers(self, company_id):
        """Filtre les chauffeurs pour le Manager d'une entreprise spécifique"""
        users = self.get_users()
        return [u for u in users if u.get('company_id') == company_id and u.get('role') == 'DRIVER']

    def create_user(self, username, password, role, company_id):
        """Crée un utilisateur avec mot de passe haché"""
        users = self.get_users()
        if any(u['username'] == username for u in users):
            return False
        
        hashed_pw = pwd_context.hash(password)
        new_user = {
            "id": str(uuid.uuid4()),
            "username": username,
            "password_hash": hashed_pw,
            "role": role, # SUPERADMIN, MANAGER, DRIVER, AUDITOR
            "company_id": company_id,
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        users.append(new_user)
        with open(self.paths["users"], 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
        return True

    def verify_user(self, username, password):
        """Vérifie les identifiants lors du login"""
        users = self.get_users()
        for u in users:
            if u['username'] == username and pwd_context.verify(password, u['password_hash']):
                return u
        return None

    def delete_user(self, username, company_id):
        """Suppression sécurisée : un manager ne peut supprimer que ses propres chauffeurs"""
        users = self.get_users()
        new_list = [u for u in users if not (u['username'] == username and u['company_id'] == company_id)]
        if len(users) != len(new_list):
            with open(self.paths["users"], 'w', encoding='utf-8') as f:
                json.dump(new_list, f, indent=4)
            return True
        return False

    # --- GESTION DES LICENCES ---

    def get_licenses(self):
        with open(self.paths["licenses"], 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_license(self, company_name, license_type, expiration_date):
        """Génère un ID entreprise unique et une licence associée"""
        licenses = self.get_licenses()
        company_id = str(uuid.uuid4())[:8].upper()
        new_lic = {
            "company_id": company_id,
            "company_name": company_name,
            "type": license_type,
            "expiration": expiration_date,
            "active": True
        }
        licenses.append(new_lic)
        with open(self.paths["licenses"], 'w', encoding='utf-8') as f:
            json.dump(licenses, f, indent=4)
        return new_lic

    # --- GESTION DU PARC (FLOTTE / GÉNÉRATEURS) ---

    def get_fleet(self, company_id=None):
        with open(self.paths["fleet"], 'r', encoding='utf-8') as f:
            all_fleet = json.load(f)
        if company_id and company_id != "GEN-PURE-HQ":
            return [a for a in all_fleet if a.get('company_id') == company_id]
        return all_fleet

    def register_asset(self, asset):
        with open(self.paths["fleet"], 'r', encoding='utf-8') as f:
            full_fleet = json.load(f)
        full_fleet.append(asset)
        with open(self.paths["fleet"], 'w', encoding='utf-8') as f:
            json.dump(full_fleet, f, indent=4)

    def delete_asset(self, asset_id, company_id):
        """Supprime un véhicule ou GE du parc"""
        with open(self.paths["fleet"], 'r', encoding='utf-8') as f:
            fleet = json.load(f)
        new_list = [a for a in fleet if not (a['id'] == asset_id and a.get('company_id') == company_id)]
        if len(fleet) != len(new_list):
            with open(self.paths["fleet"], 'w', encoding='utf-8') as f:
                json.dump(new_list, f, indent=4)
            return True
        return False

    # --- GESTION DES RAPPORTS DE SCAN ---

    def get_all_scans(self, company_id=None):
        with open(self.paths["scans"], 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        if company_id and company_id != "GEN-PURE-HQ":
            return [s for s in all_data if s.get('company_id') == company_id]
        return all_data

    def archive_diagnostic(self, diag):
        with open(self.paths["scans"], 'r', encoding='utf-8') as f:
            history = json.load(f)
        history.insert(0, diag)
        with open(self.paths["scans"], 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)

    def get_all_rejections(self):
        with open(self.paths["rejections"], 'r', encoding='utf-8') as f:
            return json.load(f)

    def archive_rejection(self, diag):
        """Stocke les alertes et tentatives de fraude pour le ROI"""
        rejs = self.get_all_rejections()
        rejs.insert(0, diag)
        with open(self.paths["rejections"], 'w', encoding='utf-8') as f:
            json.dump(rejs, f, indent=4)

    def overwrite_scans(self, new_data):
        """Mise à jour globale (utilisée après correction IA)"""
        with open(self.paths["scans"], 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=4)
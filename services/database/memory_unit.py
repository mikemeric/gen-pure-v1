import json
import os
import uuid
from datetime import datetime
from passlib.context import CryptContext

# Initialisation du hachage (Bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class MemoryUnit:
    """Agent ARCHIVISTE V3.7 : Version Anti-Crash & Reset Automatique"""

    def __init__(self):
        self.base_dir = "data"
        
        # --- STRATÉGIE DE RESET ---
        # Nous utilisons 'users_v2.json' pour ignorer l'ancien fichier corrompu sur Render.
        # Cela force le système à recréer une base propre immédiatement.
        self.paths = {
            "scans": os.path.join(self.base_dir, "scans.json"),
            "users": os.path.join(self.base_dir, "users_v2.json"), 
            "licenses": os.path.join(self.base_dir, "licenses.json"),
            "fleet": os.path.join(self.base_dir, "fleet_registry.json"),
            "rejections": os.path.join(self.base_dir, "rejections.json")
        }
        
        os.makedirs(self.base_dir, exist_ok=True)
        self._initialize_storage()

    def _initialize_storage(self):
        """Crée les fichiers vides et l'Admin par défaut si nécessaire"""
        for key in self.paths:
            if not os.path.exists(self.paths[key]):
                with open(self.paths[key], 'w', encoding='utf-8') as f:
                    json.dump([], f)
        
        # Création automatique du SuperAdmin sur la nouvelle base
        users = self.get_users()
        if not any(u.get('role') == 'SUPERADMIN' for u in users):
            print("INITIALISATION : Création du SuperAdmin Idriss...")
            self.create_user("Idriss", "OMEGA123", "SUPERADMIN", "GEN-PURE-HQ")

    # --- GESTION UTILISATEURS (BLINDÉE) ---

    def get_users(self):
        try:
            if not os.path.exists(self.paths["users"]): return []
            with open(self.paths["users"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"ERREUR LECTURE USERS: {e}")
            return []

    def create_user(self, username, password, role, company_id):
        """Crée un utilisateur avec protection anti-crash (longueur mot de passe)"""
        users = self.get_users()
        if any(u['username'] == username for u in users):
            return False
        
        # 1. SÉCURITÉ : Tronquage à 71 caractères (Bcrypt plante à 72+)
        safe_password = str(password)[:71]
        
        try:
            hashed_pw = pwd_context.hash(safe_password)
        except Exception as e:
            print(f"ERREUR HASHAGE: {e}")
            return False

        new_user = {
            "id": str(uuid.uuid4()),
            "username": username,
            "password_hash": hashed_pw,
            "role": role,
            "company_id": company_id,
            "created_at": datetime.now().strftime("%Y-%m-%d")
        }
        
        users.append(new_user)
        self._save_json("users", users)
        return True

    def verify_user(self, username, password):
        """Vérifie le login sans faire planter le serveur"""
        users = self.get_users()
        # On tronque aussi à l'entrée pour correspondre au hash
        safe_password = str(password)[:71]
        
        for u in users:
            if u['username'] == username:
                try:
                    # Vérification standard
                    if pwd_context.verify(safe_password, u['password_hash']):
                        return u
                except Exception as e:
                    print(f"ERREUR VERIFICATION ({username}): {e}")
                    # En cas de hash corrompu, on refuse l'accès proprement au lieu de planter
                    continue
        return None

    def delete_user(self, username, company_id):
        users = self.get_users()
        new_list = [u for u in users if not (u['username'] == username and u['company_id'] == company_id)]
        if len(users) != len(new_list):
            self._save_json("users", new_list)
            return True
        return False

    def get_company_drivers(self, company_id):
        users = self.get_users()
        return [u for u in users if u.get('company_id') == company_id and u.get('role') == 'DRIVER']

    # --- MÉTHODE UTILITAIRE D'ÉCRITURE ---
    def _save_json(self, key, data):
        with open(self.paths[key], 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    # --- GESTION LICENCES ---

    def get_licenses(self):
        with open(self.paths["licenses"], 'r', encoding='utf-8') as f: return json.load(f)

    def create_license(self, company_name, license_type, expiration_date):
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
        self._save_json("licenses", licenses)
        return new_lic

    # --- GESTION FLOTTE ---

    def get_fleet(self, company_id=None):
        with open(self.paths["fleet"], 'r', encoding='utf-8') as f: all_fleet = json.load(f)
        if company_id and company_id != "GEN-PURE-HQ":
            return [a for a in all_fleet if a.get('company_id') == company_id]
        return all_fleet

    def register_asset(self, asset):
        with open(self.paths["fleet"], 'r', encoding='utf-8') as f: full_fleet = json.load(f)
        full_fleet.append(asset)
        self._save_json("fleet", full_fleet)

    def delete_asset(self, asset_id, company_id):
        with open(self.paths["fleet"], 'r', encoding='utf-8') as f: fleet = json.load(f)
        new_list = [a for a in fleet if not (a['id'] == asset_id and a.get('company_id') == company_id)]
        if len(fleet) != len(new_list):
            self._save_json("fleet", new_list)
            return True
        return False

    # --- GESTION SCANS & REJETS ---

    def get_all_scans(self, company_id=None):
        with open(self.paths["scans"], 'r', encoding='utf-8') as f: all_data = json.load(f)
        if company_id and company_id != "GEN-PURE-HQ":
            return [s for s in all_data if s.get('company_id') == company_id]
        return all_data

    def archive_diagnostic(self, diag):
        with open(self.paths["scans"], 'r', encoding='utf-8') as f: history = json.load(f)
        history.insert(0, diag)
        self._save_json("scans", history)

    def get_all_rejections(self):
        with open(self.paths["rejections"], 'r', encoding='utf-8') as f: return json.load(f)

    def archive_rejection(self, diag):
        rejs = self.get_all_rejections()
        rejs.insert(0, diag)
        self._save_json("rejections", rejs)

    def overwrite_scans(self, new_data):
        self._save_json("scans", new_data)
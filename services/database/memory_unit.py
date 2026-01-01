import json
import os
import uuid
from datetime import datetime
from passlib.context import CryptContext

# --- CHANGEMENT STRATÉGIQUE ---
# Nous utilisons pbkdf2_sha256 qui est natif à Python.
# Il ne crashe jamais sur Render contrairement à Bcrypt.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class MemoryUnit:
    """Agent ARCHIVISTE V3.8 : Version Universelle (Pbkdf2) & Anti-Crash"""

    def __init__(self):
        self.base_dir = "data"
        
        # Nous changeons le nom du fichier pour forcer la réinitialisation de la base
        # Cela élimine définitivement les anciennes erreurs de corruption
        self.paths = {
            "scans": os.path.join(self.base_dir, "scans.json"),
            "users": os.path.join(self.base_dir, "users_v3.json"), 
            "licenses": os.path.join(self.base_dir, "licenses.json"),
            "fleet": os.path.join(self.base_dir, "fleet_registry.json"),
            "rejections": os.path.join(self.base_dir, "rejections.json")
        }
        
        os.makedirs(self.base_dir, exist_ok=True)
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialise les fichiers vides et crée le SuperAdmin"""
        for key in self.paths:
            if not os.path.exists(self.paths[key]):
                with open(self.paths[key], 'w', encoding='utf-8') as f:
                    json.dump([], f)
        
        # Création automatique du SuperAdmin sur la nouvelle base v3
        users = self.get_users()
        if not any(u.get('role') == 'SUPERADMIN' for u in users):
            print("INITIALISATION : Création du SuperAdmin Idriss (Mode Pbkdf2)...")
            # Mot de passe par défaut
            self.create_user("Idriss", "OMEGA123", "SUPERADMIN", "GEN-PURE-HQ")

    # --- GESTION UTILISATEURS (BLINDÉE) ---

    def get_users(self):
        try:
            if not os.path.exists(self.paths["users"]): return []
            with open(self.paths["users"], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"ERREUR CRITIQUE LECTURE USERS: {e}")
            return []

    def create_user(self, username, password, role, company_id):
        """Crée un utilisateur avec le nouveau cryptage sûr"""
        users = self.get_users()
        if any(u['username'] == username for u in users):
            return False
        
        try:
            # Hachage sécurisé universel
            hashed_pw = pwd_context.hash(password)
        except Exception as e:
            print(f"ERREUR HASHAGE ({username}): {e}")
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
        """Vérifie le login sans jamais faire planter le serveur (Error 500 Fix)"""
        users = self.get_users()
        
        for u in users:
            if u['username'] == username:
                try:
                    # Vérification standard
                    if pwd_context.verify(password, u['password_hash']):
                        return u
                except Exception as e:
                    print(f"ERREUR VERIFICATION LOGIN ({username}): {e}")
                    # En cas de problème technique, on refuse l'accès sans crasher
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
        try:
            with open(self.paths[key], 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"ERREUR ECRITURE {key}: {e}")

    # --- GESTION LICENCES ---

    def get_licenses(self):
        try:
            with open(self.paths["licenses"], 'r', encoding='utf-8') as f: return json.load(f)
        except: return []

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
        try:
            with open(self.paths["fleet"], 'r', encoding='utf-8') as f: all_fleet = json.load(f)
            if company_id and company_id != "GEN-PURE-HQ":
                return [a for a in all_fleet if a.get('company_id') == company_id]
            return all_fleet
        except: return []

    def register_asset(self, asset):
        try:
            with open(self.paths["fleet"], 'r', encoding='utf-8') as f: full_fleet = json.load(f)
            full_fleet.append(asset)
            self._save_json("fleet", full_fleet)
        except: pass

    def delete_asset(self, asset_id, company_id):
        try:
            with open(self.paths["fleet"], 'r', encoding='utf-8') as f: fleet = json.load(f)
            new_list = [a for a in fleet if not (a['id'] == asset_id and a.get('company_id') == company_id)]
            if len(fleet) != len(new_list):
                self._save_json("fleet", new_list)
                return True
        except: pass
        return False

    # --- GESTION SCANS & REJETS ---

    def get_all_scans(self, company_id=None):
        try:
            with open(self.paths["scans"], 'r', encoding='utf-8') as f: all_data = json.load(f)
            if company_id and company_id != "GEN-PURE-HQ":
                return [s for s in all_data if s.get('company_id') == company_id]
            return all_data
        except: return []

    def archive_diagnostic(self, diag):
        try:
            with open(self.paths["scans"], 'r', encoding='utf-8') as f: history = json.load(f)
            history.insert(0, diag)
            self._save_json("scans", history)
        except: pass

    def get_all_rejections(self):
        try:
            with open(self.paths["rejections"], 'r', encoding='utf-8') as f: return json.load(f)
        except: return []

    def archive_rejection(self, diag):
        try:
            rejs = self.get_all_rejections()
            rejs.insert(0, diag)
            self._save_json("rejections", rejs)
        except: pass

    def overwrite_scans(self, new_data):
        self._save_json("scans", new_data)
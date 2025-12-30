import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    """Agent SENTINELLE V6.0 : Algorithme 'Bunker' Anti-Faux Positifs"""

    def __init__(self):
        self.model_path = "data/omega_model.pkl"
        self.model = self._load_model()
        # Chargement du détecteur de visage ultra-rapide
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def _load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f: return pickle.load(f)
        return RandomForestClassifier(n_estimators=100)

    def _calculate_entropy(self, img_gray):
        """Calcule la 'complexité' de l'image.
        Liquide = Entropie faible.
        Visage/Décor = Entropie élevée.
        """
        hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256])
        hist = hist / hist.sum()
        non_zero_hist = hist[hist > 0]
        entropy = -np.sum(non_zero_hist * np.log2(non_zero_hist))
        return entropy

    def _firewall_check(self, img, gray):
        """LE PARE-FEU : Bloque tout ce qui n'est pas du liquide propre"""
        
        # 1. DÉTECTION VISAGE (Sécurité Biométrique)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
        if len(faces) > 0:
            return False, "VISAGE DÉTECTÉ : Veuillez photographier uniquement l'éprouvette."

        # 2. ANALYSE D'ENTROPIE (Texture)
        # Un liquide est 'lisse'. Un visage ou un arrière-plan est 'complexe'.
        entropy = self._calculate_entropy(gray)
        # Seuil empirique : au-dessus de 5.5, c'est trop complexe pour être juste du liquide
        if entropy > 5.5:
            return False, "ENVIRONNEMENT TROP COMPLEXE : Cadrage incorrect (trop de détails d'arrière-plan)."

        # 3. VARIANCE DE COULEUR (Uniformité)
        # Le carburant est monochrome (Jaune ou Orange).
        # Si l'écart-type (std) est élevé, il y a trop de couleurs différentes (ex: peau + mur + t-shirt)
        color_variance = np.std(img)
        if color_variance > 60: 
            return False, "COULEURS HÉTÉROGÈNES : L'image contient trop d'objets différents."

        # 4. LUMINOSITÉ (Noir total)
        if np.mean(gray) < 30:
            return False, "ÉCLAIRAGE INSUFFISANT : Image trop sombre."

        return True, "OK"

    def _analyze_physics(self, img, gray):
        """Analyse technique (si le Pare-Feu est passé)"""
        h, w, _ = img.shape
        bottom = img[int(h*0.80):, :] 
        top = img[int(h*0.2):int(h*0.6), :] 
        
        # EAU (Différence bas/haut)
        diff_val = abs(np.mean(bottom) - np.mean(top))
        water_risk = bool(diff_val > 35) # Seuil resserré
        
        # SÉDIMENTS (Contours)
        edges = cv2.Canny(gray, 100, 200)
        impurities = int(np.count_nonzero(edges))
        
        # TURBIDITÉ (Flou interne)
        turbidity = float(gray.std())
        
        return {
            "water": water_risk, 
            "sediments": impurities, 
            "turbidity": turbidity, 
            "avg_color": [float(c) for c in cv2.mean(img)[:3]]
        }

    async def analyze_with_turbo_mode(self, img_bytes, station):
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None: 
            return {"risk_level": "REJET", "diagnostic": "Fichier corrompu"}

        # Redimensionnement (Optimisation Render RAM + Détection)
        img_std = cv2.resize(img, (300, 400))
        gray = cv2.cvtColor(img_std, cv2.COLOR_BGR2GRAY)

        # --- PHASE 1 : LE PARE-FEU (Bloquant) ---
        is_valid, reason = self._firewall_check(img_std, gray)
        
        if not is_valid:
            # ARRÊT IMMÉDIAT DU PROCESSUS
            # On renvoie un objet REJET propre
            return {
                "risk_level": "REJET",  # Déclenche l'icône TRIANGLE JAUNE dans scan.html
                "turbidity": 0.0, 
                "water_presence": False, 
                "impurities": 0,
                "diagnostic": reason, # Ex: "VISAGE DÉTECTÉ"
                "features": [0.0, 0.0, 0.0, 0.0, 0.0]
            }

        # --- PHASE 2 : ANALYSE LABORATOIRE (Seulement si Phase 1 OK) ---
        phys = self._analyze_physics(img_std, gray)

        verdict = []
        risk_score = 0
        
        if phys['water']:
            verdict.append("EAU SUSPECTÉE")
            risk_score += 60
        if phys['sediments'] > 1500:
            verdict.append(f"IMPURETÉS ({phys['sediments']})")
            risk_score += 30
        if phys['turbidity'] < 10:
            verdict.append("OPACITÉ ANORMALE")
            risk_score += 20

        final_risk = "NORMAL"
        if risk_score >= 50: final_risk = "DANGER CRITIQUE"
        elif risk_score > 0: final_risk = "ATTENTION"
        
        diag_text = " // ".join(verdict) if verdict else "Carburant conforme."

        return {
            "risk_level": final_risk,
            "turbidity": round(phys['turbidity'], 2),
            "water_presence": phys['water'],
            "impurities": phys['sediments'],
            "diagnostic": diag_text,
            "features": [
                phys['avg_color'][0], phys['avg_color'][1], phys['avg_color'][2], 
                phys['turbidity'], float(phys['sediments'])
            ]
        }
    
    def train_model(self, data):
        # ... (Code existant inchangé)
        pass
import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    """Agent SENTINELLE V5.0 : Filtre Biométrique & Anti-Leurre"""

    def __init__(self):
        self.model_path = "data/omega_model.pkl"
        self.model = self._load_model()
        # Chargement du détecteur de visage (intégré à OpenCV)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def _load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f: return pickle.load(f)
        return RandomForestClassifier(n_estimators=100)

    def _check_validity(self, img, gray):
        """Vérifie si c'est bien du carburant et pas un humain ou un mur"""
        
        # 1. DÉTECTION DE VISAGE (Sécurité Biométrique)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            return False, "VISAGE DÉTECTÉ : Ceci n'est pas du carburant."

        # 2. ANALYSE DE VARIANCE CHROMATIQUE (Le carburant est uniforme)
        # On convertit en HSV pour analyser la teinte (Hue)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h_channel = hsv[:,:,0]
        s_channel = hsv[:,:,1]
        
        # L'écart-type (std) de la teinte doit être faible pour un liquide uniforme
        # Un visage ou un paysage a beaucoup de couleurs différentes -> std élevé
        hue_variance = np.std(h_channel)
        
        if hue_variance > 50: 
            return False, "ENVIRONNEMENT COMPLEXE : Veuillez cadrer uniquement le liquide."

        # 3. LUMINOSITÉ MINIMALE (Éviter les photos noires)
        if np.mean(gray) < 20:
            return False, "IMAGE TROP SOMBRE : Éclairage insuffisant."

        return True, "OK"

    def _analyze_physics(self, img, gray):
        """Analyse physique avec conversion stricte des types"""
        h, w, _ = img.shape
        
        # Zones d'intérêt
        bottom = img[int(h*0.85):, :] 
        top = img[int(h*0.2):int(h*0.6), :] 
        
        # 1. Analyse EAU
        diff_val = abs(np.mean(bottom) - np.mean(top))
        water_risk = bool(diff_val > 40) 
        
        # 2. Analyse SÉDIMENTS
        edges = cv2.Canny(gray, 100, 200)
        impurities = int(np.count_nonzero(edges))
        
        # 3. Analyse TURBIDITÉ
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
            return {"risk_level": "REJET", "diagnostic": "Image corrompue."}

        # Redimensionnement standard
        img_std = cv2.resize(img, (300, 400)) # Un peu plus grand pour détecter les visages
        gray = cv2.cvtColor(img_std, cv2.COLOR_BGR2GRAY)

        # --- ÉTAPE 1 : CONTRÔLE DE VALIDITÉ (Le fameux correctif) ---
        is_valid, reason = self._check_validity(img_std, gray)
        
        if not is_valid:
            # Rejet immédiat si c'est un visage ou n'importe quoi d'autre
            return {
                "risk_level": "REJET", 
                "turbidity": 0.0, 
                "water_presence": False, 
                "impurities": 0,
                "diagnostic": reason, # Ex: "VISAGE DÉTECTÉ"
                "features": [0.0, 0.0, 0.0, 0.0, 0.0]
            }

        # --- ÉTAPE 2 : ANALYSE TECHNIQUE (Si c'est bien du liquide) ---
        phys = self._analyze_physics(img_std, gray)

        # LOGIQUE MÉTIER
        verdict = []
        risk_score = 0
        
        if phys['water']:
            verdict.append("EAU DÉTECTÉE (Séparation Phase)")
            risk_score += 60
            
        if phys['sediments'] > 2000:
            verdict.append(f"SÉDIMENTS CRITIQUES ({phys['sediments']} ppm)")
            risk_score += 30
            
        if phys['turbidity'] < 15:
            verdict.append("OPACITÉ SUSPECTE (Mélange ?)")
            risk_score += 20

        final_risk = "NORMAL"
        if risk_score >= 50: final_risk = "DANGER CRITIQUE"
        elif risk_score > 0: final_risk = "ATTENTION"
        
        diag_text = " // ".join(verdict) if verdict else "Carburant conforme. Pas d'anomalie visible."

        features = [
            phys['avg_color'][0], 
            phys['avg_color'][1], 
            phys['avg_color'][2], 
            phys['turbidity'], 
            float(phys['sediments'])
        ]

        return {
            "risk_level": final_risk,
            "turbidity": round(phys['turbidity'], 2),
            "water_presence": phys['water'],
            "impurities": phys['sediments'],
            "diagnostic": diag_text,
            "features": features
        }

    def train_model(self, data):
        # (Code d'apprentissage inchangé)
        X = []
        y = []
        for d in data:
            if 'features' in d and 'manual_validation' in d:
                try:
                    feat = [float(x) for x in d['features']]
                    label = 1 if d['manual_validation'] != 'NORMAL' else 0
                    X.append(feat)
                    y.append(label)
                except: continue
        if len(y) >= 5:
            self.model.fit(X, y)
            with open(self.model_path, 'wb') as f: pickle.dump(self.model, f)
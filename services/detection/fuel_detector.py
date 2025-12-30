import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    """Agent SENTINELLE V4.2 : Patch Typage Strict"""

    def __init__(self):
        self.model_path = "data/omega_model.pkl"
        self.model = self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f: return pickle.load(f)
        return RandomForestClassifier(n_estimators=100)

    def _analyze_physics(self, img):
        """Analyse physique avec conversion stricte des types (Fix Crash JSON)"""
        h, w, _ = img.shape
        bottom = img[int(h*0.85):, :] 
        top = img[int(h*0.2):int(h*0.6), :] 
        
        # --- CORRECTION SENTINELLE : Conversion explicite en bool() python natif ---
        # L'erreur venait d'ici : 'numpy.bool_' n'est pas sérialisable
        diff_val = abs(np.mean(bottom) - np.mean(top))
        water_risk = bool(diff_val > 40) 
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        
        # --- CORRECTION SENTINELLE : Conversion explicite en int() et float() ---
        impurities = int(np.count_nonzero(edges))
        turbidity = float(gray.std())
        
        # On renvoie des types Python purs que le serveur comprendra
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
            return {"risk_level": "REJET", "diagnostic": "Image noire/invalide"}

        img_std = cv2.resize(img, (200, 300))
        phys = self._analyze_physics(img_std)

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

        # Conversion finale de la liste features pour ML (Liste de floats purs)
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
        X = []
        y = []
        for d in data:
            if 'features' in d and 'manual_validation' in d:
                try:
                    # Sécurisation des données entrantes pour l'apprentissage
                    feat = [float(x) for x in d['features']]
                    label = 1 if d['manual_validation'] != 'NORMAL' else 0
                    X.append(feat)
                    y.append(label)
                except: continue
        
        if len(y) >= 5:
            self.model.fit(X, y)
            with open(self.model_path, 'wb') as f: pickle.dump(self.model, f)
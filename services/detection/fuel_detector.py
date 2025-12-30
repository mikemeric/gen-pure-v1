import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    def __init__(self):
        self.model_path = "data/omega_model.pkl"
        self.model = self._load()

    def _load(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f: return pickle.load(f)
        return RandomForestClassifier(n_estimators=100)

    def _analyze_physics(self, img):
        # 1. Analyse EAU (Séparation de phase bas de tube)
        h, w, _ = img.shape
        bottom = img[int(h*0.85):, :] # Fond du tube
        top = img[int(h*0.2):int(h*0.6), :] # Milieu du tube
        
        # Si le fond est beaucoup plus clair/foncé que le milieu -> Eau
        water_risk = abs(np.mean(bottom) - np.mean(top)) > 40
        
        # 2. Analyse SÉDIMENTS (Impuretés solides)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        impurities = np.count_nonzero(edges)
        
        # 3. Analyse TURBIDITÉ (Trouble)
        turbidity = gray.std()
        
        return {"water": water_risk, "sediments": impurities, "turbidity": turbidity, "avg_color": cv2.mean(img)[:3]}

    async def analyze_with_turbo_mode(self, img_bytes, station):
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return {"risk_level": "REJET", "diagnostic": "Image noire/invalide"}

        img_std = cv2.resize(img, (200, 300))
        phys = self._analyze_physics(img_std)

        # LOGIQUE MÉTIER CAMEROUN (Zoa-Zoa vs Bon Gasoil)
        verdict = []
        risk_score = 0
        
        # Critère 1 : Eau (Mortel pour injecteurs)
        if phys['water']:
            verdict.append("EAU DÉTECTÉE (Séparation Phase)")
            risk_score += 60
            
        # Critère 2 : Sédiments (Bouche les filtres)
        if phys['sediments'] > 2000:
            verdict.append(f"SÉDIMENTS CRITIQUES ({phys['sediments']} ppm)")
            risk_score += 30
            
        # Critère 3 : Turbidité (Mélange pétrole lampant/eau)
        if phys['turbidity'] < 15: # Trop "plat" visuellement
            verdict.append("OPACITÉ SUSPECTE (Mélange ?)")
            risk_score += 20

        final_risk = "NORMAL"
        if risk_score >= 50: final_risk = "DANGER CRITIQUE"
        elif risk_score > 0: final_risk = "ATTENTION"
        
        diag_text = " // ".join(verdict) if verdict else "Carburant conforme. Pas d'anomalie visible."

        # Extraction features pour ML
        features = [*phys['avg_color'], phys['turbidity'], float(phys['sediments'])]

        return {
            "risk_level": final_risk,
            "turbidity": round(phys['turbidity'], 2),
            "water_presence": phys['water'],
            "impurities": phys['sediments'],
            "diagnostic": diag_text,
            "features": features
        }

    def train_model(self, data):
        # Apprentissage sur les corrections manuelles (vrai ML)
        X = [d['features'] for d in data if 'features' in d and 'manual_validation' in d]
        y = [1 if d['manual_validation'] != 'NORMAL' else 0 for d in data if 'features' in d and 'manual_validation' in d]
        
        if len(y) >= 5:
            self.model.fit(X, y)
            with open(self.model_path, 'wb') as f: pickle.dump(self.model, f)
import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    """Agent SENTINELLE V3 : IA Souveraine Auto-Apprenante"""

    def __init__(self):
        self.model_path = "data/omega_model.pkl"
        os.makedirs("data", exist_ok=True)
        self.model = self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    return pickle.load(f)
            except: pass
        # Modèle par défaut : Forêt Aléatoire
        return RandomForestClassifier(n_estimators=100)

    def _extract_features(self, image_bytes):
        """Extraction de la signature numérique du carburant (Vision par ordinateur)"""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return None
        
        img = cv2.resize(img, (100, 100))
        
        # Couleurs moyennes (BGR)
        avg_color = cv2.mean(img)[:3]
        
        # Turbidité (Écart-type de la luminance)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        turbidity_score = gray.std()
        
        # Pureté/Texture (Variance du Laplacien)
        purity_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        return np.array([*avg_color, turbidity_score, purity_score])

    async def analyze_with_turbo_mode(self, image_bytes, station):
        features = self._extract_features(image_bytes)
        
        if features is None:
            return {"risk_level": "REJET", "diagnostic": "Image illisible."}

        # Détection de Rejet (Si l'image est trop uniforme ou sombre - ex: cheveux/doigt)
        if features[3] < 5: 
            return {"risk_level": "REJET", "diagnostic": "Objet non identifié détecté."}

        try:
            # Prédiction IA
            prediction = self.model.predict([features])[0]
            risk = "DANGER" if prediction == 1 else "NORMAL"
        except:
            # Mode secours si non entraîné
            risk = "DANGER" if features[3] > 40 else "NORMAL"

        return {
            "risk_level": risk,
            "turbidity": round(features[3], 2),
            "diagnostic": f"Analyse IA Locale : {risk}",
            "features": features.tolist()
        }

    def train_model(self, data_list):
        """L'IA apprend des décisions du Général"""
        X, y = [], []
        for d in data_list:
            if 'features' in d and 'manual_validation' in d:
                X.append(d['features'])
                y.append(1 if d['manual_validation'] == 'DANGER' else 0)
        
        if len(y) >= 3:
            self.model.fit(X, y)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            return True
        return False
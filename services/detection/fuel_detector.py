import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    """Agent SENTINELLE V7.1 : Vision IA avec Pare-feu Anti-Fraude intégré"""

    def __init__(self):
        self.model_path = "data/omega_model.pkl"
        self.model = self._load_model()

    def _load_model(self):
        """Charge le modèle de Machine Learning si disponible"""
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f:
                return pickle.load(f)
        # Modèle de secours si non entraîné
        return RandomForestClassifier(n_estimators=100)

    def _detect_skin(self, img):
        """Détecte la présence de chair humaine (Anti-fraude visage/main)"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # Plages de couleurs de peau en HSV
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Calcul du pourcentage de pixels "peau"
        ratio = (np.count_nonzero(mask) / (img.shape[0] * img.shape[1])) * 100
        return ratio > 15

    def _calculate_entropy(self, img_gray):
        """Calcule la complexité visuelle (Entropie). Liquide = Faible."""
        hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256])
        hist = hist / hist.sum()
        non_zero_hist = hist[hist > 0]
        return float(-np.sum(non_zero_hist * np.log2(non_zero_hist)))

    def _firewall_check(self, img, gray):
        """Pare-feu bloquant : Rejette l'image avant l'analyse si suspecte"""
        if self._detect_skin(img):
            return False, "OBJET NON CONFORME : Présence humaine détectée."
        
        if self._calculate_entropy(gray) > 5.0:
            return False, "ENVIRONNEMENT TROP COMPLEXE : Veuillez cadrer uniquement l'éprouvette."
        
        if np.std(img) > 55:
            return False, "COULEURS HÉTÉROGÈNES : Image non uniforme."
        
        if np.mean(gray) < 30:
            return False, "ÉCLAIRAGE INSUFFISANT : Image trop sombre."
            
        return True, "OK"

    def _analyze_physics(self, img, gray):
        """Analyse les métriques physiques du carburant"""
        h, w, _ = img.shape
        # Zones d'intérêt : Bas (sédiments/eau) vs Milieu (référence)
        bottom = img[int(h*0.80):, :]
        top = img[int(h*0.2):int(h*0.6), :]
        
        # Détection d'eau par différence de densité optique
        diff_val = abs(np.mean(bottom) - np.mean(top))
        water_risk = bool(diff_val > 35) # Conversion stricte pour JSON
        
        # Détection de sédiments par détection de contours (Canny)
        edges = cv2.Canny(gray, 100, 200)
        impurities = int(np.count_nonzero(edges))
        
        # Turbidité (Niveau de trouble)
        turbidity = float(gray.std())
        
        # Couleur moyenne (BGR -> RGB pour la BI)
        avg_color = [float(c) for c in cv2.mean(img)[:3]]
        
        return {
            "water": water_risk,
            "sediments": impurities,
            "turbidity": turbidity,
            "avg_color": avg_color
        }

    async def analyze_with_turbo_mode(self, img_bytes, station):
        """Point d'entrée principal de l'analyse"""
        # Conversion du flux binaire en image OpenCV
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"risk_level": "REJET", "diagnostic": "Fichier image corrompu."}

        # Redimensionnement standard pour l'IA
        img_std = cv2.resize(img, (300, 400))
        gray = cv2.cvtColor(img_std, cv2.COLOR_BGR2GRAY)

        # 1. PASSAGE DU PARE-FEU
        is_valid, reason = self._firewall_check(img_std, gray)
        if not is_valid:
            return {
                "risk_level": "REJET",
                "turbidity": 0.0,
                "water_presence": False,
                "impurities": 0,
                "diagnostic": reason,
                "features": [0.0] * 5
            }

        # 2. ANALYSE PHYSIQUE
        phys = self._analyze_physics(img_std, gray)
        
        # 3. ÉTABLISSEMENT DU VERDICT
        verdict = []
        risk_score = 0
        
        if phys['water']:
            verdict.append("EAU DÉTECTÉE")
            risk_score += 60
        if phys['sediments'] > 1500:
            verdict.append(f"IMPURETÉS ÉLEVÉES ({phys['sediments']})")
            risk_score += 30
        if phys['turbidity'] < 10:
            verdict.append("TURBIDITÉ ANORMALE")
            risk_score += 20

        # Détermination du niveau de risque final
        if risk_score >= 50:
            final_risk = "DANGER CRITIQUE"
        elif risk_score > 0:
            final_risk = "ATTENTION"
        else:
            final_risk = "NORMAL"

        diag_text = " // ".join(verdict) if verdict else "Carburant conforme aux normes visuelles."

        return {
            "risk_level": final_risk,
            "turbidity": round(phys['turbidity'], 2),
            "water_presence": phys['water'],
            "impurities": phys['sediments'],
            "diagnostic": diag_text,
            "features": phys['avg_color'] + [phys['turbidity'], float(phys['sediments'])]
        }

    def train_model(self, data):
        """Réentraînement (Placeholder pour le cycle ML)"""
        pass
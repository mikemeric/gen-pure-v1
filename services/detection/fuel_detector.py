import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    """Agent SENTINELLE V7.0 : Algorithme Mathématique Anti-Humain"""

    def __init__(self):
        self.model_path = "data/omega_model.pkl"
        self.model = self._load_model()
        # On supprime la dépendance Haarcascade (trop fragile sur Render)

    def _load_model(self):
        if os.path.exists(self.model_path):
            with open(self.model_path, 'rb') as f: return pickle.load(f)
        return RandomForestClassifier(n_estimators=100)

    def _detect_skin(self, img):
        """Détecte la présence de peau humaine via analyse spectrale HSV"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Plage de couleur de peau générique (Teinte basse, Saturation moyenne)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        skin_pixels = np.count_nonzero(mask)
        total_pixels = img.shape[0] * img.shape[1]
        
        ratio = (skin_pixels / total_pixels) * 100
        # Si plus de 15% de l'image ressemble à de la peau -> REJET
        return ratio > 15

    def _calculate_entropy(self, img_gray):
        """Mesure le désordre. Liquide = Faible. Visage = Élevé."""
        hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256])
        hist = hist / hist.sum()
        non_zero_hist = hist[hist > 0]
        entropy = -np.sum(non_zero_hist * np.log2(non_zero_hist))
        return float(entropy)

    def _firewall_check(self, img, gray):
        """LE PARE-FEU : Bloque tout ce qui n'est pas du liquide pur"""
        
        # 1. DÉTECTION DE PEAU (Remplace la détection faciale)
        if self._detect_skin(img):
            return False, "OBJET NON CONFORME : Peau ou main détectée. Cadrez l'éprouvette."

        # 2. ANALYSE D'ENTROPIE (Texture)
        # Seuil abaissé à 5.0 pour être très strict
        entropy = self._calculate_entropy(gray)
        if entropy > 5.0:
            return False, "ENVIRONNEMENT TROP COMPLEXE : Trop de détails (visage/fond)."

        # 3. VARIANCE DE COULEUR (Le gasoil est uniforme)
        color_variance = np.std(img)
        if color_variance > 55: 
            return False, "COULEURS HÉTÉROGÈNES : L'image n'est pas uniforme."

        # 4. LUMINOSITÉ
        if np.mean(gray) < 30:
            return False, "IMAGE TROP SOMBRE."

        return True, "OK"

    def _analyze_physics(self, img, gray):
        """Analyse technique (si le Pare-Feu est passé)"""
        h, w, _ = img.shape
        bottom = img[int(h*0.80):, :] 
        top = img[int(h*0.2):int(h*0.6), :] 
        
        # EAU
        diff_val = abs(np.mean(bottom) - np.mean(top))
        water_risk = bool(diff_val > 35)
        
        # SÉDIMENTS
        edges = cv2.Canny(gray, 100, 200)
        impurities = int(np.count_nonzero(edges))
        
        # TURBIDITÉ
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
            return {"risk_level": "REJET", "diagnostic": "Fichier illisible"}

        # Redimensionnement (Optimisation Render RAM)
        img_std = cv2.resize(img, (300, 400))
        gray = cv2.cvtColor(img_std, cv2.COLOR_BGR2GRAY)

        # --- PHASE 1 : LE PARE-FEU (Bloquant) ---
        is_valid, reason = self._firewall_check(img_std, gray)
        
        if not is_valid:
            # REJET SYSTÉMATIQUE ET DÉFINITIF
            return {
                "risk_level": "REJET",  # C'est ce mot-clé exact que le frontend attend
                "turbidity": 999.9,     # Valeur aberrante pour forcer l'alerte
                "water_presence": True, 
                "impurities": 9999,
                "diagnostic": reason,   # Ex: "OBJET NON CONFORME..."
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
        pass
        
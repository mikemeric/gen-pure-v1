import cv2
import numpy as np
import os
import pickle
from sklearn.ensemble import RandomForestClassifier

class GlobalIntelligenceUnit:
    """Agent SENTINELLE V8.0 (TITANIUM) : Fusion Pare-Feu V7 + Apprentissage V5"""

    def __init__(self):
        self.model_path = "data/omega_brain.pkl"
        self.model = self._load_model()
        # Indicateur d'état pour savoir si on peut faire confiance à l'IA
        self.is_trained = os.path.exists(self.model_path)

    def _load_model(self):
        """Charge le cerveau ou en crée un vierge"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"ERREUR CHARGEMENT IA: {e}")
        return RandomForestClassifier(n_estimators=100)

    # --- MODULE 1 : LE PARE-FEU (Héritage V7.1) ---

    def _detect_skin(self, img):
        """Détecte la présence humaine (Sabotage/Main devant l'objectif)"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        ratio = (np.count_nonzero(mask) / (img.shape[0] * img.shape[1])) * 100
        return ratio > 15

    def _calculate_entropy(self, img_gray):
        """Vérifie si l'image est un liquide (faible entropie) ou un décor complexe"""
        hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256])
        hist = hist / hist.sum()
        non_zero_hist = hist[hist > 0]
        return float(-np.sum(non_zero_hist * np.log2(non_zero_hist)))

    def _firewall_check(self, img, gray):
        """Le Gardien : Bloque les mauvaises images avant analyse"""
        # 1. Anti-Sabotage Humain
        if self._detect_skin(img):
            return False, "SABOTAGE : Main ou visage détecté. Cadrez la bouteille."
        
        # 2. Anti-Décor (Entropie)
        if self._calculate_entropy(gray) > 5.5:
            return False, "CADRAGE INCORRECT : Trop de détails de fond."
        
        # 3. Qualité Lumière
        if np.mean(gray) < 20:
            return False, "IMAGE TROP SOMBRE : Allumez le flash."
        if np.std(img) > 65:
            return False, "ÉCLAIRAGE HÉTÉROGÈNE : Évitez les reflets violents."
            
        return True, "OK"

    # --- MODULE 2 : ANALYSE PHYSIQUE (Héritage V7.1 + Features V5) ---

    def _analyze_physics(self, img, gray):
        """Extraction des données mathématiques"""
        h, w, _ = img.shape
        # Zone Basse (Sédiments/Eau) vs Zone Haute (Carburant)
        bottom = img[int(h*0.80):, :]
        top = img[int(h*0.2):int(h*0.6), :]
        
        # Détection Eau (Différence de densité visuelle)
        diff_val = abs(np.mean(bottom) - np.mean(top))
        water_risk = bool(diff_val > 35)
        
        # Sédiments (Contours)
        edges = cv2.Canny(gray, 100, 200)
        impurities = int(np.count_nonzero(edges))
        
        # Turbidité
        turbidity = float(gray.std())
        
        # Couleur Moyenne (R, G, B)
        avg_color = [float(c) for c in cv2.mean(img)[:3]]
        
        # Création du vecteur de caractéristiques pour l'IA (5 valeurs)
        # [Rouge, Vert, Bleu, Turbidité, Impuretés]
        features = avg_color + [turbidity, float(impurities)]
        
        return {
            "water": water_risk,
            "sediments": impurities,
            "turbidity": turbidity,
            "features": features
        }

    # --- MODULE 3 : INTELLIGENCE & DÉCISION (Hybride) ---

    async def analyze_with_turbo_mode(self, img_bytes, station):
        """Le Cerveau Central : Orchestre Pare-feu, Physique et IA"""
        
        # 1. Décodage
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return {"risk_level": "REJET", "diagnostic": "Image corrompue"}

        img_std = cv2.resize(img, (300, 400))
        gray = cv2.cvtColor(img_std, cv2.COLOR_BGR2GRAY)

        # 2. Pare-Feu
        valid, reason = self._firewall_check(img_std, gray)
        if not valid:
            return {
                "risk_level": "REJET", 
                "diagnostic": reason, 
                "water_presence": False, 
                "impurities": 0,
                "features": [] 
            }

        # 3. Physique
        phys = self._analyze_physics(img_std, gray)

        # 4. Intelligence Artificielle (Si entraînée)
        ai_vote = None
        if self.is_trained:
            try:
                # 1 = DANGER, 0 = NORMAL
                prediction = self.model.predict([phys['features']])[0]
                ai_vote = "DANGER" if prediction == 1 else "NORMAL"
            except: pass

        # 5. Calcul du Score de Risque (Mode Hybride)
        score = 0
        verdict_text = []

        # Points Physique
        if phys['water']: 
            score += 50
            verdict_text.append("EAU DÉTECTÉE")
        if phys['sediments'] > 1500: 
            score += 30
            verdict_text.append(f"IMPURETÉS ({phys['sediments']})")
        
        # Influence de l'IA (Pondération)
        if ai_vote == "DANGER":
            score += 20 # L'IA penche vers le danger
            verdict_text.append("SUSPICION IA")
        elif ai_vote == "NORMAL" and score < 60:
            score -= 10 # L'IA rassure sur les cas limites (faux positifs)

        # Verdict Final
        final_risk = "NORMAL"
        if score >= 50: final_risk = "DANGER CRITIQUE"
        elif score > 0: final_risk = "ATTENTION"

        full_diag = " // ".join(verdict_text) if verdict_text else "Carburant Conforme (Analysé par OMEGA)."

        return {
            "risk_level": final_risk,
            "turbidity": round(phys['turbidity'], 2),
            "water_presence": phys['water'],
            "impurities": phys['sediments'],
            "diagnostic": full_diag,
            "features": phys['features'] # Crucial pour l'apprentissage futur
        }

    # --- MODULE 4 : APPRENTISSAGE (Héritage V5.0) ---

    def train_model(self, scans_data):
        """Apprend des corrections manuelles du Manager"""
        X = [] # Features
        y = [] # Labels (0 ou 1)
        count = 0

        for scan in scans_data:
            # On ne garde que les scans validés manuellement qui ont des features
            if scan.get('manual_validation') and scan.get('features'):
                feat = scan['features']
                # Si le manager a dit DANGER ou ATTENTION -> 1, sinon -> 0
                label = 1 if scan['manual_validation'] in ['DANGER CRITIQUE', 'ATTENTION'] else 0
                
                # Sécurité format
                if isinstance(feat, list) and len(feat) == 5:
                    X.append(feat)
                    y.append(label)
                    count += 1
        
        # Seuil d'apprentissage (10 exemples minimum)
        if count >= 10:
            print(f"--- OMEGA LEARNING : Mise à jour sur {count} échantillons ---")
            self.model.fit(X, y)
            self.is_trained = True
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            return True
        else:
            print(f"--- OMEGA WAITING : Pas assez de données ({count}/10) ---")
            return False
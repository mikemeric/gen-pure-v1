import cv2
import numpy as np
from PIL import Image
import io

class FuelLevelDetector:
    def __init__(self):
        self.water_threshold = 0.15  # Seuil de détection d'eau
        
    async def analyze(self, image_bytes):
        # Conversion de l'image pour OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Calcul de la Turbidité (Clarté)
        # On mesure l'écart-type de la luminosité (un fuel pur est limpide)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        turbidity_score = max(0, min(100, 100 - (laplacian_var / 10)))
        
        # 2. Détection d'Eau (Séparation de phase au fond)
        # Recherche de lignes horizontales dans le tiers inférieur
        height, width = gray.shape
        roi_bottom = gray[int(height*0.7):height, :]
        edges = cv2.Canny(roi_bottom, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=width*0.3)
        
        water_detected = False
        if lines is not None:
            water_detected = True # Une ligne nette au fond indique souvent de l'eau
            
        # 3. Détection d'Impuretés (Particules sombres)
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        impurity_count = len([c for c in contours if cv2.contourArea(c) > 5])

        # Synthèse des résultats
        status = "CONFORME"
        if water_detected or turbidity_score > 50 or impurity_count > 20:
            status = "CRITIQUE"
        elif turbidity_score > 20:
            status = "ATTENTION"

        return {
            "status": status,
            "turbidity": round(turbidity_score, 2),
            "water_present": water_detected,
            "impurities_found": impurity_count,
            "recommendation": self._get_advice(status, water_detected)
        }

    def _get_advice(self, status, water):
        if water: return "STOP ! Eau détectée au fond. Purge immédiate requise."
        if status == "CRITIQUE": return "Carburant très trouble ou pollué. Analyse labo nécessaire."
        if status == "ATTENTION": return "Légère turbidité. Surveiller la filtration."
        return "Carburant conforme aux normes de pureté."
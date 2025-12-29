import cv2
import numpy as np

class FuelLevelDetector:
    async def analyze(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Turbidité (Clarté)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        turbidity = max(0, min(100, 100 - (laplacian_var / 10)))
        
        # Détection d'Eau (Séparation de phase)
        height, width = gray.shape
        roi_bottom = gray[int(height*0.7):height, :]
        edges = cv2.Canny(roi_bottom, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=width*0.3)
        water_detected = lines is not None
        
        status = "CONFORME"
        if water_detected or turbidity > 30: status = "CRITIQUE"

        return {
            "status": status,
            "turbidity": round(turbidite, 2),
            "water_present": water_detected,
            "impurities_found": "Analyse optique terminée",
            "recommendation": "Vérifier la filtration" if status == "CRITIQUE" else "RAS"
        }
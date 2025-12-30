import cv2
import numpy as np

class FuelLevelDetector:
    async def analyze(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None: return {"status": "ERREUR IMAGE"}

        # Conversion et réduction du bruit
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 1. Calcul de la Turbidité (Basé sur la fréquence des contrastes)
        edges_full = cv2.Canny(blurred, 100, 200)
        edge_density = np.sum(edges_full > 0) / (gray.size)
        turbidity = round(max(0, min(100, (1-edge_density*50) * 100)), 1)

        # 2. Détection d'Eau (Séparation de phase par gradient de densité)
        h, w = gray.shape
        roi_bottom = gray[int(h*0.65):h, :] # On focus sur le bas de l'éprouvette
        edges_bottom = cv2.Canny(roi_bottom, 30, 100)
        lines = cv2.HoughLinesP(edges_bottom, 1, np.pi/180, 50, minLineLength=w*0.4)
        water_detected = lines is not None

        # Diagnostic
        if water_detected:
            status = "CRITIQUE : EAU PRÉSENTE"
            advice = "STOP ! Phase aqueuse détectée au fond de l'échantillon. Purge de cuve indispensable."
        elif turbidity > 45:
            status = "ALERTE : TURBIDITÉ ÉLEVÉE"
            advice = "Attention : Carburant trouble (émulsion possible). Vérifiez l'étanchéité et les filtres."
        else:
            status = "CARBURANT CONFORME"
            advice = "Pureté optimale détectée. Pas d'anomalie visible."

        return {
            "status": status,
            "turbidity": turbidity,
            "water_present": water_detected,
            "recommendation": advice
        }
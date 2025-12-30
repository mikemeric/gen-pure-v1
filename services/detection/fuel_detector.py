import cv2
import numpy as np
from PIL import Image
import io
import google.generativeai as genai

class GlobalIntelligenceUnit:
    """Agent SENTINELLE : Expertise visuelle et chimique par IA"""

    def __init__(self):
        # Configuration du modèle de vision OMEGA
        genai.configure(api_key="VOTRE_CLE_API_GOOGLE")
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def analyze_with_turbo_mode(self, image_bytes, station_name, history_data=None):
        """
        Analyse hybride : OpenCV pour les métriques physiques + Gemini pour le diagnostic expert.
        """
        # 1. PRÉ-TRAITEMENT VISION (OpenCV & NumPy)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Calcul de la turbidité via la variance du Laplacien (netteté/particules)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        turbidity_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Normalisation du score (0 à 100) pour l'Agent VISION
        normalized_turbidity = min(max(round(turbidity_score / 10, 2), 0.5), 99.0)

        # 2. ANALYSE EXPERTE (Gemini Vision)
        pil_img = Image.open(io.BytesIO(image_bytes))
        
        prompt = f"""
        ANALYSE TACTIQUE GEN-PURE OMEGA
        Station: {station_name}
        Métriques physiques : Turbidité détectée à {normalized_turbidity} NTU.
        
        Instructions : 
        1. Détecter la présence d'eau libre (bulles ou séparation de phase).
        2. Analyser la clarté du carburant.
        3. Rendre un verdict : CONFORME, VIGILANCE ou DANGER.
        
        Format de réponse JSON uniquement :
        {{
            "status": "Verdict",
            "risk_level": "DANGER/VIGILANCE/NORMAL",
            "diagnostic": "Explication courte",
            "turbidity": {normalized_turbidity}
        }}
        """

        try:
            response = await self.model.generate_content_async([prompt, pil_img])
            # Nettoyage et extraction du JSON de la réponse
            result = self._parse_json_response(response.text)
            return result
        except Exception as e:
            # Mode dégradé si l'API échoue
            return {
                "status": "MODE DÉGRADÉ",
                "risk_level": "VIGILANCE" if normalized_turbidity > 50 else "NORMAL",
                "diagnostic": f"Analyse locale effectuée. Turbidité: {normalized_turbidity}",
                "turbidity": normalized_turbidity
            }

    def _parse_json_response(self, text):
        import json
        # Nettoie les balises markdown si présentes
        clean_text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
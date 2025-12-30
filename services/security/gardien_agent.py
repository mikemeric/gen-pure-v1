from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

# Clé de chiffrement de l'État-Major (À garder secrète)
SECRET_KEY = "OMEGA_SUPER_SECRET_REDACTED_2024"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class GardienAgent:
    """Agent GARDIEN : Responsable de l'accès et de l'intégrité des données"""

    def hash_password(self, password: str):
        return pwd_context.hash(password)

    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=8)  # Session de 8h
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def seal_report(self, report_id, operator_name):
        """Crée une signature numérique pour le rapport"""
        payload = {
            "report": report_id,
            "op": operator_name,
            "ts": datetime.utcnow().isoformat()
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
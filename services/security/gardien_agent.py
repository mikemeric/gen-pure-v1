from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional

class GardienAgent:
    def __init__(self):
        self.SECRET_KEY = "OMEGA_SECRET_KEY_CHANGE_ME_IN_PROD"
        self.ALGORITHM = "HS256"

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(hours=12) # Session de 12h
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)

    def verify_token(self, token: str):
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            return payload # Retourne {sub: username, role: ..., company_id: ...}
        except JWTError:
            return None
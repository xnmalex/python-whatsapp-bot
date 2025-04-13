import jwt
import os
from datetime import datetime, timedelta

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24  # 1 day

def create_token(payload: dict, expires_in_minutes: int = JWT_EXPIRATION_MINUTES) -> str:
    payload = payload.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

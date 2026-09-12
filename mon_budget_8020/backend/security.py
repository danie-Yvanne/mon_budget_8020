"""
Sécurité : hachage des mots de passe (bcrypt) + jetons JWT.

IMPORTANT : SECRET_KEY doit venir d'une variable d'environnement en
production, jamais codée en dur. Génère-la une fois avec :
    python -c "import secrets; print(secrets.token_hex(32))"
"""
import os
import datetime
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "CHANGE_MOI_EN_PRODUCTION")
ALGORITHM = "HS256"
EXPIRATION_TOKEN_HEURES = 24 * 30  # 30 jours

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_mot_de_passe(mot_de_passe: str) -> str:
    return pwd_context.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    return pwd_context.verify(mot_de_passe, mot_de_passe_hash)


def creer_token(user_id: int) -> str:
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=EXPIRATION_TOKEN_HEURES)
    payload = {"sub": str(user_id), "exp": expiration}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decoder_token(token: str) -> Optional[int]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except JWTError:
        return None

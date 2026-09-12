import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from security import decoder_token
import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    erreur = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée, merci de te reconnecter.",
    )
    user_id = decoder_token(token)
    if user_id is None:
        raise erreur
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise erreur
    return user


def calculer_statut_pro(user: models.User, db: Session) -> dict:
    """
    Seule source de vérité pour savoir si un utilisateur est PRO : la table
    Abonnement (payant OU parrainage, même mécanisme), jamais un booléen
    stocké côté client. On prend l'abonnement ACTIF dont la date de fin la
    plus lointaine, tous plans confondus (les périodes peuvent se cumuler,
    ex: Pass payant + jours de parrainage).
    """
    maintenant = datetime.datetime.utcnow()

    abo_actif = (
        db.query(models.Abonnement)
        .filter(
            models.Abonnement.user_id == user.id,
            models.Abonnement.statut == models.StatutAbonnement.ACTIF,
            models.Abonnement.date_fin > maintenant,
        )
        .order_by(models.Abonnement.date_fin.desc())
        .first()
    )
    if abo_actif:
        return {
            "is_pro": True,
            "plan_actuel": abo_actif.plan.value,
            "date_fin": abo_actif.date_fin,
            "jours_pro_bonus": user.jours_pro_bonus,
        }

    return {
        "is_pro": False,
        "plan_actuel": None,
        "date_fin": None,
        "jours_pro_bonus": user.jours_pro_bonus,
    }

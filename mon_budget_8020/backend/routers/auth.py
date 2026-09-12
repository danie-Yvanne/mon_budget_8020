import secrets
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from security import hash_mot_de_passe, verifier_mot_de_passe, creer_token
from deps import get_current_user, calculer_statut_pro

router = APIRouter(prefix="/auth", tags=["Authentification"])

# Règle de parrainage : 1 ami inscrit + première utilisation = 10 jours PRO,
# plafonné à 30 jours offerts cumulés par période de 60 jours pour limiter les abus.
JOURS_OFFERTS_PAR_PARRAINAGE = 10
PLAFOND_JOURS_PARRAINAGE = 30


def _generer_code_parrainage() -> str:
    return secrets.token_hex(3).upper()  # ex: "A1B2C3"


@router.post("/inscription", response_model=schemas.UserOut, status_code=201)
def inscription(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if not payload.email and not payload.telephone:
        raise HTTPException(400, "Un email ou un numéro de téléphone est requis.")

    existe = None
    if payload.email:
        existe = db.query(models.User).filter(models.User.email == payload.email).first()
    if not existe and payload.telephone:
        existe = db.query(models.User).filter(models.User.telephone == payload.telephone).first()
    if existe:
        raise HTTPException(409, "Un compte existe déjà avec cet email ou ce numéro.")

    parrain = None
    if payload.code_parrain:
        parrain = db.query(models.User).filter(
            models.User.code_parrainage == payload.code_parrain.upper()
        ).first()

    nouvel_utilisateur = models.User(
        nom=payload.nom,
        email=payload.email,
        telephone=payload.telephone,
        mot_de_passe_hash=hash_mot_de_passe(payload.mot_de_passe),
        revenu_mensuel_declare=payload.revenu_mensuel_declare,
        code_parrainage=_generer_code_parrainage(),
        parraine_par_id=parrain.id if parrain else None,
    )
    db.add(nouvel_utilisateur)
    db.commit()
    db.refresh(nouvel_utilisateur)

    # Récompenser le parrain dès l'inscription (le "première utilisation"
    # peut être déplacé vers la première transaction si on veut être strict
    # anti-abus ; ici on garde simple pour le MVP).
    if parrain is not None and parrain.jours_pro_bonus < PLAFOND_JOURS_PARRAINAGE:
        jours_a_ajouter = min(
            JOURS_OFFERTS_PAR_PARRAINAGE,
            PLAFOND_JOURS_PARRAINAGE - parrain.jours_pro_bonus,
        )
        parrain.jours_pro_bonus += jours_a_ajouter
        _prolonger_ou_creer_abonnement_parrainage(db, parrain, jours_a_ajouter)
        db.commit()

    return nouvel_utilisateur


def _prolonger_ou_creer_abonnement_parrainage(db: Session, user: models.User, jours: int):
    maintenant = datetime.datetime.utcnow()
    abo_parrainage = (
        db.query(models.Abonnement)
        .filter(
            models.Abonnement.user_id == user.id,
            models.Abonnement.plan == models.PlanPass.PARRAINAGE,
            models.Abonnement.statut == models.StatutAbonnement.ACTIF,
            models.Abonnement.date_fin > maintenant,
        )
        .first()
    )
    if abo_parrainage:
        abo_parrainage.date_fin += datetime.timedelta(days=jours)
    else:
        db.add(models.Abonnement(
            user_id=user.id,
            plan=models.PlanPass.PARRAINAGE,
            statut=models.StatutAbonnement.ACTIF,
            montant_fcfa=0,
            reference_paiement=f"PARRAINAGE_{user.id}_{secrets.token_hex(4)}",
            date_debut=maintenant,
            date_fin=maintenant + datetime.timedelta(days=jours),
        ))


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(
        (models.User.email == payload.identifiant) |
        (models.User.telephone == payload.identifiant)
    ).first()
    if not user or not verifier_mot_de_passe(payload.mot_de_passe, user.mot_de_passe_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect.")
    return schemas.Token(access_token=creer_token(user.id))


@router.get("/moi", response_model=schemas.UserOut)
def mon_profil(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.get("/statut-pro", response_model=schemas.StatutProOut)
def statut_pro(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calculer_statut_pro(current_user, db)

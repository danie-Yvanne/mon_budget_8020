"""
Paiements Mobile Money via Notch Pay.

Principe de sécurité central : la clé privée Notch Pay ne quitte JAMAIS ce
serveur. L'app Flet ne parle jamais directement à Notch Pay, elle appelle
ce backend, qui lui-même appelle Notch Pay. C'est aussi ce serveur qui reçoit
le webhook de confirmation et qui, seul, active le Pass PRO en base.
"""
import os
import hmac
import hashlib
import secrets
import datetime
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import get_current_user

router = APIRouter(prefix="/paiements", tags=["Paiements"])

NOTCHPAY_PRIVATE_KEY = os.environ.get("NOTCHPAY_PRIVATE_KEY", "")
NOTCHPAY_WEBHOOK_SECRET = os.environ.get("NOTCHPAY_WEBHOOK_SECRET", "")
NOTCHPAY_BASE_URL = "https://api.notchpay.co"


@router.post("/initier", response_model=schemas.InitierPaiementOut)
def initier_paiement(
    payload: schemas.InitierPaiementIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not NOTCHPAY_PRIVATE_KEY:
        raise HTTPException(500, "Paiement non configuré côté serveur (clé Notch Pay manquante).")

    montant = schemas.PRIX_PASS_FCFA[payload.plan]
    reference = f"PASS_{payload.plan.value}_{current_user.id}_{secrets.token_hex(4)}"

    # Créer un abonnement EN_ATTENTE : il ne devient ACTIF que quand le
    # webhook confirme le paiement, jamais avant.
    abonnement = models.Abonnement(
        user_id=current_user.id,
        plan=payload.plan,
        statut=models.StatutAbonnement.EN_ATTENTE,
        montant_fcfa=montant,
        reference_paiement=reference,
    )
    db.add(abonnement)
    db.commit()

    try:
        reponse = requests.post(
            f"{NOTCHPAY_BASE_URL}/payments/initialize",
            json={
                "amount": montant,
                "currency": "XAF",
                "email": current_user.email or f"user{current_user.id}@monbudget8020.cm",
                "description": f"Pass {payload.plan.value} - Mon Budget 80/20",
                "reference": reference,
            },
            headers={"Authorization": NOTCHPAY_PRIVATE_KEY, "Accept": "application/json"},
            timeout=15,
        )
        data = reponse.json()
    except Exception as e:
        raise HTTPException(502, f"Erreur de connexion à Notch Pay : {e}")

    if reponse.status_code != 201 or data.get("status") != "accepted":
        abonnement.statut = models.StatutAbonnement.ECHOUE
        db.commit()
        raise HTTPException(502, "Notch Pay a refusé l'initialisation du paiement.")

    return schemas.InitierPaiementOut(
        authorization_url=data["authorization_url"],
        reference=reference,
        montant=montant,
    )


@router.get("/mes-abonnements", response_model=list[schemas.AbonnementOut])
def mes_abonnements(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Abonnement)
        .filter(models.Abonnement.user_id == current_user.id)
        .order_by(models.Abonnement.date_creation.desc())
        .all()
    )


@router.post("/webhook/notchpay")
async def webhook_notchpay(request: Request, db: Session = Depends(get_db)):
    """
    Reçoit la confirmation de Notch Pay. Vérifie la signature avant de faire
    quoi que ce soit : sans ça, n'importe qui pourrait POSTer ici et activer
    un Pass gratuitement.
    """
    corps_brut = await request.body()
    signature_recue = request.headers.get("x-notch-signature", "")

    if NOTCHPAY_WEBHOOK_SECRET:
        signature_attendue = hmac.new(
            NOTCHPAY_WEBHOOK_SECRET.encode(), corps_brut, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature_recue, signature_attendue):
            raise HTTPException(401, "Signature de webhook invalide.")

    payload = await request.json()
    evenement = payload.get("event", "")
    reference = payload.get("data", {}).get("reference")

    if not reference:
        raise HTTPException(400, "Référence de paiement manquante dans le webhook.")

    abonnement = (
        db.query(models.Abonnement)
        .filter(models.Abonnement.reference_paiement == reference)
        .first()
    )
    if not abonnement:
        raise HTTPException(404, "Abonnement correspondant introuvable.")

    if evenement in ("payment.complete", "payment.success"):
        duree = schemas.DUREE_JOURS_PASS[abonnement.plan]
        maintenant = datetime.datetime.utcnow()
        abonnement.statut = models.StatutAbonnement.ACTIF
        abonnement.date_debut = maintenant
        abonnement.date_fin = maintenant + datetime.timedelta(days=duree)
        db.commit()
    elif evenement in ("payment.failed", "payment.canceled"):
        abonnement.statut = models.StatutAbonnement.ECHOUE
        db.commit()

    return {"recu": True}

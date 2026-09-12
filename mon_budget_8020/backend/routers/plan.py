import datetime
import calendar
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import get_current_user

router = APIRouter(prefix="/plan", tags=["Plan"])


def _mois_courant() -> str:
    aujourdhui = datetime.date.today()
    return f"{aujourdhui.year:04d}-{aujourdhui.month:02d}"


def _construire_plan_out(mois: str, revenus_prevus, obligations) -> schemas.PlanOut:
    total_revenus = sum(l.montant for l in revenus_prevus)
    total_obligations = sum(l.montant for l in obligations)
    budget_80 = total_revenus * 0.8
    objectif_20 = total_revenus * 0.2
    flexible = max(budget_80 - total_obligations, 0)

    annee, mois_num = int(mois[:4]), int(mois[5:7])
    jours_dans_mois = calendar.monthrange(annee, mois_num)[1]
    aujourdhui = datetime.date.today()
    jours_restants = jours_dans_mois
    if aujourdhui.strftime("%Y-%m") == mois:
        jours_restants = max(jours_dans_mois - aujourdhui.day + 1, 1)

    return schemas.PlanOut(
        mois=mois,
        revenus_prevus=revenus_prevus,
        obligations=obligations,
        total_revenus_prevus=round(total_revenus, 2),
        budget_80=round(budget_80, 2),
        objectif_epargne_20=round(objectif_20, 2),
        total_obligations=round(total_obligations, 2),
        budget_flexible_restant=round(flexible, 2),
        budget_flexible_par_jour=round(flexible / jours_restants, 2),
    )


@router.get("", response_model=schemas.PlanOut)
def obtenir_plan(
    mois: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mois = mois or _mois_courant()
    lignes = db.query(models.PlanLigne).filter(
        models.PlanLigne.user_id == current_user.id, models.PlanLigne.mois == mois,
    ).all()
    revenus_prevus = [l for l in lignes if l.type == models.TypePlanLigne.REVENU_PREVU]
    obligations = [l for l in lignes if l.type == models.TypePlanLigne.OBLIGATION]
    return _construire_plan_out(mois, revenus_prevus, obligations)


@router.post("", response_model=schemas.PlanOut)
def enregistrer_plan(
    payload: schemas.PlanIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remplace entièrement le plan du mois donné par les lignes envoyées."""
    db.query(models.PlanLigne).filter(
        models.PlanLigne.user_id == current_user.id, models.PlanLigne.mois == payload.mois,
    ).delete()

    revenus_prevus = [
        models.PlanLigne(user_id=current_user.id, mois=payload.mois,
                          type=models.TypePlanLigne.REVENU_PREVU,
                          categorie=l.categorie, montant=l.montant)
        for l in payload.revenus_prevus
    ]
    obligations = [
        models.PlanLigne(user_id=current_user.id, mois=payload.mois,
                          type=models.TypePlanLigne.OBLIGATION,
                          categorie=l.categorie, montant=l.montant)
        for l in payload.obligations
    ]
    for ligne in revenus_prevus + obligations:
        db.add(ligne)
    db.commit()
    for ligne in revenus_prevus + obligations:
        db.refresh(ligne)

    return _construire_plan_out(payload.mois, revenus_prevus, obligations)


@router.post("/simulation")
def simuler_plan(
    payload: schemas.PlanSimulationIn,
    mois: str | None = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recalcule le plan avec un scenario 'et si' : delta de revenu, nouvelle
    obligation ajoutee, ou objectif d'epargne cible (auquel cas on indique le
    budget flexible restant une fois cet objectif priorise).
    """
    mois = mois or _mois_courant()
    lignes = db.query(models.PlanLigne).filter(
        models.PlanLigne.user_id == current_user.id, models.PlanLigne.mois == mois,
    ).all()
    total_revenus = sum(l.montant for l in lignes if l.type == models.TypePlanLigne.REVENU_PREVU)
    total_obligations = sum(l.montant for l in lignes if l.type == models.TypePlanLigne.OBLIGATION)

    nouveau_revenu = total_revenus + payload.delta_revenu
    nouvelles_obligations = total_obligations + payload.nouvelle_obligation
    budget_80 = nouveau_revenu * 0.8
    objectif_20_defaut = nouveau_revenu * 0.2
    epargne_visee = payload.epargne_cible if payload.epargne_cible is not None else objectif_20_defaut

    flexible = max(budget_80 - nouvelles_obligations, 0)
    flexible_apres_epargne = max(nouveau_revenu - nouvelles_obligations - epargne_visee, 0)

    return {
        "mois": mois,
        "nouveau_revenu_total": round(nouveau_revenu, 2),
        "nouvelles_obligations_total": round(nouvelles_obligations, 2),
        "budget_80_recalcule": round(budget_80, 2),
        "epargne_visee": round(epargne_visee, 2),
        "budget_flexible_restant": round(flexible, 2),
        "budget_flexible_restant_apres_epargne_visee": round(flexible_apres_epargne, 2),
    }

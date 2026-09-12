import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from deps import get_current_user, calculer_statut_pro
from coaching import generer_conseils

router = APIRouter(prefix="/transactions", tags=["Transactions"])

MAX_TRANSACTIONS_GRATUIT_PAR_JOUR = 3
MAX_TONTINES_GRATUIT = 1
JOURS_HISTORIQUE_GRATUIT = 30


def _transactions_du_jour(db: Session, user_id: int) -> int:
    """
    Quota calculé en comptant les transactions dont la date est aujourd'hui,
    directement en base -> impossible à contourner en changeant l'heure du
    téléphone ou en réinstallant l'app (contrairement au compteur en mémoire
    du prototype initial).
    """
    aujourdhui = datetime.date.today()
    return (
        db.query(models.Transaction)
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.date_transaction == aujourdhui,
        )
        .count()
    )


@router.get("/quota", response_model=schemas.QuotaOut)
def quota(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statut = calculer_statut_pro(current_user, db)
    nb_aujourdhui = _transactions_du_jour(db, current_user.id)
    peut_ajouter = statut["is_pro"] or nb_aujourdhui < MAX_TRANSACTIONS_GRATUIT_PAR_JOUR
    return schemas.QuotaOut(
        peut_ajouter=peut_ajouter,
        transactions_aujourdhui=nb_aujourdhui,
        max_gratuit=MAX_TRANSACTIONS_GRATUIT_PAR_JOUR,
        is_pro=statut["is_pro"],
    )


@router.post("/", response_model=schemas.TransactionOut, status_code=201)
def ajouter_transaction(
    payload: schemas.TransactionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statut = calculer_statut_pro(current_user, db)
    if payload.source != models.SourceTransaction.MANUEL and not statut["is_pro"]:
        raise HTTPException(403, "La saisie intelligente (SMS/vocal/PDF) nécessite un Pass PRO.")

    if not statut["is_pro"]:
        if _transactions_du_jour(db, current_user.id) >= MAX_TRANSACTIONS_GRATUIT_PAR_JOUR:
            raise HTTPException(
                403,
                f"Limite gratuite de {MAX_TRANSACTIONS_GRATUIT_PAR_JOUR} transactions/jour atteinte. "
                "Active un Pass PRO pour une saisie illimitée.",
            )

    transaction = models.Transaction(
        user_id=current_user.id,
        type=payload.type,
        montant=payload.montant,
        categorie=payload.categorie,
        est_fixe=payload.est_fixe,
        source=payload.source,
        description=payload.description,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/", response_model=list[schemas.TransactionOut])
def lister_transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statut = calculer_statut_pro(current_user, db)
    query = db.query(models.Transaction).filter(models.Transaction.user_id == current_user.id)

    if not statut["is_pro"]:
        limite = datetime.date.today() - datetime.timedelta(days=JOURS_HISTORIQUE_GRATUIT)
        query = query.filter(models.Transaction.date_transaction >= limite)

    return query.order_by(models.Transaction.date_transaction.desc()).all()


@router.get("/resume")
def resume_8020(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calcule tout ce qu'il faut pour le dashboard : répartition 80/20 du mois,
    comparaison avec le mois précédent, ventilation par catégorie, historique
    sur 6 mois (pour les graphiques d'évolution) et conseils personnalisés.
    """
    aujourdhui = datetime.date.today()

    def _bornes_mois(annee: int, mois: int):
        debut = datetime.date(annee, mois, 1)
        if mois == 12:
            fin = datetime.date(annee + 1, 1, 1)
        else:
            fin = datetime.date(annee, mois + 1, 1)
        return debut, fin

    def _totaux_periode(debut, fin):
        transactions = (
            db.query(models.Transaction)
            .filter(
                models.Transaction.user_id == current_user.id,
                models.Transaction.date_transaction >= debut,
                models.Transaction.date_transaction < fin,
            )
            .all()
        )
        revenus = sum(t.montant for t in transactions if t.type == models.TypeTransaction.REVENU)
        depenses = sum(t.montant for t in transactions if t.type == models.TypeTransaction.DEPENSE)
        return transactions, revenus, depenses

    # ---- Mois en cours ----
    debut_mois, fin_mois = _bornes_mois(aujourdhui.year, aujourdhui.month)
    transactions_mois, revenus, depenses = _totaux_periode(debut_mois, fin_mois)

    budget_80 = revenus * 0.8
    objectif_epargne_20 = revenus * 0.2
    reste_budget = budget_80 - depenses

    revenu_fixe = sum(t.montant for t in transactions_mois if t.type == models.TypeTransaction.REVENU and t.est_fixe)
    revenu_variable = revenus - revenu_fixe

    def _repartition(transactions, type_):
        totaux: dict[str, float] = {}
        for t in transactions:
            if t.type == type_:
                totaux[t.categorie] = totaux.get(t.categorie, 0) + t.montant
        total = sum(totaux.values()) or 1
        return [
            {"categorie": cat, "montant": montant, "pourcentage": round(montant / total * 100, 1)}
            for cat, montant in sorted(totaux.items(), key=lambda x: -x[1])
        ]

    repartition_revenus = _repartition(transactions_mois, models.TypeTransaction.REVENU)
    repartition_depenses = _repartition(transactions_mois, models.TypeTransaction.DEPENSE)

    # ---- Mois précédent (pour les % de comparaison) ----
    mois_prec = aujourdhui.month - 1 or 12
    annee_prec = aujourdhui.year - 1 if aujourdhui.month == 1 else aujourdhui.year
    debut_prec, fin_prec = _bornes_mois(annee_prec, mois_prec)
    _, revenus_prec, depenses_prec = _totaux_periode(debut_prec, fin_prec)
    epargne_prec = revenus_prec - depenses_prec
    epargne_actuelle = revenus - depenses

    def _variation(actuel, precedent):
        if precedent == 0:
            return None
        return round((actuel - precedent) / precedent * 100, 1)

    # ---- Dettes : montant actuel + évolution sur 6 mois ----
    dettes = db.query(models.Tontine).filter(
        models.Tontine.user_id == current_user.id, models.Tontine.est_dette == True  # noqa: E712
    ).all()
    dette_initiale_totale = sum(d.montant_cotisation for d in dettes)

    def _remboursements_cumules_avant(date_limite):
        total = (
            db.query(models.Transaction)
            .filter(
                models.Transaction.user_id == current_user.id,
                models.Transaction.type == models.TypeTransaction.DEPENSE,
                models.Transaction.categorie == "Remboursement dette",
                models.Transaction.date_transaction < date_limite,
            )
            .all()
        )
        return sum(t.montant for t in total)

    dette_actuelle = max(dette_initiale_totale - _remboursements_cumules_avant(fin_mois), 0)

    # ---- Historique 6 derniers mois (pour les graphiques d'évolution) ----
    historique = []
    for i in range(5, -1, -1):
        m = aujourdhui.month - i
        a = aujourdhui.year
        while m <= 0:
            m += 12
            a -= 1
        d_debut, d_fin = _bornes_mois(a, m)
        _, r, dep = _totaux_periode(d_debut, d_fin)
        dette_a_ce_mois = max(dette_initiale_totale - _remboursements_cumules_avant(d_fin), 0)
        historique.append({
            "mois": d_debut.strftime("%b"),
            "revenus": r,
            "depenses": dep,
            "epargne": r - dep,
            "objectif_epargne": round(r * 0.2, 2),
            "dettes": dette_a_ce_mois,
        })

    resume = {
        "revenus": revenus,
        "depenses": depenses,
        "budget_disponible_80": round(budget_80, 2),
        "objectif_epargne_20": round(objectif_epargne_20, 2),
        "reste_sur_budget": round(reste_budget, 2),
        "pourcentage_budget_utilise": round((depenses / budget_80 * 100), 1) if budget_80 > 0 else 0,
        "alerte": reste_budget < 0,
        "solde_restant": round(revenus - depenses, 2),
        "revenu_fixe": revenu_fixe,
        "revenu_variable": revenu_variable,
        "repartition_revenus": repartition_revenus,
        "repartition_depenses": repartition_depenses,
        "dette_actuelle": round(dette_actuelle, 2),
        "historique_6_mois": historique,
        "comparaison": {
            "revenus_pourcentage": _variation(revenus, revenus_prec),
            "depenses_pourcentage": _variation(depenses, depenses_prec),
            "epargne_pourcentage": _variation(epargne_actuelle, epargne_prec),
        },
    }
    resume["rythme"] = _calculer_rythme(aujourdhui, budget_80, depenses)
    resume["conseils"] = generer_conseils(resume)
    return resume


def _calculer_rythme(aujourdhui: datetime.date, budget_80: float, depenses: float) -> dict:
    """
    Le coeur de l'ecran Accueil : pas juste un pourcentage, mais un rythme
    quotidien compare a ce qu'il faudrait pour tenir jusqu'a la fin du mois.
    """
    import calendar
    jours_dans_mois = calendar.monthrange(aujourdhui.year, aujourdhui.month)[1]
    jour_actuel = aujourdhui.day
    jours_restants = max(jours_dans_mois - jour_actuel, 1)

    rythme_actuel = round(depenses / jour_actuel, 0) if jour_actuel > 0 else 0
    budget_restant = max(budget_80 - depenses, 0)
    rythme_recommande = round(budget_restant / jours_restants, 0)

    depense_projetee_fin_mois = depenses + rythme_actuel * jours_restants
    depassement_projete = max(depense_projetee_fin_mois - budget_80, 0)

    return {
        "jour_du_mois": jour_actuel,
        "jours_dans_mois": jours_dans_mois,
        "jours_restants": jours_restants,
        "rythme_quotidien_actuel": rythme_actuel,
        "rythme_quotidien_recommande": rythme_recommande,
        "trop_eleve": rythme_actuel > rythme_recommande and budget_80 > 0,
        "depassement_projete": round(depassement_projete, 2),
    }


@router.post("/simulation", response_model=schemas.SimulationOut)
def simuler_projet(
    payload: schemas.SimulationIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Simule combien de temps il faudrait pour atteindre un objectif d'épargne,
    à partir de la moyenne réelle des 3 derniers mois (pas juste le mois en
    cours, pour lisser les variations).
    """
    aujourdhui = datetime.date.today()
    epargnes_mensuelles = []
    depenses_mensuelles = []

    for i in range(2, -1, -1):
        m = aujourdhui.month - i
        a = aujourdhui.year
        while m <= 0:
            m += 12
            a -= 1
        debut = datetime.date(a, m, 1)
        fin = datetime.date(a + 1, 1, 1) if m == 12 else datetime.date(a, m + 1, 1)
        transactions = (
            db.query(models.Transaction)
            .filter(
                models.Transaction.user_id == current_user.id,
                models.Transaction.date_transaction >= debut,
                models.Transaction.date_transaction < fin,
            )
            .all()
        )
        r = sum(t.montant for t in transactions if t.type == models.TypeTransaction.REVENU)
        d = sum(t.montant for t in transactions if t.type == models.TypeTransaction.DEPENSE)
        epargnes_mensuelles.append(r - d)
        depenses_mensuelles.append(d)

    epargne_moyenne = sum(epargnes_mensuelles) / len(epargnes_mensuelles) if epargnes_mensuelles else 0
    depense_moyenne = sum(depenses_mensuelles) / len(depenses_mensuelles) if depenses_mensuelles else 0

    epargne_avec_reduction = epargne_moyenne + depense_moyenne * (payload.reduction_depenses_pourcentage / 100)

    def _mois_necessaires(epargne_mensuelle):
        if epargne_mensuelle <= 0:
            return None
        import math
        return math.ceil(payload.montant_cible / epargne_mensuelle)

    mois_actuel = _mois_necessaires(epargne_moyenne)
    mois_reduit = _mois_necessaires(epargne_avec_reduction)

    if mois_actuel is None:
        message = (
            f"Avec ton épargne moyenne actuelle, tu ne mets pas encore d'argent de côté -- "
            f"ajoute des revenus ou réduis tes dépenses pour estimer un délai pour « {payload.nom_projet} »."
        )
    elif payload.reduction_depenses_pourcentage > 0 and mois_reduit:
        gain = mois_actuel - mois_reduit
        message = (
            f"Au rythme actuel, tu peux financer « {payload.nom_projet} » en {mois_actuel} mois. "
            f"En réduisant tes dépenses de {payload.reduction_depenses_pourcentage:.0f}%, "
            f"tu y arrives en {mois_reduit} mois (soit {gain} mois plus tôt)."
        )
    else:
        message = f"Au rythme actuel, tu peux financer « {payload.nom_projet} » en environ {mois_actuel} mois."

    return schemas.SimulationOut(
        nom_projet=payload.nom_projet,
        montant_cible=payload.montant_cible,
        epargne_mensuelle_actuelle=round(epargne_moyenne, 2),
        mois_necessaires_actuel=mois_actuel,
        epargne_mensuelle_avec_reduction=round(epargne_avec_reduction, 2),
        mois_necessaires_avec_reduction=mois_reduit,
        message=message,
    )


# ---------- Tontines / dettes ----------

@router.get("/tontines", response_model=list[schemas.TontineOut])
def lister_tontines(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(models.Tontine).filter(models.Tontine.user_id == current_user.id).all()


@router.post("/tontines", response_model=schemas.TontineOut, status_code=201)
def ajouter_tontine(
    payload: schemas.TontineCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statut = calculer_statut_pro(current_user, db)
    nb_actuelles = db.query(models.Tontine).filter(models.Tontine.user_id == current_user.id).count()

    if not statut["is_pro"] and nb_actuelles >= MAX_TONTINES_GRATUIT:
        raise HTTPException(
            403,
            f"Le plan gratuit permet de suivre {MAX_TONTINES_GRATUIT} tontine/dette maximum. "
            "Passe au Pass PRO pour un suivi illimité.",
        )

    tontine = models.Tontine(user_id=current_user.id, **payload.model_dump())
    db.add(tontine)
    db.commit()
    db.refresh(tontine)
    return tontine


@router.post("/tontines/{tontine_id}/rembourser", response_model=schemas.TontineOut)
def rembourser_dette(
    tontine_id: int,
    payload: schemas.RemboursementCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enregistre un remboursement sur une dette : crée une transaction datée
    (catégorie 'Remboursement dette', utilisée par /resume pour calculer
    l'évolution mensuelle du solde de dettes) ET met à jour le cumul de la
    tontine/dette elle-même.
    """
    tontine = (
        db.query(models.Tontine)
        .filter(models.Tontine.id == tontine_id, models.Tontine.user_id == current_user.id)
        .first()
    )
    if not tontine:
        raise HTTPException(404, "Dette introuvable.")
    if not tontine.est_dette:
        raise HTTPException(400, "Cette entrée est une tontine, pas une dette.")

    tontine.montant_verse_total += payload.montant
    db.add(models.Transaction(
        user_id=current_user.id,
        type=models.TypeTransaction.DEPENSE,
        montant=payload.montant,
        categorie="Remboursement dette",
        est_fixe=False,
        source=models.SourceTransaction.MANUEL,
        description=f"Remboursement : {tontine.nom}",
    ))
    db.commit()
    db.refresh(tontine)
    return tontine

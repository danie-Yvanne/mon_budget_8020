import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from models import PlanPass, StatutAbonnement, TypeTransaction, SourceTransaction


# ---------- Auth / Utilisateur ----------

class UserCreate(BaseModel):
    nom: str
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    mot_de_passe: str
    revenu_mensuel_declare: float = 0
    code_parrain: Optional[str] = None  # code parrainage de l'ami qui invite

    @field_validator("mot_de_passe")
    @classmethod
    def check_password_len(cls, v):
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v


class UserLogin(BaseModel):
    identifiant: str  # email ou téléphone
    mot_de_passe: str


class UserOut(BaseModel):
    id: int
    nom: str
    email: Optional[str] = None
    telephone: Optional[str] = None
    revenu_mensuel_declare: float
    code_parrainage: str
    jours_pro_bonus: int

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StatutProOut(BaseModel):
    is_pro: bool
    plan_actuel: Optional[str] = None
    date_fin: Optional[datetime.datetime] = None
    jours_pro_bonus: int


# ---------- Transactions ----------

class TransactionCreate(BaseModel):
    type: TypeTransaction
    montant: float
    categorie: str = "Autre"
    est_fixe: bool = True
    source: SourceTransaction = SourceTransaction.MANUEL
    description: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    type: TypeTransaction
    montant: float
    categorie: str
    est_fixe: bool
    source: SourceTransaction
    description: Optional[str]
    date_transaction: datetime.date

    class Config:
        from_attributes = True


class QuotaOut(BaseModel):
    peut_ajouter: bool
    transactions_aujourdhui: int
    max_gratuit: int
    is_pro: bool


# ---------- Tontines / Dettes (même table, distinguées par est_dette) ----------

class TontineCreate(BaseModel):
    nom: str
    montant_cotisation: float
    frequence: str = "Mensuelle"
    est_dette: bool = False


class TontineOut(BaseModel):
    id: int
    nom: str
    montant_cotisation: float
    frequence: str
    montant_recu_total: float
    montant_verse_total: float
    est_dette: bool

    class Config:
        from_attributes = True


class RemboursementCreate(BaseModel):
    montant: float


# ---------- Paiements ----------

PRIX_PASS_FCFA = {
    PlanPass.MOIS_1: 2000,
    PlanPass.MOIS_3: 5000,
}

DUREE_JOURS_PASS = {
    PlanPass.MOIS_1: 30,
    PlanPass.MOIS_3: 90,
}


class InitierPaiementIn(BaseModel):
    plan: PlanPass


class InitierPaiementOut(BaseModel):
    authorization_url: str
    reference: str
    montant: int


class AbonnementOut(BaseModel):
    id: int
    plan: PlanPass
    statut: StatutAbonnement
    montant_fcfa: int
    date_debut: Optional[datetime.datetime]
    date_fin: Optional[datetime.datetime]

    class Config:
        from_attributes = True


# ---------- Catégories prédéfinies ----------
# Gardées ici (pas de table dédiée) pour rester simple en V1 ; suffisant tant
# qu'on n'a pas besoin de catégories personnalisées par utilisateur.

CATEGORIES_REVENU = ["Salaire", "Business", "Freelance", "Aide/Don", "Autres"]
CATEGORIES_DEPENSE = [
    "Loyer", "Transport", "Nourriture", "Santé", "Loisirs",
    "Tontine", "Remboursement dette", "Scolarité", "Autre",
]


# ---------- Simulation de projet ----------

class SimulationIn(BaseModel):
    nom_projet: str
    montant_cible: float
    reduction_depenses_pourcentage: float = 0  # ex: 10 pour "si je réduis mes dépenses de 10%"


class SimulationOut(BaseModel):
    nom_projet: str
    montant_cible: float
    epargne_mensuelle_actuelle: float
    mois_necessaires_actuel: Optional[int]
    epargne_mensuelle_avec_reduction: float
    mois_necessaires_avec_reduction: Optional[int]
    message: str


# ---------- Historique mensuel (pour les graphiques d'évolution) ----------

class MoisResume(BaseModel):
    mois_label: str       # ex: "Jan"
    revenus: float
    depenses: float
    objectif_epargne: float
    epargne_realisee: float


class HistoriqueMensuelOut(BaseModel):
    mois: list[MoisResume]


# ---------- Coaching contextuel ----------

class ConseilsOut(BaseModel):
    conseils: list[str]


# ---------- Plan mensuel (revenus prevus + obligations) ----------

class PlanLigneIn(BaseModel):
    categorie: str
    montant: float


class PlanIn(BaseModel):
    mois: str  # "YYYY-MM"
    revenus_prevus: list[PlanLigneIn]
    obligations: list[PlanLigneIn]


class PlanLigneOut(BaseModel):
    id: int
    categorie: str
    montant: float

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    mois: str
    revenus_prevus: list[PlanLigneOut]
    obligations: list[PlanLigneOut]
    total_revenus_prevus: float
    budget_80: float
    objectif_epargne_20: float
    total_obligations: float
    budget_flexible_restant: float
    budget_flexible_par_jour: float


class PlanSimulationIn(BaseModel):
    delta_revenu: float = 0
    nouvelle_obligation: float = 0
    epargne_cible: float | None = None

"""
Modèles de données.
Chaque table est liée à un user_id -> plus jamais de dictionnaire global
partagé entre utilisateurs comme dans le prototype initial.
"""
import enum
import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from database import Base


class PlanPass(str, enum.Enum):
    MOIS_1 = "1_MOIS"
    MOIS_3 = "3_MOIS"
    PARRAINAGE = "PARRAINAGE"  # jours offerts, montant_fcfa = 0


class StatutAbonnement(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"   # paiement initié, webhook pas encore reçu
    ACTIF = "ACTIF"
    EXPIRE = "EXPIRE"
    ECHOUE = "ECHOUE"


class TypeTransaction(str, enum.Enum):
    REVENU = "REVENU"
    DEPENSE = "DEPENSE"


class SourceTransaction(str, enum.Enum):
    MANUEL = "MANUEL"
    SMS = "SMS"
    VOCAL = "VOCAL"
    PDF_IMPORT = "PDF_IMPORT"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    telephone = Column(String, unique=True, index=True, nullable=True)
    mot_de_passe_hash = Column(String, nullable=False)
    revenu_mensuel_declare = Column(Float, default=0)
    code_parrainage = Column(String, unique=True, index=True)
    parraine_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    jours_pro_bonus = Column(Integer, default=0)  # jours offerts via parrainage
    date_creation = Column(DateTime, default=datetime.datetime.utcnow)

    abonnements = relationship("Abonnement", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    tontines = relationship("Tontine", back_populates="user")


class Abonnement(Base):
    __tablename__ = "abonnements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(SAEnum(PlanPass), nullable=False)
    statut = Column(SAEnum(StatutAbonnement), default=StatutAbonnement.EN_ATTENTE)
    montant_fcfa = Column(Integer, nullable=False)
    reference_paiement = Column(String, unique=True, index=True)
    date_debut = Column(DateTime, nullable=True)
    date_fin = Column(DateTime, nullable=True)
    date_creation = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="abonnements")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(SAEnum(TypeTransaction), nullable=False)
    montant = Column(Float, nullable=False)
    categorie = Column(String, default="Autre")
    est_fixe = Column(Boolean, default=True)  # revenu/dépense fixe (loyer, salaire) vs variable
    source = Column(SAEnum(SourceTransaction), default=SourceTransaction.MANUEL)
    description = Column(String, nullable=True)
    date_transaction = Column(Date, default=datetime.date.today)
    date_creation = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="transactions")


class TypePlanLigne(str, enum.Enum):
    REVENU_PREVU = "REVENU_PREVU"
    OBLIGATION = "OBLIGATION"


class PlanLigne(Base):
    __tablename__ = "plan_lignes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mois = Column(String, nullable=False)  # format "YYYY-MM"
    type = Column(SAEnum(TypePlanLigne), nullable=False)
    categorie = Column(String, nullable=False)
    montant = Column(Float, nullable=False)


class Tontine(Base):
    __tablename__ = "tontines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nom = Column(String, nullable=False)
    montant_cotisation = Column(Float, nullable=False)
    frequence = Column(String, default="Mensuelle")  # Hebdo / Mensuelle
    montant_recu_total = Column(Float, default=0)
    montant_verse_total = Column(Float, default=0)
    est_dette = Column(Boolean, default=False)  # True si c'est un suivi de dette
    date_creation = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="tontines")

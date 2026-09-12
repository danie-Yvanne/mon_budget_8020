"""
Configuration de la base de données.
SQLite pour démarrer/valider le marché (voir avis produit) -> migrer vers
PostgreSQL (Render, Railway, Supabase...) dès qu'il y a des vrais utilisateurs
payants, en changeant uniquement DATABASE_URL.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./mon_budget_8020.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency FastAPI : ouvre une session DB et la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

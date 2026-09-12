from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
import models  # noqa: F401 - nécessaire pour que Base connaisse les tables
from routers import auth, transactions, payments, plan

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mon Budget 80/20 - API",
    description="Backend sécurisé : authentification, quotas, transactions et paiements Mobile Money.",
    version="1.0.0",
)

# En production, remplace "*" par le(s) domaine(s) exact(s) de ton app / site.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(payments.router)
app.include_router(plan.router)


@app.get("/")
def racine():
    return {"app": "Mon Budget 80/20", "statut": "en ligne"}

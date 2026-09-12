# Mon Budget 80/20 — V1

## Architecture

```
                        ┌─────────────────────────┐
                        │      APP FLET (app/)      │
                        │  Interface utilisateur     │
                        │  - Sidebar + onglets        │
                        │  - Graphiques (flet_charts) │
                        │  - Formulaires              │
                        └───────────┬─────────────┘
                                    │ HTTP (requests)
                                    │ Authorization: Bearer <JWT>
                                    ▼
                        ┌─────────────────────────┐
                        │   BACKEND FASTAPI (backend/)│
                        │  - Auth (JWT, mots de passe  │
                        │    hashes)                    │
                        │  - Quotas reels (par date)     │
                        │  - Calcul 80/20 + historique    │
                        │  - Coaching contextuel           │
                        │  - Paiements Notch Pay             │
                        └───────────┬───────────────────┘
                                    │
                    ┌───────────────┼──────────────────┐
                    ▼                                   ▼
          ┌──────────────────┐              ┌────────────────────┐
          │  BASE DE DONNEES   │              │   NOTCH PAY (API)    │
          │  SQLite (dev) ->    │              │  Mobile Money         │
          │  PostgreSQL (prod)   │              │  Orange Money / MoMo   │
          └──────────────────┘              └────────────────────┘
```

Principe central : l'app Flet ne stocke **jamais** la clé Notch Pay ni de
booléen "is_premium" local. Elle appelle systématiquement le backend, qui est
la seule source de vérité pour le statut PRO, les quotas et les données
financières de chaque utilisateur.

## Structure des fichiers

```
mon_budget_8020/
├── backend/                     # API FastAPI
│   ├── main.py                  # Point d'entree, montage des routers
│   ├── database.py              # Config SQLAlchemy (SQLite par defaut)
│   ├── models.py                # Tables : User, Abonnement, Transaction, Tontine
│   ├── schemas.py                # Validation Pydantic des requetes/reponses
│   ├── security.py               # Hash mot de passe (pbkdf2) + JWT
│   ├── deps.py                    # Dependance get_current_user + calcul statut PRO
│   ├── coaching.py                 # Generation des conseils contextuels
│   ├── routers/
│   │   ├── auth.py                 # Inscription / connexion / parrainage
│   │   ├── transactions.py         # Transactions, resume 80/20, tontines/dettes, simulation
│   │   └── payments.py             # Initiation paiement Notch Pay + webhook signe
│   └── requirements.txt
│
├── app/                          # Application Flet
│   ├── main.py                    # Point d'entree, bascule connexion/dashboard
│   ├── state.py                   # Etat de session (1 instance par utilisateur connecte)
│   ├── services/
│   │   └── api_client.py          # Tous les appels HTTP vers le backend
│   ├── components/
│   │   ├── sidebar.py              # Navigation laterale + anneau 80/20
│   │   ├── kpis.py                 # Cartes KPI avec variation vs mois precedent
│   │   ├── charts.py               # Graphiques (camembert, barres, courbes)
│   │   └── pro_guard.py             # Verrouillage PRO + modal d'achat
│   └── views/
│       ├── auth_view.py             # Connexion / inscription
│       └── dashboard.py             # Vue principale (sidebar + onglets + graphiques)
│
└── requirements-app.txt
```

## Lancer en local

**1. Backend** (terminal 1) :
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**2. App Flet** (terminal 2) :
```bash
pip install -r requirements-app.txt
cd app
python main.py
```
Ouvre ensuite `http://127.0.0.1:8550` dans ton navigateur.

## Déployer sur Render (2 services séparés)

**Service 1 — Backend (Web Service Python)**
- Root Directory : `backend`
- Build Command : `pip install -r requirements.txt`
- Start Command : `uvicorn main:app --host 0.0.0.0 --port $PORT`
  (sans `--host 0.0.0.0`, Render ne peut jamais atteindre le service de l'extérieur)
- Variables d'environnement : `DATABASE_URL`, `JWT_SECRET_KEY`, `NOTCHPAY_PRIVATE_KEY`, `NOTCHPAY_WEBHOOK_SECRET`
- Note le lien public généré, ex : `https://mon-budget-8020-backend.onrender.com`

**Service 2 — App Flet (Web Service Python)**
- Root Directory : `app`
- Build Command : `pip install -r ../requirements-app.txt`
- Start Command : `python main.py`
- Variable d'environnement **obligatoire** : `BACKEND_URL` = l'URL du service 1 ci-dessus
  (sans ça, l'app essaiera de contacter `127.0.0.1`, qui ne pointe jamais vers le backend une fois déployé)

⚠️ Sur le plan gratuit de Render, un service inactif pendant ~15 minutes se
met en veille et met 30 à 60 secondes à redémarrer au prochain accès -- la
toute première requête peut donc sembler en erreur ou très lente. Si le
problème persiste au-delà de ce délai de réveil, vérifie les logs du service
concerné dans le dashboard Render.

## Variables d'environnement à définir en production

- `DATABASE_URL` (ex: `postgresql://user:pass@host/db`)
- `JWT_SECRET_KEY` (générer avec `python -c "import secrets; print(secrets.token_hex(32))"`)
- `NOTCHPAY_PRIVATE_KEY`
- `NOTCHPAY_WEBHOOK_SECRET`

Et définir la variable d'environnement `BACKEND_URL` (voir section Render
ci-dessus) sur l'URL publique du backend déployé avant de compiler l'APK.

## Ce qui manque encore avant une mise en production réelle

- Déploiement du backend (Render/Railway/Fly.io) + base PostgreSQL
- Clés Notch Pay réelles (sandbox puis production)
- Génération de rapport PDF
- Tests avec de vrais utilisateurs avant d'investir dans l'APK (voir la
  discussion sur la validation du marché)

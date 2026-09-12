"""
Client HTTP vers le backend Mon Budget 80/20.
L'app Flet ne stocke JAMAIS de clé de paiement ni de logique de statut PRO :
elle demande toujours au serveur, qui est la seule source de vérité.
"""
import os
import requests

# En local : http://127.0.0.1:8000 par defaut.
# En production (Render) : definir la variable d'environnement BACKEND_URL
# sur l'URL publique du service backend, ex:
#   BACKEND_URL=https://mon-budget-8020-backend.onrender.com
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    def __init__(self):
        self.token: str | None = None

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _traiter_reponse(self, reponse: requests.Response):
        if reponse.status_code >= 400:
            try:
                detail = reponse.json().get("detail", "Erreur inconnue.")
            except Exception:
                detail = reponse.text or "Erreur inconnue."
            raise ApiError(detail, reponse.status_code)
        if reponse.content:
            return reponse.json()
        return None

    # ---------- Auth ----------

    def inscription(self, nom: str, email: str, mot_de_passe: str,
                     revenu_mensuel: float = 0, code_parrain: str = "") -> dict:
        r = requests.post(f"{BACKEND_URL}/auth/inscription", json={
            "nom": nom, "email": email, "mot_de_passe": mot_de_passe,
            "revenu_mensuel_declare": revenu_mensuel,
            "code_parrain": code_parrain or None,
        }, timeout=10)
        return self._traiter_reponse(r)

    def login(self, identifiant: str, mot_de_passe: str) -> dict:
        r = requests.post(f"{BACKEND_URL}/auth/login", json={
            "identifiant": identifiant, "mot_de_passe": mot_de_passe,
        }, timeout=10)
        data = self._traiter_reponse(r)
        self.token = data["access_token"]
        return data

    def mon_profil(self) -> dict:
        r = requests.get(f"{BACKEND_URL}/auth/moi", headers=self._headers(), timeout=10)
        return self._traiter_reponse(r)

    def statut_pro(self) -> dict:
        r = requests.get(f"{BACKEND_URL}/auth/statut-pro", headers=self._headers(), timeout=10)
        return self._traiter_reponse(r)

    # ---------- Transactions ----------

    def quota(self) -> dict:
        r = requests.get(f"{BACKEND_URL}/transactions/quota", headers=self._headers(), timeout=10)
        return self._traiter_reponse(r)

    def ajouter_transaction(self, type_: str, montant: float, categorie: str,
                             est_fixe: bool = True, source: str = "MANUEL", description: str = "") -> dict:
        r = requests.post(f"{BACKEND_URL}/transactions/", headers=self._headers(), json={
            "type": type_, "montant": montant, "categorie": categorie, "est_fixe": est_fixe,
            "source": source, "description": description or None,
        }, timeout=10)
        return self._traiter_reponse(r)

    def lister_transactions(self) -> list:
        r = requests.get(f"{BACKEND_URL}/transactions/", headers=self._headers(), timeout=10)
        return self._traiter_reponse(r)

    def resume_8020(self) -> dict:
        r = requests.get(f"{BACKEND_URL}/transactions/resume", headers=self._headers(), timeout=10)
        return self._traiter_reponse(r)

    # ---------- Tontines ----------

    def lister_tontines(self) -> list:
        r = requests.get(f"{BACKEND_URL}/transactions/tontines", headers=self._headers(), timeout=10)
        return self._traiter_reponse(r)

    def ajouter_tontine(self, nom: str, montant_cotisation: float,
                         frequence: str = "Mensuelle", est_dette: bool = False) -> dict:
        r = requests.post(f"{BACKEND_URL}/transactions/tontines", headers=self._headers(), json={
            "nom": nom, "montant_cotisation": montant_cotisation,
            "frequence": frequence, "est_dette": est_dette,
        }, timeout=10)
        return self._traiter_reponse(r)

    def rembourser_dette(self, tontine_id: int, montant: float) -> dict:
        r = requests.post(f"{BACKEND_URL}/transactions/tontines/{tontine_id}/rembourser",
                           headers=self._headers(), json={"montant": montant}, timeout=10)
        return self._traiter_reponse(r)

    # ---------- Simulation de projet ----------

    def simuler_projet(self, nom_projet: str, montant_cible: float,
                        reduction_depenses_pourcentage: float = 0) -> dict:
        r = requests.post(f"{BACKEND_URL}/transactions/simulation", headers=self._headers(), json={
            "nom_projet": nom_projet, "montant_cible": montant_cible,
            "reduction_depenses_pourcentage": reduction_depenses_pourcentage,
        }, timeout=10)
        return self._traiter_reponse(r)

    # ---------- Paiements ----------

    def initier_paiement(self, plan: str) -> dict:
        r = requests.post(f"{BACKEND_URL}/paiements/initier", headers=self._headers(),
                           json={"plan": plan}, timeout=15)
        return self._traiter_reponse(r)

    # ---------- Plan mensuel ----------

    def obtenir_plan(self, mois: str) -> dict:
        r = requests.get(f"{BACKEND_URL}/plan", headers=self._headers(), params={"mois": mois}, timeout=10)
        return self._traiter_reponse(r)

    def enregistrer_plan(self, mois: str, revenus_prevus: list, obligations: list) -> dict:
        r = requests.post(f"{BACKEND_URL}/plan", headers=self._headers(), json={
            "mois": mois, "revenus_prevus": revenus_prevus, "obligations": obligations,
        }, timeout=10)
        return self._traiter_reponse(r)

    def simuler_plan(self, mois: str, delta_revenu: float = 0,
                      nouvelle_obligation: float = 0, epargne_cible: float | None = None) -> dict:
        r = requests.post(f"{BACKEND_URL}/plan/simulation", headers=self._headers(),
                           params={"mois": mois}, json={
                               "delta_revenu": delta_revenu,
                               "nouvelle_obligation": nouvelle_obligation,
                               "epargne_cible": epargne_cible,
                           }, timeout=10)
        return self._traiter_reponse(r)

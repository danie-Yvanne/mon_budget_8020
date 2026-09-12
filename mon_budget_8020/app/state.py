"""
État de session Flet.

Contrairement au prototype initial (un seul dict `user_state` global partagé
par tout le monde), CHAQUE client Flet obtient sa PROPRE instance de
AppState : Flet appelle main(page) une fois par session/onglet ouvert, donc
créer cet objet à l'intérieur de main() isole déjà les utilisateurs entre eux
en mémoire. La vérité définitive (statut PRO, quotas, données financières)
reste toutefois toujours côté serveur, interrogée via ApiClient.
"""
from services.api_client import ApiClient


class AppState:
    def __init__(self):
        self.api = ApiClient()
        self.utilisateur: dict | None = None
        self.statut_pro_cache: dict | None = None

    @property
    def est_connecte(self) -> bool:
        return self.api.token is not None and self.utilisateur is not None

    @property
    def est_pro(self) -> bool:
        return bool(self.statut_pro_cache and self.statut_pro_cache.get("is_pro"))

    def rafraichir_statut_pro(self):
        self.statut_pro_cache = self.api.statut_pro()

    def deconnexion(self):
        self.api.token = None
        self.utilisateur = None
        self.statut_pro_cache = None

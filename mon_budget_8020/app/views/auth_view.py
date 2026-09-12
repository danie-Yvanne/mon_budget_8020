import flet as ft
from state import AppState
from services.api_client import ApiError


class AuthView:
    """Vue de connexion / inscription. Appelle on_connecte() une fois l'utilisateur authentifié."""

    def __init__(self, page: ft.Page, state: AppState, on_connecte):
        self.page = page
        self.state = state
        self.on_connecte = on_connecte
        self.mode_inscription = False

        self.champ_nom = ft.TextField(label="Nom complet", width=300)
        self.champ_email = ft.TextField(label="Email", width=300)
        self.champ_mdp = ft.TextField(label="Mot de passe", password=True, can_reveal_password=True, width=300)
        self.champ_code_parrain = ft.TextField(label="Code de parrainage (optionnel)", width=300)
        self.zone_erreur = ft.Text(color=ft.Colors.RED_700, size=12)
        self.titre = ft.Text("Connexion", size=20, weight=ft.FontWeight.BOLD, color="#292524")
        self.bouton_principal = ft.ElevatedButton("Se connecter", bgcolor="#F97316", color=ft.Colors.WHITE,
                                                   width=300, on_click=self.valider)
        self.lien_bascule = ft.TextButton("Pas de compte ? Inscris-toi", on_click=self.basculer_mode)
        self.container = ft.Container(alignment=ft.Alignment.CENTER, expand=True)

    def basculer_mode(self, e):
        self.mode_inscription = not self.mode_inscription
        self._appliquer_mode()
        self.container.content = self._colonne()
        self.page.update()

    def _appliquer_mode(self):
        if self.mode_inscription:
            self.titre.value = "Créer un compte"
            self.bouton_principal.text = "S'inscrire"
            self.lien_bascule.text = "Déjà un compte ? Connecte-toi"
        else:
            self.titre.value = "Connexion"
            self.bouton_principal.text = "Se connecter"
            self.lien_bascule.text = "Pas de compte ? Inscris-toi"

    def valider(self, e):
        self.zone_erreur.value = ""
        try:
            if self.mode_inscription:
                if not self.champ_nom.value or not self.champ_email.value or not self.champ_mdp.value:
                    raise ApiError("Nom, email et mot de passe sont requis.")
                self.state.api.inscription(
                    nom=self.champ_nom.value, email=self.champ_email.value,
                    mot_de_passe=self.champ_mdp.value,
                    code_parrain=self.champ_code_parrain.value,
                )
                self.state.api.login(self.champ_email.value, self.champ_mdp.value)
            else:
                self.state.api.login(self.champ_email.value, self.champ_mdp.value)

            self.state.utilisateur = self.state.api.mon_profil()
            self.state.rafraichir_statut_pro()
            self.on_connecte()
        except ApiError as err:
            self.zone_erreur.value = str(err)
            self.page.update()

    def _colonne(self) -> ft.Column:
        champs = [self.champ_nom, self.champ_email, self.champ_mdp] if self.mode_inscription else [self.champ_email, self.champ_mdp]
        if self.mode_inscription:
            champs.append(self.champ_code_parrain)
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
            controls=[
                ft.Text("Mon Budget 80/20", size=24, weight=ft.FontWeight.BOLD, color="#292524"),
                self.titre,
                *champs,
                self.zone_erreur,
                self.bouton_principal,
                self.lien_bascule,
            ],
        )

    def build(self) -> ft.Container:
        self._appliquer_mode()
        self.container.content = self._colonne()
        return self.container

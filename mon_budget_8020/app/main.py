import os
import flet as ft

import theme
from state import AppState
from views.auth_view import AuthView
from views.dashboard import DashboardView


def main(page: ft.Page):
    # Flet appelle main(page) UNE FOIS PAR SESSION CLIENT : creer AppState ici
    # (et non au niveau module) garantit que chaque utilisateur a son propre
    # etat en memoire, sans jamais melanger les donnees de deux personnes.
    page.title = "Mon Budget 80/20"
    page.bgcolor = theme.BG_APP
    page.padding = 0
    page.fonts = theme.FONT_URLS
    page.theme = ft.Theme(font_family=theme.FONT_FAMILY)

    state = AppState()
    contenu = ft.Container(expand=True)
    page.add(contenu)

    def afficher_dashboard():
        def deconnexion():
            state.deconnexion()
            afficher_connexion()

        dashboard = DashboardView(page, state, on_deconnexion=deconnexion)
        contenu.padding = 20
        contenu.content = dashboard.build()
        page.update()

    def afficher_connexion():
        contenu.padding = 0
        auth = AuthView(page, state, on_connecte=afficher_dashboard)
        contenu.content = auth.build()
        page.update()

    afficher_connexion()


if __name__ == "__main__":
    # view=WEB_BROWSER + host/port explicites : indispensable pour tourner
    # comme un service web sur Render (sinon Flet essaie d'ouvrir une
    # fenetre desktop, impossible sur un serveur -> le processus plante).
    # Render impose toujours la variable d'environnement PORT -> on s'en sert
    # pour savoir si on est en prod (Render) ou en local :
    #   - en local : 127.0.0.1, sinon le navigateur ne sait pas ouvrir "0.0.0.0"
    #   - sur Render : 0.0.0.0, indispensable pour etre joignable depuis l'exterieur
    port_render = os.environ.get("PORT")
    if port_render:
        host, port = "0.0.0.0", int(port_render)
    else:
        host, port = "127.0.0.1", 8550

    ft.run(
        main,
        view=ft.AppView.WEB_BROWSER,
        host=host,
        port=port,
    )

import flet as ft

# (label affiché, icône, section réelle correspondante dans DashboardView)
# "Plan" n'apparaît pas ici : sur mobile on privilégie 4 icônes maximum
# (recommandation UX), Plan reste accessible via un lien depuis l'Accueil.
DESTINATIONS = [
    ("Accueil", ft.Icons.HOME_ROUNDED, "Accueil"),
    ("Dépenses", ft.Icons.SHOPPING_CART_ROUNDED, "Activité"),
    ("Tontines", ft.Icons.GROUP_ROUNDED, "Objectifs"),
    ("Profil", ft.Icons.PERSON_ROUNDED, "Profil"),
]

COULEUR_FOND = "#FFFFFF"
COULEUR_ACCENT = "#F97316"


def _index_pour_section(section: str) -> int:
    for i, (_, _, cle) in enumerate(DESTINATIONS):
        if cle == section:
            return i
    return 0


def BottomNavBar(section_active: str, on_navigate) -> ft.NavigationBar:
    def _changement(e):
        _, _, cle = DESTINATIONS[e.control.selected_index]
        on_navigate(cle)

    return ft.NavigationBar(
        selected_index=_index_pour_section(section_active),
        bgcolor=COULEUR_FOND,
        indicator_color=COULEUR_ACCENT,
        destinations=[
            ft.NavigationBarDestination(icon=icon, label=label)
            for label, icon, _ in DESTINATIONS
        ],
        on_change=_changement,
    )

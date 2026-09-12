import flet as ft

# Palette inspiree de l'image de reference "Finvora" (orange/corail chaud)
COULEUR_FOND_SIDEBAR = "#FFFFFF"
COULEUR_ACCENT = "#F97316"
COULEUR_ACCENT_FONCE = "#EA580C"
COULEUR_TEXTE = "#292524"
COULEUR_TEXTE_MUET = "#78716C"
COULEUR_TEINTE_CLAIRE = "#FFF1E6"
COULEUR_PISTE_ANNEAU = "#FFE4C7"

ITEMS_MENU = [
    ("Accueil", ft.Icons.HOME_ROUNDED),
    ("Plan", ft.Icons.EXPLORE_ROUNDED),
    ("Activité", ft.Icons.CREDIT_CARD_ROUNDED),
    ("Objectifs", ft.Icons.TRACK_CHANGES_ROUNDED),
    ("Profil", ft.Icons.PERSON_ROUNDED),
]


def _item_menu(label: str, icon, actif: bool, on_click) -> ft.Container:
    # Style "pastille pleine largeur" inspiré de la maquette de référence :
    # l'item actif est un bloc plein coloré, pas juste un soulignement.
    return ft.Container(
        on_click=on_click,
        bgcolor=COULEUR_ACCENT if actif else None,
        border_radius=10,
        padding=ft.Padding(14, 11, 14, 11),
        content=ft.Row(spacing=10, controls=[
            ft.Icon(icon, color=ft.Colors.WHITE if actif else COULEUR_TEXTE_MUET, size=18),
            ft.Text(label, color=ft.Colors.WHITE if actif else COULEUR_TEXTE_MUET,
                    weight=ft.FontWeight.BOLD if actif else ft.FontWeight.W_500, size=13),
        ]),
    )


def EpargneRing(pourcentage: float) -> ft.Container:
    """Anneau de progression 'objectif d'épargne atteint ce mois'."""
    pourcentage = max(0, min(pourcentage, 100))
    return ft.Container(
        bgcolor=COULEUR_TEINTE_CLAIRE, border_radius=14, padding=16, margin=ft.Margin(0, 16, 0, 0),
        content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6, controls=[
            ft.Text("Règle 80/20", color=COULEUR_TEXTE, weight=ft.FontWeight.BOLD, size=13),
            ft.Text("20% pour épargner, 80% pour dépenser", color=COULEUR_TEXTE_MUET, size=10, text_align=ft.TextAlign.CENTER),
            ft.Container(
                height=100, width=100, margin=ft.Margin(0, 8, 0, 8),
                content=ft.Stack(controls=[
                    ft.Container(
                        height=100, width=100, alignment=ft.Alignment.CENTER,
                        content=ft.ProgressRing(value=pourcentage / 100, color=COULEUR_ACCENT,
                                                 bgcolor=COULEUR_PISTE_ANNEAU, stroke_width=8, width=100, height=100),
                    ),
                    ft.Container(
                        height=100, width=100, alignment=ft.Alignment.CENTER,
                        content=ft.Text(f"{pourcentage:.0f}%", color=COULEUR_TEXTE,
                                        weight=ft.FontWeight.BOLD, size=20),
                    ),
                ]),
            ),
            ft.Text("Objectif d'épargne atteint ce mois", color=COULEUR_TEXTE_MUET, size=10, text_align=ft.TextAlign.CENTER),
        ]),
    )


class Sidebar:
    def __init__(self, on_navigate):
        self.on_navigate = on_navigate
        self.selection = "Accueil"
        self.zone_menu = ft.Column(spacing=4)
        self.zone_ring = ft.Container()

    def selectionner(self, label: str):
        self.selection = label
        self._reconstruire_menu()
        self.on_navigate(label)

    def _reconstruire_menu(self):
        self.zone_menu.controls = [
            _item_menu(label, icon, self.selection == label,
                       on_click=lambda e, l=label: self.selectionner(l))
            for label, icon in ITEMS_MENU
        ]

    def build(self, pourcentage_epargne: float = 0) -> ft.Container:
        self._reconstruire_menu()
        self.zone_ring.content = EpargneRing(pourcentage_epargne).content
        self.zone_ring.bgcolor = COULEUR_TEINTE_CLAIRE
        self.zone_ring.border_radius = 14
        self.zone_ring.padding = 16
        self.zone_ring.margin = ft.Margin(0, 16, 0, 0)

        return ft.Container(
            width=230, bgcolor=COULEUR_FOND_SIDEBAR, padding=18,
            border=ft.Border(right=ft.BorderSide(1, "#F0E4D8")),
            content=ft.Column(controls=[
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, color=COULEUR_ACCENT, size=26),
                    ft.Text("Mon Budget\n80/20", color=COULEUR_TEXTE, weight=ft.FontWeight.BOLD, size=15),
                ]),
                ft.Container(height=20),
                self.zone_menu,
                ft.Container(expand=True),
                self.zone_ring,
            ]),
        )

import flet as ft
from state import AppState
from services.api_client import ApiError

# Doit rester synchronisé avec backend/schemas.py -> PRIX_PASS_FCFA
PLANS_PRO = [
    ("1_MOIS", "Pass 1 mois", 2000),
    ("3_MOIS", "Pass 3 mois (recommandé)", 5000),
]


def _afficher_snack(page: ft.Page, message: str):
    snack = ft.SnackBar(content=ft.Text(message), open=True)
    page.overlay.append(snack)
    page.update()


def acheter_pass(page: ft.Page, state: AppState, plan: str):
    try:
        resultat = state.api.initier_paiement(plan)
        page.launch_url(resultat["authorization_url"])
    except ApiError as e:
        _afficher_snack(page, f"Paiement impossible : {e}")


def show_pro_modal(page: ft.Page, state: AppState, feature_name: str):
    boutons_plans = [
        ft.ElevatedButton(
            f"{nom} — {prix:,} FCFA".replace(",", " "),
            bgcolor="#F97316", color=ft.Colors.WHITE,
            on_click=lambda e, p=code: (page.pop_dialog(), acheter_pass(page, state, p)),
        )
        for code, nom, prix in PLANS_PRO
    ]

    dlg = ft.AlertDialog(
        title=ft.Text("🔒 Fonctionnalité Pass PRO", weight=ft.FontWeight.BOLD),
        content=ft.Column(
            tight=True, spacing=10,
            controls=[
                ft.Text(f"L'accès à « {feature_name} » nécessite un Pass PRO, "
                        "ou peut être débloqué via le parrainage."),
                *boutons_plans,
            ],
        ),
        actions=[ft.TextButton("Fermer", on_click=lambda e: page.pop_dialog())],
    )
    page.show_dialog(dlg)


def ProGuard(page: ft.Page, state: AppState, title: str, content_widget: ft.Control) -> ft.Container:
    if state.est_pro:
        return ft.Container(
            bgcolor=ft.Colors.WHITE, padding=15, border_radius=12,
            content=ft.Column(controls=[
                ft.Text(title, weight=ft.FontWeight.BOLD, color="#292524"),
                content_widget,
            ]),
        )
    return ft.Container(
        bgcolor=ft.Colors.WHITE, padding=15, border_radius=12,
        content=ft.Stack(controls=[
            ft.Column(controls=[
                ft.Text(title, weight=ft.FontWeight.BOLD, color="#292524"),
                ft.Container(
                    height=120, bgcolor=ft.Colors.GREY_100, border_radius=8,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.BAR_CHART, color=ft.Colors.GREY_400, size=40),
                ),
            ]),
            ft.Container(
                bgcolor=ft.Colors.with_opacity(0.9, ft.Colors.WHITE),
                border_radius=12, padding=10, alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.LOCK_ROUNDED, color="#F97316", size=24),
                        ft.Text("Débloquer avec le Pass PRO", size=11,
                                weight=ft.FontWeight.BOLD, color="#292524"),
                        ft.ElevatedButton(
                            "Débloquer", bgcolor="#F97316", color=ft.Colors.WHITE, height=28,
                            on_click=lambda e: show_pro_modal(page, state, title),
                        ),
                    ],
                ),
            ),
        ]),
    )

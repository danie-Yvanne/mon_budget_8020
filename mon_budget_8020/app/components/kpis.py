import flet as ft


def KpiCard(title: str, amount: str, color: str, icon, variation: float | None = None) -> ft.Container:
    controls = [
        ft.Row(controls=[
            ft.Icon(icon, color=color, size=18),
            ft.Text(title, size=10, color="#8FB0A8", weight=ft.FontWeight.BOLD),
        ]),
        ft.Text(amount, size=15, weight=ft.FontWeight.BOLD, color="#0F3D3A"),
    ]
    if variation is not None:
        hausse = variation >= 0
        controls.append(ft.Row(spacing=2, controls=[
            ft.Icon(ft.Icons.ARROW_UPWARD if hausse else ft.Icons.ARROW_DOWNWARD,
                    size=11, color="#22C55E" if hausse else "#EF4444"),
            ft.Text(f"{abs(variation):.0f}% vs mois dernier", size=9,
                    color="#22C55E" if hausse else "#EF4444"),
        ]))
    return ft.Container(
        col={"xs": 12, "sm": 6, "md": 4, "lg": 2.4},
        bgcolor=ft.Colors.WHITE,
        padding=12,
        border_radius=10,
        content=ft.Column(controls=controls, spacing=4),
    )


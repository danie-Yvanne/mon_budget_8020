"""
Graphiques réutilisables pour le dashboard, basés sur le package flet_charts
(BarChart, PieChart, LineChart utilisent l'API du moteur de rendu Flutter fl_chart).
"""
import flet as ft
from flet_charts import (
    BarChart, BarChartGroup, BarChartRod,
    PieChart, PieChartSection,
    LineChart, LineChartData, LineChartDataPoint,
    ChartAxis, ChartAxisLabel,
)
from flet_charts.types import ChartGridLines

PALETTE = ["#F97316", "#FB923C", "#FDBA74", "#A855F7", "#22C55E", "#38BDF8", "#EAB308"]


def GraphiqueBarres(labels: list[str], valeurs: list[float], couleurs: list[str] | None = None,
                     height: float = 220) -> ft.Container:
    """Barres verticales simples (ex: Revenu fixe vs variable, Situation globale)."""
    if not couleurs:
        couleurs = PALETTE[: len(labels)]
    max_val = max(valeurs) if valeurs and max(valeurs) > 0 else 1

    groupes = [
        BarChartGroup(x=i, rods=[
            BarChartRod(to_y=v, color=couleurs[i % len(couleurs)], width=28,
                        border_radius=ft.BorderRadius(6, 6, 0, 0))
        ])
        for i, v in enumerate(valeurs)
    ]
    return ft.Container(
        height=height,
        content=BarChart(
            groups=groupes,
            max_y=max_val * 1.25,
            interactive=True,
            bottom_axis=ChartAxis(
                labels=[ChartAxisLabel(value=i, label=ft.Text(lbl, size=10, color="#78716C"))
                        for i, lbl in enumerate(labels)],
                label_size=28,
            ),
            left_axis=ChartAxis(label_size=40),
            horizontal_grid_lines=ChartGridLines(),
        ),
    )


def GraphiqueCamembert(repartition: list[dict], height: float = 220) -> ft.Row:
    """
    Camembert + légende, à partir d'une liste [{categorie, montant, pourcentage}]
    telle que retournée par /transactions/resume.
    """
    if not repartition:
        return ft.Row(controls=[ft.Text("Pas encore de données ce mois-ci.", size=12, color="#78716C")])

    sections = [
        PieChartSection(
            value=item["montant"],
            color=PALETTE[i % len(PALETTE)],
            radius=55,
            title=f"{item['pourcentage']:.0f}%" if item["pourcentage"] >= 6 else "",
            title_style=ft.TextStyle(size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        )
        for i, item in enumerate(repartition)
    ]
    legende = ft.Column(spacing=6, controls=[
        ft.Row(spacing=6, controls=[
            ft.Container(width=10, height=10, bgcolor=PALETTE[i % len(PALETTE)], border_radius=3),
            ft.Column(spacing=0, controls=[
                ft.Text(item["categorie"], size=11, weight=ft.FontWeight.BOLD, color="#292524"),
                ft.Text(f"{item['montant']:,.0f} FCFA".replace(",", " "), size=10, color="#78716C"),
            ]),
        ])
        for i, item in enumerate(repartition)
    ])
    return ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=height, height=height,
                content=PieChart(sections=sections, center_space_radius=30, sections_space=2),
            ),
            ft.Container(width=16),
            ft.Container(expand=True, content=legende),
        ],
    )


def GraphiqueEvolution(mois_labels: list[str], series: list[tuple[str, list[float], str]],
                        height: float = 220) -> ft.Column:
    """
    Courbe(s) d'évolution mensuelle.
    `series` : liste de (nom_serie, valeurs, couleur_hex).
    """
    data_series = [
        LineChartData(
            points=[LineChartDataPoint(x=i, y=v) for i, v in enumerate(valeurs)],
            color=couleur, stroke_width=3, curved=True,
        )
        for _, valeurs, couleur in series
    ]
    toutes_valeurs = [v for _, valeurs, _ in series for v in valeurs] or [0]

    graphique = ft.Container(
        height=height,
        content=LineChart(
            data_series=data_series,
            min_y=0, max_y=max(toutes_valeurs) * 1.2 if max(toutes_valeurs) > 0 else 10,
            bottom_axis=ChartAxis(
                labels=[ChartAxisLabel(value=i, label=ft.Text(lbl, size=10, color="#78716C"))
                        for i, lbl in enumerate(mois_labels)],
                label_size=28,
            ),
            left_axis=ChartAxis(label_size=45),
            horizontal_grid_lines=ChartGridLines(),
        ),
    )
    legende = ft.Row(spacing=14, controls=[
        ft.Row(spacing=4, controls=[
            ft.Container(width=10, height=3, bgcolor=couleur),
            ft.Text(nom, size=10, color="#78716C"),
        ])
        for nom, _, couleur in series
    ])
    return ft.Column(controls=[legende, graphique], spacing=6)

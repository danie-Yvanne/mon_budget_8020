import re
import datetime
import flet as ft

from state import AppState
from services.api_client import ApiError
from components.pro_guard import ProGuard, show_pro_modal, PLANS_PRO, acheter_pass
from components.sidebar import Sidebar
from components.bottom_nav import BottomNavBar
from components.charts import GraphiqueBarres, GraphiqueCamembert, GraphiqueEvolution

SEUIL_MOBILE = 820  # en dessous de cette largeur (px) : sidebar -> barre de navigation en bas

CATEGORIES_REVENU = ["Salaire", "Business", "Freelance", "Aide/Don", "Autres"]
CATEGORIES_DEPENSE = ["Loyer", "Transport", "Nourriture", "Sante", "Loisirs",
                      "Tontine", "Scolarite", "Autre"]


def _fcfa(montant: float) -> str:
    return f"{montant:,.0f} FCFA".replace(",", " ")


def _snack(page: ft.Page, message: str, erreur: bool = False):
    snack = ft.SnackBar(content=ft.Text(message), bgcolor="#FDEAEA" if erreur else None, open=True)
    page.overlay.append(snack)
    page.update()


def _carte(content, bgcolor="#FFF7ED", padding=16) -> ft.Container:
    return ft.Container(bgcolor=bgcolor, border_radius=12, padding=padding, content=content)


class DashboardView:
    """
    Navigation en 5 sections dans la sidebar : Accueil / Plan / Activité /
    Objectifs / Profil -- pas un logiciel comptable, un copilote financier.
    """

    def __init__(self, page: ft.Page, state: AppState, on_deconnexion):
        self.page = page
        self.state = state
        self.on_deconnexion = on_deconnexion
        self.sidebar = Sidebar(on_navigate=self._on_navigate)

        self.resume: dict = {}
        self.tontines: list = []
        self.transactions: list = []
        self.plan: dict = {}
        self.mois_courant = datetime.date.today().strftime("%Y-%m")
        self.filtre_activite = "Tout"

        self.zone_contenu = ft.Container(expand=True)
        self.zone_layout = ft.Container(expand=True)
        self.es_mobile = False

        self._lignes_revenus_plan: list[tuple[ft.TextField, ft.TextField]] = []
        self._lignes_obligations_plan: list[tuple[ft.TextField, ft.TextField]] = []
        self.zone_lignes_revenus = ft.Column(spacing=6)
        self.zone_lignes_obligations = ft.Column(spacing=6)
        self.zone_resultat_plan = ft.Container()
        self.zone_simulation_plan = ft.Container()

        self._construire_dialog_ajout()
        self.rafraichir_donnees()

    # ---------- Navigation ----------

    def _on_navigate(self, label: str):
        self.sidebar.selection = label
        self._rendre_layout()
        self.page.update()

    # ---------- Chargement des données ----------

    def rafraichir_donnees(self):
        try:
            self.state.rafraichir_statut_pro()
            self.resume = self.state.api.resume_8020()
            self.tontines = self.state.api.lister_tontines()
            self.transactions = self.state.api.lister_transactions()
            self.plan = self.state.api.obtenir_plan(self.mois_courant)
        except ApiError as e:
            _snack(self.page, f"Erreur de synchronisation : {e}", erreur=True)
            return
        self._charger_lignes_plan()
        self._rendre_section()

    def _charger_lignes_plan(self):
        self._lignes_revenus_plan = [
            (ft.TextField(label="Catégorie", value=l["categorie"], width=180),
             ft.TextField(label="Montant", value=str(int(l["montant"])), width=140, keyboard_type=ft.KeyboardType.NUMBER))
            for l in self.plan.get("revenus_prevus", [])
        ] or [self._nouvelle_ligne_vide()]
        self._lignes_obligations_plan = [
            (ft.TextField(label="Catégorie", value=l["categorie"], width=180),
             ft.TextField(label="Montant", value=str(int(l["montant"])), width=140, keyboard_type=ft.KeyboardType.NUMBER))
            for l in self.plan.get("obligations", [])
        ] or [self._nouvelle_ligne_vide()]

    @staticmethod
    def _nouvelle_ligne_vide():
        return (ft.TextField(label="Catégorie", width=180), ft.TextField(label="Montant", width=140, keyboard_type=ft.KeyboardType.NUMBER))

    # ---------- Rendu général ----------

    def _rendre_section(self):
        section = self.sidebar.selection
        if section == "Plan":
            contenu = self._section_plan()
        elif section == "Activité":
            contenu = self._section_activite()
        elif section == "Objectifs":
            contenu = self._section_objectifs()
        elif section == "Profil":
            contenu = self._section_profil()
        else:
            contenu = self._section_accueil()

        entete = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
            ft.Column(spacing=0, controls=[
                ft.Text(f"Bonjour {self._prenom()} 👋", size=20, weight=ft.FontWeight.BOLD, color="#292524"),
                ft.Text(self._sous_titre(section), size=12, color="#78716C"),
            ]),
            ft.Row(controls=[
                ft.ElevatedButton("Ajouter", icon=ft.Icons.ADD, bgcolor="#F97316",
                                  color=ft.Colors.WHITE, on_click=self.ouvrir_dialog_ajout),
                ft.IconButton(icon=ft.Icons.NOTIFICATIONS_NONE_ROUNDED),
            ]),
        ])

        self.zone_contenu.content = ft.Column(
            expand=True, scroll=ft.ScrollMode.AUTO, spacing=16,
            controls=[entete, contenu],
        )

    def _prenom(self) -> str:
        return self.state.utilisateur.get("nom", "").split(" ")[0] if self.state.utilisateur else ""

    def _sous_titre(self, section: str) -> str:
        return {
            "Accueil": "Voici où tu en es ce mois-ci",
            "Plan": "Voici ce que tu peux faire",
            "Activité": "Voici ce qui s'est passé",
            "Objectifs": "Voici ce que tu construis",
            "Profil": "Voici tes réglages",
        }.get(section, "")

    def _panneau_conseil(self, titre="Ce que tu dois savoir", icon=ft.Icons.LIGHTBULB_ROUNDED) -> ft.Container:
        conseils = self.resume.get("conseils", [])
        message = conseils[0] if conseils else "Continue à saisir tes transactions pour affiner tes conseils."
        return _carte(bgcolor="#FFF1E6", content=ft.Column(spacing=8, controls=[
            ft.Row(controls=[ft.Icon(icon, color="#16A34A"), ft.Text(titre, weight=ft.FontWeight.BOLD, color="#292524")]),
            ft.Text(message, size=12, color="#1F4A44"),
        ]))

    # ==================== 1. ACCUEIL ====================

    def _action_rapide(self, icon, label: str, on_click) -> ft.Column:
        return ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
            controls=[
                ft.Container(
                    width=44, height=44, border_radius=22, bgcolor=ft.Colors.with_opacity(0.22, ft.Colors.WHITE),
                    alignment=ft.Alignment.CENTER, on_click=on_click,
                    content=ft.Icon(icon, color=ft.Colors.WHITE, size=20),
                ),
                ft.Text(label, size=10, color=ft.Colors.WHITE),
            ],
        )

    def _ouvrir_ajout_type(self, type_transaction: str):
        self.selecteur_type.value = type_transaction
        self._maj_categories_dialog(None)
        self.ouvrir_dialog_ajout()

    def _section_accueil(self) -> ft.Column:
        r = self.resume
        rythme = r.get("rythme", {})
        revenus = r.get("revenus", 0)
        depenses = r.get("depenses", 0)
        budget_80 = r.get("budget_disponible_80", 0)
        objectif_20 = r.get("objectif_epargne_20", 0)
        epargne_realisee = max(revenus - depenses, 0)
        reste_disponible = max(budget_80 - depenses, 0)

        pct_depense = min(depenses / budget_80 * 100, 100) if budget_80 > 0 else 0
        pct_epargne = min(epargne_realisee / objectif_20 * 100, 100) if objectif_20 > 0 else 0

        carte_principale = ft.Container(
            border_radius=16, padding=20,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#FB923C", "#EA580C"],
            ),
            content=ft.Column(spacing=10, controls=[
                ft.Text("Ton argent ce mois-ci", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=13),
                ft.Text(_fcfa(revenus), size=26, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Row(controls=[
                    ft.Text(f"Budget dépenses : {_fcfa(budget_80)}", size=11, color="#FFEDD5"),
                    ft.Text(f"Objectif épargne : {_fcfa(objectif_20)}", size=11, color="#FFEDD5"),
                ]),
                ft.ProgressBar(value=0.8, color=ft.Colors.WHITE, bgcolor="#FDBA74", height=8, border_radius=6),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("80% dépenses", size=10, color="#FFEDD5"),
                    ft.Text("20% épargne", size=10, color="#FFEDD5"),
                ]),
                ft.Container(height=6),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_EVENLY, controls=[
                    self._action_rapide(ft.Icons.ADD_ROUNDED, "Revenu", lambda e: self._ouvrir_ajout_type("REVENU")),
                    self._action_rapide(ft.Icons.REMOVE_ROUNDED, "Dépense", lambda e: self._ouvrir_ajout_type("DEPENSE")),
                    self._action_rapide(ft.Icons.TRACK_CHANGES_ROUNDED, "Objectifs", lambda e: self._on_navigate("Objectifs")),
                ]),
            ]),
        )

        carte_ou_tu_en_es = _carte(content=ft.Column(spacing=10, controls=[
            ft.Text("Où tu en es", weight=ft.FontWeight.BOLD, color="#292524"),
            ft.Column(spacing=2, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("Dépensé", size=12, color="#78716C"),
                    ft.Text(f"{_fcfa(depenses)} / {_fcfa(budget_80)}", size=12, weight=ft.FontWeight.BOLD),
                ]),
                ft.ProgressBar(value=pct_depense / 100, color="#EF4444" if pct_depense >= 100 else "#FB923C", bgcolor="#FFE4C7", height=6),
            ]),
            ft.Column(spacing=2, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("Épargné", size=12, color="#78716C"),
                    ft.Text(f"{_fcfa(epargne_realisee)} / {_fcfa(objectif_20)}", size=12, weight=ft.FontWeight.BOLD),
                ]),
                ft.ProgressBar(value=pct_epargne / 100, color="#22C55E", bgcolor="#FFE4C7", height=6),
            ]),
            ft.Divider(),
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text("Reste disponible", size=12, color="#78716C"),
                ft.Text(_fcfa(reste_disponible), size=14, weight=ft.FontWeight.BOLD, color="#292524"),
            ]),
        ]))

        trop_eleve = rythme.get("trop_eleve", False)
        carte_rythme = _carte(
            bgcolor="#FDEAEA" if trop_eleve else "#DCFCE7",
            content=ft.Column(spacing=8, controls=[
                ft.Row(controls=[
                    ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, color="#EF4444" if trop_eleve else "#16A34A"),
                    ft.Text("Ton rythme actuel", weight=ft.FontWeight.BOLD, color="#292524"),
                ]),
                ft.Text(f"Tu dépenses environ {_fcfa(rythme.get('rythme_quotidien_actuel', 0))} / jour", size=13),
                ft.Text(f"Pour tenir jusqu'à la fin du mois : {_fcfa(rythme.get('rythme_quotidien_recommande', 0))} / jour", size=13),
                ft.Text(
                    ("⚠️ Ton rythme est trop élevé, tu risques de dépasser ton budget d'environ "
                     f"{_fcfa(rythme.get('depassement_projete', 0))}.") if trop_eleve else
                    "✅ Ton rythme est bon, continue ainsi.",
                    size=12, weight=ft.FontWeight.BOLD,
                    color="#C53030" if trop_eleve else "#16A34A",
                ),
            ]),
        )

        rep_depenses = r.get("repartition_depenses", [])[:6]
        carte_repartition = _carte(content=ft.Column(spacing=10, controls=[
            ft.Text("Où part ton argent ?", weight=ft.FontWeight.BOLD, color="#292524"),
            GraphiqueCamembert(rep_depenses) if rep_depenses else
            ft.Text("Pas encore de dépenses ce mois-ci.", size=12, color="#78716C"),
        ]))

        return ft.Column(spacing=14, controls=[
            ft.ResponsiveRow(controls=[
                ft.Container(col={"xs": 12, "md": 6}, content=carte_principale),
                ft.Container(col={"xs": 12, "md": 6}, content=carte_ou_tu_en_es),
            ]),
            carte_rythme,
            self._panneau_conseil(),
            carte_repartition,
            ft.TextButton("Voir/modifier mon plan du mois →",
                          icon=ft.Icons.EXPLORE_ROUNDED,
                          on_click=lambda e: self._on_navigate("Plan")),
        ])

    # ==================== 2. PLAN ====================

    def _rendre_lignes_plan(self):
        self.zone_lignes_revenus.controls = [
            ft.Row(controls=[cat, mnt, ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e, i=i: self._retirer_ligne("revenus", i))])
            for i, (cat, mnt) in enumerate(self._lignes_revenus_plan)
        ]
        self.zone_lignes_obligations.controls = [
            ft.Row(controls=[cat, mnt, ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e, i=i: self._retirer_ligne("obligations", i))])
            for i, (cat, mnt) in enumerate(self._lignes_obligations_plan)
        ]

    def _retirer_ligne(self, groupe: str, index: int):
        liste = self._lignes_revenus_plan if groupe == "revenus" else self._lignes_obligations_plan
        if len(liste) > 1:
            liste.pop(index)
        self._rendre_lignes_plan()
        self.page.update()

    def _ajouter_ligne(self, groupe: str, e=None):
        liste = self._lignes_revenus_plan if groupe == "revenus" else self._lignes_obligations_plan
        liste.append(self._nouvelle_ligne_vide())
        self._rendre_lignes_plan()
        self.page.update()

    def _enregistrer_plan(self, e):
        revenus_prevus = [
            {"categorie": cat.value, "montant": float(mnt.value)}
            for cat, mnt in self._lignes_revenus_plan if cat.value and mnt.value
        ]
        obligations = [
            {"categorie": cat.value, "montant": float(mnt.value)}
            for cat, mnt in self._lignes_obligations_plan if cat.value and mnt.value
        ]
        try:
            self.plan = self.state.api.enregistrer_plan(self.mois_courant, revenus_prevus, obligations)
        except (ApiError, ValueError) as err:
            _snack(self.page, f"Erreur : {err}", erreur=True)
            return
        self._rendre_resultat_plan()
        _snack(self.page, "Plan enregistré !")
        self.page.update()

    def _rendre_resultat_plan(self):
        p = self.plan
        self.zone_resultat_plan.content = ft.Column(spacing=6, controls=[
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text("Total revenus prévus", size=12, color="#78716C"),
                ft.Text(_fcfa(p.get("total_revenus_prevus", 0)), size=13, weight=ft.FontWeight.BOLD)]),
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text("80% dépenses / 20% épargne", size=12, color="#78716C"),
                ft.Text(f"{_fcfa(p.get('budget_80', 0))} / {_fcfa(p.get('objectif_epargne_20', 0))}", size=13, weight=ft.FontWeight.BOLD)]),
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text("Total obligations", size=12, color="#78716C"),
                ft.Text(_fcfa(p.get("total_obligations", 0)), size=13, weight=ft.FontWeight.BOLD)]),
            ft.Divider(),
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text("Budget flexible restant", size=13, weight=ft.FontWeight.BOLD, color="#292524"),
                ft.Text(_fcfa(p.get("budget_flexible_restant", 0)), size=15, weight=ft.FontWeight.BOLD, color="#16A34A")]),
            ft.Text(f"Soit environ {_fcfa(p.get('budget_flexible_par_jour', 0))} par jour pour tes dépenses variables.",
                    size=12, color="#78716C"),
        ])
        self.zone_resultat_plan.bgcolor = "#FFF1E6"
        self.zone_resultat_plan.border_radius = 12
        self.zone_resultat_plan.padding = 16

    def _panneau_simulation_plan(self) -> ft.Container:
        champ_delta_revenu = ft.TextField(label="Si mon revenu change de (+/- FCFA)", width=240, keyboard_type=ft.KeyboardType.NUMBER, value="0")
        champ_nouvelle_obligation = ft.TextField(label="Si j'ajoute une obligation de (FCFA)", width=240, keyboard_type=ft.KeyboardType.NUMBER, value="0")
        champ_epargne_cible = ft.TextField(label="Épargne visée (optionnel, FCFA)", width=220, keyboard_type=ft.KeyboardType.NUMBER)
        resultat = ft.Text(size=12, color="#292524")

        def simuler(e):
            try:
                res = self.state.api.simuler_plan(
                    self.mois_courant,
                    delta_revenu=float(champ_delta_revenu.value or 0),
                    nouvelle_obligation=float(champ_nouvelle_obligation.value or 0),
                    epargne_cible=float(champ_epargne_cible.value) if champ_epargne_cible.value else None,
                )
                resultat.value = (
                    f"Nouveau budget flexible : {_fcfa(res['budget_flexible_restant'])} "
                    f"(après épargne visée de {_fcfa(res['epargne_visee'])} : {_fcfa(res['budget_flexible_restant_apres_epargne_visee'])})"
                )
                resultat.color = "#16A34A"
            except (ApiError, ValueError) as err:
                resultat.value = f"Erreur : {err}"
                resultat.color = "#C53030"
            self.page.update()

        return _carte(content=ft.Column(spacing=10, controls=[
            ft.Row(controls=[ft.Icon(ft.Icons.CALCULATE_ROUNDED, color="#FB923C"),
                              ft.Text("Simuler mon budget", weight=ft.FontWeight.BOLD, color="#292524")]),
            ft.Row(wrap=True, controls=[champ_delta_revenu, champ_nouvelle_obligation, champ_epargne_cible]),
            ft.ElevatedButton("Simuler", icon=ft.Icons.PLAY_ARROW_ROUNDED, bgcolor="#FB923C",
                              color=ft.Colors.WHITE, on_click=simuler),
            resultat,
        ]))

    def _section_plan(self) -> ft.Column:
        self._rendre_lignes_plan()
        self._rendre_resultat_plan()
        return ft.Column(spacing=16, controls=[
            ft.Text(f"Ton plan de {self.mois_courant}", size=15, weight=ft.FontWeight.BOLD, color="#292524"),
            ft.ResponsiveRow(controls=[
                ft.Container(col={"xs": 12, "md": 6}, content=_carte(bgcolor=ft.Colors.WHITE, content=ft.Column(spacing=10, controls=[
                    ft.Text("Revenus prévus", weight=ft.FontWeight.BOLD, color="#292524"),
                    self.zone_lignes_revenus,
                    ft.TextButton("+ Ajouter une ligne", on_click=lambda e: self._ajouter_ligne("revenus")),
                ]))),
                ft.Container(col={"xs": 12, "md": 6}, content=_carte(bgcolor=ft.Colors.WHITE, content=ft.Column(spacing=10, controls=[
                    ft.Text("Dépenses obligatoires", weight=ft.FontWeight.BOLD, color="#292524"),
                    self.zone_lignes_obligations,
                    ft.TextButton("+ Ajouter une ligne", on_click=lambda e: self._ajouter_ligne("obligations")),
                ]))),
            ]),
            ft.ElevatedButton("Enregistrer mon plan", icon=ft.Icons.SAVE_ROUNDED, bgcolor="#F97316",
                              color=ft.Colors.WHITE, on_click=self._enregistrer_plan),
            self.zone_resultat_plan,
            self._panneau_simulation_plan(),
        ])

    # ==================== 3. ACTIVITÉ ====================

    def _filtrer_activite(self, filtre: str):
        self.filtre_activite = filtre
        self._rendre_section()
        self.page.update()

    def _section_activite(self) -> ft.Column:
        filtres = ["Tout", "Revenus", "Dépenses"]
        transactions = self.transactions
        if self.filtre_activite == "Revenus":
            transactions = [t for t in transactions if t["type"] == "REVENU"]
        elif self.filtre_activite == "Dépenses":
            transactions = [t for t in transactions if t["type"] == "DEPENSE"]

        barre_filtres = ft.Row(controls=[
            ft.Container(
                padding=ft.Padding(14, 8, 14, 8), border_radius=20,
                bgcolor="#F97316" if self.filtre_activite == f else "#FFF7ED",
                on_click=lambda e, ff=f: self._filtrer_activite(ff),
                content=ft.Text(f, size=12, weight=ft.FontWeight.BOLD,
                                 color=ft.Colors.WHITE if self.filtre_activite == f else "#78716C"),
            )
            for f in filtres
        ])

        if not transactions:
            liste = ft.Text("Aucune transaction pour l'instant.", size=12, color="#78716C")
        else:
            liste = ft.Column(spacing=6, controls=[self._ligne_transaction(t) for t in transactions])

        return ft.Column(spacing=14, controls=[
            barre_filtres,
            _carte(bgcolor=ft.Colors.WHITE, content=liste),
        ])

    def _ligne_transaction(self, t: dict) -> ft.Container:
        est_revenu = t["type"] == "REVENU"
        icones = {"MANUEL": ft.Icons.EDIT_NOTE_ROUNDED, "SMS": ft.Icons.SMS_ROUNDED,
                  "VOCAL": ft.Icons.MIC_ROUNDED, "PDF_IMPORT": ft.Icons.PICTURE_AS_PDF_ROUNDED}
        return ft.Container(
            bgcolor="#FFF7ED", border_radius=8, padding=10,
            content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Row(controls=[
                    ft.Icon(icones.get(t["source"], ft.Icons.RECEIPT_LONG_ROUNDED), size=18, color="#78716C"),
                    ft.Column(spacing=0, controls=[
                        ft.Text(t["categorie"], size=12, weight=ft.FontWeight.BOLD),
                        ft.Text(t["date_transaction"], size=10, color="#A8A29E"),
                    ]),
                ]),
                ft.Text(("+" if est_revenu else "-") + _fcfa(t["montant"]), size=13, weight=ft.FontWeight.BOLD,
                        color="#22C55E" if est_revenu else "#EF4444"),
            ]),
        )

    # ==================== 4. OBJECTIFS ====================

    def _section_objectifs(self) -> ft.Column:
        r = self.resume
        historique = r.get("historique_6_mois", [])
        mois_labels = [m["mois"] for m in historique]
        objectifs = [m["objectif_epargne"] for m in historique]
        realisees = [max(m["epargne"], 0) for m in historique]
        valeurs_dettes = [m["dettes"] for m in historique]

        dettes = [t for t in self.tontines if t.get("est_dette")]
        tontines_pures = [t for t in self.tontines if not t.get("est_dette")]
        lignes_dettes = [self._ligne_dette(d) for d in dettes] if dettes else \
            [ft.Text("Aucune dette suivie pour l'instant.", size=12, color="#78716C")]
        lignes_tontines = [self._ligne_tontine(t) for t in tontines_pures] if tontines_pures else \
            [ft.Text("Aucune tontine suivie pour l'instant.", size=12, color="#78716C")]

        return ft.Column(spacing=16, controls=[
            ft.Text("Épargne", size=15, weight=ft.FontWeight.BOLD, color="#292524"),
            ProGuard(self.page, self.state, "Objectif d'épargne vs épargne réalisée",
                     GraphiqueEvolution(mois_labels, [
                         ("Objectif (20%)", objectifs, "#FB923C"),
                         ("Épargne réalisée", realisees, "#22C55E"),
                     ])),
            self._panneau_simulation(),
            ft.Divider(),
            ft.Text("Dettes", size=15, weight=ft.FontWeight.BOLD, color="#292524"),
            ProGuard(self.page, self.state, "Évolution du solde des dettes",
                     GraphiqueEvolution(mois_labels, [("Solde restant", valeurs_dettes, "#A855F7")])),
            _carte(bgcolor=ft.Colors.WHITE, content=ft.Column(spacing=10, controls=lignes_dettes)),
            ft.Divider(),
            ft.Text("Tontines", size=15, weight=ft.FontWeight.BOLD, color="#292524"),
            _carte(bgcolor=ft.Colors.WHITE, content=ft.Column(spacing=10, controls=lignes_tontines)),
            self._formulaire_ajout_tontine(),
        ])

    def _panneau_simulation(self) -> ft.Container:
        champ_nom = ft.TextField(label="Nom du projet (ex: Ordinateur portable)", width=260)
        champ_montant = ft.TextField(label="Montant cible (FCFA)", width=180, keyboard_type=ft.KeyboardType.NUMBER)
        champ_reduction = ft.TextField(label="Réduction dépenses envisagée (%)", width=220,
                                        keyboard_type=ft.KeyboardType.NUMBER, value="10")
        resultat = ft.Text(size=12, color="#292524")

        def simuler(e):
            if not champ_nom.value or not champ_montant.value:
                _snack(self.page, "Indique le nom du projet et le montant cible.", erreur=True)
                return
            try:
                res = self.state.api.simuler_projet(
                    nom_projet=champ_nom.value, montant_cible=float(champ_montant.value),
                    reduction_depenses_pourcentage=float(champ_reduction.value or 0),
                )
                resultat.value = res["message"]
                resultat.color = "#16A34A"
            except (ApiError, ValueError) as err:
                resultat.value = f"Erreur : {err}"
                resultat.color = "#C53030"
            self.page.update()

        return _carte(content=ft.Column(spacing=10, controls=[
            ft.Row(controls=[ft.Icon(ft.Icons.ROCKET_LAUNCH_ROUNDED, color="#FB923C"),
                              ft.Text("Simuler un projet", weight=ft.FontWeight.BOLD, color="#292524")]),
            ft.Row(wrap=True, controls=[champ_nom, champ_montant, champ_reduction]),
            ft.ElevatedButton("Simuler", icon=ft.Icons.CALCULATE, bgcolor="#FB923C",
                              color=ft.Colors.WHITE, on_click=simuler),
            resultat,
        ]))

    def _ligne_dette(self, dette: dict) -> ft.Container:
        restant = dette["montant_cotisation"] - dette["montant_verse_total"]
        champ_montant = ft.TextField(label="Montant remboursé", width=140, keyboard_type=ft.KeyboardType.NUMBER)

        def rembourser(e):
            if not champ_montant.value:
                return
            try:
                self.state.api.rembourser_dette(dette["id"], float(champ_montant.value))
                _snack(self.page, "Remboursement enregistré !")
                self.rafraichir_donnees()
                self.page.update()
            except (ApiError, ValueError) as err:
                _snack(self.page, str(err), erreur=True)

        return ft.Container(
            bgcolor="#FFF7ED", border_radius=8, padding=10,
            content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True, controls=[
                ft.Column(spacing=0, controls=[
                    ft.Text(dette["nom"], size=12, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Restant : {_fcfa(max(restant, 0))} / {_fcfa(dette['montant_cotisation'])}", size=11, color="#78716C"),
                ]),
                ft.Row(controls=[champ_montant, ft.IconButton(icon=ft.Icons.CHECK_CIRCLE, icon_color="#F97316", on_click=rembourser)]),
            ]),
        )

    def _ligne_tontine(self, tontine: dict) -> ft.Container:
        return ft.Container(
            bgcolor="#FFF7ED", border_radius=8, padding=10,
            content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text(tontine["nom"], size=12, weight=ft.FontWeight.BOLD),
                ft.Text(f"{_fcfa(tontine['montant_cotisation'])} / {tontine['frequence']}", size=11, color="#78716C"),
            ]),
        )

    def _formulaire_ajout_tontine(self) -> ft.Container:
        champ_nom = ft.TextField(label="Nom", width=200)
        champ_montant = ft.TextField(label="Montant", width=140, keyboard_type=ft.KeyboardType.NUMBER)
        case_dette = ft.Checkbox(label="C'est une dette à rembourser")

        def ajouter(e):
            if not champ_nom.value or not champ_montant.value:
                _snack(self.page, "Nom et montant requis.", erreur=True)
                return
            try:
                self.state.api.ajouter_tontine(nom=champ_nom.value, montant_cotisation=float(champ_montant.value),
                                                est_dette=case_dette.value or False)
            except ApiError as err:
                if err.status_code == 403:
                    show_pro_modal(self.page, self.state, "Suivi illimité de tontines et dettes")
                else:
                    _snack(self.page, str(err), erreur=True)
                return
            except ValueError:
                _snack(self.page, "Montant invalide.", erreur=True)
                return
            champ_nom.value, champ_montant.value, case_dette.value = "", "", False
            _snack(self.page, "Ajouté !")
            self.rafraichir_donnees()
            self.page.update()

        return _carte(bgcolor=ft.Colors.WHITE, content=ft.Column(spacing=8, controls=[
            ft.Text("Ajouter une tontine ou une dette", weight=ft.FontWeight.BOLD, color="#292524"),
            ft.Row(wrap=True, controls=[champ_nom, champ_montant, case_dette]),
            ft.ElevatedButton("Ajouter", icon=ft.Icons.ADD, on_click=ajouter),
        ]))

    # ==================== 5. PROFIL ====================

    def _section_profil(self) -> ft.Container:
        utilisateur = self.state.utilisateur or {}
        statut = self.state.statut_pro_cache or {}
        return _carte(bgcolor=ft.Colors.WHITE, padding=20, content=ft.Column(spacing=14, controls=[
            ft.Text(utilisateur.get("nom", ""), size=16, weight=ft.FontWeight.BOLD, color="#292524"),
            ft.Text(f"Plan : {'PRO' if statut.get('is_pro') else 'Gratuit'}", size=13,
                    color="#16A34A" if statut.get("is_pro") else "#78716C"),
            ft.Divider(),
            ft.Text(f"Email : {utilisateur.get('email', '')}", size=13),
            ft.Text(f"Code de parrainage : {utilisateur.get('code_parrainage', '')}", size=13),
            ft.Text("Partage ton code : 1 ami inscrit = 10 jours PRO offerts (max 30j).", size=11, color="#78716C"),
            ft.Divider(),
            ft.Text("Mon Pass PRO", weight=ft.FontWeight.BOLD, color="#292524"),
            ft.Row(wrap=True, controls=[
                acheter_pass_button(self.page, self.state, nom, code, prix)
                for code, nom, prix in PLANS_PRO
            ]),
            ft.Container(height=10),
            ft.ElevatedButton("Déconnexion", icon=ft.Icons.LOGOUT, bgcolor="#EF4444",
                              color=ft.Colors.WHITE, on_click=lambda e: self.on_deconnexion()),
        ]))

    # ---------- Dialogue d'ajout de transaction ----------

    def _construire_dialog_ajout(self):
        self.selecteur_type = ft.Dropdown(
            label="Type", width=180,
            options=[ft.dropdown.Option("DEPENSE", "Dépense"), ft.dropdown.Option("REVENU", "Revenu")],
            value="DEPENSE", on_select=self._maj_categories_dialog,
        )
        self.selecteur_categorie = ft.Dropdown(
            label="Catégorie", width=180,
            options=[ft.dropdown.Option(c) for c in CATEGORIES_DEPENSE], value=CATEGORIES_DEPENSE[0],
        )
        self.champ_montant = ft.TextField(label="Montant (FCFA)", width=180, keyboard_type=ft.KeyboardType.NUMBER)
        self.case_fixe = ft.Checkbox(label="Revenu fixe (salaire...)", value=True, visible=False)
        self.zone_quota_info = ft.Text(size=11, color="#78716C")

        self.champ_sms = ft.TextField(label="Ou coller un SMS Mobile Money", multiline=True,
                                       value="Vous avez envoye 5000 FCFA a Jean")
        self.zone_sms_resultat = ft.Text(size=11)

        self.dialog_ajout = ft.AlertDialog(
            title=ft.Text("Ajouter"),
            content=ft.Column(tight=True, spacing=10, width=380, controls=[
                self.zone_quota_info,
                ft.Row(wrap=True, controls=[self.selecteur_type, self.selecteur_categorie]),
                ft.Row(controls=[self.champ_montant, self.case_fixe]),
                ft.ElevatedButton("Ajouter", icon=ft.Icons.ADD, bgcolor="#F97316",
                                  color=ft.Colors.WHITE, on_click=self._ajouter_manuel),
                ft.Divider(),
                self.champ_sms,
                ft.ElevatedButton("Analyser le SMS (PRO)", icon=ft.Icons.CONTENT_PASTE, on_click=self._analyser_sms),
                self.zone_sms_resultat,
            ]),
            actions=[ft.TextButton("Fermer", on_click=lambda e: self.page.pop_dialog())],
        )

    def _maj_categories_dialog(self, e):
        est_revenu = self.selecteur_type.value == "REVENU"
        self.selecteur_categorie.options = [ft.dropdown.Option(c) for c in (CATEGORIES_REVENU if est_revenu else CATEGORIES_DEPENSE)]
        self.selecteur_categorie.value = (CATEGORIES_REVENU if est_revenu else CATEGORIES_DEPENSE)[0]
        self.case_fixe.visible = est_revenu
        self.page.update()

    def ouvrir_dialog_ajout(self, e=None):
        try:
            q = self.state.api.quota()
            self.zone_quota_info.value = (
                "Saisie illimitée (Pass PRO actif)." if q["is_pro"] else
                f"{q['transactions_aujourdhui']}/{q['max_gratuit']} transactions utilisées aujourd'hui."
            )
        except ApiError:
            pass
        self.page.show_dialog(self.dialog_ajout)

    def _ajouter_manuel(self, e):
        if not self.champ_montant.value:
            _snack(self.page, "Merci d'indiquer un montant.", erreur=True)
            return
        try:
            montant = float(self.champ_montant.value)
        except ValueError:
            _snack(self.page, "Montant invalide.", erreur=True)
            return
        try:
            self.state.api.ajouter_transaction(
                type_=self.selecteur_type.value, montant=montant, categorie=self.selecteur_categorie.value,
                est_fixe=self.case_fixe.value if self.selecteur_type.value == "REVENU" else False, source="MANUEL",
            )
        except ApiError as e2:
            if e2.status_code == 403:
                self.page.pop_dialog()
                show_pro_modal(self.page, self.state, "Saisie manuelle illimitée (limite 3/jour atteinte)")
            else:
                _snack(self.page, str(e2), erreur=True)
            return
        self.champ_montant.value = ""
        self.page.pop_dialog()
        _snack(self.page, "Transaction ajoutée !")
        self.rafraichir_donnees()
        self.page.update()

    def _analyser_sms(self, e):
        if not self.state.est_pro:
            self.page.pop_dialog()
            show_pro_modal(self.page, self.state, "Analyse SMS intelligente")
            return
        match = re.search(r"(\d+)\s*FCFA", self.champ_sms.value or "")
        if match:
            montant = float(match.group(1))
            try:
                self.state.api.ajouter_transaction(type_="DEPENSE", montant=montant, categorie="Autre", source="SMS")
                self.zone_sms_resultat.value = f"Dépense de {_fcfa(montant)} détectée et enregistrée !"
                self.zone_sms_resultat.color = ft.Colors.GREEN_700
                self.rafraichir_donnees()
            except ApiError as err:
                self.zone_sms_resultat.value = f"Erreur : {err}"
                self.zone_sms_resultat.color = ft.Colors.RED_700
        else:
            self.zone_sms_resultat.value = "Impossible de lire le montant dans ce SMS."
            self.zone_sms_resultat.color = ft.Colors.RED_700
        self.page.update()

    # ---------- Construction générale (responsive) ----------

    def _pourcentage_epargne(self) -> float:
        objectif = self.resume.get("objectif_epargne_20", 0)
        if objectif <= 0:
            return 0
        realise = max(self.resume.get("revenus", 0) - self.resume.get("depenses", 0), 0)
        return min(realise / objectif * 100, 100)

    def _on_resize(self, e=None):
        nouvelle_valeur = (self.page.width or 1200) < SEUIL_MOBILE
        if nouvelle_valeur != self.es_mobile:
            self.es_mobile = nouvelle_valeur
            self._rendre_layout()
            self.page.update()

    def _bouton_flottant(self) -> ft.FloatingActionButton:
        return ft.FloatingActionButton(
            icon=ft.Icons.ADD, bgcolor="#F97316", foreground_color=ft.Colors.WHITE,
            on_click=self.ouvrir_dialog_ajout,
            right=16, bottom=86 if self.es_mobile else 20,
        )

    def _rendre_layout(self):
        self._rendre_section()

        if self.es_mobile:
            # Sur petit ecran : pas de sidebar (elle prendrait trop de place
            # horizontalement), barre de navigation en bas avec 4 icones,
            # bouton flottant "+" toujours accessible au-dessus de la barre.
            self.zone_layout.content = ft.Column(expand=True, spacing=0, controls=[
                ft.Stack(expand=True, controls=[
                    ft.Container(expand=True, content=self.zone_contenu),
                    self._bouton_flottant(),
                ]),
                BottomNavBar(self.sidebar.selection, self._on_navigate),
            ])
        else:
            # Ecran tablette/PC : sidebar complete conservee.
            self.zone_layout.content = ft.Row(
                expand=True, vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    self.sidebar.build(self._pourcentage_epargne()),
                    ft.Container(width=16),
                    ft.Stack(expand=True, controls=[self.zone_contenu, self._bouton_flottant()]),
                ],
            )

    def build(self) -> ft.Container:
        self.es_mobile = (self.page.width or 1200) < SEUIL_MOBILE
        self.page.on_resize = self._on_resize
        self._rendre_layout()
        return self.zone_layout


def acheter_pass_button(page, state, nom, code, prix):
    return ft.OutlinedButton(
        f"{nom.split(' (')[0]} — {prix:,} FCFA".replace(",", " "),
        on_click=lambda e: acheter_pass(page, state, code),
    )

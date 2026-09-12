"""
Coaching contextuel : transforme les chiffres en phrases utiles.

Principe : rester factuel et bienveillant, jamais culpabilisant. On informe
("il te reste X FCFA pour Y jours"), on ne donne pas d'ordre ("arrête de
dépenser"). Les messages sont générés à la volée à partir des vraies
données -- aucun stockage de jugement sur l'utilisateur.
"""
import datetime
import calendar


def generer_conseils(resume: dict) -> list[str]:
    conseils = []

    aujourdhui = datetime.date.today()
    jour_du_mois = aujourdhui.day
    jours_dans_mois = calendar.monthrange(aujourdhui.year, aujourdhui.month)[1]
    proportion_mois_ecoule = jour_du_mois / jours_dans_mois

    revenus = resume.get("revenus", 0)
    depenses = resume.get("depenses", 0)
    budget_80 = resume.get("budget_disponible_80", 0)
    reste = resume.get("reste_sur_budget", 0)
    pourcentage_utilise = resume.get("pourcentage_budget_utilise", 0) / 100

    if revenus == 0:
        conseils.append("Ajoute ton premier revenu du mois pour activer ton suivi 80/20 personnalisé.")
        return conseils

    # Rythme de dépense vs avancement du mois
    if budget_80 > 0:
        if pourcentage_utilise >= 1:
            conseils.append(
                f"Ton budget de dépenses du mois est dépassé de {abs(reste):,.0f} FCFA. "
                "Regarde tes dernières catégories pour voir où ajuster.".replace(",", " ")
            )
        elif pourcentage_utilise - proportion_mois_ecoule > 0.15:
            jours_restants = jours_dans_mois - jour_du_mois
            budget_jour = reste / jours_restants if jours_restants > 0 else reste
            conseils.append(
                f"Tu es le {jour_du_mois} du mois et tu as déjà utilisé "
                f"{pourcentage_utilise*100:.0f}% de ton budget dépenses. "
                f"Il te reste environ {budget_jour:,.0f} FCFA/jour pour les {jours_restants} jours restants."
                .replace(",", " ")
            )
        elif proportion_mois_ecoule - pourcentage_utilise > 0.15:
            conseils.append(
                f"Bon rythme : tu n'as utilisé que {pourcentage_utilise*100:.0f}% de ton budget "
                f"alors qu'on est déjà le {jour_du_mois}. Continue ainsi !"
            )

    # Concentration des revenus (dépendance à une seule source)
    repartition_revenus = resume.get("repartition_revenus", [])
    if repartition_revenus:
        principale = max(repartition_revenus, key=lambda x: x["montant"])
        part = principale["montant"] / revenus if revenus > 0 else 0
        if part > 0.75 and len(repartition_revenus) == 1:
            conseils.append(
                f"Ton revenu dépend à 100% de « {principale['categorie']} ». "
                "Diversifier tes sources de revenus réduit le risque en cas de coup dur."
            )

    # Concentration des dépenses (une catégorie qui domine)
    repartition_depenses = resume.get("repartition_depenses", [])
    if repartition_depenses and depenses > 0:
        principale_dep = max(repartition_depenses, key=lambda x: x["montant"])
        part_dep = principale_dep["montant"] / depenses
        if part_dep > 0.4:
            conseils.append(
                f"« {principale_dep['categorie']} » représente {part_dep*100:.0f}% de tes dépenses "
                "ce mois-ci -- ça vaut peut-être le coup d'y regarder de plus près."
            )

    # Épargne réalisée vs objectif (félicitation)
    epargne_realisee = revenus - depenses
    objectif_20 = resume.get("objectif_epargne_20", 0)
    if objectif_20 > 0 and epargne_realisee > objectif_20:
        surplus = epargne_realisee - objectif_20
        conseils.append(
            f"Bravo ! Tu as épargné {surplus:,.0f} FCFA de plus que ton objectif ce mois-ci. "
            "Pense à les verser sur ta tontine ou ton épargne de côté.".replace(",", " ")
        )

    if not conseils:
        conseils.append("Continue à saisir tes transactions pour affiner tes conseils personnalisés.")

    return conseils

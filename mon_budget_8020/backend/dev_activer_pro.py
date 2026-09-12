"""
Script de DEVELOPPEMENT uniquement : active un Pass PRO pour un utilisateur
sans passer par Notch Pay, pour tester les fonctionnalites PRO en local.

Ce n'est PAS un endpoint API (donc pas accessible depuis internet ou l'app),
juste un script a lancer a la main sur ta machine pendant les tests.
Ne jamais utiliser ça en production.

Usage :
    cd backend
    python dev_activer_pro.py yvanne@test.cm 3_MOIS
"""
import sys
import datetime

from database import SessionLocal
import models
import schemas


def activer_pro(email: str, plan: str = "3_MOIS", jours: int | None = None):
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        print(f"Aucun utilisateur trouve avec l'email {email}")
        return

    plan_enum = models.PlanPass(plan)
    duree = jours or schemas.DUREE_JOURS_PASS.get(plan_enum, 30)
    maintenant = datetime.datetime.utcnow()

    abonnement = models.Abonnement(
        user_id=user.id,
        plan=plan_enum,
        statut=models.StatutAbonnement.ACTIF,
        montant_fcfa=0,
        reference_paiement=f"DEV_TEST_{user.id}_{maintenant.timestamp()}",
        date_debut=maintenant,
        date_fin=maintenant + datetime.timedelta(days=duree),
    )
    db.add(abonnement)
    db.commit()
    print(f"Pass PRO ({plan}, {duree} jours) active pour {email} jusqu'au {abonnement.date_fin}")
    db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python dev_activer_pro.py <email> [1_MOIS|3_MOIS]")
        sys.exit(1)
    email = sys.argv[1]
    plan = sys.argv[2] if len(sys.argv) > 2 else "3_MOIS"
    activer_pro(email, plan)

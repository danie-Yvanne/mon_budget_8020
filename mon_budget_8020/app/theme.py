"""
Thème centralisé de l'app : palette "vert/turquoise moderne" + police Poppins.

Pour changer le style de l'app plus tard, c'est CE fichier qu'il faut
modifier -- pas besoin de chercher dans chaque composant.
"""

# ---------- Couleurs de marque ----------
PRIMARY = "#00C896"          # vert-turquoise, couleur de marque (boutons, accents)
PRIMARY_DARK = "#00A876"     # variante plus foncée (texte sur fond clair, hover)

# ---------- Sidebar (fond sombre) ----------
SIDEBAR_BG = "#0B2B27"           # fond principal de la sidebar
SIDEBAR_BG_DEEPEST = "#071F1B"   # dégradé le plus sombre
SIDEBAR_ITEM_ACTIVE = "#0D3B34"  # item de menu sélectionné
SIDEBAR_TEXT_INACTIF = "#7FA89E"

# ---------- Accents (variété visuelle sur KPIs/graphiques) ----------
ACCENT_TEAL = "#14B8A6"      # remplace l'ancien bleu (ex: revenus)
ACCENT_PURPLE = "#A855F7"    # dettes
ACCENT_AMBER = "#EAB308"     # mise en avant, conseils, étoiles

# ---------- Sémantique (ne change pas avec la palette) ----------
DANGER = "#EF4444"
DANGER_DARK = "#C53030"
DANGER_BG = "#FDEAEA"
SUCCESS = "#22C55E"

# ---------- Textes ----------
TEXT_HEADING = "#0F3D3A"       # titres, texte important
TEXT_BODY = "#1F4A44"          # texte de conseils/paragraphes
TEXT_MUTED = "#5C7A73"         # texte secondaire (labels, dates)
TEXT_MUTED_LIGHT = "#8FB0A8"   # texte tertiaire (très discret)

# ---------- Fonds ----------
BG_APP = "#F1FAF6"            # fond général de l'app (teinte menthe très claire)
BG_CARD_TEAL = "#E3F7F1"      # fond de carte teinté teal
BG_CARD_GREEN = "#EAF7F0"     # fond de carte teinté vert (conseils)
WHITE = "#FFFFFF"

# ---------- Typographie ----------
FONT_FAMILY = "Poppins"
FONT_URLS = {
    "Poppins": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Regular.ttf",
    "Poppins-Bold": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf",
    "Poppins-SemiBold": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-SemiBold.ttf",
}

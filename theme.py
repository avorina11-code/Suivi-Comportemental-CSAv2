# -*- coding: utf-8 -*-
"""
theme.py
========
Couche purement visuelle de l'application Adhérence Planning CSA.

Ce module ne contient AUCUNE logique métier : il n'importe ni ne modifie
`parsers.py` ni `analysis.py`. Il fournit uniquement :
  - une feuille de style globale (CSS) injectée une fois au chargement,
  - des cartes KPI avec compteur animé en JavaScript (rendu via une
    iframe autonome `st.components.v1.html`, donc avec son propre CSS
    embarqué — le CSS global de la page ne traverse pas les iframes),
  - un habillage de badges de statut pour les tableaux (pandas Styler,
    donc 100% compatible avec le st.dataframe interactif existant :
    tri, redimensionnement, export restent natifs),
  - un thème Plotly cohérent avec la charte graphique.

Objectif : rendre l'app plus agréable visuellement sans toucher au
fonctionnement (imports, calculs, jointures, statuts restent identiques).

--------------------------------------------------------------------------
DIRECTION ARTISTIQUE — "poste de contrôle" d'un plateau d'appels
--------------------------------------------------------------------------
La sidebar (import des fichiers, réglages) est traitée comme le panneau
de commande physique d'un poste opérateur : fond encre sombre, contrôles
techniques. La zone principale (les données analysées) reste un support
clair et dense, comme une feuille de rapport posée sur ce panneau — c'est
elle qui doit rester lisible longtemps par un superviseur.

Un seul motif se répète pour signaler un statut ou une intensité : un
petit "rail" de couleur (trait vertical ou point), plutôt que des blocs
pastel pleins partout. C'est l'unique geste stylistique fort ; le reste
(typographie, espacements, bordures) reste discret et discipliné.

Typographies : "Space Grotesk" (titres, valeurs chiffrées — la voix des
données) et "Inter" (texte courant, libellés, tableaux — le texte de
travail). Deux familles, clairement différenciées.
"""

from __future__ import annotations

import streamlit as st
import plotly.io as pio
import plotly.graph_objects as go

# --------------------------------------------------------------------
# PALETTE
# --------------------------------------------------------------------

# Surfaces "panneau de commande" (sidebar, encre)
INK = "#10182B"           # fond du panneau de commande (sidebar)
INK_RAISED = "#1B2740"    # contrôles sur fond encre (inputs, cadres)
INK_BORDER = "#2C3A57"    # hairline sur fond encre
INK_TEXT = "#E9EDF5"      # texte sur fond encre
INK_TEXT_MUTED = "#8C9BB5"  # texte secondaire sur fond encre

# Surfaces "feuille de rapport" (zone principale)
PAPER = "#F2F4F8"         # fond de la zone principale
PAPER_RAISED = "#FFFFFF"  # cartes / tuiles sur la feuille
BORDER = "#E1E5EC"        # hairline sur fond clair

# Couleurs de marque / signal — gardent les mêmes NOMS que la version
# précédente (utilisés directement par app.py), seules les valeurs
# changent pour coller à la nouvelle direction.
PRIMARY = "#0E7C86"       # sarcelle "ligne téléphonique" — accent structurant
PRIMARY_DARK = "#0A5F67"
ACCENT = "#E08E1D"        # ambre "voyant" — attire l'oeil, alertes douces
SUCCESS = "#1F9D6B"
WARNING = "#D97F13"
DANGER = "#D6483D"
NEUTRAL = "#8A97AC"

TEXT_DARK = "#10182B"     # texte principal sur fond clair
TEXT_MUTED = "#5B6B84"    # texte secondaire sur fond clair

# (fond, texte) par statut — utilisé pour les badges et le style du tableau.
# Fonds très pâles pour rester lisibles sur les tuiles blanches du tableau ;
# le petit emoji au début de chaque libellé de statut fait déjà office de
# "point de signal", inutile d'ajouter un bloc de couleur agressif derrière.
STATUS_COLORS = {
    "🔴 Écart à recadrer":            ("#FCECEA", "#B23A2F"),
    "🟠 Écart mineur":                 ("#FDF2E3", "#AD6A0E"),
    "🟢 Conforme":                     ("#E9F6F0", "#187A55"),
    "🚫 Absence non justifiée":        ("#FBE8E6", "#8B2A21"),
    "⚪ Non planifié (OFF/Congé)":     ("#F1F3F6", "#5B6B84"),
    "⌛ Pas encore commencé":          ("#E9F2F4", "#0E5D68"),
}
DEFAULT_STATUS_COLOR = ("#F1F3F6", "#33415A")

PLOTLY_TEMPLATE_NAME = "csa_theme"


def _register_plotly_template():
    if PLOTLY_TEMPLATE_NAME in pio.templates:
        return
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family="Inter, -apple-system, sans-serif", color=TEXT_DARK, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[PRIMARY, ACCENT, SUCCESS, DANGER, NEUTRAL, WARNING],
        title=dict(font=dict(family="Space Grotesk, sans-serif", size=16, color=TEXT_DARK)),
        xaxis=dict(showgrid=False, linecolor=BORDER, tickfont=dict(color=TEXT_MUTED)),
        yaxis=dict(gridcolor="#EAEDF3", zerolinecolor=BORDER, tickfont=dict(color=TEXT_MUTED)),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=60, l=10, r=10, b=10),
    )
    pio.templates[PLOTLY_TEMPLATE_NAME] = tmpl


_register_plotly_template()


# --------------------------------------------------------------------
# CSS GLOBAL (page principale — n'affecte pas les iframes de composants)
# --------------------------------------------------------------------

def inject_global_style():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}
        h1, h2, h3, h4 {{ font-family: 'Space Grotesk', 'Inter', sans-serif; }}

        /* ---------------------------------------------------------- */
        /* Zone principale = "feuille de rapport"                     */
        /* ---------------------------------------------------------- */
        [data-testid="stAppViewContainer"] {{ background: {PAPER}; }}
        [data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stMainBlockContainer"] {{ padding-top: 1.6rem; }}

        /* ---------------------------------------------------------- */
        /* Sidebar = "panneau de commande" (fond encre)                */
        /* ---------------------------------------------------------- */
        [data-testid="stSidebar"] {{
            background: {INK};
            border-right: 1px solid {INK_BORDER};
        }}
        [data-testid="stSidebar"] * {{ color: {INK_TEXT}; }}
        [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {{
            color: {INK_TEXT_MUTED} !important;
        }}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {{
            font-family: 'Space Grotesk', sans-serif; letter-spacing: -0.01em;
        }}
        [data-testid="stSidebar"] hr {{ border-color: {INK_BORDER}; }}

        /* Champs de saisie de la sidebar (uploader, number/time input) */
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
        [data-testid="stSidebar"] div[data-baseweb="input"],
        [data-testid="stSidebar"] div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] div[data-testid="stNumberInput"] input,
        [data-testid="stSidebar"] div[data-testid="stTimeInput"] input {{
            background: {INK_RAISED} !important;
            border: 1px solid {INK_BORDER} !important;
            color: {INK_TEXT} !important;
            border-radius: 8px !important;
        }}
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {{
            background: transparent !important;
            border: 1px solid {ACCENT} !important;
            color: {ACCENT} !important;
        }}
        [data-testid="stSidebar"] [data-testid="stCheckbox"] label span[data-testid] {{
            border-color: {INK_BORDER} !important;
        }}

        /* Bouton principal de la sidebar — plat, pas de dégradé décoratif */
        [data-testid="stSidebar"] div.stButton > button[kind="primary"] {{
            background: {ACCENT};
            color: {INK};
            border: none; border-radius: 8px; font-weight: 700;
            transition: filter .12s ease;
        }}
        [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {{
            filter: brightness(1.08);
        }}
        [data-testid="stSidebar"] div.stButton > button[kind="primary"]:focus-visible {{
            outline: 2px solid {INK_TEXT}; outline-offset: 2px;
        }}

        /* Expander "détection automatique" dans la sidebar */
        [data-testid="stSidebar"] [data-testid="stExpander"] {{
            background: {INK_RAISED};
            border: 1px solid {INK_BORDER};
            border-radius: 8px;
        }}

        /* ---------------------------------------------------------- */
        /* Bannière d'en-tête — bandeau plat, pas de dégradé décoratif */
        /* ---------------------------------------------------------- */
        .csa-hero {{
            position: relative;
            background: {PAPER_RAISED};
            padding: 22px 26px 20px 26px;
            border: 1px solid {BORDER};
            border-radius: 12px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .csa-hero::before {{
            content: '';
            position: absolute; top: 0; left: 0; height: 3px; width: 0%;
            background: {ACCENT};
        }}
        @media (prefers-reduced-motion: no-preference) {{
            .csa-hero::before {{ animation: csa-trace 0.9s ease-out forwards; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .csa-hero::before {{ width: 100%; }}
        }}
        @keyframes csa-trace {{ to {{ width: 100%; }} }}
        .csa-hero h1 {{
            margin: 0; font-size: 23px; font-weight: 700; color: {TEXT_DARK};
            letter-spacing: -0.01em; display: flex; align-items: center; gap: 10px;
        }}
        .csa-hero h1::before {{
            content: ''; display: inline-block; width: 9px; height: 9px;
            border-radius: 50%; background: {ACCENT}; flex-shrink: 0;
        }}
        .csa-hero p {{ margin: 6px 0 0 19px; color: {TEXT_MUTED}; font-size: 13.5px; }}

        /* ---------------------------------------------------------- */
        /* Onglets — sélecteur plat, indicateur ambre (pas de pilule)  */
        /* ---------------------------------------------------------- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 22px; background: transparent; border-bottom: 1px solid {BORDER};
            padding: 0;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 0; padding: 8px 2px; font-weight: 600; color: {TEXT_MUTED};
            background: transparent;
        }}
        .stTabs [aria-selected="true"] {{
            color: {TEXT_DARK} !important; background: transparent !important;
        }}
        .stTabs [data-baseweb="tab-highlight"] {{
            background-color: {ACCENT} !important; height: 2px;
        }}
        .stTabs [data-baseweb="tab-border"] {{ background-color: transparent; }}

        /* ---------------------------------------------------------- */
        /* Cartes / conteneurs de la zone principale                   */
        /* ---------------------------------------------------------- */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            border-radius: 10px !important;
        }}

        /* Badge de statut inline (fiche individuelle) */
        .csa-badge {{
            display: inline-flex; align-items: center; gap: 7px;
            padding: 4px 13px; border-radius: 999px;
            font-weight: 700; font-size: 13.5px;
        }}
        .csa-badge::before {{
            content: ''; width: 7px; height: 7px; border-radius: 50%;
            background: currentColor; flex-shrink: 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_banner(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="csa-hero">
            <h1>{title}</h1>
            {f'<p>{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status_text: str) -> str:
    """ Retourne le HTML d'un badge coloré pour un statut donné (à insérer via st.markdown(..., unsafe_allow_html=True)). """
    bg, fg = STATUS_COLORS.get(status_text, DEFAULT_STATUS_COLOR)
    return f'<span class="csa-badge" style="background:{bg};color:{fg};">{status_text}</span>'


# --------------------------------------------------------------------
# CARTES KPI AVEC COMPTEUR ANIMÉ (JavaScript, iframe autonome)
# --------------------------------------------------------------------

_KPI_CSS = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@500;600&display=swap');
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: 'Inter', -apple-system, sans-serif; }}
  .kpi-row {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .kpi-card {{
      flex: 1; min-width: 155px; background: {PAPER_RAISED}; border-radius: 8px;
      padding: 14px 16px 14px 16px; border: 1px solid {BORDER};
      border-left: 3px solid var(--rail-color, {PRIMARY});
      position: relative;
  }}
  .kpi-card.alert {{ animation: csa-signal 1.9s ease-in-out infinite; }}
  @keyframes csa-signal {{
      0%, 100% {{ border-left-color: var(--rail-color, {DANGER}); }}
      50%      {{ border-left-color: {PAPER_RAISED}; }}
  }}
  .kpi-icon {{
      position: absolute; top: 12px; right: 14px; font-size: 15px; opacity: .55;
  }}
  .kpi-value {{
      font-family: 'Space Grotesk', sans-serif;
      font-size: 26px; font-weight: 700; color: {TEXT_DARK}; line-height: 1.1;
      font-variant-numeric: tabular-nums;
  }}
  .kpi-label {{
      font-size: 12px; color: {TEXT_MUTED}; font-weight: 500;
      margin-top: 5px;
  }}
</style>
"""

_KPI_JS = """
<script>
  const vals = document.querySelectorAll('.kpi-value');
  vals.forEach(function(el) {
    const target = parseFloat(el.getAttribute('data-target')) || 0;
    const suffix = el.getAttribute('data-suffix') || '';
    const isInt = el.getAttribute('data-int') === '1';
    const duration = 700;
    let start = null;
    function step(ts) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
      el.textContent = (isInt ? Math.round(current) : current.toFixed(1)) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
</script>
"""


def render_kpi_row(items, height: int = 130):
    """
    Affiche une rangée de cartes KPI avec compteur animé en JS.

    items : liste de dicts
        {"label": str, "value": float|int, "icon": str,
         "color": str (couleur du rail d'accent, optionnel),
         "suffix": str (optionnel, ex " min"),
         "alert": bool (optionnel, active un léger signal de pulsation
                  sur le rail de couleur — pas de halo/ombre agressif)}
    """
    cards = []
    for it in items:
        color = it.get("color", PRIMARY)
        suffix = it.get("suffix", "")
        is_int = isinstance(it["value"], int) or float(it["value"]).is_integer()
        alert_cls = " alert" if it.get("alert") else ""
        cards.append(f"""
        <div class="kpi-card{alert_cls}" style="--rail-color:{color};">
          <div class="kpi-icon">{it.get('icon', '📌')}</div>
          <div class="kpi-value" data-target="{it['value']}" data-suffix="{suffix}" data-int="{1 if is_int else 0}">0{suffix}</div>
          <div class="kpi-label">{it['label']}</div>
        </div>
        """)
    html = _KPI_CSS + f'<div class="kpi-row">{"".join(cards)}</div>' + _KPI_JS
    st.components.v1.html(html, height=height, scrolling=False)


# --------------------------------------------------------------------
# STYLE DU TABLEAU (pandas Styler — reste un st.dataframe natif/interactif)
# --------------------------------------------------------------------

def style_matrice(df, status_col: str = "Statut", numeric_cols=None):
    """
    Retourne un pandas Styler appliquant un badge de couleur sur la colonne
    de statut et un format compact sur les colonnes numériques, tout en
    conservant le rendu st.dataframe natif (tri, redimensionnement, etc.).
    """
    numeric_cols = numeric_cols or []

    def _status_style(val):
        bg, fg = STATUS_COLORS.get(val, DEFAULT_STATUS_COLOR)
        return f"background-color:{bg}; color:{fg}; font-weight:600; border-radius:6px;"

    styler = df.style
    if status_col in df.columns:
        try:
            styler = styler.map(_status_style, subset=[status_col])
        except AttributeError:
            # pandas < 2.1 : Styler.map n'existe pas encore, on retombe sur applymap
            styler = styler.applymap(_status_style, subset=[status_col])
    fmt = {c: "{:.0f}" for c in numeric_cols if c in df.columns}
    if fmt:
        styler = styler.format(fmt, na_rep="—")
    return styler

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
"""

from __future__ import annotations

import streamlit as st
import plotly.io as pio
import plotly.graph_objects as go

# --------------------------------------------------------------------
# PALETTE
# --------------------------------------------------------------------

PRIMARY = "#4F46E5"      # indigo
PRIMARY_DARK = "#3730A3"
ACCENT = "#06B6D4"       # cyan
SUCCESS = "#10B981"
WARNING = "#F59E0B"
DANGER = "#EF4444"
NEUTRAL = "#94A3B8"
TEXT_DARK = "#1E293B"
TEXT_MUTED = "#64748B"

# (fond, texte) par statut — utilisé pour les badges et le style du tableau
STATUS_COLORS = {
    "🔴 Écart à recadrer":            ("#FEF2F2", "#DC2626"),
    "🟠 Écart mineur":                 ("#FFFBEB", "#D97706"),
    "🟢 Conforme":                     ("#F0FDF4", "#16A34A"),
    "🚫 Absence non justifiée":        ("#FEF2F2", "#991B1B"),
    "⚪ Non planifié (OFF/Congé)":     ("#F8FAFC", "#64748B"),
    "⌛ Pas encore commencé":          ("#EFF6FF", "#2563EB"),
}
DEFAULT_STATUS_COLOR = ("#F8FAFC", "#334155")

PLOTLY_TEMPLATE_NAME = "csa_theme"


def _register_plotly_template():
    if PLOTLY_TEMPLATE_NAME in pio.templates:
        return
    tmpl = go.layout.Template()
    tmpl.layout = go.Layout(
        font=dict(family="Inter, -apple-system, sans-serif", color=TEXT_DARK, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[PRIMARY, ACCENT, SUCCESS, WARNING, DANGER, NEUTRAL],
        title=dict(font=dict(size=16, color=TEXT_DARK)),
        xaxis=dict(showgrid=False, linecolor="#E2E8F0", tickfont=dict(color=TEXT_MUTED)),
        yaxis=dict(gridcolor="#EEF2F7", zerolinecolor="#E2E8F0", tickfont=dict(color=TEXT_MUTED)),
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}

        /* Bannière d'en-tête */
        .csa-hero {{
            background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%);
            padding: 26px 30px;
            border-radius: 18px;
            color: white;
            margin-bottom: 18px;
            box-shadow: 0 10px 30px rgba(79,70,229,0.22);
        }}
        .csa-hero h1 {{ margin: 0; font-size: 25px; font-weight: 800; letter-spacing: -0.01em; }}
        .csa-hero p {{ margin: 6px 0 0 0; opacity: 0.92; font-size: 13.5px; }}

        /* Onglets en pilules */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px; background: #F1F5F9; padding: 6px; border-radius: 14px;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 10px; padding: 8px 18px; font-weight: 600; color: #475569;
        }}
        .stTabs [aria-selected="true"] {{
            background: linear-gradient(135deg, {PRIMARY}, {ACCENT}) !important;
            color: white !important;
        }}

        /* Bouton principal de la sidebar */
        [data-testid="stSidebar"] div.stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, {PRIMARY}, {ACCENT});
            border: none; border-radius: 10px; font-weight: 700;
            box-shadow: 0 4px 14px rgba(79,70,229,0.30);
        }}
        [data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {{
            filter: brightness(1.06);
        }}

        /* Badge de statut inline (fiche individuelle) */
        .csa-badge {{
            display: inline-block; padding: 4px 14px; border-radius: 999px;
            font-weight: 700; font-size: 13.5px;
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
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: 'Inter', -apple-system, sans-serif; }}
  .kpi-row {{ display: flex; gap: 14px; flex-wrap: wrap; }}
  .kpi-card {{
      flex: 1; min-width: 155px; background: #ffffff; border-radius: 16px;
      padding: 16px 18px; border: 1px solid #EEF2F7;
      box-shadow: 0 2px 10px rgba(15,23,42,0.06);
      transition: transform .15s ease, box-shadow .15s ease;
  }}
  .kpi-card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 22px rgba(15,23,42,0.12); }}
  .kpi-card.alert {{ animation: pulse 1.8s ease-in-out infinite; }}
  @keyframes pulse {{
      0%   {{ box-shadow: 0 2px 10px rgba(220,38,38,0.10); }}
      50%  {{ box-shadow: 0 2px 18px rgba(220,38,38,0.35); }}
      100% {{ box-shadow: 0 2px 10px rgba(220,38,38,0.10); }}
  }}
  .kpi-icon {{ font-size: 21px; margin-bottom: 4px; }}
  .kpi-value {{ font-size: 27px; font-weight: 800; color: #1E293B; line-height: 1.1; }}
  .kpi-label {{
      font-size: 11.5px; color: #64748B; font-weight: 700; text-transform: uppercase;
      letter-spacing: .04em; margin-top: 2px;
  }}
  .kpi-accent {{ height: 4px; border-radius: 4px; margin-top: 10px; }}
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
         "color": str (couleur d'accent, optionnel),
         "suffix": str (optionnel, ex " min"),
         "alert": bool (optionnel, active un léger effet de pulsation)}
    """
    cards = []
    for it in items:
        color = it.get("color", PRIMARY)
        suffix = it.get("suffix", "")
        is_int = isinstance(it["value"], int) or float(it["value"]).is_integer()
        alert_cls = " alert" if it.get("alert") else ""
        cards.append(f"""
        <div class="kpi-card{alert_cls}">
          <div class="kpi-icon">{it.get('icon', '📌')}</div>
          <div class="kpi-value" data-target="{it['value']}" data-suffix="{suffix}" data-int="{1 if is_int else 0}">0{suffix}</div>
          <div class="kpi-label">{it['label']}</div>
          <div class="kpi-accent" style="background:{color};"></div>
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
        return f"background-color:{bg}; color:{fg}; font-weight:700; border-radius:6px;"

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

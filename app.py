# -*- coding: utf-8 -*-
"""
app.py
======
Application Streamlit d'analyse d'adhérence planning et de suivi
comportemental pour centre de contacts (CSA).

Croise le Planning Hebdo (théorique) avec les exports Vocalcom (réel)
pour identifier automatiquement retards, dépassements de pause, départs
anticipés et absences.

Lancement :
    streamlit run app.py
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import parsers as P
import analysis as A
import theme as T

st.set_page_config(
    page_title="Adhérence Planning CSA",
    page_icon="📞",
    layout="wide",
)

T.inject_global_style()

# ==========================================================================
# ÉTAT DE SESSION
# ==========================================================================

if "planning_df" not in st.session_state:
    st.session_state.planning_df = None
if "pause_result" not in st.session_state:
    st.session_state.pause_result = None
if "agents_report_df" not in st.session_state:
    st.session_state.agents_report_df = None
if "activities_df" not in st.session_state:
    st.session_state.activities_df = None
if "detections" not in st.session_state:
    st.session_state.detections = []  # [(nom_fichier, type_detecte), ...]


# ==========================================================================
# SIDEBAR — IMPORT & PARAMÈTRES
# ==========================================================================

st.sidebar.title("📁 Import des fichiers")

planning_file = st.sidebar.file_uploader(
    "Planning Hebdo (théorique) — .xlsx",
    type=["xlsx"],
    help="Fichier obligatoire. Doit contenir une feuille 'Planning_Hebdo' "
    "avec les colonnes Matricule_RH, Login_Vocalcom, Nom_Prenom et les "
    "heures de début/fin par jour.",
)

vocalcom_files = st.sidebar.file_uploader(
    "Exports Vocalcom (réel) — .xls / .xlsx",
    type=["xls", "xlsx"],
    accept_multiple_files=True,
    help="Déposez ici un ou plusieurs exports Vocalcom : 'Agents pause "
    "report' (obligatoire), et éventuellement 'Agents report' et/ou "
    "'Agents activities by dates'. Le type de chaque fichier est détecté "
    "AUTOMATIQUEMENT à partir de son contenu — peu importe le nom du "
    "fichier.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Paramètres")

export_temps_reel = st.sidebar.checkbox(
    "Export en cours de journée (Temps Réel)",
    value=False,
    help="Cochez si l'export Vocalcom a été réalisé en pleine journée. "
    "Désactive l'alerte de départ anticipé pour les agents dont le "
    "shift prévisionnel se termine après l'heure d'extraction indiquée.",
)
heure_extraction = None
if export_temps_reel:
    heure_extraction = st.sidebar.time_input(
        "Heure d'extraction", value=dt.time(13, 0)
    )

seuil_retard = st.sidebar.number_input(
    "Seuil de retard toléré (min)", min_value=0, max_value=60, value=5, step=1
)
pause_autorisee = st.sidebar.number_input(
    "Pause autorisée (min)", min_value=0, max_value=180, value=30, step=5
)
seuil_depassement_alerte = st.sidebar.number_input(
    "Seuil d'alerte dépassement pause (min)", min_value=0, max_value=60, value=5, step=1
)

st.sidebar.markdown("---")
process_btn = st.sidebar.button("🔄 Analyser", type="primary", use_container_width=True)


# ==========================================================================
# TRAITEMENT DES IMPORTS
# ==========================================================================

def _process_uploads():
    detections = []

    if planning_file is not None:
        try:
            st.session_state.planning_df = P.load_planning(planning_file)
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Erreur lecture Planning Hebdo : {exc}")
            st.session_state.planning_df = None

    st.session_state.pause_result = None
    st.session_state.agents_report_df = None
    st.session_state.activities_df = None

    for f in vocalcom_files or []:
        try:
            rtype, result = P.load_any_vocalcom_export(f, filename=f.name)
        except Exception as exc:  # noqa: BLE001
            detections.append((f.name, f"❌ Erreur : {exc}"))
            continue

        label = {
            "pause_report": "✅ Agents pause report (obligatoire)",
            "agents_report": "ℹ️ Agents report (détail états, optionnel)",
            "activities_by_date": "ℹ️ Agents activities by dates (résumé, optionnel)",
            "unknown": "⚠️ Type non reconnu — fichier ignoré",
        }.get(rtype, rtype)
        detections.append((f.name, label))

        if rtype == "pause_report":
            st.session_state.pause_result = result
        elif rtype == "agents_report":
            st.session_state.agents_report_df = result
        elif rtype == "activities_by_date":
            st.session_state.activities_df = result

    st.session_state.detections = detections


if process_btn:
    _process_uploads()

if st.session_state.detections:
    with st.sidebar.expander("🔍 Détection automatique des fichiers", expanded=True):
        for fname, label in st.session_state.detections:
            st.write(f"**{fname}**")
            st.caption(label)


# ==========================================================================
# GARDE-FOUS
# ==========================================================================

T.hero_banner(
    "📞 Adhérence Planning & Suivi Comportemental — CSA",
    "Analyse factuelle des retards, pauses et absences à partir des logs Vocalcom",
)

if st.session_state.planning_df is None or st.session_state.pause_result is None:
    st.info(
        "👈 Importez le **Planning Hebdo** ainsi qu'au moins un export "
        "Vocalcom de type **Agents pause report** dans la barre latérale, "
        "puis cliquez sur **Analyser**."
    )
    st.markdown(
        """
### Rappel des fichiers attendus
| Fichier | Statut | Contenu utilisé |
|---|---|---|
| Planning Hebdo | **Obligatoire** | Heures théoriques de début/fin par jour et par agent |
| Agents pause report | **Obligatoire** | Arrivée/départ réels, durée de pause, timeline des pauses par tranche de 30 min |
| Agents report | Optionnel | Détail des états (Attente, Traitement, Post-travail, Pause…) pour enrichir l'analyse |
| Agents activities by dates | Optionnel | Résumé arrivée/départ en secours (nom tronqué, jointure par Login uniquement) |

⚠️ Le **type réel** de chaque export Vocalcom est détecté automatiquement
à partir de son contenu, indépendamment de son nom de fichier (les
exports Vocalcom sont parfois nommés de façon trompeuse).
        """
    )
    st.stop()


# ==========================================================================
# CONSTRUCTION DE LA MATRICE COMPORTEMENTALE
# ==========================================================================

pause_result = st.session_state.pause_result
report_date = pause_result.date or dt.date.today()
jour_semaine = P.date_to_jour_fr(report_date)

st.caption(
    f"📅 Date détectée dans l'export Vocalcom : **{report_date.strftime('%d/%m/%Y')}** "
    f"→ colonne planning ciblée automatiquement : **{jour_semaine}**"
)

shift_today = P.get_shift_for_day(st.session_state.planning_df, jour_semaine)

# Agents présents dans le Vocalcom mais absents du planning (matricule inconnu)
logins_planning = set(shift_today["Login"])
logins_pointes = set(pause_result.summary["Login"]) if not pause_result.summary.empty else set()
logins_hors_planning = logins_pointes - logins_planning

matrice = A.build_matrice_comportementale(
    shift_today,
    pause_result.summary,
    seuil_retard_min=seuil_retard,
    pause_autorisee_min=pause_autorisee,
    seuil_depassement_alerte_min=seuil_depassement_alerte,
    export_temps_reel=export_temps_reel,
    heure_extraction=heure_extraction,
)

tab1, tab2, tab3 = st.tabs(
    ["📊 Vue Équipe & Indicateurs", "⏱️ Timeline & Distribution des Pauses", "📝 Fiche Individuelle"]
)


# ==========================================================================
# ONGLET 1 — VUE ÉQUIPE
# ==========================================================================

with tab1:
    nb_presents = (matrice["Arrivee_reelle"].notna()).sum()
    nb_absents = (matrice["Statut"] == "🚫 Absence non justifiée").sum()
    nb_recadrer = (matrice["Statut"] == "🔴 Écart à recadrer").sum()
    cumul_retards = matrice["Retard_min"].fillna(0).sum()
    cumul_depassements = matrice["Depassement_pause_min"].fillna(0).sum()

    T.render_kpi_row([
        {"label": "Présents", "value": int(nb_presents), "icon": "🟢", "color": T.SUCCESS},
        {"label": "Absents non justifiés", "value": int(nb_absents), "icon": "🚫", "color": T.DANGER,
         "alert": nb_absents > 0},
        {"label": "Cas à recadrer", "value": int(nb_recadrer), "icon": "🔴", "color": T.DANGER,
         "alert": nb_recadrer > 0},
        {"label": "Cumul retards plateau", "value": round(float(cumul_retards)), "icon": "⏱️",
         "color": T.WARNING, "suffix": " min"},
        {"label": "Cumul dépassements pause", "value": round(float(cumul_depassements)), "icon": "☕",
         "color": T.ACCENT, "suffix": " min"},
    ])


    if logins_hors_planning:
        st.warning(
            f"⚠️ {len(logins_hors_planning)} login(s) présents dans l'export Vocalcom "
            f"mais absents du Planning Hebdo pour {jour_semaine} : "
            + ", ".join(sorted(logins_hors_planning))
        )

    st.markdown("### Matrice comportementale")
    statuts_dispo = matrice["Statut"].unique().tolist()
    filtre_statut = st.multiselect(
        "Filtrer par statut", options=statuts_dispo, default=statuts_dispo
    )
    df_affiche = matrice[matrice["Statut"].isin(filtre_statut)].copy()

    display_cols = [
        "Matricule_RH", "Login", "Nom", "Statut_planning",
        "Debut_prevu", "Fin_prevu", "Arrivee_reelle", "Depart_reel",
        "Retard_min", "Duree_pause_min", "Depassement_pause_min",
        "Depart_anticipe_min", "Statut",
    ]
    with st.container(border=True):
        numeric_cols = ["Retard_min", "Duree_pause_min", "Depassement_pause_min", "Depart_anticipe_min"]
        st.dataframe(
            T.style_matrice(df_affiche[display_cols], status_col="Statut", numeric_cols=numeric_cols),
            use_container_width=True, hide_index=True,
        )

    st.download_button(
        "📥 Télécharger la matrice (CSV)",
        data=df_affiche[display_cols].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"matrice_comportementale_{report_date.isoformat()}.csv",
        mime="text/csv",
    )

    if st.session_state.agents_report_df is not None:
        with st.expander("ℹ️ Détail des états (source : Agents report)"):
            st.dataframe(st.session_state.agents_report_df, use_container_width=True, hide_index=True)


# ==========================================================================
# ONGLET 2 — TIMELINE & DISTRIBUTION DES PAUSES
# ==========================================================================

with tab2:
    timeline = pause_result.timeline

    st.markdown("### Cumul des pauses par créneau (plateau entier)")
    cumul_par_slot = (
        timeline.groupby("Slot", as_index=False)["Pause_min"].sum().sort_values("Slot")
    )
    # Tri chronologique correct (00:00 -> 23:30) plutôt qu'alphabétique
    ordre_slots = P.SLOTS_AM_24H + P.SLOTS_PM_24H
    cumul_par_slot["Slot"] = pd.Categorical(cumul_par_slot["Slot"], categories=ordre_slots, ordered=True)
    cumul_par_slot = cumul_par_slot.sort_values("Slot")

    fig1 = px.bar(
        cumul_par_slot,
        x="Slot",
        y="Pause_min",
        labels={"Slot": "Créneau", "Pause_min": "Cumul pause (min)"},
        title="Cumul de pause consommée par tranche de 30 minutes — plateau entier",
        color="Pause_min",
        color_continuous_scale=[T.ACCENT, T.PRIMARY],
        template=T.PLOTLY_TEMPLATE_NAME,
    )
    fig1.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False)
    fig1.update_traces(hovertemplate="Créneau %{x}<br>Pause cumulée : %{y:.0f} min<extra></extra>")
    with st.container(border=True):
        st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### Timeline individuelle")
    agents_avec_login = matrice[["Login", "Nom"]].drop_duplicates()
    agents_avec_login["label"] = agents_avec_login["Login"] + " — " + agents_avec_login["Nom"].fillna("")
    choix = st.selectbox("Choisir un agent", options=agents_avec_login["label"].tolist())
    login_choisi = choix.split(" — ")[0] if choix else None

    if login_choisi:
        tl_agent = timeline[timeline["Login"] == login_choisi].copy()
        tl_agent["Slot"] = pd.Categorical(tl_agent["Slot"], categories=ordre_slots, ordered=True)
        tl_agent = tl_agent.sort_values("Slot")
        fig2 = px.bar(
            tl_agent,
            x="Slot",
            y="Pause_min",
            labels={"Slot": "Créneau", "Pause_min": "Pause (min)"},
            title=f"Consommation de pause — {choix}",
            color="Pause_min",
            color_continuous_scale=[T.ACCENT, T.PRIMARY],
            template=T.PLOTLY_TEMPLATE_NAME,
        )
        fig2.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False)
        fig2.update_traces(hovertemplate="Créneau %{x}<br>Pause : %{y:.0f} min<extra></extra>")
        with st.container(border=True):
            st.plotly_chart(fig2, use_container_width=True)


# ==========================================================================
# ONGLET 3 — FICHE INDIVIDUELLE DE RECADRAGE
# ==========================================================================

with tab3:
    agents_liste = matrice[["Login", "Nom"]].drop_duplicates()
    agents_liste["label"] = agents_liste["Login"] + " — " + agents_liste["Nom"].fillna("")
    choix_fiche = st.selectbox(
        "Sélectionner un agent", options=agents_liste["label"].tolist(), key="fiche_select"
    )
    login_fiche = choix_fiche.split(" — ")[0] if choix_fiche else None

    if login_fiche:
        row = matrice[matrice["Login"] == login_fiche].iloc[0]

        st.markdown(f"## {row['Nom']}  \n**Login :** {row['Login']} — **Matricule :** {row['Matricule_RH']}")
        st.markdown(f"**Statut du jour :** {T.status_badge(row['Statut'])}", unsafe_allow_html=True)

        retard = row["Retard_min"] or 0
        depassement = row["Depassement_pause_min"] or 0
        depart_anticipe_ignore = bool(row["Depart_anticipe_ignore"])
        depart_anticipe = row["Depart_anticipe_min"] or 0

        with st.container(border=True):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown("#### 🕐 Prise de poste")
                st.write(f"Prévu : {row['Debut_prevu']}")
                st.write(f"Réel : {row['Arrivee_reelle']}")
                T.render_kpi_row([{
                    "label": "Retard", "value": round(float(retard)), "icon": "⏱️",
                    "color": T.DANGER if retard > 0 else T.SUCCESS, "suffix": " min", "alert": retard > 0,
                }], height=110)
            with col_b:
                st.markdown("#### ☕ Pauses")
                st.write(f"Durée pause réelle : {row['Duree_pause_min'] or 0:.0f} min")
                st.write(f"Pause autorisée : {pause_autorisee} min")
                T.render_kpi_row([{
                    "label": "Dépassement", "value": round(float(depassement)), "icon": "☕",
                    "color": T.DANGER if depassement > 0 else T.SUCCESS, "suffix": " min", "alert": depassement > 0,
                }], height=110)
            with col_c:
                st.markdown("#### 🏁 Fin de poste")
                st.write(f"Prévu : {row['Fin_prevu']}")
                st.write(f"Réel : {row['Depart_reel']}")
                if depart_anticipe_ignore:
                    st.info("Non évalué (export temps réel)")
                else:
                    T.render_kpi_row([{
                        "label": "Départ anticipé", "value": round(float(depart_anticipe)), "icon": "🚪",
                        "color": T.DANGER if depart_anticipe > 0 else T.SUCCESS, "suffix": " min",
                        "alert": depart_anticipe > 0,
                    }], height=110)

        st.markdown("---")
        st.markdown("### 📝 Synthèse d'entretien (copier / coller)")
        texte = A.synthese_recadrage(row, report_date)
        st.text_area("Synthèse", value=texte, height=260, label_visibility="collapsed")
        st.download_button(
            "📥 Télécharger la synthèse (.txt)",
            data=texte.encode("utf-8"),
            file_name=f"synthese_{row['Login']}_{report_date.isoformat()}.txt",
            mime="text/plain",
        )

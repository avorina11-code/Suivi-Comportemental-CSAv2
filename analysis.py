# -*- coding: utf-8 -*-
"""
analysis.py
===========
Logique métier : croise le planning théorique du jour avec les données
réelles issues du "Agents pause report" Vocalcom, calcule les écarts
(retard, dépassement de pause, départ anticipé) et classe chaque agent
selon un statut comportemental.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd


def _minutes_between(t1: Optional[dt.time], t2: Optional[dt.time]) -> Optional[float]:
    """Retourne (t2 - t1) en minutes, ou None si une des deux valeurs manque."""
    if t1 is None or t2 is None:
        return None
    d1 = dt.datetime.combine(dt.date.today(), t1)
    d2 = dt.datetime.combine(dt.date.today(), t2)
    return (d2 - d1).total_seconds() / 60.0


def build_matrice_comportementale(
    shift_today: pd.DataFrame,
    pause_summary: pd.DataFrame,
    *,
    seuil_retard_min: int = 5,
    pause_autorisee_min: int = 30,
    seuil_depassement_alerte_min: int = 5,
    export_temps_reel: bool = False,
    heure_extraction: Optional[dt.time] = None,
) -> pd.DataFrame:
    """Construit la matrice comportementale complète, une ligne par agent
    présent dans le planning du jour.

    Règles appliquées (voir cahier des charges) :
      - Agent planifié mais absent du rapport Vocalcom -> Absence non justifiée
      - Agent noté OFF/CONGE/... au planning -> Non planifié (statut neutre)
      - Retard = Arrivée réelle - Début prévu (compté seulement si > seuil)
      - Dépassement pause = Pause réelle - Pause autorisée
      - Départ anticipé = Fin prévue - Départ réel (ignoré si export en
        cours de journée et fin de poste prévue > heure d'extraction)
    """
    df = shift_today.merge(
        pause_summary, on="Login", how="left", suffixes=("", "_reel")
    )

    records = []
    for _, r in df.iterrows():
        statut_planning = r["Statut_planning"]
        a_pointe = pd.notna(r.get("Arrivee_reelle"))

        retard_min = None
        depassement_pause_min = None
        depart_anticipe_min = None
        depart_anticipe_ignore = False

        if statut_planning != "TRAVAIL":
            statut_comportemental = "⚪ Non planifié (OFF/Congé)"
        elif not a_pointe:
            statut_comportemental = "🚫 Absence non justifiée"
        else:
            debut_prevu = r.get("Debut_prevu")
            fin_prevu = r.get("Fin_prevu")
            arrivee = r.get("Arrivee_reelle")
            depart = r.get("Depart_reel")
            duree_pause_reelle = r.get("Duree_pause_min")

            # --- Retard à la prise de poste ---
            ecart_arrivee = _minutes_between(debut_prevu, arrivee)
            if ecart_arrivee is not None and ecart_arrivee > seuil_retard_min:
                retard_min = round(ecart_arrivee, 1)
            else:
                retard_min = 0.0

            # --- Dépassement de pause ---
            if pd.notna(duree_pause_reelle):
                depassement_pause_min = round(duree_pause_reelle - pause_autorisee_min, 1)
                if depassement_pause_min < 0:
                    depassement_pause_min = 0.0
            else:
                depassement_pause_min = 0.0

            # --- Départ anticipé (avec correction export "temps réel") ---
            fin_ignoree = (
                export_temps_reel
                and heure_extraction is not None
                and fin_prevu is not None
                and fin_prevu > heure_extraction
            )
            if fin_ignoree:
                depart_anticipe_ignore = True
                depart_anticipe_min = 0.0
            else:
                ecart_depart = _minutes_between(depart, fin_prevu)
                if ecart_depart is not None and ecart_depart > 0:
                    depart_anticipe_min = round(ecart_depart, 1)
                else:
                    depart_anticipe_min = 0.0

            # --- Classification ---
            ecart_majeur = (
                (retard_min or 0) > seuil_retard_min
                or (depassement_pause_min or 0) > seuil_depassement_alerte_min
                or (depart_anticipe_min or 0) > 0
            )
            ecart_mineur = (
                not ecart_majeur
                and ((retard_min or 0) > 0 or (depassement_pause_min or 0) > 0)
            )
            if ecart_majeur:
                statut_comportemental = "🔴 Écart à recadrer"
            elif ecart_mineur:
                statut_comportemental = "🟠 Écart mineur"
            else:
                statut_comportemental = "🟢 Conforme"

        records.append(
            {
                "Matricule_RH": r.get("Matricule_RH"),
                "Login": r.get("Login"),
                "Nom": r.get("Nom") or r.get("Nom_Vocalcom"),
                "Statut_planning": statut_planning,
                "Debut_prevu": r.get("Debut_prevu"),
                "Fin_prevu": r.get("Fin_prevu"),
                "Arrivee_reelle": r.get("Arrivee_reelle"),
                "Depart_reel": r.get("Depart_reel"),
                "Retard_min": retard_min,
                "Duree_pause_min": r.get("Duree_pause_min"),
                "Depassement_pause_min": depassement_pause_min,
                "Depart_anticipe_min": depart_anticipe_min,
                "Depart_anticipe_ignore": depart_anticipe_ignore,
                "Duree_travail_min": r.get("Duree_travail_min"),
                "Statut": statut_comportemental,
            }
        )

    return pd.DataFrame(records)


def synthese_recadrage(row: pd.Series, date_jour: dt.date) -> str:
    """Génère un texte de synthèse prêt à copier/coller pour un entretien
    de recadrage RH/Superviseur, à partir d'une ligne de la matrice
    comportementale.
    """
    nom = row.get("Nom") or "Agent"
    login = row.get("Login")
    date_str = date_jour.strftime("%d/%m/%Y") if date_jour else "date inconnue"

    lignes = [f"Entretien de recadrage du {date_str} — {nom} (Login {login})", ""]

    retard = row.get("Retard_min") or 0
    depassement = row.get("Depassement_pause_min") or 0
    depart_anticipe = row.get("Depart_anticipe_min") or 0

    if retard > 0:
        lignes.append(
            f"• Prise de poste : retard de {retard:.0f} min constaté sur les logs "
            f"Vocalcom (arrivée prévue {row.get('Debut_prevu')}, arrivée réelle "
            f"{row.get('Arrivee_reelle')})."
        )
    else:
        lignes.append("• Prise de poste : conforme au planning, aucun retard constaté.")

    if depassement > 0:
        lignes.append(
            f"• Pauses : dépassement de {depassement:.0f} min par rapport au temps "
            f"de pause autorisé (durée totale de pause relevée : "
            f"{row.get('Duree_pause_min', 0):.0f} min)."
        )
    else:
        lignes.append("• Pauses : consommation de pause conforme au temps autorisé.")

    if row.get("Depart_anticipe_ignore"):
        lignes.append(
            "• Fin de poste : non évaluée (export réalisé en cours de journée, "
            "avant la fin de poste prévue)."
        )
    elif depart_anticipe > 0:
        lignes.append(
            f"• Fin de poste : départ anticipé de {depart_anticipe:.0f} min avant "
            f"l'heure de fin de poste prévue ({row.get('Fin_prevu')}, dernier "
            f"pointage réel {row.get('Depart_reel')})."
        )
    else:
        lignes.append("• Fin de poste : conforme au planning, aucun départ anticipé constaté.")

    lignes.append("")
    lignes.append(f"Statut global retenu : {row.get('Statut')}.")
    lignes.append(
        "Ces éléments sont issus des relevés automatiques Vocalcom et doivent être "
        "présentés à l'agent à titre d'échange contradictoire avant toute décision RH."
    )
    return "\n".join(lignes)

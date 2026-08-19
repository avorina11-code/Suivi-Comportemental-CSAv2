# Adhérence Planning & Suivi Comportemental — CSA

Application Streamlit qui croise le **Planning Hebdo** (théorique) avec les
**exports bruts Vocalcom** (réel) pour identifier automatiquement retards,
dépassements de pause, départs anticipés et absences non justifiées.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Structure du projet

```
adherence_csa/
├── app.py          # Interface Streamlit (sidebar, 3 onglets)
├── parsers.py       # Lecture & parsing de tous les fichiers Excel
├── analysis.py       # Logique métier : calcul des écarts et statuts
├── requirements.txt
└── README.md
```

## Fichiers en entrée

| Fichier | Statut | Format accepté | Contenu utilisé |
|---|---|---|---|
| **Planning Hebdo** | Obligatoire | `.xlsx` (feuille `Planning_Hebdo`) | Heures théoriques de début/fin par jour et par agent |
| **Agents pause report** | Obligatoire | `.xls` ou `.xlsx` | Arrivée/départ réels, durée de pause, timeline des pauses par tranche de 30 min |
| **Agents report** | Optionnel | `.xls` ou `.xlsx` | Détail des états (Attente, Traitement, Post-travail, Pause…) |
| **Agents activities by dates** | Optionnel | `.xls` ou `.xlsx` | Résumé arrivée/départ en secours |

### ⚠️ Détection automatique du type de fichier — pourquoi c'est important

En pratique, **le nom des fichiers exportés depuis Vocalcom ne correspond
pas toujours à leur contenu réel** (constaté sur des exports réels lors du
développement de cette application : un fichier nommé
`distribution_de_pause_agent.xls` contenait en réalité un export
`Agents activities by dates`, et inversement).

C'est pourquoi l'application **ignore complètement le nom du fichier** et
détecte le type réel de chaque export en scannant son contenu (titre
`"Agents pause report"` / `"Agents report"` / `"Agents activities by
dates"` présent dans les 15 premières lignes). Le résultat de cette
détection est affiché dans la barre latérale après import, pour que
l'utilisateur puisse vérifier que le fichier attendu a bien été reconnu.

### Format `.xls` (Excel 97-2003 / OLE)

Les exports Vocalcom/Crystal Reports sont très souvent au format binaire
`.xls`. La librairie `openpyxl` ne sait pas lire ce format : l'application
utilise donc `xlrd` en repli automatique (voir `parsers.load_sheet_grid`).
Assurez-vous que `xlrd>=2.0.1` est bien installé (inclus dans
`requirements.txt`).

## Règles de calcul

- **Retard** = Arrivée réelle − Début prévu, compté seulement s'il dépasse
  le seuil de retard toléré (paramétrable, 5 min par défaut).
- **Dépassement de pause** = Durée de pause réelle (issue du bloc
  "Résumé" du pause report, la source la plus fiable) − Pause autorisée
  (30 min par défaut).
- **Départ anticipé** = Fin prévue − Départ réel. Si le toggle **"Export
  en cours de journée (Temps Réel)"** est activé, ce calcul est ignoré
  pour tout agent dont la fin de poste prévue est postérieure à l'heure
  d'extraction renseignée (pour éviter les faux départs anticipés sur un
  export réalisé en milieu de journée).
- **Statut** :
  - 🔴 Écart à recadrer : retard > seuil, ou dépassement pause > seuil
    d'alerte, ou départ anticipé avéré.
  - 🟠 Écart mineur : écart présent mais sous les seuils d'alerte.
  - 🟢 Conforme.
  - 🚫 Absence non justifiée : planifié mais aucun pointage Vocalcom.
  - ⚪ Non planifié : OFF / CONGÉ / PERMISSION / FORMATION / CM au planning.

## Limitations connues (documentées dans le code)

1. **Shifts éclatés** (ex: `09:00/16:00` dans le planning) : l'application
   prend la borne globale (première heure de début, dernière heure de
   fin) plutôt que de gérer chaque sous-créneau séparément.
2. **Tranche 00:00 (a.m.)** du pause report : un artefact d'export connu
   fait que le libellé `"a.m."` écrase la valeur de cette toute première
   tranche horaire dans le fichier source ; elle est donc toujours
   comptée à 0 minute de pause (impact négligeable en pratique, les
   centres d'appels n'opérant généralement pas avant 6h du matin).
3. **`Agents activities by dates`** : dans cet export, les graphiques à
   barres empilées d'origine (répartition Attente/Traitement/Pause) ne
   sont pas récupérables comme données tabulaires — seuls Arrivée/Départ
   et durée de travail totale restent exploitables ; le nom de l'agent y
   est en plus tronqué (largeur de colonne fixe), donc la jointure se
   fait uniquement sur le Login.

## Personnalisation rapide

- Seuils (retard, pause autorisée, seuil d'alerte dépassement) réglables
  directement dans la barre latérale, aucune modification de code requise.
- Pour ajouter une nouvelle règle de statut, modifier
  `analysis.build_matrice_comportementale`.
- Pour supporter un nouveau format d'export Vocalcom, ajouter une entrée
  dans `parsers.REPORT_TITLES` et une fonction `parse_xxx(grid)` dédiée.

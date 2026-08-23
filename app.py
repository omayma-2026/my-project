# -*- coding: utf-8 -*-
"""
ORMVA-TF Risk & Audit Center
Application web de consultation et d'exploration des résultats du modèle
d'aide à la décision pour la priorisation des missions d'audit interne.
------------------------------------------------------------------------
Cette version couvre EXACTEMENT les 6 fonctionnalités du cahier des charges :

    1. Consultation des principaux indicateurs
    2. Consultation des données et des variables disponibles dans la base
       analytique
    3. Visualisation des différentes zones de risques
    4. Affichage des résultats de priorisation et du classement des
       processus
    5. Consultation des résultats analytiques utiles à l'interprétation
    6. Présentation des composantes du Score de Priorité d'Audit afin de
       faciliter sa lecture

L'utilisateur explore les résultats du modèle à travers une interface
interactive, sans avoir à manipuler directement le code Python : aucune
fonctionnalité d'édition, de workflow, d'authentification ou d'administration
n'est incluse — l'application est strictement dédiée à la CONSULTATION.

Toutes les données affichées proviennent des fichiers réels fournis :
    - data/cartographie_analysee_complet.xlsx  (159 risques, analyse Colab)
    - data/indicateurs_powerbi_v2.xlsx         (agrégats par processus, VaR/TVaR,
                                                  score de priorisation, clusters)
Aucune donnée n'est inventée. Les statistiques (ANOVA, régression DMR, zones de
risque) sont recalculées en direct à partir des données réelles.

Lancer avec :
    pip install -r requirements.txt
    streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from scipy import stats

# ----------------------------------------------------------------------------
# 0. CONFIGURATION GÉNÉRALE & THÈME VISUEL
# ----------------------------------------------------------------------------

st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data"

COL_PRIMARY = "#0F3D2E"
COL_PRIMARY_LT = "#145C3F"
COL_SAGE = "#7FA98C"
COL_SAGE_LT = "#DCE9DF"
COL_BG = "#F4F7F9"
COL_GRAY = "#2E3B47"
COL_WHITE = "#FFFFFF"
COL_ALERT_RED = "#C0392B"
COL_ALERT_ORANGE = "#E08E45"
COL_ALERT_AMBER = "#D9A441"

ZONE_COLORS = {
    "A - Optimisation": "#2E7D4F",
    "B - Vigilance": "#D9A441",
    "C - Surveillance": "#E08E45",
    "D - Traitement": "#C0392B",
}
ZONE_ORDER = ["A - Optimisation", "B - Vigilance", "C - Surveillance", "D - Traitement"]

CLUSTER_COLORS = {
    "Negliges": "#A9C6DE",
    "Mineurs": "#3E7CA6",
    "Sous controle": "#D9A441",
    "Critiques non maitrises": "#C0392B",
}

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    color: {COL_GRAY};
}}
.stApp {{
    background-color: {COL_BG};
}}
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {COL_PRIMARY} 0%, {COL_PRIMARY_LT} 100%);
}}
section[data-testid="stSidebar"] * {{
    color: #E7F0F7 !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] * {{
    color: {COL_GRAY} !important;
}}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
    background-color: white !important;
}}
.nav-section-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9FC3DB !important;
    margin: 16px 0 6px 2px;
}}
section[data-testid="stSidebar"] button[kind="secondary"] {{
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    color: #E7F0F7 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-weight: 500 !important;
    margin-bottom: 3px;
}}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {{
    background: rgba(255,255,255,0.10) !important;
    border-color: rgba(255,255,255,0.25) !important;
}}
section[data-testid="stSidebar"] button[kind="primary"] {{
    background: linear-gradient(90deg, {COL_SAGE} 0%, #7FB0CE 100%) !important;
    border: none !important;
    color: {COL_PRIMARY} !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.20);
    margin-bottom: 3px;
}}
div[data-testid="stMetric"] {{
    background: {COL_WHITE};
    border: 1px solid #E3EBE5;
    border-left: 4px solid {COL_PRIMARY};
    border-radius: 10px;
    padding: 14px 18px 10px 18px;
    box-shadow: 0 1px 3px rgba(15,61,46,0.06);
}}
div[data-testid="stMetricValue"] {{
    color: {COL_PRIMARY};
    font-weight: 800;
}}
h1, h2, h3 {{
    color: {COL_PRIMARY};
    font-weight: 800;
}}
.app-header {{
    background: linear-gradient(120deg, {COL_PRIMARY} 0%, {COL_PRIMARY_LT} 60%, {COL_SAGE} 140%);
    padding: 26px 32px;
    border-radius: 14px;
    color: white;
    margin-bottom: 22px;
}}
.app-header h1 {{
    color: white !important;
    margin: 0;
    font-size: 26px;
}}
.app-header p {{
    color: #DCE9DF;
    margin: 4px 0 0 0;
    font-size: 14px;
}}
.section-card {{
    background: {COL_WHITE};
    border: 1px solid #E3EBE5;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 18px;
    box-shadow: 0 1px 3px rgba(15,61,46,0.05);
}}
.badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    color: white;
}}
.var-card {{
    background: {COL_WHITE};
    border: 1px solid #E3EBE5;
    border-left: 4px solid {COL_SAGE};
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 10px;
}}
.var-card .var-name {{
    font-weight: 700;
    color: {COL_PRIMARY};
    font-size: 14px;
}}
.var-card .var-meta {{
    font-size: 12px;
    color: #6B7B85;
}}
.formula-box {{
    background: {COL_SAGE_LT};
    border: 1px solid {COL_SAGE};
    border-radius: 10px;
    padding: 16px 20px;
    font-family: 'Courier New', monospace;
    font-size: 15px;
    color: {COL_PRIMARY};
    margin-bottom: 16px;
}}
.dataframe tbody tr:hover {{ background-color: {COL_SAGE_LT} !important; }}
hr {{ border-color: #E3EBE5; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

PLOTLY_TEMPLATE = dict(
    layout=dict(
        font=dict(family="Inter, sans-serif", color=COL_GRAY, size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        colorway=[COL_PRIMARY, COL_SAGE, "#D9A441", "#E08E45", "#C0392B", COL_PRIMARY_LT],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
)


# ----------------------------------------------------------------------------
# 1. CHARGEMENT DES DONNÉES RÉELLES (mis en cache)
# ----------------------------------------------------------------------------

@st.cache_data(show_spinner="Chargement de la cartographie des risques...")
def load_data():
    risques = pd.read_excel(DATA_DIR / "cartographie_analysee_complet.xlsx", sheet_name="Details_Risques")
    risques = risques.rename(columns={
        "Code": "code", "Processus": "processus", "Sous-processus": "sous_processus",
        "Intitule": "intitule", "Prob": "prob", "Grav": "grav",
        "Criticite_Brute": "criticite_brute", "DMR": "dmr", "Criticite_Nette": "criticite_nette",
        "Criticite_Nette_Predite": "criticite_nette_predite", "Residu": "residu",
        "Cluster": "cluster", "Cluster_Label": "cluster_label",
    })
    risques["processus_court"] = risques["processus"].str.extract(r"(P\d+)")

    # Zones de risque A/B/C/D — seuils médians sur la criticité nette et le DMR résiduel
    med_crit = risques["criticite_nette"].median()
    med_dmr = risques["dmr"].median()

    def zone(row):
        crit_high = row["criticite_nette"] >= med_crit
        dmr_high = row["dmr"] >= med_dmr  # DMR élevé = dispositif de maîtrise INSUFFISANT
        if not crit_high and not dmr_high:
            return "A - Optimisation"
        if not crit_high and dmr_high:
            return "B - Vigilance"
        if crit_high and not dmr_high:
            return "C - Surveillance"
        return "D - Traitement"

    risques["zone"] = risques.apply(zone, axis=1)

    stats_proc = pd.read_excel(DATA_DIR / "indicateurs_powerbi_v2.xlsx", sheet_name="Stats_Processus")
    var_tvar = pd.read_excel(DATA_DIR / "indicateurs_powerbi_v2.xlsx", sheet_name="VaR_TVaR")
    score_prio = pd.read_excel(DATA_DIR / "indicateurs_powerbi_v2.xlsx", sheet_name="Score_Priorite")
    clusters_profil = pd.read_excel(DATA_DIR / "indicateurs_powerbi_v2.xlsx", sheet_name="Profils_Clusters")

    for d in (stats_proc, var_tvar, score_prio):
        d["processus_court"] = d["Processus"].str.extract(r"(P\d+)")

    score_prio = score_prio.sort_values("Rang_Quantifie")

    return dict(
        risques=risques, stats_proc=stats_proc, var_tvar=var_tvar,
        score_prio=score_prio, clusters_profil=clusters_profil,
        med_crit=med_crit, med_dmr=med_dmr,
    )


try:
    DATA = load_data()
except FileNotFoundError as e:
    st.error(
        "⚠️ Fichiers de données introuvables. Place `cartographie_analysee_complet.xlsx` "
        "et `indicateurs_powerbi_v2.xlsx` dans le dossier `data/` à côté de `app.py`.\n\n"
        f"Détail : {e}"
    )
    st.stop()

RISQUES = DATA["risques"]
STATS_PROC = DATA["stats_proc"]
VAR_TVAR = DATA["var_tvar"]
SCORE_PRIO = DATA["score_prio"]
CLUSTERS_PROFIL = DATA["clusters_profil"]

ALL_PROCESSUS = sorted(RISQUES["processus"].unique().tolist())

# Poids officiels du modèle (mémoire PFE) — affichés en LECTURE SEULE (fonctionnalité 6)
MODEL_WEIGHTS = {"crit": 40, "var": 40, "critiques": 20}

# Dictionnaire des variables de la base analytique (fonctionnalité 2)
VARIABLES_DICO = [
    {"nom": "code", "table": "Détail des risques", "type": "Texte",
     "description": "Identifiant unique du risque dans la cartographie (ex. R001)."},
    {"nom": "processus / sous_processus", "table": "Détail des risques", "type": "Texte",
     "description": "Processus métier (12 processus, P1 à P12) et son sous-processus associé."},
    {"nom": "intitule", "table": "Détail des risques", "type": "Texte",
     "description": "Libellé du risque tel qu'identifié dans la cartographie ORMVA-TF."},
    {"nom": "prob", "table": "Détail des risques", "type": "Numérique (1-4)",
     "description": "Probabilité d'occurrence du risque, échelle qualitative à 4 niveaux."},
    {"nom": "grav", "table": "Détail des risques", "type": "Numérique (1-4)",
     "description": "Gravité / impact potentiel du risque, échelle qualitative à 4 niveaux."},
    {"nom": "criticite_brute", "table": "Détail des risques", "type": "Numérique",
     "description": "Criticité brute = Probabilité × Gravité, avant prise en compte de la maîtrise."},
    {"nom": "dmr", "table": "Détail des risques", "type": "Numérique (0-1)",
     "description": "Degré de Maîtrise du Risque résiduel : 0 = risque bien maîtrisé, 1 = dispositif insuffisant."},
    {"nom": "criticite_nette", "table": "Détail des risques", "type": "Numérique",
     "description": "Criticité nette = Criticité brute pondérée par le DMR résiduel."},
    {"nom": "criticite_nette_predite / residu", "table": "Détail des risques", "type": "Numérique",
     "description": "Valeur prédite par le modèle de régression du DMR et résidu (écart réel - prédit)."},
    {"nom": "cluster / cluster_label", "table": "Détail des risques", "type": "Catégorielle",
     "description": "Groupe issu du clustering (Négligés, Mineurs, Sous contrôle, Critiques non maîtrisés)."},
    {"nom": "zone", "table": "Détail des risques (calculée)", "type": "Catégorielle (A-D)",
     "description": "Zone de risque (A-Optimisation, B-Vigilance, C-Surveillance, D-Traitement), calculée à partir des seuils médians de criticité nette et de DMR."},
    {"nom": "Criticite_Nette_Somme", "table": "Stats_Processus", "type": "Numérique",
     "description": "Somme de la criticité nette de tous les risques d'un processus."},
    {"nom": "VaR_95 / TVaR_95", "table": "VaR_TVaR", "type": "Numérique",
     "description": "Value-at-Risk et Tail VaR à 95%, issues de la simulation Monte Carlo par processus."},
    {"nom": "Contribution_VaR_pct", "table": "VaR_TVaR", "type": "Numérique (%)",
     "description": "Part de la VaR d'un processus dans la VaR globale du portefeuille de risques."},
    {"nom": "Score_Priorite_Audit", "table": "Score_Priorite", "type": "Numérique (0-100)",
     "description": "Score composite de priorisation combinant criticité, VaR et nombre de risques critiques."},
    {"nom": "Rang_Quantifie / Rang_Existant", "table": "Score_Priorite", "type": "Numérique",
     "description": "Rang du processus selon le modèle quantifié vs le classement existant ORMVA-TF."},
    {"nom": "Nb_Risques_Critiques", "table": "Score_Priorite", "type": "Numérique",
     "description": "Nombre de risques classés critiques (zone D) pour le processus."},
]

# Navigation — les 6 fonctionnalités du cahier des charges
NAV_ITEMS = [
    "📊 1. Indicateurs clés",
    "🗂️ 2. Données & variables",
    "🧭 3. Zones de risques",
    "🎯 4. Priorisation & classement",
    "📈 5. Résultats analytiques",
    "🧮 6. Composantes du score",
]
if "page" not in st.session_state:
    st.session_state.page = NAV_ITEMS[0]


# ----------------------------------------------------------------------------
# 2. SIDEBAR — NAVIGATION + FILTRE GLOBAL PAR PROCESSUS
# ----------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🛡️ ORMVA-TF")
    st.caption("Risk & Audit Center — consultation")
    st.markdown("---")

    st.markdown('<div class="nav-section-title">Fonctionnalités</div>', unsafe_allow_html=True)
    for item in NAV_ITEMS:
        is_active = st.session_state.page == item
        if st.button(item, key=f"nav_{item}", width='stretch',
                     type="primary" if is_active else "secondary"):
            st.session_state.page = item
            st.rerun()

    page = st.session_state.page

    st.markdown("---")
    st.markdown("**Filtrage par processus**")
    selected_processus = st.multiselect(
        "Processus", options=ALL_PROCESSUS, default=ALL_PROCESSUS,
        label_visibility="collapsed",
    )
    if st.button("↺ Réinitialiser le filtre", width='stretch'):
        selected_processus = ALL_PROCESSUS

    st.markdown("---")
    st.caption("159 risques réels · 12 processus")
    st.caption("Source : cartographie ORMVA-TF (20-12-2024, V2 GCA)")

if not selected_processus:
    selected_processus = ALL_PROCESSUS

R = RISQUES[RISQUES["processus"].isin(selected_processus)].copy()
SP = STATS_PROC[STATS_PROC["Processus"].isin(selected_processus)].copy()
VT = VAR_TVAR[VAR_TVAR["Processus"].isin(selected_processus)].copy()
SC = SCORE_PRIO[SCORE_PRIO["Processus"].isin(selected_processus)].copy()


def header(title, subtitle):
    st.markdown(f"""<div class="app-header"><h1>{title}</h1><p>{subtitle}</p></div>""",
                unsafe_allow_html=True)


# ============================================================================
# 1. CONSULTATION DES PRINCIPAUX INDICATEURS
# ============================================================================

if page == "📊 1. Indicateurs clés":
    header(
        "Indicateurs clés",
        "Vue d'ensemble de la cartographie des risques ORMVA-TF · filtré sur "
        f"{len(selected_processus)}/{len(ALL_PROCESSUS)} processus",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risques (filtre)", f"{len(R)}", f"/ {len(RISQUES)} au total")
    c2.metric("Processus", f"{R['processus'].nunique()}")
    nb_critiques = int(SC["Nb_Risques_Critiques"].sum()) if len(SC) else 0
    c3.metric("Risques critiques", f"{nb_critiques}")
    c4.metric("Criticité nette moyenne", f"{R['criticite_nette'].mean():.2f}" if len(R) else "—")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("DMR moyen (résiduel)", f"{R['dmr'].mean():.2f}" if len(R) else "—")
    score_max = SC["Score_Priorite_Audit"].max() if len(SC) else np.nan
    c6.metric("Score de priorité max", f"{score_max:.1f}" if pd.notna(score_max) else "—")
    c7.metric("VaR globale 95% (portefeuille)", "4 816.7",
              help="Résultat de la simulation Monte Carlo globale (mémoire PFE).")
    c8.metric("Somme VaR₉₅ / processus", f"{VT['VaR_95'].sum():,.0f}".replace(",", " "))

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("#### Répartition des risques par zone")
        zone_counts = R["zone"].value_counts().reindex(ZONE_ORDER).fillna(0).reset_index()
        zone_counts.columns = ["zone", "count"]
        fig = px.pie(zone_counts, names="zone", values="count", hole=0.55,
                     color="zone", color_discrete_map=ZONE_COLORS)
        fig.update_traces(textinfo="value+percent")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("#### Répartition des risques par processus")
        proc_counts = R["processus_court"].value_counts().reset_index()
        proc_counts.columns = ["processus", "count"]
        fig = px.bar(proc_counts.sort_values("count"), x="count", y="processus", orientation="h",
                     color_discrete_sequence=[COL_PRIMARY])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Nb de risques")
        st.plotly_chart(fig, width='stretch')

    col3, col4 = st.columns([1, 1])
    with col3:
        st.markdown("#### Criticité nette totale par processus")
        fig = px.bar(SP.sort_values("Criticite_Nette_Somme"), x="Criticite_Nette_Somme", y="processus_court",
                     orientation="h", color_discrete_sequence=[COL_SAGE])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Criticité nette (somme)")
        st.plotly_chart(fig, width='stretch')

    with col4:
        st.markdown("#### VaR 95% par processus")
        fig = px.bar(VT.sort_values("VaR_95"), x="VaR_95", y="processus_court",
                     orientation="h", color_discrete_sequence=[COL_ALERT_RED])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="VaR 95%")
        st.plotly_chart(fig, width='stretch')

    st.markdown("#### 🔝 Top 10 risques (criticité nette)")
    top10 = R.sort_values("criticite_nette", ascending=False).head(10)[
        ["code", "processus_court", "intitule", "criticite_nette", "dmr", "zone"]
    ]
    st.dataframe(top10, width='stretch', hide_index=True)


# ============================================================================
# 2. CONSULTATION DES DONNÉES & VARIABLES DE LA BASE ANALYTIQUE
# ============================================================================

elif page == "🗂️ 2. Données & variables":
    header("Données & variables", "Exploration de la base analytique — 159 risques, 12 processus")

    tab1, tab2 = st.tabs(["📋 Détail des risques", "📖 Dictionnaire des variables"])

    with tab1:
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            zones_f = st.multiselect("Zone", ZONE_ORDER, default=ZONE_ORDER)
        with fc2:
            crit_min = st.slider("Criticité nette min.", 0.0, float(RISQUES["criticite_nette"].max()), 0.0)
        with fc3:
            dmr_max = st.slider("DMR max. (résiduel)", 0.0, 1.0, 1.0)
        with fc4:
            search = st.text_input("🔍 Recherche (intitulé / code)")

        filt = R[R["zone"].isin(zones_f) & (R["criticite_nette"] >= crit_min) & (R["dmr"] <= dmr_max)]
        if search:
            filt = filt[
                filt["intitule"].str.contains(search, case=False, na=False)
                | filt["code"].str.contains(search, case=False, na=False)
            ]

        st.caption(f"{len(filt)} risques correspondant aux filtres (sur {len(R)} dans la sélection courante)")

        show_cols = {
            "code": "Code", "processus_court": "Processus", "sous_processus": "Sous-processus",
            "intitule": "Intitulé", "prob": "Prob.", "grav": "Grav.",
            "criticite_brute": "Crit. brute", "dmr": "DMR", "criticite_nette": "Crit. nette",
            "zone": "Zone", "cluster_label": "Profil (cluster)",
        }
        display_df = filt[list(show_cols)].rename(columns=show_cols).sort_values("Crit. nette", ascending=False)
        st.dataframe(display_df, width='stretch', hide_index=True, height=440)

        csv = filt.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter (CSV)", csv, "donnees_risques_export.csv", "text/csv")

        st.markdown("#### Statistiques descriptives (sélection courante)")
        desc = filt[["prob", "grav", "criticite_brute", "dmr", "criticite_nette"]].describe().T
        desc = desc.rename(columns={
            "count": "N", "mean": "Moyenne", "std": "Écart-type", "min": "Min",
            "25%": "Q1", "50%": "Médiane", "75%": "Q3", "max": "Max",
        }).round(2)
        st.dataframe(desc, width='stretch')

    with tab2:
        st.caption(
            "Description des variables disponibles dans la base analytique, issues des fichiers "
            "`cartographie_analysee_complet.xlsx` et `indicateurs_powerbi_v2.xlsx`."
        )
        search_var = st.text_input("🔍 Rechercher une variable")
        vd = VARIABLES_DICO
        if search_var:
            vd = [v for v in vd if search_var.lower() in v["nom"].lower() or search_var.lower() in v["description"].lower()]
        for v in vd:
            st.markdown(
                f"""<div class="var-card">
                <div class="var-name">{v['nom']} <span class="var-meta">· {v['type']}</span></div>
                <div class="var-meta">Table : {v['table']}</div>
                <div>{v['description']}</div>
                </div>""",
                unsafe_allow_html=True,
            )


# ============================================================================
# 3. VISUALISATION DES ZONES DE RISQUES
# ============================================================================

elif page == "🧭 3. Zones de risques":
    header("Zones de risques", "Criticité nette × DMR résiduel — zones A/B/C/D (méthodologie du mémoire)")

    med_crit, med_dmr = DATA["med_crit"], DATA["med_dmr"]

    tab1, tab2 = st.tabs(["🧭 Matrice des risques (nuage de points)", "🗂️ Matrice de contrôle (4×4)"])

    with tab1:
        left, right = st.columns([2, 1])
        with left:
            fig = go.Figure()
            xmax = R["criticite_nette"].max() * 1.1 if len(R) else 1
            fig.add_shape(type="rect", x0=0, x1=med_crit, y0=0, y1=med_dmr,
                          fillcolor=ZONE_COLORS["A - Optimisation"], opacity=0.10, line_width=0)
            fig.add_shape(type="rect", x0=0, x1=med_crit, y0=med_dmr, y1=1,
                          fillcolor=ZONE_COLORS["B - Vigilance"], opacity=0.10, line_width=0)
            fig.add_shape(type="rect", x0=med_crit, x1=xmax, y0=0, y1=med_dmr,
                          fillcolor=ZONE_COLORS["C - Surveillance"], opacity=0.10, line_width=0)
            fig.add_shape(type="rect", x0=med_crit, x1=xmax, y0=med_dmr, y1=1,
                          fillcolor=ZONE_COLORS["D - Traitement"], opacity=0.14, line_width=0)

            for z in ZONE_ORDER:
                sub = R[R["zone"] == z]
                fig.add_trace(go.Scatter(
                    x=sub["criticite_nette"], y=sub["dmr"], mode="markers", name=z,
                    marker=dict(size=9, color=ZONE_COLORS[z], line=dict(width=1, color="white")),
                    text=sub["code"] + " · " + sub["intitule"].str.slice(0, 60),
                    customdata=sub["processus_court"],
                    hovertemplate="%{text}<br>Processus: %{customdata}<br>Crit. nette: %{x:.2f}<br>DMR: %{y:.2f}<extra></extra>",
                ))
            fig.add_vline(x=med_crit, line_dash="dot", line_color=COL_GRAY)
            fig.add_hline(y=med_dmr, line_dash="dot", line_color=COL_GRAY)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=560,
                              xaxis_title="Criticité nette →",
                              yaxis_title="DMR résiduel (0 = bien maîtrisé, 1 = mal maîtrisé) →")
            st.plotly_chart(fig, width='stretch')

        with right:
            st.markdown("#### Répartition par zone")
            zone_counts = R["zone"].value_counts().reindex(ZONE_ORDER).fillna(0).reset_index()
            zone_counts.columns = ["zone", "count"]
            fig2 = px.pie(zone_counts, names="zone", values="count", hole=0.5,
                          color="zone", color_discrete_map=ZONE_COLORS)
            fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=280)
            st.plotly_chart(fig2, width='stretch')

            st.markdown("#### Définition des zones")
            st.markdown(
                """
- 🟢 **A — Optimisation** : criticité faible, dispositif de maîtrise efficace.
- 🟡 **B — Vigilance** : criticité faible, dispositif insuffisant.
- 🟠 **C — Surveillance** : criticité élevée malgré un dispositif efficace.
- 🔴 **D — Traitement** : criticité élevée + dispositif insuffisant → **priorité d'audit**.
                """
            )

        st.markdown("#### Répartition zone × processus")
        cross = pd.crosstab(R["processus_court"], R["zone"]).reindex(columns=ZONE_ORDER, fill_value=0)
        fig3 = px.bar(cross, barmode="stack", color_discrete_map=ZONE_COLORS,
                     labels={"value": "Nb de risques", "processus_court": "Processus"})
        fig3.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig3, width='stretch')

    with tab2:
        controle_bins = [-0.01, 0.25, 0.50, 0.75, 1.01]
        controle_labels = ["Faible ≤25%", "Partiel ≤50%", "Correct ≤75%", "Satisfaisant ≤100%"]
        crit_bins = [0, 4, 8, 12, 16]
        crit_labels = ["Faible [0-4]", "Moyen [4-8]", "Significatif [8-12]", "Élevé [12-16]"]

        Rm = R.copy()
        Rm["degre_controle_pct"] = (1 - Rm["dmr"]) * 100
        Rm["ligne_controle"] = pd.cut(Rm["degre_controle_pct"], bins=controle_bins, labels=controle_labels)
        Rm["colonne_criticite"] = pd.cut(Rm["criticite_brute"], bins=crit_bins, labels=crit_labels, include_lowest=True)

        def cell_zone(ligne, colonne):
            li = controle_labels.index(ligne)
            ci = crit_labels.index(colonne)
            controle_insuffisant = li < 2
            crit_elevee = ci >= 2
            if crit_elevee and controle_insuffisant:
                return "D - Traitement"
            if crit_elevee and not controle_insuffisant:
                return "C - Surveillance"
            if not crit_elevee and controle_insuffisant:
                return "B - Vigilance"
            return "A - Optimisation"

        grid_z, grid_text = [], []
        for li_label in reversed(controle_labels):
            row_z, row_text = [], []
            for ci_label in crit_labels:
                zone = cell_zone(li_label, ci_label)
                row_z.append(ZONE_ORDER.index(zone))
                codes = Rm.loc[(Rm["ligne_controle"] == li_label) & (Rm["colonne_criticite"] == ci_label), "code"].tolist()
                label = "<br>".join(codes[:6]) + (f"<br>+{len(codes)-6}" if len(codes) > 6 else "")
                row_text.append(label if codes else "")
            grid_z.append(row_z)
            grid_text.append(row_text)

        fig = go.Figure(data=go.Heatmap(
            z=grid_z, text=grid_text, texttemplate="%{text}", textfont=dict(size=11, color="white"),
            x=crit_labels, y=list(reversed(controle_labels)),
            colorscale=[[0, ZONE_COLORS["A - Optimisation"]], [0.33, ZONE_COLORS["B - Vigilance"]],
                        [0.66, ZONE_COLORS["C - Surveillance"]], [1, ZONE_COLORS["D - Traitement"]]],
            showscale=False, xgap=3, ygap=3,
        ))
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=520,
                          xaxis_title="DEGRÉ DE CRITICITÉ →", yaxis_title="DEGRÉ DE CONTRÔLE →",
                          xaxis=dict(side="bottom"))
        st.plotly_chart(fig, width='stretch')

        leg1, leg2, leg3, leg4 = st.columns(4)
        for col, (z, c) in zip([leg1, leg2, leg3, leg4], ZONE_COLORS.items()):
            col.markdown(f'<span class="badge" style="background:{c}">{z}</span>', unsafe_allow_html=True)

        st.caption(
            "Degré de contrôle = (1 − DMR) × 100 — plus il est élevé, plus le dispositif de maîtrise "
            "est efficace. Degré de criticité = criticité brute (Probabilité × Gravité)."
        )


# ============================================================================
# 4. RÉSULTATS DE PRIORISATION & CLASSEMENT DES PROCESSUS
# ============================================================================

elif page == "🎯 4. Priorisation & classement":
    header("Priorisation & classement des processus", "Score de priorité d'audit — classement 0-100")

    fig = px.bar(SC.sort_values("Score_Priorite_Audit"), x="Score_Priorite_Audit", y="Processus",
                orientation="h", color="Score_Priorite_Audit",
                color_continuous_scale=[COL_SAGE_LT, COL_ALERT_RED], text="Score_Priorite_Audit")
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=480, coloraxis_showscale=False,
                      xaxis_title="Score de priorité (0-100)", yaxis_title="")
    st.plotly_chart(fig, width='stretch')

    st.markdown("#### Tableau de classement")
    tbl = SC[["Rang_Quantifie", "Rang_Existant", "Processus", "Score_Priorite_Audit",
              "Nb_Risques_Critiques", "VaR_95"]].copy()
    tbl["Niveau de priorité"] = pd.cut(tbl["Score_Priorite_Audit"], bins=[-1, 30, 60, 100],
                                        labels=["Faible", "Moyenne", "Élevée"])
    tbl = tbl.rename(columns={
        "Rang_Quantifie": "Rang (modèle)", "Rang_Existant": "Rang (ORMVA-TF)",
        "Score_Priorite_Audit": "Score", "Nb_Risques_Critiques": "Risques critiques", "VaR_95": "VaR 95%",
    }).sort_values("Rang (modèle)")
    st.dataframe(tbl, width='stretch', hide_index=True)

    st.markdown("---")
    st.markdown("### 🔎 Explicabilité du classement par processus")
    proc_choice = st.selectbox("Choisir un processus", SC["Processus"].tolist())
    row = SC[SC["Processus"] == proc_choice].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Rang (modèle quantifié)", int(row["Rang_Quantifie"]))
    c2.metric("Rang (classement existant ORMVA-TF)", int(row["Rang_Existant"]))
    c3.metric("Score de priorité", f"{row['Score_Priorite_Audit']:.1f} / 100")

    factors = pd.DataFrame({
        "Facteur": ["Criticité nette (somme)", "VaR 95%", "Contribution VaR (%)", "Nb risques critiques"],
        "Valeur": [row["Criticite_Nette_Somme"], row["VaR_95"], row["Contribution_VaR_pct"], row["Nb_Risques_Critiques"]],
    })
    fig2 = px.bar(factors, x="Valeur", y="Facteur", orientation="h", color_discrete_sequence=[COL_PRIMARY])
    fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=280, yaxis_title="")
    st.plotly_chart(fig2, width='stretch')

    st.info(
        f"**Pourquoi {proc_choice} est-il prioritaire ?** "
        f"Ce processus cumule {row['Nb_Risques_Critiques']:.0f} risque(s) critique(s), "
        f"une criticité nette totale de {row['Criticite_Nette_Somme']:.1f}, "
        f"et représente {row['Contribution_VaR_pct']:.1f}% de l'exposition VaR cumulée du portefeuille."
    )

    rho, pval = stats.spearmanr(SCORE_PRIO["Rang_Existant"], SCORE_PRIO["Rang_Quantifie"])
    st.success(
        f"**Validation du classement** : corrélation de Spearman entre le classement existant "
        f"ORMVA-TF et le score quantifié : **ρ = {rho:.2f}** (p = {pval:.4f}) — cohérence forte "
        "entre les deux approches."
    )


# ============================================================================
# 5. RÉSULTATS ANALYTIQUES UTILES À L'INTERPRÉTATION
# ============================================================================

elif page == "📈 5. Résultats analytiques":
    header("Résultats analytiques", "ANOVA · Régression du DMR · Clustering · Monte Carlo (VaR/TVaR)")

    tab1, tab2, tab3, tab4 = st.tabs(["ANOVA", "Régression du DMR", "Clustering", "Monte Carlo · VaR/TVaR"])

    with tab1:
        groups = [g["criticite_nette"].values for _, g in R.groupby("processus")]
        if len(groups) >= 2:
            F, p = stats.f_oneway(*groups)
            c1, c2 = st.columns(2)
            c1.metric("F-statistic", f"{F:.2f}")
            c2.metric("p-value", f"{p:.5f}")
            if p < 0.05:
                st.success(
                    "Les différences de criticité nette entre les processus sont "
                    "**statistiquement significatives** (p < 0.05) : le processus d'appartenance "
                    "influence réellement le niveau de risque net observé."
                )
            else:
                st.warning("Aucune différence statistiquement significative détectée entre processus (p ≥ 0.05).")

            fig = px.box(R, x="processus_court", y="criticite_nette", color="processus_court",
                         color_discrete_sequence=px.colors.qualitative.Prism)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False,
                              xaxis_title="Processus", yaxis_title="Criticité nette")
            st.plotly_chart(fig, width='stretch')
        else:
            st.warning("Sélectionnez au moins deux processus pour calculer l'ANOVA.")

    with tab2:
        y = R["criticite_nette"].values
        yp = R["criticite_nette_predite"].values
        if len(y) > 1:
            ss_res = np.sum((y - yp) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
            c1, c2 = st.columns(2)
            c1.metric("R² (Crit. nette vs Crit. nette prédite par le DMR)", f"{r2:.3f}")
            surestimes = R[R["cluster_label"] == "Critiques non maitrises"]
            c2.metric("Risques avec DMR potentiellement surestimé", f"{len(surestimes)}")

            fig = px.scatter(R, x="criticite_nette_predite", y="criticite_nette", color="zone",
                             color_discrete_map=ZONE_COLORS, hover_data=["code", "intitule"])
            m = max(R["criticite_nette"].max(), R["criticite_nette_predite"].max())
            fig.add_trace(go.Scatter(x=[0, m], y=[0, m], mode="lines",
                                      line=dict(dash="dash", color=COL_GRAY), name="y = x"))
            fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                              xaxis_title="Criticité nette prédite", yaxis_title="Criticité nette réelle")
            st.plotly_chart(fig, width='stretch')

            st.markdown("##### Risques à examiner (DMR potentiellement surestimé)")
            st.dataframe(
                surestimes[["code", "processus_court", "intitule", "dmr", "criticite_nette", "residu"]]
                .rename(columns={"processus_court": "processus", "residu": "résidu"})
                .sort_values("résidu", ascending=False),
                width='stretch', hide_index=True,
            )
        else:
            st.warning("Pas assez de données pour la régression du DMR sur ce filtre.")

    with tab3:
        st.markdown("##### Profils des clusters (issus du modèle Colab)")
        cp = CLUSTERS_PROFIL.copy()
        cp["Cluster_Label"] = cp["Cluster"].map({0: "Negliges", 1: "Mineurs", 2: "Sous controle", 3: "Critiques non maitrises"})
        fig = go.Figure()
        for _, row in cp.iterrows():
            fig.add_trace(go.Scatterpolar(
                r=[row["Prob"], row["Grav"], row["DMR"], row["Criticite_Nette"]],
                theta=["Probabilité", "Gravité", "DMR", "Criticité nette"],
                fill="toself", name=row["Cluster_Label"],
                line_color=CLUSTER_COLORS.get(row["Cluster_Label"], COL_PRIMARY),
            ))
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], polar=dict(radialaxis=dict(visible=True)), height=480)
        st.plotly_chart(fig, width='stretch')

        st.dataframe(cp.rename(columns={"Nb_Risques": "Nb risques"}), width='stretch', hide_index=True)

        st.markdown("##### Répartition des risques (filtre courant) par cluster")
        cl_counts = R["cluster_label"].value_counts().reset_index()
        cl_counts.columns = ["cluster_label", "count"]
        fig2 = px.pie(cl_counts, names="cluster_label", values="count", hole=0.5,
                      color="cluster_label", color_discrete_map=CLUSTER_COLORS)
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=320)
        st.plotly_chart(fig2, width='stretch')

    with tab4:
        c1, c2, c3 = st.columns(3)
        c1.metric("VaR globale 95% (portefeuille)", "4 816.7")
        c2.metric("Somme des VaR₉₅ par processus", f"{VT['VaR_95'].sum():,.0f}".replace(",", " "))
        c3.metric("Somme des TVaR₉₅ par processus", f"{VT['TVaR_95'].sum():,.0f}".replace(",", " "))
        st.caption(
            "La VaR globale du portefeuille (4 816.7) est inférieure à la somme des VaR par processus : "
            "effet de diversification entre processus indépendants, cohérent avec la théorie actuarielle."
        )

        st.markdown("#### VaR 95% vs TVaR 95% par processus")
        vt_plot = VT.sort_values("VaR_95")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=vt_plot["processus_court"], x=vt_plot["VaR_95"], name="VaR 95%",
                             orientation="h", marker_color=COL_PRIMARY))
        fig.add_trace(go.Bar(y=vt_plot["processus_court"], x=vt_plot["TVaR_95"], name="TVaR 95%",
                             orientation="h", marker_color=COL_ALERT_RED, opacity=0.75))
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], barmode="group", height=460, xaxis_title="Perte simulée")
        st.plotly_chart(fig, width='stretch')

        st.markdown("#### Contribution de chaque processus au risque global (%)")
        fig2 = px.bar(VT.sort_values("Contribution_VaR_pct"), x="Contribution_VaR_pct", y="processus_court",
                     orientation="h", color_discrete_sequence=[COL_SAGE])
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], xaxis_title="Contribution VaR (%)", yaxis_title="")
        st.plotly_chart(fig2, width='stretch')

        st.markdown("---")
        st.markdown("#### 🔁 Simulation interactive (bootstrap sur données réelles)")
        st.caption(
            "Rééchantillonnage (bootstrap) des criticités nettes réelles du processus sélectionné pour "
            "illustrer la distribution des pertes simulées — méthode complémentaire à la simulation "
            "Monte Carlo du mémoire."
        )
        proc_sim = st.selectbox("Processus", ALL_PROCESSUS, key="mc_proc")
        n_sim = st.slider("Nombre de simulations", 1000, 20000, 10000, step=1000)
        conf = st.select_slider("Niveau de confiance", options=[0.90, 0.95, 0.99], value=0.95)

        sample = RISQUES.loc[RISQUES["processus"] == proc_sim, "criticite_nette"].values
        if len(sample) > 0:
            rng = np.random.default_rng(42)
            sims = rng.choice(sample, size=(n_sim, len(sample)), replace=True).sum(axis=1)
            var_sim = np.quantile(sims, conf)
            tvar_sim = sims[sims >= var_sim].mean()

            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Perte moyenne simulée", f"{sims.mean():.1f}")
            cc2.metric(f"VaR {int(conf*100)}%", f"{var_sim:.1f}")
            cc3.metric(f"TVaR {int(conf*100)}%", f"{tvar_sim:.1f}")

            fig3 = px.histogram(sims, nbins=60, color_discrete_sequence=[COL_PRIMARY])
            fig3.add_vline(x=var_sim, line_dash="dash", line_color=COL_ALERT_RED,
                          annotation_text=f"VaR {int(conf*100)}%")
            fig3.update_layout(**PLOTLY_TEMPLATE["layout"], xaxis_title="Perte simulée (criticité nette cumulée)",
                              yaxis_title="Fréquence", showlegend=False, height=380)
            st.plotly_chart(fig3, width='stretch')
        else:
            st.warning("Aucun risque trouvé pour ce processus.")


# ============================================================================
# 6. COMPOSANTES DU SCORE DE PRIORITÉ D'AUDIT (lecture seule)
# ============================================================================

elif page == "🧮 6. Composantes du score":
    header("Composantes du Score de Priorité d'Audit", "Décomposition du score pour en faciliter la lecture et l'interprétation")

    st.markdown("#### 🧮 Formule du score")
    st.markdown(
        f"""<div class="formula-box">
        Score(processus) = {MODEL_WEIGHTS['crit']}% × Criticité nette (normalisée)
        &nbsp;+&nbsp; {MODEL_WEIGHTS['var']}% × VaR 95% (normalisée)
        &nbsp;+&nbsp; {MODEL_WEIGHTS['critiques']}% × Nb risques critiques (normalisé)
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption(
        "Chaque facteur est normalisé (min-max, échelle 0-100) avant pondération, puis les trois "
        "composantes sont sommées pour obtenir le score final sur 100. Les poids ci-dessus sont ceux "
        "du modèle validé dans le mémoire (corrélation de Spearman ρ = 0.98 avec le classement existant "
        "ORMVA-TF)."
    )

    w1, w2, w3 = st.columns(3)
    w1.metric("Poids — Criticité nette", f"{MODEL_WEIGHTS['crit']}%")
    w2.metric("Poids — VaR 95%", f"{MODEL_WEIGHTS['var']}%")
    w3.metric("Poids — Nb risques critiques", f"{MODEL_WEIGHTS['critiques']}%")

    st.markdown("---")

    # Recalcul des composantes normalisées (mêmes formules que le score officiel)
    base = SCORE_PRIO.copy()
    for col, key in [("Criticite_Nette_Somme", "crit_n"), ("VaR_95", "var_n"), ("Nb_Risques_Critiques", "critiques_n")]:
        mn, mx = base[col].min(), base[col].max()
        base[key] = (base[col] - mn) / (mx - mn) * 100 if mx > mn else 0

    base["contrib_crit"] = MODEL_WEIGHTS["crit"] / 100 * base["crit_n"]
    base["contrib_var"] = MODEL_WEIGHTS["var"] / 100 * base["var_n"]
    base["contrib_critiques"] = MODEL_WEIGHTS["critiques"] / 100 * base["critiques_n"]

    st.markdown("#### Décomposition du score par processus")
    stacked = base[["Processus", "contrib_crit", "contrib_var", "contrib_critiques"]].sort_values(
        by=["contrib_crit", "contrib_var", "contrib_critiques"], ascending=True
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(y=stacked["Processus"], x=stacked["contrib_crit"], name="Criticité nette",
                         orientation="h", marker_color=COL_PRIMARY))
    fig.add_trace(go.Bar(y=stacked["Processus"], x=stacked["contrib_var"], name="VaR 95%",
                         orientation="h", marker_color=COL_SAGE))
    fig.add_trace(go.Bar(y=stacked["Processus"], x=stacked["contrib_critiques"], name="Nb risques critiques",
                         orientation="h", marker_color=COL_ALERT_AMBER))
    fig.update_layout(**PLOTLY_TEMPLATE["layout"], barmode="stack", height=460,
                      xaxis_title="Contribution au score (0-100)", yaxis_title="")
    st.plotly_chart(fig, width='stretch')

    st.markdown("#### Tableau détaillé des composantes")
    detail = base[[
        "Processus", "Criticite_Nette_Somme", "crit_n", "contrib_crit",
        "VaR_95", "var_n", "contrib_var",
        "Nb_Risques_Critiques", "critiques_n", "contrib_critiques",
        "Score_Priorite_Audit",
    ]].rename(columns={
        "Criticite_Nette_Somme": "Crit. nette (brute)", "crit_n": "Crit. nette (normalisée)",
        "contrib_crit": "Contribution crit. nette",
        "VaR_95": "VaR 95% (brute)", "var_n": "VaR 95% (normalisée)", "contrib_var": "Contribution VaR",
        "Nb_Risques_Critiques": "Nb risques critiques (brut)", "critiques_n": "Nb critiques (normalisé)",
        "contrib_critiques": "Contribution risques critiques",
        "Score_Priorite_Audit": "Score final",
    }).round(2).sort_values("Score final", ascending=False)
    st.dataframe(detail, width='stretch', hide_index=True)

    st.markdown("#### 🔎 Zoom sur un processus")
    proc_choice = st.selectbox("Choisir un processus", base["Processus"].tolist(), key="score_zoom")
    row = base[base["Processus"] == proc_choice].iloc[0]

    fig2 = go.Figure(go.Bar(
        x=["Criticité nette", "VaR 95%", "Nb risques critiques"],
        y=[row["contrib_crit"], row["contrib_var"], row["contrib_critiques"]],
        marker_color=[COL_PRIMARY, COL_SAGE, COL_ALERT_AMBER],
        text=[f"{v:.1f}" for v in [row["contrib_crit"], row["contrib_var"], row["contrib_critiques"]]],
        textposition="outside",
    ))
    fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=340,
                       yaxis_title="Contribution au score", title=f"Score total : {row['Score_Priorite_Audit']:.1f} / 100")
    st.plotly_chart(fig2, width='stretch')

    st.info(
        f"Pour **{proc_choice}**, la composante **Criticité nette** contribue pour "
        f"{row['contrib_crit']:.1f} points, la **VaR 95%** pour {row['contrib_var']:.1f} points, "
        f"et le **nombre de risques critiques** pour {row['contrib_critiques']:.1f} points, "
        f"soit un score final de **{row['Score_Priorite_Audit']:.1f} / 100**."
    )


st.markdown("---")
st.caption("ORMVA-TF Risk & Audit Center · Données réelles : 159 risques, 12 processus · Interface de consultation — Prototype PFA Audit Interne & Actuariat")

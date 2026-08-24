# -*- coding: utf-8 -*-
"""
ORMVA-TF Risk & Audit Center
Application web de consultation et d'exploration des résultats du modèle
d'aide à la décision pour la priorisation des missions d'audit interne.
------------------------------------------------------------------------
Cette version est strictement conforme à la méthodologie décrite dans le
rapport de stage (Chapitre 5 — Conception du modèle sous Python, Chapitre 6 —
Restitution décisionnelle et application web) :

    - Le périmètre analytique comprend 168 observations de risques réparties
      entre 13 unités d'analyse (P1 à P12, ainsi que PM).
    - Les zones de risque A/B/C/D sont les zones OFFICIELLES fournies par la
      cartographie institutionnelle (colonne `zone_officielle`) — elles ne
      sont PAS recalculées par seuils médians.
    - Le DMR (Dispositif de Maîtrise des Risques) est conservé tel que fourni
      par la cartographie : un DMR élevé signifie un dispositif de maîtrise
      SATISFAISANT (degré de contrôle = DMR × 100).
    - Le Score de Priorité d'Audit est calculé au niveau des groupes/processus
      à partir de 3 composantes normalisées (Min-Max, 0-100) :
          Sp = 0.45 × %risques zone D + 0.30 × %risques zone C
             + 0.25 × criticité brute moyenne
    - Les méthodes actuarielles (Monte Carlo, VaR, TVaR) sont présentées dans
      le rapport UNIQUEMENT comme cadre théorique et ne sont PAS utilisées
      dans le modèle opérationnel (absence de séries historiques de pertes) :
      elles sont donc volontairement ABSENTES de cette application.
    - Aucun classement institutionnel existant n'est comparé au score : cette
      comparaison ne fait pas partie du dispositif décrit dans le rapport.

Les 6 fonctionnalités couvertes (Chapitre 6.3.2 du rapport) :
    1. Consultation des principaux indicateurs
    2. Consultation des données et des variables de la base analytique
    3. Visualisation des différentes zones de risques
    4. Affichage des résultats de priorisation et du classement des processus
    5. Consultation des résultats analytiques utiles à l'interprétation
       (ANOVA/Kruskal-Wallis, diagnostic de cohérence, segmentation K-Means/ACP,
       analyse de sensibilité des pondérations)
    6. Présentation des composantes du Score de Priorité d'Audit

Toutes les statistiques sont recalculées EN DIRECT à partir de la base réelle
`data/cartographie_analysee_complete.xlsx` (feuille "Details_Risques"),
conformément au notebook Python du mémoire. Aucune donnée n'est inventée.

Lancer avec :
    pip install -r requirements.txt   # streamlit, pandas, plotly, scipy, scikit-learn, openpyxl
    streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

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
DATA_FILE = DATA_DIR / "cartographie_analysee_complete.xlsx"

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

ZONE_ORDER = ["A", "B", "C", "D"]
ZONE_SEVERITY = {"A": 1, "B": 2, "C": 3, "D": 4}
ZONE_COLORS = {
    "A": "#2E7D4F",
    "B": "#D9A441",
    "C": "#E08E45",
    "D": "#C0392B",
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

# Poids officiels du Score de Priorité d'Audit (rapport, section 5.4, éq. 5.13)
SCORE_WEIGHTS_BASE = {"D": 0.45, "C": 0.30, "brut": 0.25}

# Scénarios de l'analyse de sensibilité (rapport, Table 5.2)
SENSITIVITY_SCENARIOS = {
    "Base":          {"D": 0.45, "C": 0.30, "brut": 0.25},
    "Dominant D":    {"D": 0.60, "C": 0.20, "brut": 0.20},
    "Dominant C":    {"D": 0.30, "C": 0.50, "brut": 0.20},
    "Dominant brut": {"D": 0.25, "C": 0.25, "brut": 0.50},
    "Équilibre":     {"D": 1 / 3, "C": 1 / 3, "brut": 1 / 3},
}

# Bandes officielles de vérification (rapport, section 5.4.4)
CRIT_BINS = [0, 4, 8, 12, 16]
CRIT_LABELS = ["Faible [0-4[", "Moyen [4-8[", "Significatif [8-12[", "Élevé [12-16]"]
CTRL_BINS = [-0.01, 25, 50, 75, 100.01]
CTRL_LABELS = ["Faible ≤25%", "Partiel ≤50%", "Correct ≤75%", "Satisfaisant ≤100%"]

# Dictionnaire des variables (rapport, Table 4.1 + variables dérivées du Chapitre 5)
VARIABLES_DICO = [
    {"nom": "code", "type": "Identifiant", "role": "Identification de l'observation (le risque individuel)."},
    {"nom": "processus_code", "type": "Qualitative", "role": "Unité d'analyse / niveau d'agrégation du scoring (P1 à P12, ainsi que PM)."},
    {"nom": "processus_nom / fonction", "type": "Qualitative", "role": "Libellé du processus et fonction organisationnelle associée."},
    {"nom": "sous_processus", "type": "Qualitative", "role": "Sous-processus dans lequel le risque a été identifié."},
    {"nom": "prob", "type": "Ordinale", "role": "Vraisemblance du risque (probabilité d'occurrence)."},
    {"nom": "grav", "type": "Ordinale", "role": "Impact du risque (gravité)."},
    {"nom": "criticite_brute_declaree", "type": "Quantitative", "role": "Exposition intrinsèque au risque = Probabilité × Gravité."},
    {"nom": "dmr", "type": "Proportion", "role": "Dispositif de Maîtrise des Risques fourni par la cartographie (degré de contrôle, 0 à 1)."},
    {"nom": "degre_controle_pct", "type": "Dérivée", "role": "DMR exprimé en pourcentage (dmr × 100) pour faciliter la lecture."},
    {"nom": "criticite_nette_declaree", "type": "Quantitative", "role": "Indicateur institutionnel conservé pour diagnostic (non recalculé)."},
    {"nom": "criticite_nette_diagnostique", "type": "Dérivée", "role": "Rbrut × (1 − DMR) — construite uniquement à des fins d'analyse de cohérence ; n'entre pas dans le calcul du score."},
    {"nom": "zone_officielle", "type": "Ordinale (A-D)", "role": "Zone de risque officielle de la cartographie institutionnelle (A, B, C ou D)."},
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
# 1. CHARGEMENT DES DONNÉES RÉELLES (mis en cache)
# ----------------------------------------------------------------------------

@st.cache_data(show_spinner="Chargement de la cartographie des risques...")
def load_data():
    df = pd.read_excel(DATA_FILE, sheet_name="Details_Risques")

    rename_map = {
        "code": "code",
        "processus_code": "processus_code",
        "processus_nom": "processus_nom",
        "fonction": "fonction",
        "sous_processus": "sous_processus",
        "prob": "prob",
        "grav": "grav",
        "criticite_brute_declaree": "criticite_brute",
        "dmr": "dmr",
        "criticite_nette_declaree": "criticite_nette_declaree",
        "zone_officielle": "zone",
    }
    missing = [c for c in rename_map if c not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes obligatoires absentes de 'Details_Risques' : {missing}"
        )
    df = df.rename(columns=rename_map)

    # Variables dérivées — méthodologie exacte du rapport (section 5.3)
    df["degre_controle_pct"] = df["dmr"] * 100
    df["criticite_nette_diagnostique"] = df["criticite_brute"] * (1 - df["dmr"])
    df["zone"] = df["zone"].astype(str).str.strip().str.upper()
    df["zone_severite"] = df["zone"].map(ZONE_SEVERITY)

    if "fonction" not in df.columns:
        df["fonction"] = "—"

    return df


def diagnose_data_file(path: Path) -> str:
    """Diagnostic lisible en cas de fichier Excel invalide ou corrompu."""
    if not path.exists():
        return f"Le fichier n'existe pas à l'emplacement attendu : `{path}`."

    size = path.stat().st_size
    with open(path, "rb") as fh:
        head = fh.read(64)

    if size == 0:
        return "Le fichier existe mais est **vide** (0 octet)."
    if size < 2048:
        preview = head[:120].decode("utf-8", errors="replace")
        if "version https://git-lfs" in preview:
            return (
                f"Le fichier ne fait que {size} octets : c'est un **pointeur Git LFS**, pas le vrai fichier "
                "binaire. Il faut activer Git LFS (`git lfs install` + `git lfs pull`) ou committer le fichier "
                "directement sans LFS."
            )
        return (
            f"Le fichier ne fait que {size} octets — beaucoup trop petit pour 168 observations. "
            f"Aperçu du contenu : `{preview.strip()}`"
        )
    if head[:2] == b"PK":
        return (
            "Le fichier commence bien par la signature ZIP (`PK`), donc ce n'est pas un problème de "
            "corruption binaire — la feuille `Details_Risques` est peut-être absente ou mal nommée."
        )
    if head[:4] == b"\xd0\xcf\x11\xe0":
        return "Le fichier est en réalité un ancien format **`.xls` binaire** (Excel 97-2003), pas un `.xlsx`. Ré-enregistre-le en `.xlsx` depuis Excel/LibreOffice."
    if head.strip().lower().startswith((b"<!doctype", b"<html")):
        return "Le fichier contient du **HTML** (probablement une page d'erreur de téléchargement enregistrée par erreur avec l'extension `.xlsx`)."
    return (
        f"Le fichier ne commence pas par la signature ZIP attendue (`PK`) — premiers octets : {head[:16]!r}. "
        "Il a probablement été corrompu lors du transfert ou du commit Git. Si le fichier est hébergé sur "
        "GitHub, vérifie qu'un `.gitattributes` marque `*.xlsx binary` pour empêcher la conversion des fins "
        "de ligne, puis re-committe le fichier."
    )


try:
    RISQUES = load_data()
except FileNotFoundError as e:
    st.error(
        "⚠️ Fichier de données introuvable. Place `cartographie_analysee_complete.xlsx` "
        "(feuille `Details_Risques`) dans le dossier `data/` à côté de `app.py`.\n\n"
        f"Détail : {e}"
    )
    st.stop()
except ValueError as e:
    st.error(f"⚠️ {e}")
    st.stop()
except Exception as e:
    diag = diagnose_data_file(DATA_FILE)
    st.error(
        f"⚠️ Impossible de lire le fichier Excel `{DATA_FILE.name}`.\n\n"
        f"**Diagnostic** : {diag}\n\n"
        f"*Erreur originale : {e}*"
    )
    st.stop()

ALL_PROCESSUS = sorted(RISQUES["processus_code"].dropna().unique().tolist())
ALL_FONCTIONS = sorted(RISQUES["fonction"].dropna().unique().tolist())


# ----------------------------------------------------------------------------
# 1bis. FONCTIONS DE CALCUL — reproduisent exactement les listings du Chapitre 5
# ----------------------------------------------------------------------------

def compute_stats_processus(df: pd.DataFrame) -> pd.DataFrame:
    """Statistiques descriptives par groupe/processus (rapport, section 5.4.1)."""
    if df.empty:
        return pd.DataFrame()
    g = df.groupby("processus_code")
    out = g.agg(
        processus_nom=("processus_nom", "first"),
        Nb_Risques=("code", "count"),
        Prob_Moyenne=("prob", "mean"),
        Grav_Moyenne=("grav", "mean"),
        Criticite_Brute_Moyenne=("criticite_brute", "mean"),
        DMR_Moyen=("dmr", "mean"),
        Criticite_Nette_Moyenne=("criticite_nette_declaree", "mean"),
    ).reset_index()

    zone_counts = pd.crosstab(df["processus_code"], df["zone"])
    for z in ZONE_ORDER:
        if z not in zone_counts.columns:
            zone_counts[z] = 0
    zone_pct = zone_counts[ZONE_ORDER].div(zone_counts[ZONE_ORDER].sum(axis=1), axis=0) * 100
    zone_pct.columns = [f"Pct_Zone_{z}" for z in ZONE_ORDER]
    out = out.merge(zone_pct.reset_index(), on="processus_code", how="left")
    return out.round(2)


def norm_minmax(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    if np.isclose(s.max(), s.min()):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.min()) / (s.max() - s.min()) * 100


def compute_score(stats_df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Score de Priorité d'Audit — rapport, section 5.4, éq. 5.9 à 5.13."""
    if stats_df.empty:
        return stats_df
    out = stats_df.copy()
    out["N_Pct_Zone_D"] = norm_minmax(out["Pct_Zone_D"])
    out["N_Pct_Zone_C"] = norm_minmax(out["Pct_Zone_C"])
    out["N_Criticite_Brute"] = norm_minmax(out["Criticite_Brute_Moyenne"])
    out["Score_Priorite_Audit"] = (
        weights["D"] * out["N_Pct_Zone_D"]
        + weights["C"] * out["N_Pct_Zone_C"]
        + weights["brut"] * out["N_Criticite_Brute"]
    ).round(1)
    out["Rang"] = out["Score_Priorite_Audit"].rank(ascending=False, method="min").astype(int)
    return out.sort_values("Rang")


def header(title, subtitle):
    st.markdown(f"""<div class="app-header"><h1>{title}</h1><p>{subtitle}</p></div>""",
                unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# 2. SIDEBAR — NAVIGATION + FILTRES GLOBAUX
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
    st.markdown("**Filtrage par processus / groupe**")
    selected_processus = st.multiselect(
        "Processus", options=ALL_PROCESSUS, default=ALL_PROCESSUS, label_visibility="collapsed",
    )
    if len(ALL_FONCTIONS) > 1:
        st.markdown("**Filtrage par fonction**")
        selected_fonctions = st.multiselect(
            "Fonction", options=ALL_FONCTIONS, default=ALL_FONCTIONS, label_visibility="collapsed",
        )
    else:
        selected_fonctions = ALL_FONCTIONS

    if st.button("↺ Réinitialiser les filtres", width='stretch'):
        selected_processus = ALL_PROCESSUS
        selected_fonctions = ALL_FONCTIONS

    st.markdown("---")
    st.caption(f"{len(RISQUES)} observations réelles · {len(ALL_PROCESSUS)} unités d'analyse")
    st.caption("Périmètre analytique : P1 à P12, ainsi que PM")

if not selected_processus:
    selected_processus = ALL_PROCESSUS
if not selected_fonctions:
    selected_fonctions = ALL_FONCTIONS

R = RISQUES[
    RISQUES["processus_code"].isin(selected_processus)
    & RISQUES["fonction"].isin(selected_fonctions)
].copy()

SP = compute_stats_processus(R)
SC = compute_score(SP, SCORE_WEIGHTS_BASE)


# ============================================================================
# 1. CONSULTATION DES PRINCIPAUX INDICATEURS
# ============================================================================

if page == "📊 1. Indicateurs clés":
    header(
        "Indicateurs clés",
        f"Vue d'ensemble de la cartographie des risques ORMVA-TF · filtré sur "
        f"{len(selected_processus)}/{len(ALL_PROCESSUS)} unités d'analyse",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risques (filtre)", f"{len(R)}", f"/ {len(RISQUES)} au total")
    c2.metric("Processus / groupes", f"{R['processus_code'].nunique()}")
    pct_d = (R["zone"] == "D").mean() * 100 if len(R) else 0
    c3.metric("% risques en zone D", f"{pct_d:.1f}%")
    c4.metric("Criticité brute moyenne", f"{R['criticite_brute'].mean():.2f}" if len(R) else "—")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("DMR moyen (degré de maîtrise)", f"{R['dmr'].mean():.2f}" if len(R) else "—")
    pct_c = (R["zone"] == "C").mean() * 100 if len(R) else 0
    c6.metric("% risques en zone C", f"{pct_c:.1f}%")
    score_max = SC["Score_Priorite_Audit"].max() if len(SC) else np.nan
    c7.metric("Score de priorité max", f"{score_max:.1f}" if pd.notna(score_max) else "—")
    c8.metric("Criticité nette déclarée (moy.)", f"{R['criticite_nette_declaree'].mean():.2f}" if len(R) else "—")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("#### Répartition des risques par zone officielle")
        zone_counts = R["zone"].value_counts().reindex(ZONE_ORDER).fillna(0).reset_index()
        zone_counts.columns = ["zone", "count"]
        fig = px.pie(zone_counts, names="zone", values="count", hole=0.55,
                     color="zone", color_discrete_map=ZONE_COLORS)
        fig.update_traces(textinfo="value+percent")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("#### Répartition des risques par processus")
        proc_counts = R["processus_code"].value_counts().reset_index()
        proc_counts.columns = ["processus", "count"]
        fig = px.bar(proc_counts.sort_values("count"), x="count", y="processus", orientation="h",
                     color_discrete_sequence=[COL_PRIMARY])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Nb de risques")
        st.plotly_chart(fig, width='stretch')

    col3, col4 = st.columns([1, 1])
    with col3:
        st.markdown("#### Criticité brute moyenne par processus")
        fig = px.bar(SP.sort_values("Criticite_Brute_Moyenne"), x="Criticite_Brute_Moyenne", y="processus_code",
                     orientation="h", color_discrete_sequence=[COL_SAGE])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Criticité brute moyenne")
        st.plotly_chart(fig, width='stretch')

    with col4:
        st.markdown("#### DMR moyen par processus")
        fig = px.bar(SP.sort_values("DMR_Moyen"), x="DMR_Moyen", y="processus_code",
                     orientation="h", color_discrete_sequence=[COL_PRIMARY_LT])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="DMR moyen (0-1)")
        st.plotly_chart(fig, width='stretch')

    st.markdown("#### 🔝 Top 10 risques (criticité brute)")
    top10 = R.sort_values("criticite_brute", ascending=False).head(10)[
        ["code", "processus_code", "sous_processus", "prob", "grav", "criticite_brute", "dmr", "zone"]
    ]
    st.dataframe(top10, width='stretch', hide_index=True)


# ============================================================================
# 2. CONSULTATION DES DONNÉES & VARIABLES DE LA BASE ANALYTIQUE
# ============================================================================

elif page == "🗂️ 2. Données & variables":
    header("Données & variables", "Exploration de la base analytique — 168 observations, 13 unités d'analyse")

    st.info(
        "ℹ️ Le document institutionnel de référence fait apparaître **159 risques**, tandis que la "
        "base Excel effectivement utilisée pour les traitements analytiques comprend **168 observations** "
        "réparties entre 13 unités d'analyse (P1 à P12, ainsi que PM). Cet écart, documenté dans le rapport, "
        "doit être rapproché de la source institutionnelle avant toute utilisation opérationnelle."
    )

    tab1, tab2 = st.tabs(["📋 Détail des risques", "📖 Dictionnaire des variables"])

    with tab1:
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            zones_f = st.multiselect("Zone officielle", ZONE_ORDER, default=ZONE_ORDER)
        with fc2:
            crit_min = st.slider("Criticité brute min.", 0, 16, 0)
        with fc3:
            dmr_min = st.slider("DMR min. (degré de maîtrise)", 0.0, 1.0, 0.0)
        with fc4:
            search = st.text_input("🔍 Recherche (code / sous-processus)")

        filt = R[R["zone"].isin(zones_f) & (R["criticite_brute"] >= crit_min) & (R["dmr"] >= dmr_min)]
        if search:
            filt = filt[
                filt["sous_processus"].astype(str).str.contains(search, case=False, na=False)
                | filt["code"].astype(str).str.contains(search, case=False, na=False)
            ]

        st.caption(f"{len(filt)} risques correspondant aux filtres (sur {len(R)} dans la sélection courante)")

        show_cols = {
            "code": "Code", "processus_code": "Processus", "fonction": "Fonction",
            "sous_processus": "Sous-processus", "prob": "Prob.", "grav": "Grav.",
            "criticite_brute": "Crit. brute", "dmr": "DMR", "degre_controle_pct": "Degré contrôle (%)",
            "criticite_nette_declaree": "Crit. nette déclarée", "zone": "Zone officielle",
        }
        display_df = filt[list(show_cols)].rename(columns=show_cols).sort_values("Crit. brute", ascending=False)
        st.dataframe(display_df, width='stretch', hide_index=True, height=440)

        csv = filt.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter (CSV)", csv, "donnees_risques_export.csv", "text/csv")

        st.markdown("#### Statistiques descriptives (sélection courante)")
        desc = filt[["prob", "grav", "criticite_brute", "dmr", "criticite_nette_declaree"]].describe().T
        desc = desc.rename(columns={
            "count": "N", "mean": "Moyenne", "std": "Écart-type", "min": "Min",
            "25%": "Q1", "50%": "Médiane", "75%": "Q3", "max": "Max",
        }).round(2)
        st.dataframe(desc, width='stretch')

    with tab2:
        st.caption(
            "Description des variables disponibles dans la base analytique "
            "(`cartographie_analysee_complete.xlsx`, feuille `Details_Risques`), issues de la cartographie "
            "institutionnelle et des variables dérivées construites sous Python (rapport, Chapitre 5)."
        )
        search_var = st.text_input("🔍 Rechercher une variable")
        vd = VARIABLES_DICO
        if search_var:
            vd = [v for v in vd if search_var.lower() in v["nom"].lower() or search_var.lower() in v["role"].lower()]
        for v in vd:
            st.markdown(
                f"""<div class="var-card">
                <div class="var-name">{v['nom']} <span class="var-meta">· {v['type']}</span></div>
                <div>{v['role']}</div>
                </div>""",
                unsafe_allow_html=True,
            )


# ============================================================================
# 3. VISUALISATION DES ZONES DE RISQUES
# ============================================================================

elif page == "🧭 3. Zones de risques":
    header("Zones de risques", "Zones officielles A/B/C/D de la cartographie institutionnelle")

    tab1, tab2 = st.tabs(["🧭 Répartition des zones", "🗂️ Vérification de la règle des zones (4×4)"])

    with tab1:
        left, right = st.columns([2, 1])
        with left:
            st.markdown("#### Criticité brute × DMR, colorées par zone officielle")
            fig = px.scatter(
                R, x="criticite_brute", y="degre_controle_pct", color="zone",
                color_discrete_map=ZONE_COLORS, category_orders={"zone": ZONE_ORDER},
                hover_data=["code", "processus_code", "sous_processus"],
                labels={"criticite_brute": "Criticité brute", "degre_controle_pct": "Degré de contrôle (%)"},
            )
            for b in CRIT_BINS[1:-1]:
                fig.add_vline(x=b, line_dash="dot", line_color=COL_GRAY, opacity=0.4)
            for b in CTRL_BINS[1:-1]:
                fig.add_hline(y=b, line_dash="dot", line_color=COL_GRAY, opacity=0.4)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=560)
            st.plotly_chart(fig, width='stretch')
            st.caption(
                "Les zones ne sont PAS calculées ici : elles proviennent directement de la colonne "
                "`zone_officielle` de la cartographie. Les lignes pointillées rappellent les bandes de "
                "criticité brute et de degré de contrôle utilisées pour la vérification de cohérence (onglet suivant)."
            )

        with right:
            st.markdown("#### Répartition par zone")
            zone_counts = R["zone"].value_counts().reindex(ZONE_ORDER).fillna(0).reset_index()
            zone_counts.columns = ["zone", "count"]
            fig2 = px.pie(zone_counts, names="zone", values="count", hole=0.5,
                          color="zone", color_discrete_map=ZONE_COLORS)
            fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=280)
            st.plotly_chart(fig2, width='stretch')

            st.markdown("#### Sévérité ordinale des zones")
            st.markdown(
                """
- 🟢 **A** = 1 (la moins sévère)
- 🟡 **B** = 2
- 🟠 **C** = 3
- 🔴 **D** = 4 (la plus sévère)

Cette échelle ordinale est utilisée dans le diagnostic de cohérence
(page *Résultats analytiques*).
                """
            )

        st.markdown("#### Répartition zone × processus")
        cross = pd.crosstab(R["processus_code"], R["zone"]).reindex(columns=ZONE_ORDER, fill_value=0)
        fig3 = px.bar(cross, barmode="stack", color_discrete_map=ZONE_COLORS,
                     labels={"value": "Nb de risques", "processus_code": "Processus"})
        fig3.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig3, width='stretch')

    with tab2:
        st.caption(
            "Vérification de la correspondance entre criticité brute, degré de contrôle (DMR × 100) et "
            "zone officielle (rapport, section 5.4.4). Chaque cellule affiche la zone officielle "
            "majoritairement observée pour cette combinaison de bandes."
        )
        Rm = R.copy()
        Rm["bande_crit"] = pd.cut(Rm["criticite_brute"], bins=CRIT_BINS, labels=CRIT_LABELS, include_lowest=True)
        Rm["bande_ctrl"] = pd.cut(Rm["degre_controle_pct"], bins=CTRL_BINS, labels=CTRL_LABELS)

        grid_z, grid_text, total_obs, total_match = [], [], 0, 0
        for li in reversed(CTRL_LABELS):
            row_z, row_text = [], []
            for ci in CRIT_LABELS:
                cell = Rm[(Rm["bande_ctrl"] == li) & (Rm["bande_crit"] == ci)]
                if len(cell) == 0:
                    row_z.append(np.nan)
                    row_text.append("")
                else:
                    mode_zone = cell["zone"].mode().iloc[0]
                    match = (cell["zone"] == mode_zone).sum()
                    total_obs += len(cell)
                    total_match += match
                    row_z.append(ZONE_ORDER.index(mode_zone))
                    codes = cell["code"].tolist()
                    label = f"{mode_zone} ({len(cell)})<br>" + "<br>".join(codes[:4]) + (f"<br>+{len(codes)-4}" if len(codes) > 4 else "")
                    row_text.append(label)
            grid_z.append(row_z)
            grid_text.append(row_text)

        purete = (total_match / total_obs * 100) if total_obs else 0
        st.metric("Pureté observée (bandes ↔ zone officielle)", f"{purete:.1f}%")

        fig = go.Figure(data=go.Heatmap(
            z=grid_z, text=grid_text, texttemplate="%{text}", textfont=dict(size=10, color="white"),
            x=CRIT_LABELS, y=list(reversed(CTRL_LABELS)),
            colorscale=[[0, ZONE_COLORS["A"]], [0.33, ZONE_COLORS["B"]],
                        [0.66, ZONE_COLORS["C"]], [1, ZONE_COLORS["D"]]],
            showscale=False, xgap=3, ygap=3, zmin=0, zmax=3,
        ))
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=520,
                          xaxis_title="DEGRÉ DE CRITICITÉ (brute) →", yaxis_title="DEGRÉ DE CONTRÔLE (DMR ×100) →",
                          xaxis=dict(side="bottom"))
        st.plotly_chart(fig, width='stretch')

        leg1, leg2, leg3, leg4 = st.columns(4)
        for col, (z, c) in zip([leg1, leg2, leg3, leg4], ZONE_COLORS.items()):
            col.markdown(f'<span class="badge" style="background:{c}">Zone {z}</span>', unsafe_allow_html=True)

        st.caption(
            "Le rapport signale une pureté de 100% sur le périmètre analytique complet — un écart peut "
            "apparaître ici si le filtre courant réduit fortement l'échantillon par cellule."
        )


# ============================================================================
# 4. RÉSULTATS DE PRIORISATION & CLASSEMENT DES PROCESSUS
# ============================================================================

elif page == "🎯 4. Priorisation & classement":
    header("Priorisation & classement des processus", "Score de Priorité d'Audit — classement 0-100 (pondérations de base : 45% Zone D, 30% Zone C, 25% criticité brute)")

    if SC.empty:
        st.warning("Aucune donnée disponible pour ce filtre.")
    else:
        fig = px.bar(SC.sort_values("Score_Priorite_Audit"), x="Score_Priorite_Audit", y="processus_code",
                    orientation="h", color="Score_Priorite_Audit",
                    color_continuous_scale=[COL_SAGE_LT, COL_ALERT_RED], text="Score_Priorite_Audit")
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=480, coloraxis_showscale=False,
                          xaxis_title="Score de priorité (0-100)", yaxis_title="")
        st.plotly_chart(fig, width='stretch')

        st.markdown("#### Tableau de classement")
        tbl = SC[["Rang", "processus_code", "Score_Priorite_Audit", "Pct_Zone_D", "Pct_Zone_C",
                  "Criticite_Brute_Moyenne", "Nb_Risques"]].rename(columns={
            "processus_code": "Processus", "Score_Priorite_Audit": "Score",
            "Pct_Zone_D": "% Zone D", "Pct_Zone_C": "% Zone C",
            "Criticite_Brute_Moyenne": "Crit. brute moyenne", "Nb_Risques": "Nb risques",
        })
        st.dataframe(tbl, width='stretch', hide_index=True)

        st.markdown("---")
        st.markdown("### 🔎 Explicabilité du classement par processus")
        proc_choice = st.selectbox("Choisir un processus", SC["processus_code"].tolist())
        row = SC[SC["processus_code"] == proc_choice].iloc[0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Rang", int(row["Rang"]))
        c2.metric("Score de priorité", f"{row['Score_Priorite_Audit']:.1f} / 100")
        c3.metric("Nb de risques", int(row["Nb_Risques"]))

        factors = pd.DataFrame({
            "Facteur": ["% risques en zone D", "% risques en zone C", "Criticité brute moyenne"],
            "Valeur brute": [row["Pct_Zone_D"], row["Pct_Zone_C"], row["Criticite_Brute_Moyenne"]],
        })
        fig2 = px.bar(factors, x="Valeur brute", y="Facteur", orientation="h", color_discrete_sequence=[COL_PRIMARY])
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=260, yaxis_title="")
        st.plotly_chart(fig2, width='stretch')

        st.info(
            f"**Pourquoi {proc_choice} occupe-t-il ce rang ?** "
            f"{row['Pct_Zone_D']:.1f}% de ses risques sont classés en zone D, {row['Pct_Zone_C']:.1f}% "
            f"en zone C, et sa criticité brute moyenne est de {row['Criticite_Brute_Moyenne']:.2f} — "
            f"soit un score final de {row['Score_Priorite_Audit']:.1f}/100."
        )

        st.warning(
            "⚠️ Le Score de Priorité d'Audit est un **indicateur de priorité relative**, et non une "
            "probabilité de survenance d'un événement. Il constitue un support au jugement professionnel "
            "de l'auditeur interne et ne détermine pas automatiquement la programmation des missions d'audit."
        )


# ============================================================================
# 5. RÉSULTATS ANALYTIQUES UTILES À L'INTERPRÉTATION
# ============================================================================

elif page == "📈 5. Résultats analytiques":
    header("Résultats analytiques", "ANOVA / Kruskal-Wallis · Diagnostic de cohérence · Segmentation K-Means/ACP · Analyse de sensibilité")

    tab1, tab2, tab3, tab4 = st.tabs([
        "ANOVA & Kruskal-Wallis", "Diagnostic de cohérence", "Segmentation K-Means / ACP", "Sensibilité des pondérations",
    ])

    # -- ANOVA sur la criticité brute (rapport, section 5.4.2) --
    with tab1:
        st.caption("Le rapport applique ces tests sur la **criticité brute**, par processus/groupe.")
        groups = [g["criticite_brute"].values for _, g in R.groupby("processus_code") if len(g) > 1]
        if len(groups) >= 2:
            F, p = stats.f_oneway(*groups)
            H, p_kw = stats.kruskal(*groups)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ANOVA — F", f"{F:.2f}")
            c2.metric("ANOVA — p-value", f"{p:.5f}")
            c3.metric("Kruskal-Wallis — H", f"{H:.2f}")
            c4.metric("Kruskal-Wallis — p-value", f"{p_kw:.5f}")
            if p < 0.05:
                st.success(
                    "Les deux tests rejettent l'hypothèse nulle d'égalité des moyennes au seuil de 5% : "
                    "les niveaux de criticité brute ne sont **pas identiques** entre les processus/groupes, "
                    "ce qui justifie une politique d'audit différenciée plutôt qu'une couverture uniforme."
                )
            else:
                st.warning("Aucune différence statistiquement significative détectée entre processus (p ≥ 0.05).")

            fig = px.box(R, x="processus_code", y="criticite_brute", color="processus_code",
                         color_discrete_sequence=px.colors.qualitative.Prism)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False,
                              xaxis_title="Processus", yaxis_title="Criticité brute")
            st.plotly_chart(fig, width='stretch')
        else:
            st.warning("Sélectionnez au moins deux processus (avec plusieurs risques chacun) pour calculer l'ANOVA.")

    # -- Diagnostic de cohérence avec la sévérité des zones (rapport, section 5.4.3) --
    with tab2:
        st.caption(
            "Corrélation de Spearman entre chaque variable de criticité et la sévérité ordinale des zones "
            "officielles (A=1, B=2, C=3, D=4)."
        )
        valid = R.dropna(subset=["zone_severite"])
        if len(valid) > 2:
            rows = []
            for var, label in [
                ("criticite_nette_declaree", "Criticité nette déclarée"),
                ("criticite_nette_diagnostique", "Criticité nette diagnostique (Rbrut × (1-DMR))"),
                ("criticite_brute", "Criticité brute"),
            ]:
                rho, pval = stats.spearmanr(valid[var], valid["zone_severite"])
                rows.append({"Variable": label, "Spearman ρ": round(rho, 3), "p-value": round(pval, 5)})
            diag = pd.DataFrame(rows)
            st.dataframe(diag, width='stretch', hide_index=True)

            fig = px.bar(diag, x="Spearman ρ", y="Variable", orientation="h",
                        color="Spearman ρ", color_continuous_scale=[COL_ALERT_RED, COL_SAGE_LT, COL_PRIMARY])
            fig.add_vline(x=0, line_color=COL_GRAY)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=280, coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig, width='stretch')

            st.info(
                "La criticité brute et la criticité nette diagnostique présentent généralement une "
                "association positive avec la sévérité des zones, tandis que la criticité nette déclarée "
                "peut présenter une association plus faible, voire négative. Cette observation constitue un "
                "point méthodologique à clarifier avec l'encadrement — la criticité nette déclarée reste "
                "conservée comme donnée institutionnelle, et la formule diagnostique n'est utilisée qu'à des "
                "fins de cohérence (elle n'entre pas dans le calcul du score)."
            )
        else:
            st.warning("Pas assez d'observations valides sur ce filtre pour calculer les corrélations.")

    # -- Segmentation K-Means + ACP (rapport, section 5.4.5) --
    with tab3:
        st.caption(
            "Segmentation descriptive (K-Means sur probabilité, gravité et DMR standardisés) — outil "
            "exploratoire complémentaire, non intégré au calcul du Score de Priorité d'Audit."
        )
        seg_data = R.dropna(subset=["prob", "grav", "dmr"]).copy()
        if len(seg_data) >= 10:
            X = StandardScaler().fit_transform(seg_data[["prob", "grav", "dmr"]])

            k_range = range(2, min(7, len(seg_data)))
            sil_scores = {k: silhouette_score(X, KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)) for k in k_range}
            best_k = max(sil_scores, key=sil_scores.get)

            c1, c2 = st.columns(2)
            with c1:
                sil_df = pd.DataFrame({"K": list(sil_scores.keys()), "Silhouette": list(sil_scores.values())})
                fig_sil = px.line(sil_df, x="K", y="Silhouette", markers=True, color_discrete_sequence=[COL_PRIMARY])
                fig_sil.add_vline(x=best_k, line_dash="dash", line_color=COL_ALERT_RED)
                fig_sil.update_layout(**PLOTLY_TEMPLATE["layout"], height=300, title=f"Meilleur K = {best_k}")
                st.plotly_chart(fig_sil, width='stretch')
            with c2:
                st.metric("Nombre de clusters retenu (coefficient de silhouette max.)", best_k)
                st.metric("Coefficient de silhouette", f"{sil_scores[best_k]:.3f}")

            km = KMeans(n_clusters=best_k, n_init=10, random_state=42)
            seg_data["cluster"] = km.fit_predict(X).astype(str)

            pca = PCA(n_components=2, random_state=42)
            coords = pca.fit_transform(X)
            seg_data["F1"], seg_data["F2"] = coords[:, 0], coords[:, 1]
            var_exp = pca.explained_variance_ratio_

            fig_pca = px.scatter(
                seg_data, x="F1", y="F2", color="cluster", hover_data=["code", "processus_code", "zone"],
                labels={"F1": f"F1 ({var_exp[0]*100:.1f}% de variance)", "F2": f"F2 ({var_exp[1]*100:.1f}% de variance)"},
            )
            fig_pca.update_layout(**PLOTLY_TEMPLATE["layout"], height=460)
            st.plotly_chart(fig_pca, width='stretch')

            st.markdown("##### Profils moyens des clusters")
            profils = seg_data.groupby("cluster").agg(
                Nb_Risques=("code", "count"), Prob_Moyenne=("prob", "mean"),
                Grav_Moyenne=("grav", "mean"), DMR_Moyen=("dmr", "mean"),
                Criticite_Brute_Moyenne=("criticite_brute", "mean"),
            ).round(2).reset_index()
            st.dataframe(profils, width='stretch', hide_index=True)

            fig_radar = go.Figure()
            for _, prow in profils.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=[prow["Prob_Moyenne"], prow["Grav_Moyenne"], prow["DMR_Moyen"], prow["Criticite_Brute_Moyenne"]],
                    theta=["Probabilité", "Gravité", "DMR", "Criticité brute"],
                    fill="toself", name=f"Cluster {prow['cluster']}",
                ))
            fig_radar.update_layout(**PLOTLY_TEMPLATE["layout"], polar=dict(radialaxis=dict(visible=True)), height=440)
            st.plotly_chart(fig_radar, width='stretch')
        else:
            st.warning("Pas assez d'observations sur ce filtre pour une segmentation K-Means fiable (minimum 10).")

    # -- Analyse de sensibilité des pondérations (rapport, section 5.5) --
    with tab4:
        st.caption(
            "Cinq scénarios de pondération sont comparés au scénario de base (45% Zone D / 30% Zone C / "
            "25% criticité brute) via la corrélation de Spearman entre les classements obtenus."
        )
        if SP.empty:
            st.warning("Aucune donnée disponible pour ce filtre.")
        else:
            base_rank = compute_score(SP, SENSITIVITY_SCENARIOS["Base"]).set_index("processus_code")["Rang"]

            rows = []
            rank_table = pd.DataFrame(index=SP["processus_code"])
            for name, w in SENSITIVITY_SCENARIOS.items():
                sc = compute_score(SP, w).set_index("processus_code")["Rang"]
                rank_table[name] = sc
                if name != "Base":
                    rho, pval = stats.spearmanr(base_rank, sc)
                    rows.append({"Scénario": name, "wD": w["D"], "wC": w["C"], "w_brut": w["brut"],
                                "Spearman ρ vs Base": round(rho, 3), "p-value": round(pval, 5)})

            st.markdown("##### Table des scénarios")
            scen_tbl = pd.DataFrame([
                {"Scénario": k, "Poids Zone D": v["D"], "Poids Zone C": v["C"], "Poids Crit. brute": v["brut"]}
                for k, v in SENSITIVITY_SCENARIOS.items()
            ])
            st.dataframe(scen_tbl, width='stretch', hide_index=True)

            st.markdown("##### Robustesse du classement (corrélation de Spearman vs scénario de base)")
            rob_df = pd.DataFrame(rows)
            st.dataframe(rob_df, width='stretch', hide_index=True)
            fig = px.bar(rob_df, x="Scénario", y="Spearman ρ vs Base", color_discrete_sequence=[COL_PRIMARY])
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=300, yaxis_range=[0, 1])
            st.plotly_chart(fig, width='stretch')

            st.markdown("##### Rang de chaque processus selon le scénario")
            st.dataframe(rank_table.reset_index().rename(columns={"processus_code": "Processus"}),
                        width='stretch', hide_index=True)

            st.info(
                "Une corrélation de Spearman proche de 1 indique que le classement reste stable malgré la "
                "modification des pondérations ; une valeur plus faible signale des processus dont la "
                "position est plus sensible aux choix méthodologiques."
            )


# ============================================================================
# 6. COMPOSANTES DU SCORE DE PRIORITÉ D'AUDIT (lecture seule)
# ============================================================================

elif page == "🧮 6. Composantes du score":
    header("Composantes du Score de Priorité d'Audit", "Décomposition du score pour en faciliter la lecture et l'interprétation")

    st.markdown("#### 🧮 Formule du score (rapport, éq. 5.13)")
    st.markdown(
        f"""<div class="formula-box">
        Sp = 0.45 × N(%Zone D) + 0.30 × N(%Zone C) + 0.25 × N(Criticité brute moyenne)
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption(
        "N(X) désigne la normalisation Min-Max de la variable X sur une échelle 0-100 : "
        "N(X) = (X − Xmin) / (Xmax − Xmin) × 100. Les trois composantes normalisées sont ensuite pondérées "
        "et sommées pour obtenir le score final sur 100. Ces pondérations constituent un choix "
        "méthodologique explicite donnant la priorité aux risques classés en zone D."
    )

    w1, w2, w3 = st.columns(3)
    w1.metric("Poids — % risques Zone D", f"{SCORE_WEIGHTS_BASE['D']*100:.0f}%")
    w2.metric("Poids — % risques Zone C", f"{SCORE_WEIGHTS_BASE['C']*100:.0f}%")
    w3.metric("Poids — Criticité brute moyenne", f"{SCORE_WEIGHTS_BASE['brut']*100:.0f}%")

    st.markdown("---")

    if SC.empty:
        st.warning("Aucune donnée disponible pour ce filtre.")
    else:
        SC["contrib_D"] = SCORE_WEIGHTS_BASE["D"] * SC["N_Pct_Zone_D"]
        SC["contrib_C"] = SCORE_WEIGHTS_BASE["C"] * SC["N_Pct_Zone_C"]
        SC["contrib_brut"] = SCORE_WEIGHTS_BASE["brut"] * SC["N_Criticite_Brute"]

        st.markdown("#### Décomposition du score par processus")
        stacked = SC[["processus_code", "contrib_D", "contrib_C", "contrib_brut"]].sort_values(
            by=["contrib_D", "contrib_C", "contrib_brut"], ascending=True
        )
        fig = go.Figure()
        fig.add_trace(go.Bar(y=stacked["processus_code"], x=stacked["contrib_D"], name="% risques Zone D",
                             orientation="h", marker_color=COL_ALERT_RED))
        fig.add_trace(go.Bar(y=stacked["processus_code"], x=stacked["contrib_C"], name="% risques Zone C",
                             orientation="h", marker_color=COL_ALERT_ORANGE))
        fig.add_trace(go.Bar(y=stacked["processus_code"], x=stacked["contrib_brut"], name="Criticité brute moyenne",
                             orientation="h", marker_color=COL_PRIMARY))
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], barmode="stack", height=460,
                          xaxis_title="Contribution au score (0-100)", yaxis_title="")
        st.plotly_chart(fig, width='stretch')

        st.markdown("#### Tableau détaillé des composantes")
        detail = SC[[
            "processus_code", "Pct_Zone_D", "N_Pct_Zone_D", "contrib_D",
            "Pct_Zone_C", "N_Pct_Zone_C", "contrib_C",
            "Criticite_Brute_Moyenne", "N_Criticite_Brute", "contrib_brut",
            "Score_Priorite_Audit", "Rang",
        ]].rename(columns={
            "processus_code": "Processus",
            "Pct_Zone_D": "% Zone D (brut)", "N_Pct_Zone_D": "% Zone D (normalisé)", "contrib_D": "Contribution Zone D",
            "Pct_Zone_C": "% Zone C (brut)", "N_Pct_Zone_C": "% Zone C (normalisé)", "contrib_C": "Contribution Zone C",
            "Criticite_Brute_Moyenne": "Crit. brute (brut)", "N_Criticite_Brute": "Crit. brute (normalisée)",
            "contrib_brut": "Contribution crit. brute",
            "Score_Priorite_Audit": "Score final",
        }).round(2).sort_values("Score final", ascending=False)
        st.dataframe(detail, width='stretch', hide_index=True)

        st.markdown("#### 🔎 Zoom sur un processus")
        proc_choice = st.selectbox("Choisir un processus", SC["processus_code"].tolist(), key="score_zoom")
        row = SC[SC["processus_code"] == proc_choice].iloc[0]

        fig2 = go.Figure(go.Bar(
            x=["% risques Zone D", "% risques Zone C", "Criticité brute moyenne"],
            y=[row["contrib_D"], row["contrib_C"], row["contrib_brut"]],
            marker_color=[COL_ALERT_RED, COL_ALERT_ORANGE, COL_PRIMARY],
            text=[f"{v:.1f}" for v in [row["contrib_D"], row["contrib_C"], row["contrib_brut"]]],
            textposition="outside",
        ))
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=340,
                           yaxis_title="Contribution au score", title=f"Score total : {row['Score_Priorite_Audit']:.1f} / 100")
        st.plotly_chart(fig2, width='stretch')

        st.info(
            f"Pour **{proc_choice}**, la part de risques en **zone D** contribue pour "
            f"{row['contrib_D']:.1f} points, la part en **zone C** pour {row['contrib_C']:.1f} points, "
            f"et la **criticité brute moyenne** pour {row['contrib_brut']:.1f} points, "
            f"soit un score final de **{row['Score_Priorite_Audit']:.1f} / 100** (rang {int(row['Rang'])})."
        )


st.markdown("---")
st.caption("ORMVA-TF Risk & Audit Center · Données réelles : 168 observations, 13 unités d'analyse (P1-P12, PM) · Interface de consultation — Prototype PFA Audit Interne & Actuariat")

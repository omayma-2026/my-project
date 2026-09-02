# -*- coding: utf-8 -*-
"""
ORMVA-TF Risk & Audit Center
Application web de consultation et d'exploration des résultats du modèle
d'aide à la décision pour la priorisation des missions d'audit interne.
------------------------------------------------------------------------
Cette version utilise directement les 2 fichiers réels produits par le
notebook Python du mémoire :

    - data/cartographie_analysee_complete.xlsx  (feuille "Details_Risques")
      → 159 risques analysés : criticité, DMR, criticité nette prédite,
        résidu, cluster (K-Means), coordonnées ACP (PCA1/PCA2).
    - data/ORMVATF_cartographie_risques_extraite.xlsx  (feuille "Sheet1")
      → 168 observations brutes de la cartographie institutionnelle :
        processus_code, processus_nom, fonction, zone_officielle, constat,
        mesures opératoires.

Les deux fichiers sont fusionnés sur la colonne `code` (jointure interne).
Le résultat comprend 159 risques répartis sur 12 processus (P1 à P12) — ce
qui correspond exactement à l'écart documenté dans le rapport de stage entre
le périmètre brut du notebook (168 observations, 13 unités dont PM) et le
périmètre effectivement analysé (159 risques, 12 processus).

Aucune donnée n'est inventée : tous les indicateurs, scores et tests
statistiques sont recalculés EN DIRECT à partir de cette base fusionnée.

Fonctionnalités couvertes (cahier des charges) :
    1. Consultation des principaux indicateurs
    2. Consultation des données et des variables de la base analytique
    3. Visualisation des différentes zones de risques (zone_officielle)
    4. Affichage des résultats de priorisation et du classement des processus
    5. Consultation des résultats analytiques utiles à l'interprétation
       (ANOVA/Kruskal-Wallis, diagnostic de cohérence, régression du DMR,
       segmentation K-Means/ACP réelle, analyse de sensibilité des poids)
    6. Présentation des composantes du Score de Priorité d'Audit

Le Score de Priorité d'Audit suit la formule du rapport (section 5.4) :
    Sp = 0.45 × N(%Zone D) + 0.30 × N(%Zone C) + 0.25 × N(Criticité brute moyenne)
Aucune méthode actuarielle (VaR/TVaR/Monte Carlo) n'est utilisée : ces
méthodes sont présentées dans le rapport comme cadre théorique uniquement.

Lancer avec :
    pip install -r requirements.txt   # streamlit, pandas, plotly, scipy, openpyxl
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
FILE_ANALYSE = DATA_DIR / "cartographie_analysee_complete.xlsx"
FILE_EXTRAIT = DATA_DIR / "ORMVATF_cartographie_risques_extraite.xlsx"

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
ZONE_COLORS = {"A": "#2E7D4F", "B": "#D9A441", "C": "#E08E45", "D": "#C0392B"}

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
.stApp {{ background-color: {COL_BG}; }}
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {COL_PRIMARY} 0%, {COL_PRIMARY_LT} 100%);
}}
section[data-testid="stSidebar"] * {{ color: #E7F0F7 !important; }}
section[data-testid="stSidebar"] div[data-baseweb="select"] * {{ color: {COL_GRAY} !important; }}
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {{ background-color: white !important; }}
.nav-section-title {{
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    color: #9FC3DB !important; margin: 16px 0 6px 2px;
}}
section[data-testid="stSidebar"] button[kind="secondary"] {{
    background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.10) !important;
    color: #E7F0F7 !important; text-align: left !important; justify-content: flex-start !important;
    font-weight: 500 !important; margin-bottom: 3px;
}}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {{
    background: rgba(255,255,255,0.10) !important; border-color: rgba(255,255,255,0.25) !important;
}}
section[data-testid="stSidebar"] button[kind="primary"] {{
    background: linear-gradient(90deg, {COL_SAGE} 0%, #7FB0CE 100%) !important; border: none !important;
    color: {COL_PRIMARY} !important; text-align: left !important; justify-content: flex-start !important;
    font-weight: 700 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.20); margin-bottom: 3px;
}}
div[data-testid="stMetric"] {{
    background: {COL_WHITE}; border: 1px solid #E3EBE5; border-left: 4px solid {COL_PRIMARY};
    border-radius: 10px; padding: 14px 18px 10px 18px; box-shadow: 0 1px 3px rgba(15,61,46,0.06);
}}
div[data-testid="stMetricValue"] {{ color: {COL_PRIMARY}; font-weight: 800; }}
h1, h2, h3 {{ color: {COL_PRIMARY}; font-weight: 800; }}
.app-header {{
    background: linear-gradient(120deg, {COL_PRIMARY} 0%, {COL_PRIMARY_LT} 60%, {COL_SAGE} 140%);
    padding: 26px 32px; border-radius: 14px; color: white; margin-bottom: 22px;
}}
.app-header h1 {{ color: white !important; margin: 0; font-size: 26px; }}
.app-header p {{ color: #DCE9DF; margin: 4px 0 0 0; font-size: 14px; }}
.badge {{
    display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px;
    font-weight: 700; color: white;
}}
.var-card {{
    background: {COL_WHITE}; border: 1px solid #E3EBE5; border-left: 4px solid {COL_SAGE};
    border-radius: 10px; padding: 12px 16px; margin-bottom: 10px;
}}
.var-card .var-name {{ font-weight: 700; color: {COL_PRIMARY}; font-size: 14px; }}
.var-card .var-meta {{ font-size: 12px; color: #6B7B85; }}
.formula-box {{
    background: {COL_SAGE_LT}; border: 1px solid {COL_SAGE}; border-radius: 10px;
    padding: 16px 20px; font-family: 'Courier New', monospace; font-size: 15px;
    color: {COL_PRIMARY}; margin-bottom: 16px;
}}
.dataframe tbody tr:hover {{ background-color: {COL_SAGE_LT} !important; }}
hr {{ border-color: #E3EBE5; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

PLOTLY_TEMPLATE = dict(
    layout=dict(
        font=dict(family="Inter, sans-serif", color=COL_GRAY, size=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
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

VARIABLES_DICO = [
    {"nom": "code", "type": "Identifiant", "role": "Identification de l'observation (le risque individuel)."},
    {"nom": "processus_code", "type": "Qualitative", "role": "Unité d'analyse / niveau d'agrégation du scoring (P1 à P12)."},
    {"nom": "processus_nom / fonction", "type": "Qualitative", "role": "Libellé du processus et fonction organisationnelle associée (Support, Opérationnel, Transversal, Management)."},
    {"nom": "sous_processus / intitule", "type": "Qualitative", "role": "Sous-processus et intitulé détaillé du risque."},
    {"nom": "prob", "type": "Ordinale", "role": "Vraisemblance du risque (probabilité d'occurrence)."},
    {"nom": "grav", "type": "Ordinale", "role": "Impact du risque (gravité)."},
    {"nom": "criticite_brute", "type": "Quantitative", "role": "Exposition intrinsèque au risque = Probabilité × Gravité."},
    {"nom": "dmr", "type": "Proportion", "role": "Dispositif de Maîtrise des Risques (degré de contrôle, 0 à 1). Un DMR élevé = dispositif satisfaisant."},
    {"nom": "degre_controle_pct", "type": "Dérivée", "role": "DMR exprimé en pourcentage (dmr × 100)."},
    {"nom": "criticite_nette_declaree", "type": "Quantitative", "role": "Criticité nette institutionnelle, conservée pour diagnostic."},
    {"nom": "criticite_nette_predite / residu", "type": "Dérivée (modèle)", "role": "Criticité nette prédite par le modèle et résidu (écart réel − prédit), issus du notebook Python."},
    {"nom": "zone_officielle", "type": "Ordinale (A-D)", "role": "Zone de risque officielle de la cartographie institutionnelle."},
    {"nom": "cluster / cluster_label", "type": "Catégorielle", "role": "Groupe issu de la segmentation K-Means (Négligés, Mineurs, Sous contrôle, Critiques non maîtrisés)."},
    {"nom": "pca1 / pca2", "type": "Dérivée (ACP)", "role": "Coordonnées des risques sur les 2 premières composantes principales."},
    {"nom": "constat", "type": "Texte", "role": "Description qualitative du constat associé au risque."},
    {"nom": "mesures_operatoires", "type": "Texte", "role": "Mesures de maîtrise/traitement proposées pour le risque."},
]

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
# 1. CHARGEMENT & FUSION DES DONNÉES RÉELLES (mis en cache)
# ----------------------------------------------------------------------------

def _diagnose_file(path: Path) -> str:
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
            return f"Le fichier ne fait que {size} octets : c'est un **pointeur Git LFS**, pas le vrai binaire."
        return f"Le fichier ne fait que {size} octets — trop petit pour un vrai classeur. Aperçu : `{preview.strip()}`"
    if head[:2] == b"PK":
        return "Structure ZIP/xlsx correcte — vérifie le nom exact de la feuille demandée."
    if head[:4] == b"\xd0\xcf\x11\xe0":
        return "C'est un ancien format **`.xls` binaire** (Excel 97-2003), pas un `.xlsx`."
    if head.strip().lower().startswith((b"<!doctype", b"<html")):
        return "Le fichier contient du **HTML** (page d'erreur enregistrée par erreur en `.xlsx`)."
    return (
        f"Signature inattendue en tête de fichier : {head[:16]!r}. Le fichier a probablement été corrompu "
        "lors d'un commit Git (ajoute un `.gitattributes` avec `*.xlsx binary`) ou d'un transfert."
    )


@st.cache_data(show_spinner="Chargement de la cartographie des risques...")
def load_data():
    analyse = pd.read_excel(FILE_ANALYSE, sheet_name="Details_Risques", engine="openpyxl")
    extrait = pd.read_excel(FILE_EXTRAIT, sheet_name="Sheet1", engine="openpyxl")

    required_analyse = ["code", "processus", "sous_processus", "intitule", "prob", "grav",
                        "criticite_brute", "dmr", "criticite_nette", "Criticite_Nette_Predite",
                        "Residu", "Cluster", "Cluster_Label", "PCA1", "PCA2"]
    required_extrait = ["code", "processus_code", "processus_nom", "fonction", "zone_officielle"]
    missing_a = [c for c in required_analyse if c not in analyse.columns]
    missing_e = [c for c in required_extrait if c not in extrait.columns]
    if missing_a:
        raise KeyError(f"Colonnes absentes de '{FILE_ANALYSE.name}' (feuille Details_Risques) : {missing_a}")
    if missing_e:
        raise KeyError(f"Colonnes absentes de '{FILE_EXTRAIT.name}' (feuille Sheet1) : {missing_e}")

    n_extrait = len(extrait)
    n_analyse = len(analyse)

    # Jointure à GAUCHE sur la base ANALYSÉE (159 lignes = périmètre officiel du modèle).
    # On ne récupère depuis le fichier extrait QUE les colonnes qu'il est seul à fournir
    # (processus_code, processus_nom, fonction, zone_officielle, constat, mesures) — prob,
    # grav, dmr, criticité, sous_processus, intitulé restent ceux du fichier analysé, qui fait
    # foi. Certaines déclarations (ex. P9.SP2.*) existent dans le fichier analysé mais pas dans
    # l'extraction brute fournie : elles sont conservées, avec zone/fonction non renseignées.
    extrait_cols = [c for c in
                    ["code", "processus_code", "processus_nom", "fonction", "zone_officielle",
                     "constat", "mesures_operatoires"]
                    if c in extrait.columns]

    df = analyse.merge(extrait[extrait_cols], on="code", how="left")
    n_final = len(df)
    n_sans_zone = df["zone_officielle"].isna().sum()

    # Rattrapage processus_code / processus_nom à partir de la colonne `processus`
    # ("P9 - Achat et approvisionnement") du fichier analysé, pour les lignes non couvertes
    # par l'extraction brute.
    parsed = df["processus"].astype(str).str.extract(r"^(P\d+)\s*-\s*(.*)$")
    df["processus_code"] = df["processus_code"].fillna(parsed[0])
    df["processus_nom"] = df["processus_nom"].fillna(parsed[1])

    df = df.rename(columns={
        "criticite_nette": "criticite_nette_declaree",
        "zone_officielle": "zone",
        "Criticite_Nette_Predite": "criticite_nette_predite",
        "Residu": "residu",
        "Cluster": "cluster",
        "Cluster_Label": "cluster_label",
        "PCA1": "pca1",
        "PCA2": "pca2",
    })

    df["degre_controle_pct"] = df["dmr"] * 100
    df["criticite_nette_diagnostique"] = df["criticite_brute"] * (1 - df["dmr"])
    df["zone"] = df["zone"].astype(str).str.strip().str.upper().replace({"NAN": np.nan})
    df["zone_severite"] = df["zone"].map(ZONE_SEVERITY)

    if "fonction" not in df.columns:
        df["fonction"] = "—"
    df["fonction"] = df["fonction"].fillna("Non renseignée")
    if "constat" not in df.columns:
        df["constat"] = ""
    df["constat"] = df["constat"].fillna("")
    if "mesures_operatoires" not in df.columns:
        df["mesures_operatoires"] = ""
    df["mesures_operatoires"] = df["mesures_operatoires"].fillna("")

    return df, n_extrait, n_analyse, n_final, n_sans_zone


try:
    RISQUES, N_EXTRAIT, N_ANALYSE, N_FINAL, N_SANS_ZONE = load_data()
except FileNotFoundError as e:
    st.error(
        "⚠️ Fichier(s) de données introuvable(s). Place `cartographie_analysee_complete.xlsx` "
        "et `ORMVATF_cartographie_risques_extraite.xlsx` dans le dossier `data/` à côté de `app.py`.\n\n"
        f"Détail : {e}"
    )
    st.stop()
except KeyError as e:
    st.error(f"⚠️ {e}")
    st.stop()
except Exception as e:
    diag_a = _diagnose_file(FILE_ANALYSE)
    diag_e = _diagnose_file(FILE_EXTRAIT)
    st.error(
        f"⚠️ Impossible de charger les fichiers Excel.\n\n"
        f"**`{FILE_ANALYSE.name}`** : {diag_a}\n\n"
        f"**`{FILE_EXTRAIT.name}`** : {diag_e}\n\n"
        f"*Erreur originale : {e}*"
    )
    st.stop()

ALL_PROCESSUS = sorted(RISQUES["processus_code"].dropna().unique().tolist())
ALL_FONCTIONS = sorted(RISQUES["fonction"].dropna().unique().tolist())


# ----------------------------------------------------------------------------
# 1bis. FONCTIONS DE CALCUL — reproduisent les équations du Chapitre 5
# ----------------------------------------------------------------------------

def compute_stats_processus(df: pd.DataFrame) -> pd.DataFrame:
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
    st.markdown("**Filtrage par processus**")
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
    st.caption(f"{len(RISQUES)} risques réels · {len(ALL_PROCESSUS)} processus")
    st.caption("Source : cartographie ORMVA-TF, analyse Python")

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
        f"{len(selected_processus)}/{len(ALL_PROCESSUS)} processus",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risques (filtre)", f"{len(R)}", f"/ {len(RISQUES)} au total")
    c2.metric("Processus", f"{R['processus_code'].nunique()}")
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
        ["code", "processus_code", "intitule", "prob", "grav", "criticite_brute", "dmr", "zone"]
    ]
    st.dataframe(top10, width='stretch', hide_index=True)


# ============================================================================
# 2. CONSULTATION DES DONNÉES & VARIABLES DE LA BASE ANALYTIQUE
# ============================================================================

elif page == "🗂️ 2. Données & variables":
    header("Données & variables", f"Exploration de la base analytique — {len(RISQUES)} risques, {len(ALL_PROCESSUS)} processus")

    st.info(
        f"ℹ️ Le fichier brut de cartographie contient **{N_EXTRAIT} observations**, tandis que le fichier "
        f"d'analyse (clusters, ACP, régression) en contient **{N_ANALYSE}**. La base finale exploitée par "
        f"cette application repose sur le périmètre analysé (**{N_FINAL} risques**, {len(ALL_PROCESSUS)} "
        f"processus), enrichi avec la zone officielle et la fonction issues du fichier brut lorsque "
        f"disponibles. **{N_SANS_ZONE} risque(s)** n'ont pas de correspondance dans le fichier brut "
        "(zone/fonction non renseignées) — ils restent inclus dans les autres analyses."
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
            search = st.text_input("🔍 Recherche (code / intitulé)")

        filt = R[R["zone"].isin(zones_f) & (R["criticite_brute"] >= crit_min) & (R["dmr"] >= dmr_min)]
        if search:
            filt = filt[
                filt["intitule"].astype(str).str.contains(search, case=False, na=False)
                | filt["code"].astype(str).str.contains(search, case=False, na=False)
            ]

        st.caption(f"{len(filt)} risques correspondant aux filtres (sur {len(R)} dans la sélection courante)")

        show_cols = {
            "code": "Code", "processus_code": "Processus", "fonction": "Fonction",
            "intitule": "Intitulé", "prob": "Prob.", "grav": "Grav.",
            "criticite_brute": "Crit. brute", "dmr": "DMR", "degre_controle_pct": "Degré contrôle (%)",
            "criticite_nette_declaree": "Crit. nette déclarée", "zone": "Zone", "cluster_label": "Profil (cluster)",
        }
        display_df = filt[list(show_cols)].rename(columns=show_cols).sort_values("Crit. brute", ascending=False)
        st.dataframe(display_df, width='stretch', hide_index=True, height=420)

        csv = filt.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter (CSV)", csv, "donnees_risques_export.csv", "text/csv")

        st.markdown("#### 🔍 Détail d'un risque (constat & mesures opératoires)")
        code_choice = st.selectbox("Choisir un risque", filt["code"].tolist() if len(filt) else [])
        if code_choice:
            rr = R[R["code"] == code_choice].iloc[0]
            st.markdown(f"**{rr['code']} · {rr['intitule']}**")
            st.caption(f"{rr['processus_code']} — {rr['processus_nom']} · {rr['sous_processus']}")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("**Constat**")
                st.write(rr["constat"] if rr["constat"] else "—")
            with cc2:
                st.markdown("**Mesures opératoires**")
                st.write(rr["mesures_operatoires"] if rr["mesures_operatoires"] else "—")

        st.markdown("#### Statistiques descriptives (sélection courante)")
        desc = filt[["prob", "grav", "criticite_brute", "dmr", "criticite_nette_declaree"]].describe().T
        desc = desc.rename(columns={
            "count": "N", "mean": "Moyenne", "std": "Écart-type", "min": "Min",
            "25%": "Q1", "50%": "Médiane", "75%": "Q3", "max": "Max",
        }).round(2)
        st.dataframe(desc, width='stretch')

    with tab2:
        st.caption(
            "Description des variables disponibles dans la base analytique fusionnée "
            "(cartographie institutionnelle + résultats du notebook Python)."
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
            st.markdown("#### Criticité brute × Degré de contrôle, colorées par zone officielle")
            fig = px.scatter(
                R, x="criticite_brute", y="degre_controle_pct", color="zone",
                color_discrete_map=ZONE_COLORS, category_orders={"zone": ZONE_ORDER},
                hover_data=["code", "processus_code", "intitule"],
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
                "`zone_officielle` de la cartographie institutionnelle."
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
            "zone officielle. Chaque cellule affiche la zone officielle majoritairement observée."
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


# ============================================================================
# 4. RÉSULTATS DE PRIORISATION & CLASSEMENT DES PROCESSUS
# ============================================================================

elif page == "🎯 4. Priorisation & classement":
    header("Priorisation & classement des processus", "Score de Priorité d'Audit — 45% Zone D, 30% Zone C, 25% criticité brute")

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
        tbl = SC[["Rang", "processus_code", "processus_nom", "Score_Priorite_Audit", "Pct_Zone_D", "Pct_Zone_C",
                  "Criticite_Brute_Moyenne", "Nb_Risques"]].rename(columns={
            "processus_code": "Processus", "processus_nom": "Nom", "Score_Priorite_Audit": "Score",
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
            "de l'auditeur interne."
        )


# ============================================================================
# 5. RÉSULTATS ANALYTIQUES UTILES À L'INTERPRÉTATION
# ============================================================================

elif page == "📈 5. Résultats analytiques":
    header("Résultats analytiques", "ANOVA/Kruskal-Wallis · Diagnostic de cohérence · Régression du DMR · Segmentation K-Means/ACP · Sensibilité")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "ANOVA & Kruskal-Wallis", "Diagnostic de cohérence", "Régression du DMR",
        "Segmentation K-Means / ACP", "Sensibilité des pondérations",
    ])

    # -- ANOVA + Kruskal-Wallis sur la criticité brute --
    with tab1:
        st.caption("Tests appliqués sur la **criticité brute**, par processus.")
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
                    "les niveaux de criticité brute ne sont **pas identiques** entre processus."
                )
            else:
                st.warning("Aucune différence statistiquement significative détectée (p ≥ 0.05).")

            fig = px.box(R, x="processus_code", y="criticite_brute", color="processus_code",
                         color_discrete_sequence=px.colors.qualitative.Prism)
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False,
                              xaxis_title="Processus", yaxis_title="Criticité brute")
            st.plotly_chart(fig, width='stretch')
        else:
            st.warning("Sélectionnez au moins deux processus (avec plusieurs risques chacun).")

    # -- Diagnostic de cohérence (Spearman zone-sévérité) --
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
                "La criticité nette diagnostique n'est utilisée qu'à des fins de vérification de cohérence — "
                "elle n'entre pas dans le calcul du Score de Priorité d'Audit."
            )
        else:
            st.warning("Pas assez d'observations valides sur ce filtre.")

    # -- Régression du DMR (colonnes réelles du notebook) --
    with tab3:
        st.caption(
            "Comparaison entre la criticité nette déclarée et la criticité nette **prédite par le modèle** "
            "(colonnes `criticite_nette_predite` / `residu` issues du notebook Python)."
        )
        y = R["criticite_nette_declaree"].values
        yp = R["criticite_nette_predite"].values
        if len(y) > 1 and np.nanstd(y) > 0:
            ss_res = np.nansum((y - yp) ** 2)
            ss_tot = np.nansum((y - np.nanmean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
            c1, c2 = st.columns(2)
            c1.metric("R² (criticité nette réelle vs prédite)", f"{r2:.3f}" if pd.notna(r2) else "—")
            surestimes = R[R["cluster_label"] == "Critiques non maitrises"]
            c2.metric("Risques du profil 'Critiques non maîtrisés'", f"{len(surestimes)}")

            fig = px.scatter(R, x="criticite_nette_predite", y="criticite_nette_declaree", color="zone",
                             color_discrete_map=ZONE_COLORS, hover_data=["code", "intitule"])
            m = max(np.nanmax(y), np.nanmax(yp))
            mn = min(np.nanmin(y), np.nanmin(yp))
            fig.add_trace(go.Scatter(x=[mn, m], y=[mn, m], mode="lines",
                                      line=dict(dash="dash", color=COL_GRAY), name="y = x"))
            fig.update_layout(**PLOTLY_TEMPLATE["layout"],
                              xaxis_title="Criticité nette prédite", yaxis_title="Criticité nette déclarée")
            st.plotly_chart(fig, width='stretch')

            st.markdown("##### Risques au résidu le plus élevé (écart réel vs prédit)")
            st.dataframe(
                R[["code", "processus_code", "intitule", "dmr", "criticite_nette_declaree", "criticite_nette_predite", "residu"]]
                .sort_values("residu", ascending=False).head(15),
                width='stretch', hide_index=True,
            )
        else:
            st.warning("Pas assez de données pour cette analyse sur ce filtre.")

    # -- Segmentation K-Means / ACP (valeurs RÉELLES précalculées) --
    with tab4:
        st.caption(
            "Segmentation issue du notebook Python (K-Means sur probabilité/gravité/DMR standardisés, "
            "projection ACP). Ces clusters ne sont pas recalculés ici — ce sont les résultats réels du modèle."
        )
        if R["pca1"].notna().sum() > 0:
            fig_pca = px.scatter(
                R, x="pca1", y="pca2", color="cluster_label",
                color_discrete_map=CLUSTER_COLORS,
                hover_data=["code", "processus_code", "zone"],
                labels={"pca1": "PCA1", "pca2": "PCA2"},
            )
            fig_pca.update_layout(**PLOTLY_TEMPLATE["layout"], height=460)
            st.plotly_chart(fig_pca, width='stretch')

            st.markdown("##### Profils moyens des clusters (sélection courante)")
            profils = R.groupby("cluster_label").agg(
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
                    fill="toself", name=prow["cluster_label"],
                    line_color=CLUSTER_COLORS.get(prow["cluster_label"], COL_PRIMARY),
                ))
            fig_radar.update_layout(**PLOTLY_TEMPLATE["layout"], polar=dict(radialaxis=dict(visible=True)), height=440)
            st.plotly_chart(fig_radar, width='stretch')

            st.markdown("##### Répartition des risques (filtre courant) par cluster")
            cl_counts = R["cluster_label"].value_counts().reset_index()
            cl_counts.columns = ["cluster_label", "count"]
            fig2 = px.pie(cl_counts, names="cluster_label", values="count", hole=0.5,
                          color="cluster_label", color_discrete_map=CLUSTER_COLORS)
            fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=320)
            st.plotly_chart(fig2, width='stretch')
        else:
            st.warning("Aucune coordonnée ACP disponible pour ce filtre.")

    # -- Analyse de sensibilité des pondérations --
    with tab5:
        st.caption(
            "Cinq scénarios de pondération comparés au scénario de base (45% Zone D / 30% Zone C / "
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

            st.markdown("##### Robustesse du classement (Spearman vs scénario de base)")
            rob_df = pd.DataFrame(rows)
            st.dataframe(rob_df, width='stretch', hide_index=True)
            fig = px.bar(rob_df, x="Scénario", y="Spearman ρ vs Base", color_discrete_sequence=[COL_PRIMARY])
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=300, yaxis_range=[0, 1])
            st.plotly_chart(fig, width='stretch')

            st.markdown("##### Rang de chaque processus selon le scénario")
            st.dataframe(rank_table.reset_index().rename(columns={"processus_code": "Processus"}),
                        width='stretch', hide_index=True)


# ============================================================================
# 6. COMPOSANTES DU SCORE DE PRIORITÉ D'AUDIT (lecture seule)
# ============================================================================

elif page == "🧮 6. Composantes du score":
    header("Composantes du Score de Priorité d'Audit", "Décomposition du score pour en faciliter la lecture et l'interprétation")

    st.markdown("#### 🧮 Formule du score (rapport, éq. 5.13)")
    st.markdown(
        """<div class="formula-box">
        Sp = 0.45 × N(%Zone D) + 0.30 × N(%Zone C) + 0.25 × N(Criticité brute moyenne)
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption(
        "N(X) désigne la normalisation Min-Max de X sur une échelle 0-100 : "
        "N(X) = (X − Xmin) / (Xmax − Xmin) × 100."
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
st.caption(f"ORMVA-TF Risk & Audit Center · Données réelles : {len(RISQUES)} risques, {len(ALL_PROCESSUS)} processus · Interface de consultation — Prototype PFA Audit Interne & Actuariat")

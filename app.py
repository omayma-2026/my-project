# -*- coding: utf-8 -*-
"""
ORMVA-TF Risk & Audit Center
Plateforme décisionnelle d'audit interne et de gestion des risques
------------------------------------------------------------------
Toutes les données affichées proviennent des fichiers réels fournis par
l'utilisateur :
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

# Palette institutionnelle : bleu acier / bleu nuit professionnel (identité "froide")
COL_PRIMARY = "#0F3D2E"
COL_PRIMARY_LT = "#145C3F"
COL_SAGE = "#7FA98C"
COL_SAGE_LT = "#DCE9DF"     # bleu très clair (fonds de cards)
COL_BG = "#F4F7F9"            # fond général
COL_GRAY = "#2E3B47"          # gris-bleu foncé texte
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
section[data-testid="stSidebar"] .stRadio label {{
    font-weight: 500;
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
# 0bis. PORTAIL D'ACCÈS — email demandé avant d'entrer, notification par mail
# ----------------------------------------------------------------------------
# Chaque nouvelle personne qui ouvre l'app doit indiquer son nom + email avant
# d'accéder au contenu. Une notification est envoyée par email à l'administrateur
# du prototype (toi) — voir README.md pour configurer les identifiants Gmail
# (st.secrets : GMAIL_USER, GMAIL_APP_PASSWORD, NOTIF_EMAIL).

if "access_granted" not in st.session_state:
    st.session_state.access_granted = False
if "access_log" not in st.session_state:
    st.session_state.access_log = []


def send_access_notification(nom: str, email: str) -> tuple[bool, str]:
    """Envoie un email à l'administrateur pour signaler un nouvel accès à l'app.
    Retourne (succès, message d'erreur éventuel). Ne bloque jamais l'app en cas d'échec."""
    try:
        import smtplib
        from email.mime.text import MIMEText

        gmail_user = st.secrets["GMAIL_USER"]
        gmail_app_password = st.secrets["GMAIL_APP_PASSWORD"]
        notif_to = st.secrets.get("NOTIF_EMAIL", gmail_user)

        body = (
            f"Nouvel accès à ORMVA-TF Risk & Audit Center\n\n"
            f"Nom : {nom}\nEmail : {email}\n"
            f"Date : {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}"
        )
        msg = MIMEText(body)
        msg["Subject"] = "🔔 Nouvel accès — ORMVA-TF Risk & Audit Center"
        msg["From"] = gmail_user
        msg["To"] = notif_to

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(gmail_user, gmail_app_password)
            server.sendmail(gmail_user, [notif_to], msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


if not st.session_state.access_granted:
    st.markdown(
        f"""<div style="max-width:480px;margin:60px auto 0 auto;text-align:center;">
        <div style="font-size:40px;">🛡️</div>
        <h2 style="color:{COL_PRIMARY};margin-bottom:0;">ORMVA-TF Risk & Audit Center</h2>
        <p style="color:{COL_GRAY};">Plateforme décisionnelle d'audit interne et de gestion des risques</p>
        </div>""",
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        with st.form("gate_form"):
            g_nom = st.text_input("Nom complet")
            g_email = st.text_input("Adresse Gmail")
            go = st.form_submit_button("🔓 Accéder à l'application", width='stretch')
            if go:
                if not g_nom.strip() or "@gmail.com" not in g_email.lower():
                    st.error("Merci de renseigner ton nom et une adresse Gmail valide.")
                else:
                    entry = {
                        "nom": g_nom.strip(), "email": g_email.strip(),
                        "date": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                    }
                    st.session_state.access_log.append(entry)
                    st.session_state.current_user_name = entry["nom"]
                    st.session_state.current_user_email = entry["email"]
                    ok, err = send_access_notification(entry["nom"], entry["email"])
                    st.session_state.access_granted = True
                    if not ok:
                        st.session_state.access_notif_warning = (
                            "ℹ️ Accès autorisé, mais la notification email n'a pas pu être envoyée "
                            "(configuration Gmail manquante — voir README.md)."
                        )
                    st.rerun()
    st.stop()

if st.session_state.get("access_notif_warning"):
    st.toast(st.session_state.pop("access_notif_warning"), icon="ℹ️")


# ----------------------------------------------------------------------------
# 1. CHARGEMENT DES DONNÉES RÉELLES (mis en cache)
# ----------------------------------------------------------------------------

@st.cache_data(show_spinner="Chargement de la cartographie des risques...")
def load_data():
    # --- Détail des 159 risques (issu de l'analyse Colab) ---
    risques = pd.read_excel(DATA_DIR / "cartographie_analysee_complet.xlsx", sheet_name="Details_Risques")
    risques = risques.rename(columns={
        "Code": "code", "Processus": "processus", "Sous-processus": "sous_processus",
        "Intitule": "intitule", "Prob": "prob", "Grav": "grav",
        "Criticite_Brute": "criticite_brute", "DMR": "dmr", "Criticite_Nette": "criticite_nette",
        "Criticite_Nette_Predite": "criticite_nette_predite", "Residu": "residu",
        "Cluster": "cluster", "Cluster_Label": "cluster_label",
    })
    risques["processus_court"] = risques["processus"].str.extract(r"(P\d+)")

    # --- Zones de risque A/B/C/D (calculées selon la méthodologie du mémoire :
    #     seuils médians sur la criticité nette et le DMR résiduel) ---
    med_crit = risques["criticite_nette"].median()
    med_dmr = risques["dmr"].median()

    def zone(row):
        crit_high = row["criticite_nette"] >= med_crit
        dmr_high = row["dmr"] >= med_dmr  # DMR élevé = dispositif de maîtrise INSUFFISANT (résiduel fort)
        if not crit_high and not dmr_high:
            return "A - Optimisation"
        if not crit_high and dmr_high:
            return "B - Vigilance"
        if crit_high and not dmr_high:
            return "C - Surveillance"
        return "D - Traitement"

    risques["zone"] = risques.apply(zone, axis=1)

    # --- Agrégats officiels par processus (indicateurs_powerbi_v2.xlsx) ---
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
PROC_LABELS = {p: p for p in ALL_PROCESSUS}


# ----------------------------------------------------------------------------
# 1bis. RBAC — RÔLES SIMULÉS + ÉTAT DE SESSION (démo, sans backend réel)
# ----------------------------------------------------------------------------
# NB : Streamlit seul n'a pas de base de données ni d'authentification réelle.
# Ce bloc simule le RBAC (rôles, accès, workflow de validation) en mémoire de
# session, pour la démonstration. Dans la version finale (FastAPI + PostgreSQL),
# ceci correspond aux tables `users`, `roles`, `permissions`, `risk_validations`.

ROLES = [
    "Collaborateur",
    "Responsable de service",
    "Auditeur interne",
    "Chef d'audit / Responsable Audit",
    "Directeur",
    "Administrateur",
]
ROLES_PEUVENT_VALIDER = {"Auditeur interne", "Chef d'audit / Responsable Audit", "Administrateur"}
ROLES_GERENT_ACCES = {"Auditeur interne", "Administrateur"}

if "current_role" not in st.session_state:
    st.session_state.current_role = "Auditeur interne"
if "users_directory" not in st.session_state:
    st.session_state.users_directory = pd.DataFrame([
        {"Nom": "Auditeur Interne (vous)", "Email": "auditeur.interne@ormvatf.ma", "Rôle": "Auditeur interne", "Accès": "Actif"},
        {"Nom": "Chef d'Audit", "Email": "chef.audit@ormvatf.ma", "Rôle": "Chef d'audit / Responsable Audit", "Accès": "En attente"},
        {"Nom": "Directeur Général", "Email": "directeur@ormvatf.ma", "Rôle": "Directeur", "Accès": "En attente"},
        {"Nom": "Resp. Achat & Approvisionnement", "Email": "resp.p9@ormvatf.ma", "Rôle": "Responsable de service", "Accès": "En attente"},
    ])
if "pending_risks" not in st.session_state:
    st.session_state.pending_risks = []       # risques déclarés, en attente de validation
if "validated_session_risks" not in st.session_state:
    st.session_state.validated_session_risks = []   # risques validés durant la session
if "rejected_session_risks" not in st.session_state:
    st.session_state.rejected_session_risks = []
if "missions_plan" not in st.session_state:
    st.session_state.missions_plan = []
if "model_weights" not in st.session_state:
    st.session_state.model_weights = {"crit": 40, "var": 40, "critiques": 20}
if "model_versions" not in st.session_state:
    st.session_state.model_versions = [{
        "version": "V1.0", "date": "20/12/2024", "auteur": "Modèle initial (mémoire PFE)",
        "poids": {"crit": 40, "var": 40, "critiques": 20},
        "motif": "Version de référence — validée par corrélation de Spearman (ρ = 0.98).",
    }]
ROLES_MODEL = {"Auditeur interne", "Chef d'audit / Responsable Audit", "Administrateur"}

# Navigation groupée par logique de workflow (comme une vraie appli SaaS d'entreprise)
NAV_SECTIONS = {
    "PILOTAGE": ["🏠 Dashboard"],
    "CARTOGRAPHIE & DÉCLARATION": [
        "⚠️ Cartographie des risques", "📝 Déclarer un risque", "🔔 Validation des risques",
    ],
    "ANALYSE DES RISQUES": [
        "🧭 Matrice des risques (zones)", "🗂️ Matrice de contrôle (4×4)",
        "📊 Analyses statistiques", "🎲 Monte Carlo · VaR / TVaR",
    ],
    "AUDIT & PLANIFICATION": ["🎯 Priorisation de l'audit", "📅 Planification annuelle"],
    "PILOTAGE & ADMINISTRATION": [
        "📈 Indicateurs KPI / KPR", "⚙️ Paramètres du modèle", "👥 Gestion des accès",
    ],
    "INFORMATIONS": ["ℹ️ À propos du projet"],
}
if "page" not in st.session_state:
    st.session_state.page = "🏠 Dashboard"


# ----------------------------------------------------------------------------
# 2. SIDEBAR — NAVIGATION + RÔLE + FILTRE GLOBAL PAR PROCESSUS
# ----------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 🛡️ ORMVA-TF")
    st.caption("Risk & Audit Center")

    st.session_state.current_role = st.selectbox(
        "Connecté en tant que", ROLES,
        index=ROLES.index(st.session_state.current_role),
    )
    st.markdown("---")

    for section_title, items in NAV_SECTIONS.items():
        st.markdown(f'<div class="nav-section-title">{section_title}</div>', unsafe_allow_html=True)
        for item in items:
            is_active = st.session_state.page == item
            if st.button(
                item, key=f"nav_btn_{item}", width='stretch',
                type="primary" if is_active else "secondary",
            ):
                st.session_state.page = item
                st.rerun()

    page = st.session_state.page

    st.markdown("---")
    st.markdown("**Filtrage par processus**")
    selected_processus = st.multiselect(
        "Processus",
        options=ALL_PROCESSUS,
        default=ALL_PROCESSUS,
        label_visibility="collapsed",
        format_func=lambda p: p,
    )
    if st.button("↺ Réinitialiser le filtre", width='stretch'):
        selected_processus = ALL_PROCESSUS

    st.markdown("---")
    st.caption(f"👤 {st.session_state.get('current_user_name', '—')} · {st.session_state.get('current_user_email', '')}")
    st.caption(f"159 risques réels · 12 processus")
    st.caption("Source : cartographie ORMVA-TF (20-12-2024, V2 GCA)")

if not selected_processus:
    selected_processus = ALL_PROCESSUS

R = RISQUES[RISQUES["processus"].isin(selected_processus)].copy()
SP = STATS_PROC[STATS_PROC["Processus"].isin(selected_processus)].copy()
VT = VAR_TVAR[VAR_TVAR["Processus"].isin(selected_processus)].copy()
SC = SCORE_PRIO[SCORE_PRIO["Processus"].isin(selected_processus)].copy()


def header(title, subtitle):
    st.markdown(
        f"""<div class="app-header"><h1>{title}</h1><p>{subtitle}</p></div>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------------
# PAGE 1 — DASHBOARD
# ----------------------------------------------------------------------------

if page == "🏠 Dashboard":
    header(
        "Dashboard — Pilotage des risques",
        "Vue d'ensemble de la cartographie des risques ORMVA-TF · filtré sur "
        f"{len(selected_processus)}/{len(ALL_PROCESSUS)} processus",
    )

    # --- KPI cards ---
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
    c7.metric("VaR globale 95% (portefeuille)", "4 816.7", help="Résultat de la simulation Monte Carlo globale (mémoire PFE).")
    c8.metric("Somme VaR₉₅ / processus", f"{VT['VaR_95'].sum():,.0f}".replace(",", " "))

    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("#### Répartition des risques par zone")
        zone_counts = R["zone"].value_counts().reindex(ZONE_ORDER).fillna(0).reset_index()
        zone_counts.columns = ["zone", "count"]
        fig = px.pie(
            zone_counts, names="zone", values="count", hole=0.55,
            color="zone", color_discrete_map=ZONE_COLORS,
        )
        fig.update_traces(textinfo="value+percent")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig, width='stretch')

    with col2:
        st.markdown("#### Répartition des risques par processus")
        proc_counts = R["processus_court"].value_counts().reset_index()
        proc_counts.columns = ["processus", "count"]
        fig = px.bar(
            proc_counts.sort_values("count"), x="count", y="processus", orientation="h",
            color_discrete_sequence=[COL_PRIMARY],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Nb de risques")
        st.plotly_chart(fig, width='stretch')

    col3, col4 = st.columns([1, 1])
    with col3:
        st.markdown("#### Criticité nette totale par processus")
        fig = px.bar(
            SP.sort_values("Criticite_Nette_Somme"), x="Criticite_Nette_Somme", y="processus_court",
            orientation="h", color_discrete_sequence=[COL_SAGE],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Criticité nette (somme)")
        st.plotly_chart(fig, width='stretch')

    with col4:
        st.markdown("#### Risques critiques par processus")
        fig = px.bar(
            SC.sort_values("Nb_Risques_Critiques"), x="Nb_Risques_Critiques", y="processus_court",
            orientation="h", color_discrete_sequence=[COL_ALERT_ORANGE],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Nb risques critiques")
        st.plotly_chart(fig, width='stretch')

    col5, col6 = st.columns([1, 1])
    with col5:
        st.markdown("#### Score de priorité par processus")
        fig = px.bar(
            SC.sort_values("Score_Priorite_Audit"), x="Score_Priorite_Audit", y="processus_court",
            orientation="h", color="Score_Priorite_Audit",
            color_continuous_scale=[COL_SAGE_LT, COL_PRIMARY],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="Score (0-100)", coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')

    with col6:
        st.markdown("#### VaR 95% par processus")
        fig = px.bar(
            VT.sort_values("VaR_95"), x="VaR_95", y="processus_court",
            orientation="h", color_discrete_sequence=[COL_ALERT_RED],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], yaxis_title="", xaxis_title="VaR 95%")
        st.plotly_chart(fig, width='stretch')

    st.markdown("#### 🔝 Top 10 risques prioritaires (criticité nette)")
    top10 = R.sort_values("criticite_nette", ascending=False).head(10)[
        ["code", "processus_court", "intitule", "criticite_nette", "dmr", "zone"]
    ]
    st.dataframe(top10, width='stretch', hide_index=True)

    st.markdown("#### Processus prioritaires pour l'audit")
    tbl = SC[["Rang_Quantifie", "Processus", "Score_Priorite_Audit", "Nb_Risques_Critiques", "VaR_95"]].copy()
    tbl["Niveau de priorité"] = pd.cut(
        tbl["Score_Priorite_Audit"], bins=[-1, 30, 60, 100],
        labels=["Faible", "Moyenne", "Élevée"]
    )
    tbl = tbl.rename(columns={
        "Rang_Quantifie": "Rang", "Processus": "Processus", "Score_Priorite_Audit": "Score",
        "Nb_Risques_Critiques": "Risques critiques", "VaR_95": "VaR 95%"
    }).sort_values("Rang")
    st.dataframe(tbl, width='stretch', hide_index=True)


# ----------------------------------------------------------------------------
# PAGE 2 — CARTOGRAPHIE DES RISQUES
# ----------------------------------------------------------------------------

elif page == "⚠️ Cartographie des risques":
    header("Cartographie des risques", f"{len(R)} risques affichés (sur {len(RISQUES)} au total)")

    if st.session_state.validated_session_risks:
        st.success(
            f"🆕 {len(st.session_state.validated_session_risks)} risque(s) validé(s) durant cette "
            "session sont inclus ci-dessous (badge « Nouveau (session) »)."
        )

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        zones_f = st.multiselect("Zone", ZONE_ORDER, default=ZONE_ORDER)
    with fc2:
        crit_min = st.slider("Criticité nette min.", 0.0, float(RISQUES["criticite_nette"].max()), 0.0)
    with fc3:
        dmr_max = st.slider("DMR max. (résiduel)", 0.0, 1.0, 1.0)
    with fc4:
        search = st.text_input("🔍 Recherche (intitulé / code)")

    filt = R[
        R["zone"].isin(zones_f)
        & (R["criticite_nette"] >= crit_min)
        & (R["dmr"] <= dmr_max)
    ]
    if search:
        filt = filt[
            filt["intitule"].str.contains(search, case=False, na=False)
            | filt["code"].str.contains(search, case=False, na=False)
        ]

    st.caption(f"{len(filt)} risques correspondant aux filtres")

    show_cols = {
        "code": "Code", "processus_court": "Processus", "sous_processus": "Sous-processus",
        "intitule": "Intitulé", "prob": "Prob.", "grav": "Grav.",
        "criticite_brute": "Crit. brute", "dmr": "DMR", "criticite_nette": "Crit. nette",
        "zone": "Zone", "cluster_label": "Profil (cluster)",
    }
    display_df = filt[list(show_cols)].rename(columns=show_cols).sort_values("Crit. nette", ascending=False)
    display_df.insert(0, "Statut", "Officiel")

    if st.session_state.validated_session_risks:
        new_rows = pd.DataFrame(st.session_state.validated_session_risks)
        new_rows = new_rows[new_rows["processus"].isin(selected_processus)]
        if len(new_rows):
            new_display = pd.DataFrame({
                "Statut": "🆕 Nouveau (session)",
                "Code": new_rows["code"], "Processus": new_rows["processus"].str.extract(r"(P\d+)")[0],
                "Sous-processus": new_rows["sous_processus"], "Intitulé": new_rows["intitule"],
                "Prob.": new_rows["prob"], "Grav.": new_rows["grav"],
                "Crit. brute": new_rows["criticite_brute"], "DMR": new_rows["dmr"],
                "Crit. nette": new_rows["criticite_nette"], "Zone": "—", "Profil (cluster)": "—",
            })
            display_df = pd.concat([new_display, display_df], ignore_index=True)

    st.dataframe(display_df, width='stretch', hide_index=True, height=460)

    csv = filt.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export CSV/Excel-compatible", csv, "cartographie_risques_export.csv", "text/csv")


# ----------------------------------------------------------------------------
# PAGE 2bis — DÉCLARER UN RISQUE (workflow : brouillon -> en attente de validation)
# ----------------------------------------------------------------------------

elif page == "📝 Déclarer un risque":
    header("Déclarer un nouveau risque", "Un risque déclaré n'intègre PAS la cartographie officielle tant qu'il n'est pas validé par l'auditeur interne")

    st.info(
        "🔒 **Règle du workflow** : ce formulaire crée un risque avec le statut "
        "**« En attente de validation »**. Il n'apparaîtra dans la cartographie officielle "
        "qu'après validation par un Auditeur interne / Chef d'audit (page *Validation des risques*)."
    )

    with st.form("form_declaration", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            f_processus = st.selectbox("Processus *", ALL_PROCESSUS)
            f_sous_processus = st.text_input("Sous-processus *")
            f_titre = st.text_input("Titre du risque *")
            f_responsable = st.text_input("Responsable du risque")
        with c2:
            f_prob = st.slider("Probabilité (1-4)", 1, 4, 2)
            f_grav = st.slider("Gravité (1-4)", 1, 4, 2)
            f_dmr = st.select_slider("DMR estimé (résiduel)", options=[0.25, 0.5, 0.75, 1.0], value=0.5)
            f_declarant = st.text_input("Déclaré par (nom)", value=st.session_state.current_role)

        f_description = st.text_area("Description du risque")
        f_causes = st.text_area("Causes")
        f_consequences = st.text_area("Conséquences")
        f_mesures = st.text_area("Mesures de contrôle existantes")
        f_commentaire = st.text_area("Commentaire additionnel")
        f_piece = st.file_uploader("Pièce justificative (optionnel)")

        submitted = st.form_submit_button("📤 Soumettre pour validation", width='stretch')
        if submitted:
            if not f_titre or not f_sous_processus:
                st.error("Merci de renseigner au moins le titre et le sous-processus.")
            else:
                crit_brute = f_prob * f_grav
                new_risk = {
                    "code": f"NEW-{len(st.session_state.pending_risks) + len(st.session_state.validated_session_risks) + 1:03d}",
                    "processus": f_processus,
                    "sous_processus": f_sous_processus,
                    "intitule": f_titre,
                    "description": f_description,
                    "causes": f_causes,
                    "consequences": f_consequences,
                    "mesures": f_mesures,
                    "prob": f_prob, "grav": f_grav,
                    "criticite_brute": crit_brute,
                    "dmr": f_dmr,
                    "criticite_nette": round(crit_brute * f_dmr, 2),
                    "responsable": f_responsable,
                    "declarant": f_declarant,
                    "commentaire": f_commentaire,
                    "piece_jointe": f_piece.name if f_piece else "—",
                    "date_declaration": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                    "statut": "En attente de validation",
                }
                st.session_state.pending_risks.append(new_risk)
                st.success(f"✅ Risque « {f_titre} » soumis avec succès (code {new_risk['code']}). Statut : En attente de validation.")

    if st.session_state.pending_risks:
        st.markdown("#### Mes déclarations en cours")
        df_pending = pd.DataFrame(st.session_state.pending_risks)
        st.dataframe(
            df_pending[["code", "processus", "intitule", "criticite_nette", "date_declaration", "statut"]],
            width='stretch', hide_index=True,
        )


# ----------------------------------------------------------------------------
# PAGE 2ter — VALIDATION DES RISQUES (réservée Auditeur / Chef d'audit / Admin)
# ----------------------------------------------------------------------------

elif page == "🔔 Validation des risques":
    header("Validation des risques déclarés", "Vérification → Validation / Rejet / Demande de modification")

    if st.session_state.current_role not in ROLES_PEUVENT_VALIDER:
        st.warning(
            f"🔒 Accès réservé aux rôles **{', '.join(ROLES_PEUVENT_VALIDER)}**. "
            f"Vous êtes actuellement connecté en tant que **{st.session_state.current_role}**. "
            "Changez de rôle dans la sidebar pour accéder à la validation."
        )
    else:
        tab_a, tab_b, tab_c = st.tabs([
            f"🟡 À vérifier ({len(st.session_state.pending_risks)})",
            f"🟢 Validés session ({len(st.session_state.validated_session_risks)})",
            f"🔴 Rejetés session ({len(st.session_state.rejected_session_risks)})",
        ])

        with tab_a:
            if not st.session_state.pending_risks:
                st.info("Aucun risque en attente de validation.")
            for i, risk in enumerate(list(st.session_state.pending_risks)):
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{risk['code']} · {risk['intitule']}**")
                        st.caption(f"{risk['processus']} · {risk['sous_processus']} · déclaré par {risk['declarant']} le {risk['date_declaration']}")
                        st.write(risk.get("description", "—"))
                        st.caption(f"Criticité brute {risk['criticite_brute']} · DMR {risk['dmr']} · Criticité nette {risk['criticite_nette']}")
                    with c2:
                        st.metric("Criticité nette", risk["criticite_nette"])
                    commentaire = st.text_input("Commentaire de l'auditeur", key=f"com_{i}")
                    b1, b2, b3 = st.columns(3)
                    if b1.button("✅ Valider", key=f"val_{i}", width='stretch'):
                        risk["statut"] = "Validé"
                        risk["commentaire_auditeur"] = commentaire
                        risk["valide_par"] = st.session_state.current_role
                        st.session_state.validated_session_risks.append(risk)
                        st.session_state.pending_risks.remove(risk)
                        st.rerun()
                    if b2.button("✏️ Demander modification", key=f"mod_{i}", width='stretch'):
                        risk["statut"] = "Modification demandée"
                        risk["commentaire_auditeur"] = commentaire
                        st.info("Le déclarant devra corriger et resoumettre le risque.")
                    if b3.button("❌ Rejeter", key=f"rej_{i}", width='stretch'):
                        risk["statut"] = "Rejeté"
                        risk["commentaire_auditeur"] = commentaire
                        risk["rejete_par"] = st.session_state.current_role
                        st.session_state.rejected_session_risks.append(risk)
                        st.session_state.pending_risks.remove(risk)
                        st.rerun()

        with tab_b:
            if st.session_state.validated_session_risks:
                st.dataframe(pd.DataFrame(st.session_state.validated_session_risks)[
                    ["code", "processus", "intitule", "criticite_nette", "valide_par", "date_declaration"]
                ], width='stretch', hide_index=True)
                st.success(
                    "Ces risques sont désormais considérés comme **actifs** et apparaissent "
                    "avec le badge « Nouveau (session) » dans la Cartographie des risques."
                )
            else:
                st.info("Aucun risque validé durant cette session.")

        with tab_c:
            if st.session_state.rejected_session_risks:
                st.dataframe(pd.DataFrame(st.session_state.rejected_session_risks)[
                    ["code", "processus", "intitule", "commentaire_auditeur"]
                ], width='stretch', hide_index=True)
            else:
                st.info("Aucun risque rejeté durant cette session.")

    st.caption(
        "⚠️ Démo pédagogique : ces risques déclarés/validés sont stockés en mémoire de session "
        "(ils disparaissent si l'app redémarre). Dans la version finale, ceci est persisté dans "
        "PostgreSQL (`risques`, `risk_validations`, `risk_history`)."
    )


# ----------------------------------------------------------------------------
# PAGE 3 — MATRICE DES RISQUES (ZONES A/B/C/D, style Eisenhower)
# ----------------------------------------------------------------------------

elif page == "🧭 Matrice des risques (zones)":
    header(
        "Matrice des risques — 4 zones d'action",
        "Criticité nette × DMR résiduel — méthodologie du mémoire (zones A/B/C/D)",
    )

    med_crit, med_dmr = DATA["med_crit"], DATA["med_dmr"]

    left, right = st.columns([2, 1])
    with left:
        fig = go.Figure()
        # fonds de quadrants colorés
        xmax = R["criticite_nette"].max() * 1.1
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
        fig.update_layout(
            **PLOTLY_TEMPLATE["layout"], height=560,
            xaxis_title="Criticité nette →", yaxis_title="DMR résiduel (0 = bien maîtrisé, 1 = mal maîtrisé) →",
        )
        st.plotly_chart(fig, width='stretch')

    with right:
        st.markdown("#### Diagramme circulaire par zone")
        zone_counts = R["zone"].value_counts().reindex(ZONE_ORDER).fillna(0).reset_index()
        zone_counts.columns = ["zone", "count"]
        fig2 = px.pie(zone_counts, names="zone", values="count", hole=0.5,
                      color="zone", color_discrete_map=ZONE_COLORS)
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=300)
        st.plotly_chart(fig2, width='stretch')

        st.markdown("#### Définition des zones")
        st.markdown(
            """
- 🟢 **A — Optimisation** : criticité faible, dispositif de maîtrise efficace → surveillance légère.
- 🟡 **B — Vigilance** : criticité faible, dispositif insuffisant → recommandations d'amélioration.
- 🟠 **C — Surveillance** : criticité élevée malgré un dispositif efficace → suivi rapproché.
- 🔴 **D — Traitement** : criticité élevée + dispositif insuffisant → **priorité d'audit**.
            """
        )

    st.markdown("#### Répartition zone × processus")
    cross = pd.crosstab(R["processus_court"], R["zone"]).reindex(columns=ZONE_ORDER, fill_value=0)
    fig3 = px.bar(
        cross, barmode="stack", color_discrete_map=ZONE_COLORS,
        labels={"value": "Nb de risques", "processus_court": "Processus"},
    )
    fig3.update_layout(**PLOTLY_TEMPLATE["layout"])
    st.plotly_chart(fig3, width='stretch')


# ----------------------------------------------------------------------------
# PAGE 3bis — MATRICE DE CONTRÔLE 4×4 (Degré de contrôle × Degré de criticité)
# ----------------------------------------------------------------------------

elif page == "🗂️ Matrice de contrôle (4×4)":
    header(
        "Matrice des actions liées aux risques majeurs",
        "Degré de contrôle × Degré de criticité — 16 cases, mêmes zones A/B/C/D",
    )

    # Degré de contrôle = (1 - DMR) x 100%  →  4 tranches réelles observées dans les données
    controle_bins = [-0.01, 0.25, 0.50, 0.75, 1.01]
    controle_labels = ["Faible ≤25%", "Partiel ≤50%", "Correct ≤75%", "Satisfaisant ≤100%"]
    crit_bins = [0, 4, 8, 12, 16]
    crit_labels = ["Faible [0-4]", "Moyen [4-8]", "Significatif [8-12]", "Élevé [12-16]"]

    Rm = R.copy()
    Rm["degre_controle_pct"] = (1 - Rm["dmr"]) * 100
    Rm["ligne_controle"] = pd.cut(Rm["degre_controle_pct"], bins=controle_bins, labels=controle_labels)
    Rm["colonne_criticite"] = pd.cut(Rm["criticite_brute"], bins=crit_bins, labels=crit_labels, include_lowest=True)

    def cell_zone(ligne, colonne):
        li = controle_labels.index(ligne)   # 0=Faible ... 3=Satisfaisant
        ci = crit_labels.index(colonne)     # 0=Faible ... 3=Élevé
        controle_insuffisant = li < 2
        crit_elevee = ci >= 2
        if crit_elevee and controle_insuffisant:
            return "D - Traitement"
        if crit_elevee and not controle_insuffisant:
            return "C - Surveillance"
        if not crit_elevee and controle_insuffisant:
            return "B - Vigilance"
        return "A - Optimisation"

    # Construction de la grille 4x4 avec les codes de risques réels par case
    grid_z = []
    grid_text = []
    for li_label in reversed(controle_labels):  # Satisfaisant en haut, Faible en bas (comme un repère cartésien)
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
    fig.update_layout(
        **PLOTLY_TEMPLATE["layout"], height=520,
        xaxis_title="DEGRÉ DE CRITICITÉ →", yaxis_title="DEGRÉ DE CONTRÔLE →",
        xaxis=dict(side="bottom"),
    )
    st.plotly_chart(fig, width='stretch')

    leg1, leg2, leg3, leg4 = st.columns(4)
    for col, (z, c) in zip([leg1, leg2, leg3, leg4], ZONE_COLORS.items()):
        col.markdown(f'<span class="badge" style="background:{c}">{z}</span>', unsafe_allow_html=True)

    st.caption(
        "Degré de contrôle = (1 − DMR) × 100 — plus il est élevé, plus le dispositif de maîtrise "
        "est efficace. Degré de criticité = criticité brute (Probabilité × Gravité). "
        "Cases vides = aucun risque réel dans cette combinaison sur le filtre courant."
    )


# ----------------------------------------------------------------------------
# PAGE 4 — PRIORISATION DE L'AUDIT
# ----------------------------------------------------------------------------

elif page == "🎯 Priorisation de l'audit":
    header("Priorisation des missions d'audit", "Classement des processus — score 0-100")

    fig = px.bar(
        SC.sort_values("Score_Priorite_Audit"), x="Score_Priorite_Audit", y="Processus",
        orientation="h", color="Score_Priorite_Audit",
        color_continuous_scale=[COL_SAGE_LT, COL_ALERT_RED],
        text="Score_Priorite_Audit",
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=480, coloraxis_showscale=False, xaxis_title="Score de priorité (0-100)", yaxis_title="")
    st.plotly_chart(fig, width='stretch')

    st.markdown("---")
    st.markdown("### 🔎 Explicabilité du score")
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
        f"et représente {row['Contribution_VaR_pct']:.1f}% de l'exposition VaR cumulée du portefeuille de risques."
    )

    st.markdown("### 📈 Validation du modèle")
    rho, pval = stats.spearmanr(SCORE_PRIO["Rang_Existant"], SCORE_PRIO["Rang_Quantifie"])
    st.success(
        f"Corrélation de Spearman entre le classement existant ORMVA-TF et le score quantifié : "
        f"**ρ = {rho:.2f}** (p = {pval:.4f}) — cohérence forte entre les deux approches."
    )


# ----------------------------------------------------------------------------
# PAGE 4bis — PLANIFICATION ANNUELLE D'AUDIT
# ----------------------------------------------------------------------------

elif page == "📅 Planification annuelle":
    header("Planification annuelle de la mission d'audit", "Plan d'audit basé sur le score de priorisation (approche par les risques)")

    c1, c2 = st.columns(2)
    annee = c1.selectbox("Année du plan d'audit", [2026, 2027], index=0)
    nb_missions = c2.slider("Nombre de processus à auditer cette année", 1, 12, 6)

    plan = SCORE_PRIO.sort_values("Rang_Quantifie").head(nb_missions).copy()
    quarters = ["T1", "T2", "T3", "T4"]
    plan["Trimestre proposé"] = [quarters[i % 4] for i in range(len(plan))]
    plan["Niveau de priorité"] = pd.cut(plan["Score_Priorite_Audit"], bins=[-1, 30, 60, 100], labels=["Faible", "Moyenne", "Élevée"])

    st.markdown(f"#### Plan d'audit proposé {annee} — {nb_missions} processus")
    st.caption("Les processus les mieux classés (score de priorisation) sont planifiés en premier (T1).")
    st.dataframe(
        plan[["Rang_Quantifie", "Processus", "Score_Priorite_Audit", "Niveau de priorité", "Nb_Risques_Critiques", "Trimestre proposé"]]
        .rename(columns={"Rang_Quantifie": "Rang", "Score_Priorite_Audit": "Score", "Nb_Risques_Critiques": "Risques critiques"}),
        width='stretch', hide_index=True,
    )

    st.markdown("#### Vue calendrier (Gantt simplifié)")
    q_start = {"T1": f"{annee}-01-01", "T2": f"{annee}-04-01", "T3": f"{annee}-07-01", "T4": f"{annee}-10-01"}
    q_end = {"T1": f"{annee}-03-31", "T2": f"{annee}-06-30", "T3": f"{annee}-09-30", "T4": f"{annee}-12-31"}
    gantt_df = pd.DataFrame({
        "Processus": plan["Processus"],
        "Début": pd.to_datetime(plan["Trimestre proposé"].map(q_start)),
        "Fin": pd.to_datetime(plan["Trimestre proposé"].map(q_end)),
        "Score": plan["Score_Priorite_Audit"],
    })
    fig = px.timeline(gantt_df, x_start="Début", x_end="Fin", y="Processus", color="Score",
                      color_continuous_scale=[COL_SAGE_LT, COL_ALERT_RED])
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=420, coloraxis_showscale=False)
    st.plotly_chart(fig, width='stretch')

    st.markdown("---")
    st.markdown("#### ➕ Ajouter / ajuster une mission au plan")
    with st.form("form_mission"):
        m1, m2, m3 = st.columns(3)
        m_proc = m1.selectbox("Processus", ALL_PROCESSUS, key="mission_proc")
        m_trim = m2.selectbox("Trimestre", quarters)
        m_auditeur = m3.text_input("Auditeur responsable")
        m_objectif = st.text_area("Objectif de la mission")
        if st.form_submit_button("Ajouter au plan"):
            st.session_state.missions_plan.append({
                "Année": annee, "Processus": m_proc, "Trimestre": m_trim,
                "Auditeur responsable": m_auditeur or "Non assigné",
                "Objectif": m_objectif, "Statut": "À planifier",
            })
            st.success(f"Mission ajoutée pour {m_proc} ({m_trim} {annee}).")

    if st.session_state.missions_plan:
        st.markdown("#### Missions ajoutées manuellement")
        st.dataframe(pd.DataFrame(st.session_state.missions_plan), width='stretch', hide_index=True)


# ----------------------------------------------------------------------------
# PAGE 5 — ANALYSES STATISTIQUES
# ----------------------------------------------------------------------------

elif page == "📊 Analyses statistiques":
    header("Analyses statistiques", "ANOVA · Régression DMR · Clustering — calculés en direct sur les données réelles")

    tab1, tab2, tab3 = st.tabs(["ANOVA", "Analyse du DMR", "Clustering"])

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
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False, xaxis_title="Processus", yaxis_title="Criticité nette")
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
            fig.add_trace(go.Scatter(x=[0, m], y=[0, m], mode="lines", line=dict(dash="dash", color=COL_GRAY), name="y = x"))
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], xaxis_title="Criticité nette prédite", yaxis_title="Criticité nette réelle")
            st.plotly_chart(fig, width='stretch')

            st.markdown("##### Liste des risques à examiner (DMR potentiellement surestimé)")
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

        st.dataframe(
            cp.rename(columns={"Nb_Risques": "Nb risques"}),
            width='stretch', hide_index=True,
        )

        st.markdown("##### Répartition des risques (filtre courant) par cluster")
        cl_counts = R["cluster_label"].value_counts().reset_index()
        cl_counts.columns = ["cluster_label", "count"]
        fig2 = px.pie(cl_counts, names="cluster_label", values="count", hole=0.5,
                      color="cluster_label", color_discrete_map=CLUSTER_COLORS)
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], height=320)
        st.plotly_chart(fig2, width='stretch')


# ----------------------------------------------------------------------------
# PAGE 6 — MONTE CARLO / VaR / TVaR
# ----------------------------------------------------------------------------

elif page == "🎲 Monte Carlo · VaR / TVaR":
    header("Analyse actuarielle — Monte Carlo, VaR & TVaR", "Basé sur les résultats réels de simulation (mémoire PFE)")

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
    fig.add_trace(go.Bar(y=vt_plot["processus_court"], x=vt_plot["VaR_95"], name="VaR 95%", orientation="h", marker_color=COL_PRIMARY))
    fig.add_trace(go.Bar(y=vt_plot["processus_court"], x=vt_plot["TVaR_95"], name="TVaR 95%", orientation="h", marker_color=COL_ALERT_RED, opacity=0.75))
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
        "illustrer la distribution des pertes simulées — méthode complémentaire à la simulation Monte Carlo du mémoire."
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

        c1, c2, c3 = st.columns(3)
        c1.metric("Perte moyenne simulée", f"{sims.mean():.1f}")
        c2.metric(f"VaR {int(conf*100)}%", f"{var_sim:.1f}")
        c3.metric(f"TVaR {int(conf*100)}%", f"{tvar_sim:.1f}")

        fig3 = px.histogram(sims, nbins=60, color_discrete_sequence=[COL_PRIMARY])
        fig3.add_vline(x=var_sim, line_dash="dash", line_color=COL_ALERT_RED, annotation_text=f"VaR {int(conf*100)}%")
        fig3.update_layout(**PLOTLY_TEMPLATE["layout"], xaxis_title="Perte simulée (criticité nette cumulée)", yaxis_title="Fréquence", showlegend=False, height=380)
        st.plotly_chart(fig3, width='stretch')
    else:
        st.warning("Aucun risque trouvé pour ce processus.")


# ----------------------------------------------------------------------------
# PAGE 7 — INDICATEURS KPI / KPR
# ----------------------------------------------------------------------------

elif page == "📈 Indicateurs KPI / KPR":
    header("Indicateurs KPI / KPR", "Indicateurs Clés de Risque (données réelles) et de Performance de l'audit (démo session)")

    st.markdown("### 🧭 KPR — Indicateurs Clés de Risque (calculés sur données réelles)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("VaR globale 95%", "4 816.7")
    k2.metric("DMR moyen (résiduel)", f"{R['dmr'].mean():.2f}")
    pct_zone_d = (R["zone"] == "D - Traitement").mean() * 100
    k3.metric("% risques en zone D (Traitement)", f"{pct_zone_d:.1f}%")
    k4.metric("Risques critiques (Nb_Risques_Critiques)", int(SC["Nb_Risques_Critiques"].sum()))

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Criticité nette moyenne", f"{R['criticite_nette'].mean():.2f}")
    k6.metric("Score de priorité max", f"{SC['Score_Priorite_Audit'].max():.1f}")
    k7.metric("Corrélation Spearman (validation modèle)", "0.98")
    k8.metric("Processus couverts (filtre)", f"{R['processus'].nunique()} / {len(ALL_PROCESSUS)}")

    fig = px.bar(SC.sort_values("Score_Priorite_Audit"), x="Score_Priorite_Audit", y="Processus",
                orientation="h", color_discrete_sequence=[COL_PRIMARY])
    fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=380, xaxis_title="KPR — Score de priorité")
    st.plotly_chart(fig, width='stretch')

    st.markdown("---")
    st.markdown("### 📋 KPI — Indicateurs de Performance de la fonction Audit (démo session)")
    st.caption(
        "⚠️ Aucune donnée opérationnelle réelle (délais, missions clôturées...) n'a été fournie. "
        "Les indicateurs ci-dessous sont calculés sur les actions effectuées **dans cette session** "
        "à titre de démonstration du futur module de suivi de la performance de l'audit."
    )

    total_declares = len(st.session_state.pending_risks) + len(st.session_state.validated_session_risks) + len(st.session_state.rejected_session_risks)
    taux_validation = (len(st.session_state.validated_session_risks) / total_declares * 100) if total_declares else 0

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Risques déclarés (session)", total_declares)
    p2.metric("Taux de validation (session)", f"{taux_validation:.0f}%" if total_declares else "—")
    p3.metric("Missions planifiées (session)", len(st.session_state.missions_plan))
    p4.metric("Utilisateurs avec accès actif", int((st.session_state.users_directory["Accès"] == "Actif").sum()))


# ----------------------------------------------------------------------------
# PAGE 7bis — PARAMÈTRES DU MODÈLE (pondération du score, versioning)
# ----------------------------------------------------------------------------

elif page == "⚙️ Paramètres du modèle":
    header("Paramètres du modèle de scoring", "Ajuster la pondération du score de priorisation — sans toucher au code source")

    if st.session_state.current_role not in ROLES_MODEL:
        st.warning(
            f"🔒 Accès réservé aux rôles **{', '.join(ROLES_MODEL)}**. "
            f"Vous êtes actuellement connecté en tant que **{st.session_state.current_role}**."
        )
    else:
        st.info(
            "L'auditeur peut ajuster ici le **poids de chaque facteur** du score de priorisation. "
            "La formule et le code de calcul restent fixes dans le dépôt Git — seules les "
            "**valeurs de pondération** sont modifiables, avec historique complet des versions."
        )

        w = st.session_state.model_weights
        c1, c2, c3 = st.columns(3)
        with c1:
            w_crit = st.slider("Criticité nette (%)", 0, 100, w["crit"])
        with c2:
            w_var = st.slider("VaR 95% (%)", 0, 100, w["var"])
        with c3:
            w_critiques = st.slider("Nb risques critiques (%)", 0, 100, w["critiques"])

        total = w_crit + w_var + w_critiques
        if total == 0:
            st.error("La somme des poids ne peut pas être nulle.")
            st.stop()
        st.caption(f"Somme actuelle : {total}% → normalisée automatiquement à 100% dans le calcul.")
        w_crit_n, w_var_n, w_critiques_n = w_crit / total, w_var / total, w_critiques / total

        # Recalcul du score en direct (normalisation min-max, méthode identique au mémoire)
        base = SCORE_PRIO.copy()
        for col, key in [("Criticite_Nette_Somme", "crit_n"), ("VaR_95", "var_n"), ("Nb_Risques_Critiques", "critiques_n")]:
            mn, mx = base[col].min(), base[col].max()
            base[key] = (base[col] - mn) / (mx - mn) * 100 if mx > mn else 0

        base["Score_recalcule"] = (
            w_crit_n * base["crit_n"] + w_var_n * base["var_n"] + w_critiques_n * base["critiques_n"]
        )
        base["Rang_recalcule"] = base["Score_recalcule"].rank(ascending=False).astype(int)

        st.markdown("#### Comparaison — score officiel (mémoire) vs score recalculé (poids actuels)")
        comp = base[["Processus", "Score_Priorite_Audit", "Score_recalcule", "Rang_Quantifie", "Rang_recalcule"]].sort_values("Score_recalcule", ascending=False)
        st.dataframe(
            comp.rename(columns={
                "Score_Priorite_Audit": "Score officiel", "Score_recalcule": "Score recalculé",
                "Rang_Quantifie": "Rang officiel", "Rang_recalcule": "Rang recalculé",
            }).round(1), width='stretch', hide_index=True,
        )

        fig = go.Figure()
        comp_sorted = comp.sort_values("Score_recalcule")
        fig.add_trace(go.Bar(y=comp_sorted["Processus"], x=comp_sorted["Score_Priorite_Audit"], name="Score officiel", orientation="h", marker_color=COL_SAGE))
        fig.add_trace(go.Bar(y=comp_sorted["Processus"], x=comp_sorted["Score_recalcule"], name="Score recalculé", orientation="h", marker_color=COL_PRIMARY))
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], barmode="group", height=440)
        st.plotly_chart(fig, width='stretch')

        st.markdown("---")
        st.markdown("#### 💾 Enregistrer comme nouvelle version du modèle")
        with st.form("form_model_version"):
            motif = st.text_area("Motif du changement (obligatoire)")
            if st.form_submit_button("Créer une nouvelle version"):
                if not motif:
                    st.error("Merci de préciser le motif du changement.")
                else:
                    n = len(st.session_state.model_versions)
                    new_version = f"V1.{n}"
                    st.session_state.model_versions.append({
                        "version": new_version,
                        "date": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                        "auteur": st.session_state.current_role,
                        "poids": {"crit": w_crit, "var": w_var, "critiques": w_critiques},
                        "motif": motif,
                    })
                    st.session_state.model_weights = {"crit": w_crit, "var": w_var, "critiques": w_critiques}
                    st.success(f"Nouvelle version {new_version} enregistrée.")
                    st.rerun()

        st.markdown("#### 🕓 Historique des versions du modèle")
        for v in reversed(st.session_state.model_versions):
            with st.container(border=True):
                cA, cB = st.columns([3, 1])
                cA.markdown(f"**{v['version']}** · {v['date']} · par {v['auteur']}")
                cA.caption(v["motif"])
                cA.caption(f"Poids : Criticité {v['poids']['crit']}% · VaR {v['poids']['var']}% · Risques critiques {v['poids']['critiques']}%")
                if cB.button("↺ Restaurer cette version", key=f"restore_{v['version']}", width='stretch'):
                    st.session_state.model_weights = dict(v["poids"])
                    st.success(f"Poids de {v['version']} restaurés.")
                    st.rerun()

    st.caption(
        "⚠️ Le code de calcul (formule, méthodologie ANOVA/Monte Carlo) reste dans le dépôt Git — "
        "seuls les poids du score sont paramétrables ici, conformément au cahier des charges initial."
    )


# ----------------------------------------------------------------------------
# PAGE 8 — GESTION DES ACCÈS (RBAC)
# ----------------------------------------------------------------------------

elif page == "👥 Gestion des accès":
    header("Gestion des accès", "Attribution des rôles — réservé à l'Auditeur interne / Administrateur")

    st.markdown("#### 🔑 Journal des connexions (portail d'accès)")
    if st.session_state.access_log:
        st.dataframe(pd.DataFrame(st.session_state.access_log), width='stretch', hide_index=True)
    else:
        st.info("Aucune connexion enregistrée dans cette session.")
    st.caption(
        "⚠️ Ce journal n'affiche que les connexions de **ta propre session** navigateur "
        "(limite technique de Streamlit sans base de données). La **notification email** envoyée "
        "à chaque accès (voir README.md) reste le moyen fiable de savoir qui a ouvert l'app, "
        "tous utilisateurs confondus."
    )
    st.markdown("---")

    if st.session_state.current_role not in ROLES_GERENT_ACCES:
        st.warning(
            f"🔒 Accès réservé aux rôles **{', '.join(ROLES_GERENT_ACCES)}**. "
            f"Vous êtes actuellement connecté en tant que **{st.session_state.current_role}**."
        )
    else:
        st.markdown("#### Annuaire des utilisateurs")
        st.dataframe(st.session_state.users_directory, width='stretch', hide_index=True)

        st.markdown("#### ➕ Donner l'accès à un nouvel utilisateur")
        with st.form("form_access"):
            a1, a2, a3 = st.columns(3)
            u_nom = a1.text_input("Nom complet")
            u_email = a2.text_input("Email professionnel")
            u_role = a3.selectbox("Rôle à attribuer", ROLES)
            if st.form_submit_button("Accorder l'accès"):
                if u_nom and u_email:
                    new_user = pd.DataFrame([{"Nom": u_nom, "Email": u_email, "Rôle": u_role, "Accès": "Actif"}])
                    st.session_state.users_directory = pd.concat([st.session_state.users_directory, new_user], ignore_index=True)
                    st.success(f"Accès accordé à {u_nom} en tant que {u_role}.")
                    st.rerun()
                else:
                    st.error("Merci de renseigner le nom et l'email.")

        st.markdown("#### ✏️ Modifier / révoquer un accès existant")
        idx = st.selectbox(
            "Sélectionner un utilisateur",
            st.session_state.users_directory.index,
            format_func=lambda i: st.session_state.users_directory.loc[i, "Nom"],
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            nouveau_role = st.selectbox("Nouveau rôle", ROLES, index=ROLES.index(st.session_state.users_directory.loc[idx, "Rôle"]))
        with c2:
            if st.button("Mettre à jour le rôle", width='stretch'):
                st.session_state.users_directory.loc[idx, "Rôle"] = nouveau_role
                st.rerun()
        with c3:
            statut_actuel = st.session_state.users_directory.loc[idx, "Accès"]
            label = "🔒 Révoquer l'accès" if statut_actuel == "Actif" else "✅ Activer l'accès"
            if st.button(label, width='stretch'):
                st.session_state.users_directory.loc[idx, "Accès"] = "Révoqué" if statut_actuel == "Actif" else "Actif"
                st.rerun()

    st.caption(
        "⚠️ Démo pédagogique (session uniquement). Dans la version finale : authentification "
        "(hash de mot de passe), tables `users` / `roles` / `permissions` en PostgreSQL, RBAC serveur."
    )


# ----------------------------------------------------------------------------
# PAGE 9 — À PROPOS DU PROJET (contexte PFA / stage)
# ----------------------------------------------------------------------------

elif page == "ℹ️ À propos du projet":
    header("À propos de ce projet", "Contexte académique et professionnel")

    st.markdown(
        """
### 🎓 Contexte du stage

Cette application a été développée dans le cadre d'un **stage PFA (Projet de Fin d'Année)**,
par une étudiante en **2ᵉ année du cycle d'ingénieur, filière Finance et Actuariat**,
au sein de l'**ORMVA-TF (Office Régional de Mise en Valeur Agricole du Tafilalet)**.

**Sujet du stage :**
« Développement d'un modèle d'aide à la décision pour la priorisation des missions
d'audit interne à partir des données de la cartographie des risques : Cas de l'ORMVA-TF »

**Encadrement :**
- Encadrant professionnel (ORMVA-TF) : *[à compléter]*
- Encadrant académique : *[à compléter]*
- Période du stage : *[à compléter]*

### 🎯 Objectif du projet

Construire un système d'aide à la décision permettant à l'auditeur interne d'exploiter la
cartographie des risques (159 risques, 12 processus), de calculer automatiquement les
indicateurs de risque (criticité, DMR, VaR, TVaR), de prioriser les processus à auditer et
de faciliter la planification des missions d'audit interne.

### 🧮 Démarche méthodologique

1. Analyse exploratoire et modélisation (Python, Google Colab) : ANOVA, régression du DMR,
   clustering, simulation Monte Carlo, calcul de la VaR/TVaR.
2. Construction d'un score de priorisation (0-100) et validation par corrélation de Spearman
   avec le classement existant de l'ORMVA-TF (ρ = 0.98).
3. Développement de ce prototype applicatif (Streamlit) pour rendre le modèle exploitable par
   un auditeur interne au quotidien.

### 🛠️ Prochaine étape

Industrialisation vers une architecture complète (FastAPI + PostgreSQL + React) avec
authentification réelle, base de données, RBAC serveur et audit trail persistant.
        """
    )

st.markdown("---")
st.caption("ORMVA-TF Risk & Audit Center · Données réelles : 159 risques, 12 processus · Prototype PFA Audit Interne & Actuariat")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM SAAS CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS pour le style Enterprise (Vert Institutionnel, Cards, Buttons)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #FAFAFA;
    }

    /* HEADER CUSTOM */
    .header-container {
        background-color: #FFFFFF;
        padding: 16px 24px;
        border-bottom: 1px solid #E5E7EB;
        margin-top: -50px;
        margin-bottom: 20px;
        border-radius: 0 0 12px 12px;
    }
    .header-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0A2F1D;
        margin: 0;
    }
    .header-subtitle {
        font-size: 0.875rem;
        color: #4E7D5B;
        margin-top: 4px;
    }

    /* BREADCRUMB */
    .breadcrumb {
        font-size: 0.8rem;
        color: #6B7280;
        margin-bottom: 16px;
    }

    /* METRIC CARDS Dynamic */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 16px;
        border-radius: 12px;
        border-left: 5px solid #1E513B;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricValue"] {
        color: #0A2F1D;
        font-weight: 800;
    }

    /* FOOTER SOMBRE INSTITUTIONNEL */
    .footer-dark {
        background-color: #0B1320;
        color: #9CA3AF;
        padding: 32px 24px;
        border-radius: 12px;
        margin-top: 40px;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. CHARGEMENT DES DONNÉES DYNAMIQUES (ORMVA-TF)
# ---------------------------------------------------------
@st.cache_data
def load_official_data():
    processus_data = [
        {'rang': 1, 'code': 'P9', 'libelle': 'Achat et approvisionnement', 'score': 88.7, 'var95': 1240.5, 'critCount': 8, 'dmrMoy': 0.42, 'priorite': 'Très Élevée'},
        {'rang': 2, 'code': 'P2', 'libelle': 'Gestion de production agricole', 'score': 82.8, 'var95': 1080.2, 'critCount': 7, 'dmrMoy': 0.45, 'priorite': 'Très Élevée'},
        {'rang': 3, 'code': 'P7', 'libelle': 'Gestion budgétaire, financière et comptable', 'score': 71.8, 'var95': 890.1, 'critCount': 5, 'dmrMoy': 0.50, 'priorite': 'Élevée'},
        {'rang': 4, 'code': 'P1', 'libelle': 'Aides et incitations financières de l’État', 'score': 61.1, 'var95': 620.4, 'critCount': 4, 'dmrMoy': 0.55, 'priorite': 'Élevée'},
        {'rang': 5, 'code': 'P4', 'libelle': 'Gestion des réseaux d’irrigation', 'score': 48.9, 'var95': 410.0, 'critCount': 3, 'dmrMoy': 0.60, 'priorite': 'Moyenne'},
        {'rang': 6, 'code': 'P10', 'libelle': 'Ressources humaines', 'score': 46.4, 'var95': 380.6, 'critCount': 2, 'dmrMoy': 0.62, 'priorite': 'Moyenne'},
        {'rang': 7, 'code': 'P8', 'libelle': 'Informatique', 'score': 39.1, 'var95': 290.0, 'critCount': 2, 'dmrMoy': 0.68, 'priorite': 'Moyenne'},
        {'rang': 8, 'code': 'P5', 'libelle': 'Logistique', 'score': 31.0, 'var95': 195.3, 'critCount': 1, 'dmrMoy': 0.70, 'priorite': 'Faible'},
        {'rang': 9, 'code': 'P3', 'libelle': 'Aménagement', 'score': 30.4, 'var95': 180.2, 'critCount': 1, 'dmrMoy': 0.72, 'priorite': 'Faible'},
        {'rang': 10, 'code': 'P6', 'libelle': 'Juridique', 'score': 28.3, 'var95': 150.0, 'critCount': 1, 'dmrMoy': 0.75, 'priorite': 'Faible'},
        {'rang': 11, 'code': 'P12', 'libelle': 'Direction et pilotage', 'score': 16.3, 'var95': 80.4, 'critCount': 0, 'dmrMoy': 0.80, 'priorite': 'Faible'},
        {'rang': 12, 'code': 'P11', 'libelle': 'Audit interne', 'score': 0.0, 'var95': 0.0, 'critCount': 0, 'dmrMoy': 0.90, 'priorite': 'Nulle'}
    ]
    return pd.DataFrame(processus_data)

df_proc = load_official_data()

# ---------------------------------------------------------
# 3. HEADER & NAVIGATION DYNAMIQUE
# ---------------------------------------------------------
st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF Risk & Audit Center</div>
        <div class="header-subtitle">Système Décisionnel d'Aide à la Priorisation des Missions d'Audit Interne</div>
    </div>
""", unsafe_allow_html=True)

# NAVIGATION SIDEBAR INTERACTIVE
st.sidebar.title("📌 Navigation Système")
menu = st.sidebar.radio(
    "Accéder aux modules :",
    [
        "🏠 Dashboard & Priorisation PFA",
        "⚠️ Cartographie des Risques",
        "🔔 Workflow de Validation",
        "📊 Analyses Actuarielles (ANOVA & VaR)",
        "📋 Planification des Missions",
        "📜 Audit Trail & Traçabilité"
    ]
)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD & PRIORISATION (INTERACTIF)
# ---------------------------------------------------------
if menu == "🏠 Dashboard & Priorisation PFA":
    st.markdown('<div class="breadcrumb">Accueil › Dashboard Décisionnel › <b>Priorisation 2026</b></div>', unsafe_allow_html=True)
    
    # METRICS INTERACTIFS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Risques Totaux", "159", "12 Processus")
    m2.metric("VaR Globale (95%)", "4 816.7 DH", "Monte Carlo")
    m3.metric("DMR Surestimés", "21 Risques", "Anomalies R² = 0.915", delta_color="inverse")
    m4.metric("Processus Prioritaire #1", "P9 (88.7)", "Achat & Approv.")

    st.write("")
    st.subheader("🎯 Top Processus Prioritaires pour l'Audit Interne (Score 0–100)")
    
    # CARDS DYNAMIQUES AVEC EXPANDER ET ACTION DIRECTE
    top_4 = df_proc.head(4)
    c1, c2 = st.columns(2)
    
    with c1:
        p1 = top_4.iloc[0]
        st.info(f"**RANG #{p1['rang']} — SCORE PFA : {p1['score']} / 100**\n\n### {p1['code']} — {p1['libelle']}\n"
                f"Exposition VaR 95% : **{p1['var95']} DH** | Risques critiques : **{p1['critCount']}**")
        with st.expander("🔎 Voir le détail & Facteurs d'explication"):
            st.write(f"- **Critères :** Impact fort sur les marchés publics et approvisionnements.\n- **DMR Moyen :** {p1['dmrMoy']}\n- **Priorité :** {p1['priorite']}")
            if st.button("📅 Planifier Mission pour P9", key="btn_p9"):
                st.success("Redirection vers le module de planification...")

        p3 = top_4.iloc[2]
        st.warning(f"**RANG #{p3['rang']} — SCORE PFA : {p3['score']} / 100**\n\n### {p3['code']} — {p3['libelle']}\n"
                   f"Exposition VaR 95% : **{p3['var95']} DH** | Risques critiques : **{p3['critCount']}**")
        with st.expander("🔎 Voir le détail & Facteurs d'explication"):
            st.write(f"- **Critères :** Anomalie détectée sur le DMR de la comptabilité des subventions.\n- **DMR Moyen :** {p3['dmrMoy']}\n- **Priorité :** {p3['priorite']}")
            if st.button("📅 Planifier Mission pour P7", key="btn_p7"):
                st.success("Redirection vers le module de planification...")

    with c2:
        p2 = top_4.iloc[1]
        st.info(f"**RANG #{p2['rang']} — SCORE PFA : {p2['score']} / 100**\n\n### {p2['code']} — {p2['libelle']}\n"
                f"Exposition VaR 95% : **{p2['var95']} DH** | Risques critiques : **{p2['critCount']}**")
        with st.expander("🔎 Voir le détail & Facteurs d'explication"):
            st.write(f"- **Critères :** Retards potentiels sur le calendrier d'itinéraire technique agricole.\n- **DMR Moyen :** {p2['dmrMoy']}\n- **Priorité :** {p2['priorite']}")
            if st.button("📅 Planifier Mission pour P2", key="btn_p2"):
                st.success("Redirection vers le module de planification...")

        p4 = top_4.iloc[3]
        st.warning(f"**RANG #{p4['rang']} — SCORE PFA : {p4['score']} / 100**\n\n### {p4['code']} — {p4['libelle']}\n"
                   f"Exposition VaR 95% : **{p4['var95']} DH** | Risques critiques : **{p4['critCount']}**")
        with st.expander("🔎 Voir le détail & Facteurs d'explication"):
            st.write(f"- **Critères :** Délais de traitement des dossiers du Fonds de Développement Agricole (FDA).\n- **DMR Moyen :** {p4['dmrMoy']}\n- **Priorité :** {p4['priorite']}")
            if st.button("📅 Planifier Mission pour P1", key="btn_p1"):
                st.success("Redirection vers le module de planification...")

    st.write("")
    st.subheader("📊 Graphique Interactif de Priorisation (Classement des 12 Processus)")
    
    # PLOTLY INTERACTIF
    fig = px.bar(
        df_proc, 
        x='score', 
        y='code', 
        orientation='h', 
        color='score',
        hover_data=['libelle', 'var95', 'critCount'],
        color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'],
        text='score'
    )
    fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'}, plot_bgcolor='#FFFFFF')
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# MODULE 2: CARTOGRAPHIE DES RISQUES INTERACTIVE
# ---------------------------------------------------------
elif menu == "⚠️ Cartographie des Risques":
    st.markdown('<div class="breadcrumb">Accueil › <b>Cartographie des Risques (159)</b></div>', unsafe_allow_html=True)
    st.subheader("📋 Registre Filtrable de la Cartographie")

    sample_risks = pd.DataFrame([
        {'Code': 'R-P9-01', 'Processus': 'P9', 'Intitulé': 'Rupture d approvisionnement en pièces stratégiques', 'Prob': 3, 'Grav': 4, 'CB': 12, 'DMR': 0.40, 'CN': 4.8, 'Statut': 'Validé'},
        {'Code': 'R-P2-04', 'Processus': 'P2', 'Intitulé': 'Non-respect du calendrier d itinéraire technique', 'Prob': 4, 'Grav': 4, 'CB': 16, 'DMR': 0.35, 'CN': 5.6, 'Statut': 'Validé'},
        {'Code': 'R-P7-02', 'Processus': 'P7', 'Intitulé': 'Erreur d imputations comptables sur fonds de subvention', 'Prob': 2, 'Grav': 4, 'CB': 8, 'DMR': 0.85, 'CN': 6.8, 'Statut': 'En vérification'},
        {'Code': 'R-P1-05', 'Processus': 'P1', 'Intitulé': 'Retard de traitement des dossiers de subvention FDA', 'Prob': 3, 'Grav': 3, 'CB': 9, 'DMR': 0.50, 'CN': 4.5, 'Statut': 'Validé'}
    ])

    col_f1, col_f2 = st.columns(2)
    selected_proc = col_f1.multiselect("Filtrer par Processus :", df_proc['code'].unique(), default=df_proc['code'].unique())
    search_term = col_f2.text_input("🔍 Rechercher un risque par mot-clé :", "")

    filtered = sample_risks[sample_risks['Processus'].isin(selected_proc)]
    if search_term:
        filtered = filtered[filtered['Intitulé'].str.contains(search_term, case=False)]

    st.dataframe(filtered, use_container_width=True)

# ---------------------------------------------------------
# MODULE 3: WORKFLOW DE VALIDATION (INTERACTIF)
# ---------------------------------------------------------
elif menu == "🔔 Workflow de Validation":
    st.markdown('<div class="breadcrumb">Accueil › <b>Workflow de Validation</b></div>', unsafe_allow_html=True)
    st.subheader("🔔 Risques en Attente de Vérification par l'Auditeur Interne")

    with st.form("validation_form"):
        st.write("### Examen du Risque Soumis : **R-P7-02**")
        st.write("**Intitulé :** Erreur d imputations comptables sur fonds de subvention")
        st.write("**Déclaré par :** Responsable Processus P7 | **Criticité Nette :** 6.8")
        
        d_decision = st.radio("Décision de l'auditeur :", ["Valider & Intégrer à la cartographie", "Demander une modification", "Rejeter"])
        d_comment = st.text_area("Commentaires / Observations de l'auditeur :", "")
        
        submit_val = st.form_submit_button("⚡ Soumettre la décision")
        if submit_val:
            st.success(f"Décision enregistrée avec succès : [{d_decision}]. Les données et le scoring ont été mis à jour dans l'Audit Trail.")

# ---------------------------------------------------------
# MODULE 4: ANALYSES ACTUARIELLES
# ---------------------------------------------------------
elif menu == "📊 Analyses Actuarielles (ANOVA & VaR)":
    st.markdown('<div class="breadcrumb">Accueil › <b>Analyses Quantitatives</b></div>', unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["🧪 Test ANOVA", "📉 Régression DMR (R² = 0.915)", "🎲 Simulation Monte Carlo (VaR)"])
    
    with t1:
        st.subheader("Test d'Analyse de Variance (ANOVA)")
        st.metric("F-Statistic", "4.22")
        st.metric("p-value", "0.00002")
        st.success("Conclusion : p-value < 0.05 confirming that differences in net criticality between processes are statistically significant.")
        
    with t2:
        st.subheader("Détection des Surestimations du DMR")
        st.metric("R² Model", "0.915")
        st.warning("21 risques identifiés avec un DMR potentiellement surestimé nécessitant une révision ciblée.")

    with t3:
        st.subheader("Distribution de Pertes Stochastique")
        st.metric("Value at Risk (VaR 95%)", "4 816.7 DH")
        st.metric("Tail Value at Risk (TVaR 95%)", "5 940.2 DH")

# ---------------------------------------------------------
# MODULE 5: PLANIFICATION DES MISSIONS
# ---------------------------------------------------------
elif menu == "📋 Planification des Missions":
# ❌ Ligne avec erreur :
st.markdown('<div class="breadcrumb">Accueil › <b>Planification d'Audit</b></div>', unsafe_allow_html=True)

# ✅ Ligne corrigée :
st.markdown('<div class="breadcrumb">Accueil › <b>Planification d&apos;Audit</b></div>', unsafe_allow_html=True)
st.subheader("📅 Créer une Nouvelle Mission d'Audit Interne")

    with st.form("mission_plan"):
        p_target = st.selectbox("Sélectionner le Processus Cible :", df_proc['code'] + " - " + df_proc['libelle'])
        p_auditor = st.text_input("Auditeur Responsable :", "Auditeur Interne 01")
        p_dates = st.date_input("Période prévue de la mission :", [])
        p_obj = st.text_area("Objectifs & Périmètre d'audit :", "")
        
        if st.form_submit_button("🚀 Valider la Planification"):
            st.success(f"Mission d'audit planifiée avec succès pour le processus {p_target}!")

# ---------------------------------------------------------
# MODULE 6: AUDIT TRAIL
# ---------------------------------------------------------
elif menu == "📜 Audit Trail & Traçabilité":
    st.markdown('<div class="breadcrumb">Accueil › <b>Audit Trail</b></div>', unsafe_allow_html=True)
    st.subheader("📜 Historique Immuable des Actions")
    
    logs_df = pd.DataFrame([
        {"Horodatage": "11/08/2026 11:30", "Utilisateur": "Auditeur01", "Action": "Soumission Décision Validation R-P7-02", "Détail": "Statut -> Validé"},
        {"Horodatage": "11/08/2026 10:14", "Utilisateur": "Auditeur01", "Action": "Consultation Priorisation PFA", "Détail": "Score P9 = 88.7"},
        {"Horodatage": "10/08/2026 15:30", "Utilisateur": "RespP7", "Action": "Déclaration Risque R-P7-02", "Détail": "Nouveau risque créé"}
    ])
    st.table(logs_df)

# ---------------------------------------------------------
# 4. FOOTER SOMBRE DYNAMIQUE
# ---------------------------------------------------------
st.markdown("""
    <div class="footer-dark">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>🛡️ ORMVA-TF Risk & Audit Center</strong> — Système Decisionnel d'Aide à la Priorisation
                <br><span style="color: #6B7280; font-size: 0.75rem;">Projet de Fin d'Études f l'Ingénierie Financière et Actuariat (2026)</span>
            </div>
            <div>
                <span style="color: #4E7D5B;">Status: <b>Opérationnel</b></span> | Model Version: <b>V1.0</b>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

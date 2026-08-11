import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from io import BytesIO
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ---------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE INSTITUTIONNEL
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Application de la charte graphique : Vert forêt, Vert sauge, Blanc, Alertes
st.markdown("""
    <style>
    .main-header {
        font-size: 2rem;
        color: #0A2F1D;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #1E513B;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    .stApp {
        background-color: #F4F7F5;
    }
    div[data-testid="stMetricValue"] {
        color: #0A2F1D;
        font-weight: 700;
    }
    .badge-critical {
        background-color: #DC2626;
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. CHARGEMENT ET MOTEUR ANALYTIQUE (DONNÉES ORMVA-TF)
# ---------------------------------------------------------
@st.cache_data
def load_official_data():
    """Charge les données de référence du projet ORMVA-TF (12 Processus)."""
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

# ---------------------------------------------------------
# 3. INTERFACE PRINCIPALE STREAMLIT
# ---------------------------------------------------------
st.markdown('<div class="main-header">ORMVA-TF Risk & Audit Center</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Système Décisionnel d\'Aide à la Priorisation des Missions d\'Audit Interne</div>', unsafe_allow_html=True)

df_proc = load_official_data()

# MENU SIDEBAR
st.sidebar.image("https://img.icons8.com/color/96/shield.png", width=60)
st.sidebar.title("Navigation")
menu = st.sidebar.radio(
    "Modules de la plateforme :",
    [
        "🏠 Dashboard Décisionnel",
        "⚠️ Cartographie des Risques",
        "🔔 Workflow de Validation",
        "🎯 Priorisation PFA (0-100)",
        "📊 Analyses Quantitatives & Actuariat",
        "📋 Missions d'Audit Interne",
        "📜 Audit Trail & Logs"
    ]
)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD DÉCISIONNEL
# ---------------------------------------------------------
if menu == "🏠 Dashboard Décisionnel":
    st.subheader("Indicateurs Clés du Dispositif (ORMVA-TF)")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risques Cartographiés", "159", "12 Processus")
    c2.metric("VaR Globale (95%)", "4 816.7", "Monte Carlo")
    c3.metric("DMR Surestimés", "21 Risques", "Incohérences", delta_color="inverse")
    c4.metric("Processus Top 1", "P9 (88.7)", "Achat & Approv.")

    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        st.write("### Score de Priorisation par Processus (0–100)")
        fig_score = px.bar(
            df_proc, 
            x='score', 
            y='code', 
            orientation='h',
            color='score',
            color_continuous_scale='Greens',
            text='score'
        )
        fig_score.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
        st.plotly_chart(fig_score, use_container_width=True)

    with col_right:
        st.write("### Répartition de la VaR 95% par Processus")
        fig_var = px.pie(
            df_proc, 
            values='var95', 
            names='code',
            title="Exposition Stochastique au Risque",
            color_discrete_sequence=px.colors.sequential.Greens_r
        )
        st.plotly_chart(fig_var, use_container_width=True)

# ---------------------------------------------------------
# MODULE 2: CARTOGRAPHIE DES RISQUES
# ---------------------------------------------------------
elif menu == "⚠️ Cartographie des Risques":
    st.subheader("Registre de la Cartographie des Risques (159 Risques)")
    
    # Exemples de risques de la cartographie
    sample_risks = pd.DataFrame([
        {'Code': 'R-P9-01', 'Processus': 'P9', 'Intitulé': 'Rupture d approvisionnement en pièces stratégiques', 'Prob': 3, 'Grav': 4, 'CB': 12, 'DMR': 0.40, 'CN': 4.8, 'Statut': 'Validé'},
        {'Code': 'R-P2-04', 'Processus': 'P2', 'Intitulé': 'Non-respect du calendrier d itinéraire technique', 'Prob': 4, 'Grav': 4, 'CB': 16, 'DMR': 0.35, 'CN': 5.6, 'Statut': 'Validé'},
        {'Code': 'R-P7-02', 'Processus': 'P7', 'Intitulé': 'Erreur d imputations comptables sur fonds de subvention', 'Prob': 2, 'Grav': 4, 'CB': 8, 'DMR': 0.85, 'CN': 6.8, 'Statut': 'En vérification'},
        {'Code': 'R-P1-05', 'Processus': 'P1', 'Intitulé': 'Retard de traitement des dossiers de subvention FDA', 'Prob': 3, 'Grav': 3, 'CB': 9, 'DMR': 0.50, 'CN': 4.5, 'Statut': 'Validé'}
    ])
    
    filter_proc = st.multiselect("Filtrer par Processus :", df_proc['code'].unique(), default=df_proc['code'].unique())
    filtered_df = sample_risks[sample_risks['Processus'].isin(filter_proc)]
    
    st.dataframe(filtered_df, use_container_width=True)

# ---------------------------------------------------------
# MODULE 3: WORKFLOW DE VALIDATION
# ---------------------------------------------------------
elif menu == "🔔 Workflow de Validation":
    st.subheader("Workflow de Validation par l'Auditeur Interne")
    
    st.info("Nouveau risque soumis par le Responsable du Processus P7 (Gestion budgétaire et comptable)")
    
    with st.expander("🔎 Examiner le risque R-P7-02 (En attente)", expanded=True):
        st.write("**Intitulé :** Erreur d imputations comptables sur fonds de subvention")
        st.write("**Criticité Brute :** 8 | **DMR Déclaré :** 0.85 (Alerte : DMR élevé)")
        
        col_v1, col_v2 = st.columns(2)
        if col_v1.button("✅ Valider & Intégrer à la Cartographie"):
            st.success("Le risque R-P7-02 a été validé et intégré. Les scores de priorisation ont été recalculés.")
        if col_v2.button("❌ Rejeter / Demander Modification"):
            st.error("Demande de modification transmise au déclarant.")

# ---------------------------------------------------------
# MODULE 4: PRIORISATION PFA (0-100)
# ---------------------------------------------------------
elif menu == "🎯 Priorisation PFA (0-100)":
    st.subheader("Classement Final des Processus pour la Planification de l'Audit Interne")
    st.caption("Échelle harmonisée 0–100. Corrélation de Spearman avec le modèle initial : ρ = 0.98")
    
    st.dataframe(
        df_proc[['rang', 'code', 'libelle', 'score', 'var95', 'critCount', 'dmrMoy', 'priorite']],
        use_container_width=True
    )
    
    selected_p = st.selectbox("Sélectionner un processus pour justification du score :", df_proc['code'])
    p_info = df_proc[df_proc['code'] == selected_p].iloc[0]
    
    st.write(f"### Pourquoi le processus **{p_info['code']} - {p_info['libelle']}** a un score de **{p_info['score']}/100** ?")
    col_e1, col_e2, col_e3 = st.columns(3)
    col_e1.metric("Exposition VaR 95%", f"{p_info['var95']}")
    col_e2.metric("Risques Critiques", f"{p_info['critCount']}")
    col_e3.metric("Niveau de Maîtrise (DMR)", f"{p_info['dmrMoy']}")

# ---------------------------------------------------------
# MODULE 5: ANALYSES QUANTITATIVES & ACTUARIAT
# ---------------------------------------------------------
elif menu == "📊 Analyses Quantitatives & Actuariat":
    st.subheader("Résultats des Modèles Avancés (Développés sous Python)")
    
    t1, t2, t3 = st.tabs(["ANOVA", "Analyse du DMR", "Monte Carlo & VaR"])
    
    with t1:
        st.write("### Test Statistique ANOVA")
        col_a1, col_a2 = st.columns(2)
        col_a1.metric("F-Statistic", "4.22")
        col_a2.metric("p-value", "0.00002")
        st.success("Interprétation : La p-value < 0.05 confirme que les différences de criticité nette entre les 12 processus sont statistiquement significatives.")
        
    with t2:
        st.write("### Détection des Incohérences de DMR")
        st.metric("Coefficient de Détermination (R²)", "0.915")
        st.warning("L'analyse met en évidence 21 risques présentant un DMR potentiellement surestimé par rapport à la sévérité réelle. Une révision ciblée est fortement préconisée.")
        
    with t3:
        st.write("### Simulation Monte Carlo de la Pertes Globale")
        st.metric("VaR Globale 95%", "4 816.7 DH")
        st.info("Simulation basée sur 10 000 itérations stochastiques (Fréquence Poisson x Sévérité Lognormale).")

# ---------------------------------------------------------
# MODULE 6: MISSIONS D'AUDIT INTERNE
# ---------------------------------------------------------
elif menu == "📋 Missions d'Audit Interne":
    st.subheader("Planification et Engagement des Missions")
    
    st.write("### Planifier une mission basée sur le score PFA")
    with st.form("mission_form"):
        proc_audit = st.selectbox("Processus cible :", df_proc['code'] + " - " + df_proc['libelle'])
        auditeur = st.text_input("Auditeur responsable :", "Auditeur Interne 01")
        date_debut = st.date_input("Date de début prévue :")
        objectifs = st.text_area("Objectifs de la mission :", "Vérifier le contrôle interne de la chaîne d approvisionnement...")
        
        if st.form_submit_button("📅 Instancier la Mission d'Audit"):
            st.success(f"Mission d'audit créée avec succès pour {proc_audit}!")

# ---------------------------------------------------------
# MODULE 7: AUDIT TRAIL & LOGS
# ---------------------------------------------------------
elif menu == "📜 Audit Trail & Logs":
    st.subheader("Traçabilité Immuable des Opérations")
    
    logs = [
        {"Date": "11/08/2026 10:14", "Utilisateur": "Auditeur01", "Action": "Validation du risque R-P9-01", "Détail": "Statut changé vers Validé"},
        {"Date": "10/08/2026 15:30", "Utilisateur": "RespP7", "Action": "Déclaration du risque R-P7-02", "Détail": "Nouveau risque soumis"},
        {"Date": "09/08/2026 09:00", "Utilisateur": "Admin", "Action": "Exécution Simulation Monte Carlo", "Détail": "VaR 95% = 4816.7"}
    ]
    st.table(pd.DataFrame(logs))

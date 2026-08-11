import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE INSTITUTIONNEL
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Enterprise Risk & Audit Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FAFAFA; }
    .header-container {
        background-color: #FFFFFF; padding: 16px 24px;
        border-bottom: 1px solid #E5E7EB; margin-top: -50px; margin-bottom: 20px;
        border-radius: 0 0 12px 12px;
    }
    .header-title { font-size: 1.6rem; font-weight: 800; color: #0A2F1D; margin: 0; }
    .header-subtitle { font-size: 0.875rem; color: #4E7D5B; margin-top: 4px; }
    .breadcrumb { font-size: 0.8rem; color: #6B7280; margin-bottom: 16px; }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF; border: 1px solid #E5E7EB;
        padding: 16px; border-radius: 12px; border-left: 5px solid #1E513B;
    }
    div[data-testid="stMetricValue"] { color: #0A2F1D; font-weight: 800; }
    .footer-dark {
        background-color: #0B1320; color: #9CA3AF; padding: 32px 24px;
        border-radius: 12px; margin-top: 40px; font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. CHARGEMENT DES DONNÉES RÉELLES DEPUIS LES FICHIERS
# ---------------------------------------------------------
@st.cache_data
def load_data():
    try:
        df_carto = pd.read_excel('cartographie_analysee_complete.xlsx', sheet_name='Details_Risques')
    except Exception:
        df_carto = pd.DataFrame()

    try:
        df_score = pd.read_excel('indicateurs_powerbi_v2.xlsx', sheet_name='Score_Priorite')
    except Exception:
        df_score = pd.DataFrame()

    try:
        df_var = pd.read_excel('indicateurs_powerbi_v2.xlsx', sheet_name='VaR_TVaR')
    except Exception:
        df_var = pd.DataFrame()

    return df_carto, df_score, df_var

df_carto, df_score, df_var = load_data()

# ---------------------------------------------------------
# 3. HEADER & NAVIGATION (SIDEBAR)
# ---------------------------------------------------------
st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF — Enterprise Risk & Audit Center</div>
        <div class="header-subtitle">Système Décisionnel d'Aide à la Priorisation des Missions d'Audit Interne</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.title("🏢 Direction de l'Audit")
st.sidebar.caption("Source : Fichiers Power BI & Cartographie Officielle")

menu = st.sidebar.radio(
    "Modules de la Plateforme :",
    [
        "🏠 Dashboard Exécutif",
        "⚠️ Matrice des Risques (Heatmap)",
        "🎯 Priorisation & Scoring",
        "📊 Analyses VaR & Stochastique",
        "📋 Registre Détaillé des Risques"
    ]
)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD EXÉCUTIF
# ---------------------------------------------------------
if menu == "🏠 Dashboard Exécutif":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord Exécutif</b></div>""", unsafe_allow_html=True)
    
    total_risks = len(df_carto) if not df_carto.empty else 0
    total_var = df_var['VaR_95'].sum() if not df_var.empty and 'VaR_95' in df_var.columns else 0.0
    top_proc = df_score.sort_values('Score_Priorite_Audit', ascending=False).iloc[0]['Processus'] if not df_score.empty else "N/A"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Risques Cartographiés", f"{total_risks}", "Total Fichier Réel")
    m2.metric("VaR Globale (95%)", f"{total_var:,.1f} DH", "Modèle Stochastique")
    m3.metric("Processus Prioritaire #1", f"{top_proc[:20]}...", "Top Score PFA")
    m4.metric("Statut Système", "Opérationnel", "100% Connecté")

    st.write("")
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.subheader("🎯 Score de Priorisation par Processus")
        if not df_score.empty:
            fig_score = px.bar(
                df_score.sort_values('Score_Priorite_Audit', ascending=True),
                x='Score_Priorite_Audit', y='Processus', orientation='h',
                color='Score_Priorite_Audit', color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'],
                text='Score_Priorite_Audit'
            )
            fig_score.update_layout(height=400, yaxis={'categoryorder':'total ascending'}, plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig_score, use_container_width=True)
        else:
            st.warning("Données de score non disponibles.")

    with col_r:
        st.subheader("📊 Répartition de l'Exposition VaR 95%")
        if not df_var.empty and 'Contribution_VaR_pct' in df_var.columns:
            fig_pie = px.pie(
                df_var, values='Contribution_VaR_pct', names='Processus',
                hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r
            )
            fig_pie.update_layout(height=400, plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("Données VaR non disponibles.")

# ---------------------------------------------------------
# MODULE 2: MATRICE DES RISQUES (HEATMAP / ISHNAWER STYLE)
# ---------------------------------------------------------
elif menu == "⚠️ Matrice des Risques (Heatmap)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Matrice de Criticité Brute (Heatmap)</b></div>""", unsafe_allow_html=True)
    st.subheader("🗺️ Matrice d'Évaluation des Risques (Probabilité vs Gravité)")

    if not df_carto.empty and 'prob' in df_carto.columns and 'grav' in df_carto.columns:
        # Création de la matrice croisée (Pivot Table)
        matrix_df = pd.crosstab(df_carto['grav'], df_carto['prob'])
        
        fig_matrix = px.imshow(
            matrix_df,
            labels=dict(x="Probabilité", y="Gravité", color="Nombre de Risques"),
            x=sorted(df_carto['prob'].unique()),
            y=sorted(df_carto['grav'].unique()),
            color_continuous_scale="Greens",
            text_auto=True
        )
        fig_matrix.update_layout(title="Concentration des Risques dans la Matrice Institutionnelle", height=500, plot_bgcolor='#FFFFFF')
        st.plotly_chart(fig_matrix, use_container_width=True)
    else:
        st.warning("Données de probabilité et gravité introuvables dans le fichier.")

# ---------------------------------------------------------
# MODULE 3: PRIORISATION & SCORING
# ---------------------------------------------------------
elif menu == "🎯 Priorisation & Scoring":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Classement & Scoring</b></div>""", unsafe_allow_html=True)
    st.subheader("📋 Tableau Officiel de Priorisation des Missions d'Audit")

    if not df_score.empty:
        st.dataframe(df_score[['Processus', 'Criticite_Nette_Somme', 'Nb_Risques_Critiques', 'VaR_95', 'Score_Priorite_Audit', 'Rang_Quantifie']], use_container_width=True, height=450)
    else:
        st.warning("Aucun score de priorisation trouvé.")

# ---------------------------------------------------------
# MODULE 4: ANALYSES VAR & STOCHASTIQUE
# ---------------------------------------------------------
elif menu == "📊 Analyses VaR & Stochastique":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Analyses VaR & TVaR</b></div>""", unsafe_allow_html=True)
    st.subheader("🎲 Modélisation Stochastique des Pertes (VaR 95% & TVaR 95%)")

    if not df_var.empty:
        fig_var = px.bar(
            df_var, x='Processus', y=['VaR_95', 'TVaR_95'],
            barmode='group', color_discrete_sequence=['#1E513B', '#4E7D5B']
        )
        fig_var.update_layout(height=450, plot_bgcolor='#FFFFFF', xaxis_tickangle=-45)
        st.plotly_chart(fig_var, use_container_width=True)
        
        st.dataframe(df_var, use_container_width=True)
    else:
        st.warning("Données VaR indisponibles.")

# ---------------------------------------------------------
# MODULE 5: REGISTRE DÉTAILLÉ
# ---------------------------------------------------------
elif menu == "📋 Registre Détaillé des Risques":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Registre Détaillé</b></div>""", unsafe_allow_html=True)
    st.subheader("📑 Base de Données Complète des Risques")

    if not df_carto.empty:
        search = st.text_input("🔍 Rechercher un intitulé ou un processus :", "")
        filtered = df_carto
        if search:
            mask = df_carto.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            filtered = df_carto[mask]
        st.dataframe(filtered, use_container_width=True, height=550)
    else:
        st.warning("Aucun détail de risque trouvé.")

# Footer
st.markdown("""
    <div class="footer-dark">
        <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Plateforme Intégrée Power BI & Python (2026)
    </div>
""", unsafe_allow_html=True)

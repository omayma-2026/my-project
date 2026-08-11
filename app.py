import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

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
# 2. CHARGEMENT AUTOMATIQUE DU FICHIER 'projet1.xlsx'
# ---------------------------------------------------------
@st.cache_data
def load_projet1():
    try:
        # Lecture automatique du fichier projet1.xlsx présent dans le dossier
        df = pd.read_excel('projet1.xlsx')
        return df
    except Exception as e:
        return pd.DataFrame()

df_data = load_projet1()

# ---------------------------------------------------------
# 3. HEADER & NAVIGATION
# ---------------------------------------------------------
st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF — Enterprise Risk & Audit Center</div>
        <div class="header-subtitle">Système Décisionnel d'Aide à la Priorisation des Missions d'Audit Interne</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.title("🏢 Direction de l'Audit")
if not df_data.empty:
    st.sidebar.success(f"✅ projet1.xlsx chargé ({len(df_data)} lignes)")
else:
    st.sidebar.error("⚠️ Fichier projet1.xlsx introuvable ou vide.")

menu = st.sidebar.radio(
    "Modules de la Plateforme :",
    [
        "🏠 Dashboard Exécutif",
        "⚠️ Matrice des Risques (Heatmap)",
        "📋 Registre Détaillé des Risques"
    ]
)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD EXÉCUTIF
# ---------------------------------------------------------
if menu == "🏠 Dashboard Exécutif":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord Exécutif</b></div>""", unsafe_allow_html=True)
    
    total_risks = len(df_data) if not df_data.empty else 0
    total_proc = df_data['processus'].nunique() if not df_data.empty and 'processus' in df_data.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Risques Totaux", f"{total_risks}", "Base projet1.xlsx")
    m2.metric("Processus Impliqués", f"{total_proc}", "Actifs")
    m3.metric("Statut Source", "Connecté", "Local")
    m4.metric("Mode", "Production", "ORMVA-TF")

    st.write("")
    st.subheader("📊 Répartition des Risques par Processus")
    
    if not df_data.empty and 'processus' in df_data.columns:
        df_group = df_data.groupby('processus').size().reset_index(name='Nombre')
        fig = px.bar(
            df_group, x='Nombre', y='processus', orientation='h',
            color='Nombre', color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'], text='Nombre'
        )
        fig.update_layout(height=400, yaxis={'categoryorder':'total ascending'}, plot_bgcolor='#FFFFFF')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("La colonne 'processus' est introuvable dans le fichier projet1.xlsx.")

# ---------------------------------------------------------
# MODULE 2: MATRICE DES RISQUES (HEATMAP)
# ---------------------------------------------------------
elif menu == "⚠️ Matrice des Risques (Heatmap)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Matrice de Criticité Brute</b></div>""", unsafe_allow_html=True)
    st.subheader("🗺️ Matrice Probabilité vs Gravité")

    if not df_data.empty and 'Prob' in df_data.columns:
        # Détection automatique de la colonne gravité (grav ou Gravité)
        grav_col = 'grav' if 'grav' in df_data.columns else ('Grav' if 'Grav' in df_data.columns else None)
        
        if grav_col:
            matrix_df = pd.crosstab(df_data[grav_col], df_data['Prob'])
            fig_matrix = px.imshow(
                matrix_df,
                labels=dict(x="Probabilité", y="Gravité", color="Nombre"),
                x=sorted(df_data['Prob'].unique()),
                y=sorted(df_data[grav_col].unique()),
                color_continuous_scale="Greens",
                text_auto=True
            )
            fig_matrix.update_layout(height=450, plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig_matrix, use_container_width=True)
        else:
            st.warning("Colonne de gravité introuvable dans projet1.xlsx.")
    else:
        st.warning("Colonnes de probabilité introuvables.")

# ---------------------------------------------------------
# MODULE 3: REGISTRE DÉTAILLÉ
# ---------------------------------------------------------
elif menu == "📋 Registre Détaillé des Risques":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Registre Détaillé</b></div>""", unsafe_allow_html=True)
    st.subheader("📑 Contenu Brut de projet1.xlsx")

    if not df_data.empty:
        search = st.text_input("🔍 Rechercher dans le fichier :", "")
        filtered = df_data
        if search:
            mask = df_data.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            filtered = df_data[mask]
        st.dataframe(filtered, use_container_width=True, height=550)
    else:
        st.warning("Le fichier est vide.")

# Footer
st.markdown("""
    <div class="footer-dark">
        <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Plateforme Intégrée (2026)
    </div>
""", unsafe_allow_html=True)

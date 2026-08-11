import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk Matrix & Analytics",
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
# 2. CHARGEMENT DES DONNÉES
# ---------------------------------------------------------
@st.cache_data
def load_data():
    for filename in ['projet1.xlsx', 'data_reel.xlsx', 'cartographie_analysee_complete.xlsx']:
        try:
            df = pd.read_excel(filename)
            return df
        except Exception:
            continue
    return pd.DataFrame()

df = load_data()

# Uniformisation des noms de colonnes si nécessaire
if not df.empty:
    df.columns = [c.strip().lower() for c in df.columns]

# ---------------------------------------------------------
# 3. NAVIGATION (SIDEBAR)
# ---------------------------------------------------------
st.sidebar.title("🏢 Direction de l'Audit")
if not df.empty:
    st.sidebar.success(f"✅ Données chargées ({len(df)} risques)")
else:
    st.sidebar.error("⚠️ Fichier de données introuvable.")

menu = st.sidebar.radio(
    "Modules de la Plateforme :",
    [
        "🏠 Dashboard & Répartition (Donut)",
        "🗺️ Matrice des Risques (Heatmap Style)",
        "🔥 Top 10 Risques Prioritaires",
        "📋 Registre Détaillé"
    ]
)

st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF — Enterprise Risk & Audit Center</div>
        <div class="header-subtitle">Système Décisionnel d'Aide à la Priorisation des Missions d'Audit Interne</div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD & DONUT CHART
# ---------------------------------------------------------
if menu == "🏠 Dashboard & Répartition (Donut)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord & Répartition</b></div>""", unsafe_allow_html=True)
    
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Risques Totaux", len(df), "Base Officielle")
        m2.metric("Processus", df['processus'].nunique() if 'processus' in df.columns else 0, "Actifs")
        m3.metric("Statut", "100% Dynamique", "Conforme PFA")

        st.write("")
        col_l, col_r = st.columns(2)
        
        with col_l:
            st.subheader("🎯 Répartition par Zone d'Action (Donut)")
            # Simulation des zones si non présentes
            if 'zone' not in df.columns:
                # Attribution basique basée sur prob et grav si disponibles
                if 'prob' in df.columns and 'grav' in df.columns:
                    crit = df['prob'] * df['grav']
                    df['zone'] = pd.cut(crit, bins=[-1, 4, 8, 12, 25], labels=['Zone A - Optimisation', 'Zone B - Vigilance', 'Zone C - Surveillance', 'Zone D - Traitement Prioritaire'])
                else:
                    df['zone'] = 'Zone B - Vigilance'
            
            zone_counts = df['zone'].value_counts().reset_index()
            zone_counts.columns = ['Zone', 'Count']
            
            fig_donut = px.pie(
                zone_counts, values='Count', names='Zone', hole=0.4,
                color='Zone',
                color_discrete_map={
                    'Zone D - Traitement Prioritaire': '#A31D1D',
                    'Zone C - Surveillance': '#D9822B',
                    'Zone B - Vigilance': '#1B4965',
                    'Zone A - Optimisation': '#2D6A4F'
                }
            )
            fig_donut.update_layout(height=400, plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_r:
            st.subheader("📊 Top Processus par Nombre de Risques")
            if 'processus' in df.columns:
                df_proc = df.groupby('processus').size().reset_index(name='Nombre').sort_values(by='Nombre', ascending=True)
                fig_bar = px.bar(
                    df_proc, x='Nombre', y='processus', orientation='h',
                    color='Nombre', color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'], text='Nombre'
                )
                fig_bar.update_layout(height=400, plot_bgcolor='#FFFFFF')
                st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------
# MODULE 2: MATRICE DES RISQUES (HEATMAP STYLE)
# ---------------------------------------------------------
elif menu == "🗺️ Matrice des Risques (Heatmap Style)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Matrice des Risques</b></div>""", unsafe_allow_html=True)
    st.subheader("🗺️ Matrice d'Évaluation (Probabilité vs Gravité / Degré de Contrôle)")

    if not df.empty and 'prob' in df.columns and 'grav' in df.columns:
        # Création d'une matrice avec les codes des risques à l'intérieur
        matrix_data = pd.crosstab(df['grav'], df['prob'])
        
        fig_matrix = px.imshow(
            matrix_data,
            labels=dict(x="Probabilité", y="Gravité", color="Nombre de Risques"),
            x=sorted(df['prob'].unique()),
            y=sorted(df['grav'].unique()),
            color_continuous_scale="Reds",
            text_auto=True
        )
        fig_matrix.update_layout(height=500, plot_bgcolor='#FFFFFF', title="Concentration des Risques par Niveau")
        st.plotly_chart(fig_matrix, use_container_width=True)
        
        st.info("💡 Cette matrice reflète la criticité brute (Probabilité × Gravité) de la même manière que les matrices institutionnelles d'audit.")
    else:
        st.warning("Colonnes 'prob' et 'grav' requises pour afficher la matrice.")

# ---------------------------------------------------------
# MODULE 3: TOP 10 RISQUES PRIORITAIRES
# ---------------------------------------------------------
elif menu == "🔥 Top 10 Risques Prioritaires":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Top Risques</b></div>""", unsafe_allow_html=True)
    st.subheader("🔥 Top 10 Risques les plus Critiques (Scoring)")

    if not df.empty:
        # Calcul score si colonnes présentes
        if 'prob' in df.columns and 'grav' in df.columns:
            df['score_priorite'] = df['prob'] * df['grav']
        elif 'criticité brute' in df.columns:
            df['score_priorite'] = df['criticité brute']
        else:
            df['score_priorite'] = 10

        top10 = df.sort_values(by='score_priorite', ascending=False).head(10)
        
        fig_top = px.bar(
            top10.sort_values(by='score_priorite', ascending=True),
            x='score_priorite', y='code' if 'code' in top10.columns else top10.index.astype(str),
            orientation='h', color='score_priorite',
            color_continuous_scale=['#F4A261', '#E76F51', '#A31D1D'], text='score_priorite'
        )
        fig_top.update_layout(height=450, plot_bgcolor='#FFFFFF', xaxis_title="Score de Priorité", yaxis_title="Code Risque")
        st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.warning("Données indisponibles.")

# ---------------------------------------------------------
# MODULE 4: REGISTRE DÉTAILLÉ
# ---------------------------------------------------------
elif menu == "📋 Registre Détaillé":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Registre Détaillé</b></div>""", unsafe_allow_html=True)
    st.subheader("📑 Base de Données Complète")
    if not df.empty:
        st.dataframe(df, use_container_width=True, height=550)

# Footer
st.markdown("""
    <div class="footer-dark">
        <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Plateforme (2026)
    </div>
""", unsafe_allow_html=True)

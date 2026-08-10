%%writefile app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Configuration de la page
st.set_page_config(page_title="Audit Interne - Cartographie des Risques", layout="wide")

st.title("🛡️ Plateforme d'Audit Interne & Management des Risques")

# 1. Chargement des données (Fichier projet1.xlsx)
@st.cache_data
def load_data():
    df = pd.read_excel("projet1.xlsx")
    df = df.dropna(subset=['code']).reset_index(drop=True)

    df['Prob'] = pd.to_numeric(df['Prob'], errors='coerce')
    df['Grav'] = pd.to_numeric(df['Grav'], errors='coerce')
    df['DMR'] = pd.to_numeric(df['DMR'], errors='coerce')

    df['Criticite_Brute'] = df['Prob'] * df['Grav']
    df['Criticite_Nette'] = df['Criticite_Brute'] * df['DMR']

    # Règle des Zones du rapport Word
    def assign_zone(row):
        cb = row['Criticite_Brute']
        dmr = row['DMR']
        if cb >= 8 and dmr <= 0.50:
            return "Zone D - Traitement"
        elif cb >= 8 and dmr > 0.50:
            return "Zone C - Surveillance"
        elif cb < 8 and dmr <= 0.50:
            return "Zone B - Vigilance"
        else:
            return "Zone A - Optimisation"

    df['Zone_Action'] = df.apply(assign_zone, axis=1)
    return df

try:
    df = load_data()

    # 2. Sidebar - Filtres
    st.sidebar.header("🔍 Filtres Auditeur")
    processus_selected = st.sidebar.multiselect("Sélectionner Processus", df['processus'].unique())

    df_filtered = df.copy()
    if processus_selected:
        df_filtered = df_filtered[df_filtered['processus'].isin(processus_selected)]

    # 3. Métriques clés (KPIs)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Risques", len(df_filtered))
    k2.metric("Criticité Nette Moyenne", f"{df_filtered['Criticite_Nette'].mean():.2f}")
    k3.metric("Risques Critiques (Zone D)", len(df_filtered[df_filtered['Zone_Action'] == "Zone D - Traitement"]))
    k4.metric("DMR Moyen", f"{df_filtered['DMR'].mean()*100:.1f}%")

    st.markdown("---")

    # 4. Graphiques
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Répartition par Zone d'Action")
        fig_donut = px.pie(
            df_filtered,
            names='Zone_Action',
            hole=0.4,
            color='Zone_Action',
            color_discrete_map={
                "Zone D - Traitement": "#A61C1C",
                "Zone C - Surveillance": "#E67E22",
                "Zone B - Vigilance": "#2980B9",
                "Zone A - Optimisation": "#27AE60"
            }
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col2:
        st.subheader("Analyse PCA (Projection des Risques)")
        X = df_filtered[['Prob', 'Grav', 'Criticite_Brute', 'DMR', 'Criticite_Nette']]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        pca = PCA(n_components=2)
        coords = pca.fit_transform(X_scaled)

        df_filtered['PCA1'] = coords[:, 0]
        df_filtered['PCA2'] = coords[:, 1]

        fig_pca = px.scatter(
            df_filtered,
            x='PCA1',
            y='PCA2',
            color='Zone_Action',
            hover_data=['code', 'intitule', 'Criticite_Nette'],
            color_discrete_map={
                "Zone D - Traitement": "#A61C1C",
                "Zone C - Surveillance": "#E67E22",
                "Zone B - Vigilance": "#2980B9",
                "Zone A - Optimisation": "#27AE60"
            }
        )
        st.plotly_chart(fig_pca, use_container_width=True)

    # 5. Table des données
    st.subheader("📋 Registre des Risques")
    st.dataframe(df_filtered[['code', 'processus', 'sous_processus', 'intitule', 'Prob', 'Grav', 'Criticite_Brute', 'DMR', 'Criticite_Nette', 'Zone_Action']])

except Exception as e:
    st.error(f"Veuillez vérifier que le fichier 'projet1.xlsx' est bien importé dans Colab. Erreur : {e}")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Configuration de la page
st.set_page_config(page_title="Audit Interne & Management des Risques", layout="wide")

st.title("🛡️ Plateforme d'Audit Interne & Priorisation des Risques")

# Lecture du fichier Excel
@st.cache_data
def load_data():
    df = pd.read_excel("projet1.xlsx")
    return df

try:
    df = load_data()
    
    # -------------------------------------------------------------
    # 1. FILTRES DANS LA SIDEBAR
    # -------------------------------------------------------------
    st.sidebar.header("🔍 Filtres Auditeur")
    if "Processus" in df.columns:
        processus_list = df["Processus"].unique().tolist()
        selected_proc = st.sidebar.multiselect("Sélectionner Processus", options=processus_list, default=processus_list)
        df_filtered = df[df["Processus"].isin(selected_proc)]
    else:
        df_filtered = df.copy()

    # -------------------------------------------------------------
    # 2. INDICATEURS CLÉS (KPIs)
    # -------------------------------------------------------------
    total_risques = len(df_filtered)
    crit_moyenne = df_filtered["Criticité Nette"].mean() if "Criticité Nette" in df_filtered.columns else 0
    
    # Risques zone D (Traitement / Haute criticité)
    risques_crit = len(df_filtered[df_filtered["Zone_Action"].str.contains("Zone D", na=False)]) if "Zone_Action" in df_filtered.columns else 0
    dmr_moyen = df_filtered["DMR"].mean() if "DMR" in df_filtered.columns else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Risques", total_risques)
    col2.metric("Criticité Nette Moyenne", f"{crit_moyenne:.2f}")
    col3.metric("Risques Critiques (Zone D)", risques_crit)
    col4.metric("DMR Moyen", f"{dmr_moyen*100:.1f}%" if dmr_moyen <= 1 else f"{dmr_moyen:.1f}%")

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. MATRICE DES ACTIONS LIÉES AUX PROCESSUS (HEATMAP 4x4)
    # -------------------------------------------------------------
    st.subheader("📊 Matrice des Actions (Degré de Contrôle vs Degré de Criticité)")

    # Définition des axes
    x_bins = [0, 4, 8, 12, 16]
    x_labels = ["Faible [0-4[", "Moyen [4-8[", "Significatif [8-12[", "Elevé [12-16]"]

    # Inversion de l'axe Y pour correspondre à l'image (Faible en haut, Satisfaisant en bas)
    y_bins = [0, 0.25, 0.50, 0.75, 1.0]
    y_labels = ["Satisfaisant ≤100%", "Correcte ≤75%", "Partiel ≤50%", "Faible ≤25%"]

    # Assignation des catégories
    if "Criticité Nette" in df_filtered.columns and "DMR" in df_filtered.columns:
        df_matrix = df_filtered.copy()
        
        # Normalisation du DMR si en pourcentage (0-100 -> 0-1)
        if df_matrix["DMR"].max() > 1:
            df_matrix["DMR_norm"] = df_matrix["DMR"] / 100
        else:
            df_matrix["DMR_norm"] = df_matrix["DMR"]

        df_matrix["Cat_Criticite"] = pd.cut(df_matrix["Criticité Nette"], bins=x_bins, labels=x_labels, include_lowest=True)
        df_matrix["Cat_Controle"] = pd.cut(df_matrix["DMR_norm"], bins=y_bins, labels=y_labels, include_lowest=True)

        # Regroupement des codes risques par case
        id_col = "Code Risque" if "Code Risque" in df_matrix.columns else df_matrix.columns[0]
        
        matrix_text = np.empty((4, 4), dtype=object)
        for i, y_lab in enumerate(reversed(y_labels)): # Du haut vers le bas
            for j, x_lab in enumerate(x_labels):
                sub_df = df_matrix[(df_matrix["Cat_Controle"] == y_lab) & (df_matrix["Cat_Criticite"] == x_lab)]
                codes = sub_df[id_col].astype(str).tolist()
                matrix_text[i, j] = "<br>".join(codes) if codes else "-"

        # Matrice des couleurs (Zone A: Vert, Zone B: Jaune, Zone C: Rose, Zone D: Rouge)
        # Structure de la grille 4x4 (Lignes: Faible à Satisfaisant, Cols: Faible à Elevé)
        colorscale = [
            [0.0, "#99C2A2"], # Vert / Zone A (Optimisation)
            [0.33, "#F9E79F"], # Jaune / Zone B (Vigilance)
            [0.66, "#F1948A"], # Rose / Zone C (Surveillance)
            [1.0, "#B03A2E"]  # Rouge / Zone D (Traitement)
        ]
        
        z_values = [
            [2, 2, 3, 3], # Ligne Faible Contrôle
            [1, 2, 2, 3], # Ligne Partiel Contrôle
            [0, 1, 1, 2], # Ligne Correcte Contrôle
            [0, 0, 1, 2]  # Ligne Satisfaisant Contrôle
        ]

        fig_matrix = go.Figure(data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=list(reversed(y_labels)),
            text=matrix_text,
            texttemplate="%{text}",
            textfont={"size": 11, "color": "black"},
            colorscale=colorscale,
            showscale=False
        ))

        fig_matrix.update_layout(
            xaxis_title="DEGRÉ DE CRITICITÉ",
            yaxis_title="DEGRÉ DE CONTRÔLE",
            height=550,
            margin=dict(l=40, r=40, t=40, b=40)
        )

        st.plotly_chart(fig_matrix, use_container_width=True)

    st.markdown("---")

    # -------------------------------------------------------------
    # 4. SCORE DE PRIORISATION DES MISSIONS D'AUDIT
    # -------------------------------------------------------------
    st.subheader("🎯 Score de Priorisation d'Audit Interne")
    st.write("Classement automatique des processus/risques à auditer en priorité selon la formule : $Score = Criticité \\times (1 - DMR)$")

    if "Criticité Nette" in df_filtered.columns and "DMR" in df_filtered.columns:
        df_priorite = df_filtered.copy()
        
        dmr_val = df_priorite["DMR"] / 100 if df_priorite["DMR"].max() > 1 else df_priorite["DMR"]
        df_priorite["Score Priorité"] = df_priorite["Criticité Nette"] * (1 - dmr_val)
        
        # Tri décroissant selon le Score
        df_priorite = df_priorite.sort_values(by="Score Priorité", ascending=False)

        cols_to_display = [col for col in ["Code Risque", "Intitulé Risque", "Processus", "Criticité Nette", "DMR", "Score Priorité", "Zone_Action"] if col in df_priorite.columns]
        
        st.dataframe(
            df_priorite[cols_to_display].style.background_gradient(cmap="Reds", subset=["Score Priorité"]),
            use_container_width=True
        )

    st.markdown("---")

    # -------------------------------------------------------------
    # 5. HISTORIQUE & ÉVOLUTION DES RISQUES
    # -------------------------------------------------------------
    st.subheader("📈 Historique & Évolution Temporelle")
    
    if "Annee" in df_filtered.columns or "Date" in df_filtered.columns:
        date_col = "Annee" if "Annee" in df_filtered.columns else "Date"
        fig_histo = px.line(
            df_filtered, 
            x=date_col, 
            y="Criticité Nette", 
            color="Processus" if "Processus" in df_filtered.columns else None,
            title="Évolution de la Criticité Nette au Fil du Temps",
            markers=True
        )
        st.plotly_chart(fig_histo, use_container_width=True)
    else:
        st.info("💡 Pour afficher l'historique temporel, ajoutez une colonne 'Annee' ou 'Date' dans votre fichier Excel.")

except Exception as e:
    st.error(f"Une erreur est survenue lors du chargement des données : {e}")

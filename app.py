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
    # Nettoyage des colonnes (suppression des espaces)
    df.columns = df.columns.str.strip()
    # Suppression des lignes entièrement vides
    df = df.dropna(how='all')
    return df

try:
    df = load_data()

    # Détection automatique des noms de colonnes
    col_crit = [c for c in df.columns if 'critic' in c.lower() or 'critité' in c.lower() or 'criticite' in c.lower()]
    col_dmr = [c for c in df.columns if 'dmr' in c.lower() or 'maitrise' in c.lower()]
    col_zone = [c for c in df.columns if 'zone' in c.lower() or 'action' in c.lower()]
    col_proc = [c for c in df.columns if 'processus' in c.lower() or 'proc' in c.lower()]
    col_code = [c for c in df.columns if 'code' in c.lower() or 'risque' in c.lower() or 'id' in c.lower()]

    crit_name = col_crit[0] if col_crit else df.columns[1]
    dmr_name = col_dmr[0] if col_dmr else df.columns[2]
    zone_name = col_zone[0] if col_zone else None
    proc_name = col_proc[0] if col_proc else None
    code_name = col_code[0] if col_code else df.columns[0]

    # -------------------------------------------------------------
    # 1. FILTRES DANS LA SIDEBAR
    # -------------------------------------------------------------
    st.sidebar.header("🔍 Filtres Auditeur")
    if proc_name:
        processus_list = df[proc_name].dropna().unique().tolist()
        selected_proc = st.sidebar.multiselect("Sélectionner Processus", options=processus_list, default=processus_list)
        df_filtered = df[df[proc_name].isin(selected_proc)]
    else:
        df_filtered = df.copy()

    # -------------------------------------------------------------
    # 2. INDICATEURS CLÉS (KPIs)
    # -------------------------------------------------------------
    total_risques = len(df_filtered)
    crit_moyenne = pd.to_numeric(df_filtered[crit_name], errors='coerce').mean()
    
    dmr_series = pd.to_numeric(df_filtered[dmr_name], errors='coerce')
    dmr_moyen = dmr_series.mean()

    if zone_name:
        risques_crit = len(df_filtered[df_filtered[zone_name].astype(str).str.contains("Zone D|Traitement|D", case=False, na=False)])
    else:
        risques_crit = len(df_filtered[pd.to_numeric(df_filtered[crit_name], errors='coerce') >= 12])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Risques", total_risques)
    col2.metric("Criticité Nette Moyenne", f"{crit_moyenne:.2f}" if not np.isnan(crit_moyenne) else "N/A")
    col3.metric("Risques Critiques (Zone D)", risques_crit)
    col4.metric("DMR Moyen", f"{dmr_moyen*100:.1f}%" if dmr_moyen <= 1 else f"{dmr_moyen:.1f}%")

    st.markdown("---")

    # -------------------------------------------------------------
    # 3. MATRICE DES ACTIONS LIÉES AUX PROCESSUS (HEATMAP 4x4)
    # -------------------------------------------------------------
    st.subheader("📊 Matrice des Actions (Degré de Contrôle vs Degré de Criticité)")

    x_bins = [0, 4, 8, 12, 16]
    x_labels = ["Faible [0-4[", "Moyen [4-8[", "Significatif [8-12[", "Elevé [12-16]"]

    y_bins = [0, 0.25, 0.50, 0.75, 1.0]
    y_labels = ["Satisfaisant ≤100%", "Correcte ≤75%", "Partiel ≤50%", "Faible ≤25%"]

    df_matrix = df_filtered.copy()
    df_matrix["Criticite_Num"] = pd.to_numeric(df_matrix[crit_name], errors='coerce')
    df_matrix["DMR_Num"] = pd.to_numeric(df_matrix[dmr_name], errors='coerce')
    
    if df_matrix["DMR_Num"].max() > 1:
        df_matrix["DMR_Num"] = df_matrix["DMR_Num"] / 100

    df_matrix["Cat_Criticite"] = pd.cut(df_matrix["Criticite_Num"], bins=x_bins, labels=x_labels, include_lowest=True)
    df_matrix["Cat_Controle"] = pd.cut(df_matrix["DMR_Num"], bins=y_bins, labels=y_labels, include_lowest=True)

    matrix_text = np.empty((4, 4), dtype=object)
    for i, y_lab in enumerate(reversed(y_labels)):
        for j, x_lab in enumerate(x_labels):
            sub_df = df_matrix[(df_matrix["Cat_Controle"] == y_lab) & (df_matrix["Cat_Criticite"] == x_lab)]
            codes = sub_df[code_name].astype(str).tolist()
            matrix_text[i, j] = ", ".join(codes) if codes else "-"

    colorscale = [
        [0.0, "#99C2A2"], # Vert
        [0.33, "#F9E79F"], # Jaune
        [0.66, "#F1948A"], # Rose
        [1.0, "#B03A2E"]  # Rouge
    ]
    
    z_values = [
        [2, 2, 3, 3],
        [1, 2, 2, 3],
        [0, 1, 1, 2],
        [0, 0, 1, 2]
    ]

    fig_matrix = go.Figure(data=go.Heatmap(
        z=z_values,
        x=x_labels,
        y=list(reversed(y_labels)),
        text=matrix_text,
        texttemplate="%{text}",
        textfont={"size": 10, "color": "black"},
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

    df_priorite = df_filtered.copy()
    df_priorite["Criticite_Num"] = pd.to_numeric(df_priorite[crit_name], errors='coerce')
    df_priorite["DMR_Num"] = pd.to_numeric(df_priorite[dmr_name], errors='coerce')
    
    if df_priorite["DMR_Num"].max() > 1:
        df_priorite["DMR_Num"] = df_priorite["DMR_Num"] / 100

    df_priorite["Score Priorité"] = df_priorite["Criticite_Num"] * (1 - df_priorite["DMR_Num"])
    df_priorite = df_priorite.sort_values(by="Score Priorité", ascending=False)

    st.dataframe(
        df_priorite.style.background_gradient(cmap="Reds", subset=["Score Priorité"]),
        use_container_width=True
    )

except Exception as e:
    st.error(f"Une erreur est survenue lors du chargement des données : {e}")

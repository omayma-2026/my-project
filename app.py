import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

# -------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# -------------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    :root {
        --primary-color: #1E4620;
        --secondary-color: #87A987;
        --bg-light: #F4F7F4;
        --card-bg: #FFFFFF;
        --text-dark: #1C2826;
        --accent-red: #D9534F;
    }
    
    .stApp {
        background-color: var(--bg-light);
    }
    
    .main-header {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary-color);
        border-bottom: 2px solid var(--secondary-color);
        padding-bottom: 8px;
        margin-bottom: 20px;
    }
    
    .kpi-card {
        background-color: var(--card-bg);
        border-radius: 8px;
        padding: 16px;
        border-left: 5px solid var(--primary-color);
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .kpi-title {
        font-size: 12px;
        font-weight: 600;
        color: #555555;
        text-transform: uppercase;
    }
    
    .kpi-value {
        font-size: 24px;
        font-weight: bold;
        color: var(--primary-color);
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. CHARGEMENT STRICT DE PROJET1.XLSX
# -------------------------------------------------------------
@st.cache_data
def load_excel_data():
    file_name = "projet1.xlsx"
    if not os.path.exists(file_name):
        for root, dirs, files in os.walk("."):
            if file_name in files:
                file_name = os.path.join(root, file_name)
                break

    if not os.path.exists(file_name):
        st.error(f"❌ Le fichier '{file_name}' est introuvable sur le dépôt GitHub.")
        st.stop()

    df = pd.read_excel(file_name)
    df.columns = df.columns.astype(str).str.strip()
    df = df.dropna(how='all')

    # Cartographie automatique des colonnes de projet1.xlsx
    col_map = {}
    for col in df.columns:
        c_low = str(col).lower()
        if 'code' in c_low or 'id' in c_low or 'risque' in c_low:
            if 'code_col' not in col_map: col_map['code_col'] = col
        if 'sous' in c_low:
            col_map['sproc_col'] = col
        elif 'processus' in c_low or 'proc' in c_low:
            if 'proc_col' not in col_map: col_map['proc_col'] = col
        elif 'brute' in c_low or 'critic' in c_low or 'critité' in c_low:
            if 'crit_col' not in col_map: col_map['crit_col'] = col
        elif 'dmr' in c_low or 'maitrise' in c_low or 'contrôle' in c_low:
            if 'dmr_col' not in col_map: col_map['dmr_col'] = col
        elif 'zone' in c_low:
            if 'zone_col' not in col_map: col_map['zone_col'] = col

    # Normalisation des colonnes principales
    code_col = col_map.get('code_col', df.columns[0])
    proc_col = col_map.get('proc_col', df.columns[1] if len(df.columns) > 1 else df.columns[0])
    sproc_col = col_map.get('sproc_col', None)
    crit_col = col_map.get('crit_col', None)
    dmr_col = col_map.get('dmr_col', None)
    zone_col = col_map.get('zone_col', None)

    df['Code_Display'] = df[code_col].astype(str)
    df['Proc_Display'] = df[proc_col].astype(str)
    df['SProc_Display'] = df[sproc_col].astype(str) if sproc_col else "Général"

    if crit_col:
        df['CB_Num'] = pd.to_numeric(df[crit_col], errors='coerce').fillna(0)
    else:
        df['CB_Num'] = 0.0

    if dmr_col:
        df['DMR_Num'] = pd.to_numeric(df[dmr_col], errors='coerce').fillna(0)
    else:
        df['DMR_Num'] = 0.0

    if df['DMR_Num'].max() > 1:
        df['DMR_Num'] = df['DMR_Num'] / 100.0

    df['CN_Num'] = (df['CB_Num'] * (1 - df['DMR_Num'])).round(2)

    if zone_col:
        df['Zone_Display'] = df[zone_col].astype(str)
    else:
        # Attribution automatique de la zone si non présente
        def get_zone(cn):
            if cn >= 12: return "Zone D - Traitement"
            elif cn >= 8: return "Zone C - Surveillance"
            elif cn >= 4: return "Zone B - Vigilance"
            else: return "Zone A - Optimisation"
        df['Zone_Display'] = df['CN_Num'].apply(get_zone)

    df['statut'] = "VALIDE"
    return df

st.session_state.df_carto = load_excel_data()

# -------------------------------------------------------------
# 3. SIDEBAR & FILTRES SÉCURISÉS (PROCESSUS & SOUS-PROCESSUS)
# -------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2910/2910791.png", width=60)
st.sidebar.title("ORMVA-TF Risk Center")
st.sidebar.success(f"📊 Fichier chargé : **{len(st.session_state.df_carto)} risques**")

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtres Globaux")

# 1. Filtre Processus
raw_procs = st.session_state.df_carto["Proc_Display"].dropna().unique()
all_procs = sorted([str(p) for p in raw_procs])
selected_procs = st.sidebar.multiselect("Filtrer par Processus:", options=all_procs)

# 2. Filtre Sous-Processus
if selected_procs:
    filtered_sproc_df = st.session_state.df_carto[st.session_state.df_carto["Proc_Display"].astype(str).isin(selected_procs)]
else:
    filtered_sproc_df = st.session_state.df_carto

raw_sprocs = filtered_sproc_df["SProc_Display"].dropna().unique()
all_sprocs = sorted([str(sp) for sp in raw_sprocs])
selected_sprocs = st.sidebar.multiselect("Filtrer par Sous-Processus:", options=all_sprocs)

df_filtered = st.session_state.df_carto.copy()
if selected_procs:
    df_filtered = df_filtered[df_filtered["Proc_Display"].astype(str).isin(selected_procs)]
if selected_sprocs:
    df_filtered = df_filtered[df_filtered["SProc_Display"].astype(str).isin(selected_sprocs)]

st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation System",
    [
        "🏠 Dashboard",
        "⚠️ Cartographie des risques",
        "📊 Analyses Statistiques"
    ]
)

# -------------------------------------------------------------
# 4. DASHBOARD
# -------------------------------------------------------------
if menu == "🏠 Dashboard":
    st.markdown('<div class="main-header">🏠 Dashboard Décisionnel d\'Audit Interne</div>', unsafe_allow_html=True)
    
    total_risques = len(df_filtered)
    nb_processus = df_filtered["Proc_Display"].nunique()
    crit_critiques = len(df_filtered[df_filtered["Zone_Display"].astype(str).str.contains("Zone D|Traitement", case=False, na=False)])
    cn_moyenne = df_filtered["CN_Num"].mean() if total_risques > 0 else 0
    dmr_moyen = df_filtered["DMR_Num"].mean() if total_risques > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Risques</div><div class="kpi-value">{total_risques}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-title">Processus</div><div class="kpi-value">{nb_processus}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-title">Risques Critiques</div><div class="kpi-value" style="color:#D9534F;">{crit_critiques}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-title">Criticité Nette Moy.</div><div class="kpi-value">{cn_moyenne:.2f}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([2, 1.2])

    with col_left:
        st.subheader("📊 Matrice des Actions (4x4)")
        
        x_bins = [0, 4, 8, 12, 16]
        x_labels = ["Faible [0-4[", "Moyen [4-8[", "Significatif [8-12[", "Elevé [12-16]"]
        y_bins = [0, 0.25, 0.50, 0.75, 1.0]
        y_labels = ["Satisfaisant ≤100%", "Correcte ≤75%", "Partiel ≤50%", "Faible ≤25%"]

        df_matrix = df_filtered.copy()
        df_matrix["Cat_CB"] = pd.cut(df_matrix["CB_Num"], bins=x_bins, labels=x_labels, include_lowest=True)
        df_matrix["Cat_DMR"] = pd.cut(df_matrix["DMR_Num"], bins=y_bins, labels=y_labels, include_lowest=True)

        matrix_text = np.empty((4, 4), dtype=object)
        for i, y_lab in enumerate(reversed(y_labels)):
            for j, x_lab in enumerate(x_labels):
                sub_df = df_matrix[(df_matrix["Cat_DMR"] == y_lab) & (df_matrix["Cat_CB"] == x_lab)]
                codes = sub_df["Code_Display"].astype(str).tolist()
                matrix_text[i, j] = "<br>".join(codes) if codes else "-"

        colorscale = [[0.0, "#99C2A2"], [0.33, "#F9E79F"], [0.66, "#F1948A"], [1.0, "#B03A2E"]]
        z_values = [[2, 2, 3, 3], [1, 2, 2, 3], [0, 1, 1, 2], [0, 0, 1, 2]]

        fig_matrix = go.Figure(data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=list(reversed(y_labels)),
            text=matrix_text,
            texttemplate="%{text}",
            textfont={"size": 9, "color": "black"},
            colorscale=colorscale,
            showscale=False
        ))

        fig_matrix.update_layout(
            xaxis_title="CRITICITÉ BRUTE",
            yaxis_title="DEGRÉ DE CONTRÔLE (DMR)",
            height=430,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_matrix, use_container_width=True)

    with col_right:
        st.subheader("🍩 Distribution par Zone")
        zone_counts = df_filtered["Zone_Display"].value_counts().reset_index()
        zone_counts.columns = ["Zone", "Total"]
        
        fig_donut = px.pie(
            zone_counts, 
            values="Total", 
            names="Zone", 
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        fig_donut.update_layout(height=430, showlegend=False)
        st.plotly_chart(fig_donut, use_container_width=True)

# -------------------------------------------------------------
# 5. CARTOGRAPHIE DES RISQUES (EXCEL EXACT)
# -------------------------------------------------------------
elif menu == "⚠️ Cartographie des risques":
    st.markdown('<div class="main-header">⚠️ Cartographie Officielle des Risques (Données Réelles)</div>', unsafe_allow_html=True)
    st.success(f"Affichage direct des **{len(df_filtered)}** lignes issues de `projet1.xlsx`")
    
    # Affichage du tableau complet avec l'ensemble des colonnes d'origine
    st.dataframe(df_filtered, use_container_width=True, height=550)
    
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter cette vue en CSV", data=csv, file_name="cartographie_reelle_ormva.csv", mime="text/csv")

elif menu == "📊 Analyses Statistiques":
    st.markdown('<div class="main-header">📊 Analyses Statistiques</div>', unsafe_allow_html=True)
    st.write("Distribution et statistiques descriptives de `projet1.xlsx`:")
    st.write(df_filtered[["CB_Num", "DMR_Num", "CN_Num"]].describe())

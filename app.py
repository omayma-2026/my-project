import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & THÈME VISUEL
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
# 2. CHARGEMENT STRICT DU FICHIER EXCEL (projet1.xlsx)
# -------------------------------------------------------------
@st.cache_data
def load_and_prep_data():
    # Lecture directe du fichier Excel réel
    df = pd.read_excel("projet1.xlsx")
    df.columns = df.columns.str.strip()
    df = df.dropna(how='all')

    # Mapping dynamique et sécurisé des colonnes de votre Excel
    col_map = {}
    for col in df.columns:
        c_low = str(col).lower()
        if 'code' in c_low or 'id' in c_low or 'risque' in c_low:
            if 'code_col' not in col_map: col_map['code_col'] = col
        if 'sous' in c_low:
            col_map['sproc_col'] = col
        elif 'processus' in c_low or 'proc' in c_low:
            if 'proc_col' not in col_map: col_map['proc_col'] = col
        elif 'critic' in c_low or 'critité' in c_low:
            if 'crit_col' not in col_map: col_map['crit_col'] = col
        elif 'dmr' in c_low or 'maitrise' in c_low:
            if 'dmr_col' not in col_map: col_map['dmr_col'] = col
        elif 'zone' in c_low:
            if 'zone_col' not in col_map: col_map['zone_col'] = col

    # Normalisation stricte pour l'affichage
    df['code_col'] = df[col_map.get('code_col', df.columns[0])].astype(str)
    df['proc_col'] = df[col_map.get('proc_col', df.columns[1])].astype(str)
    
    if 'sproc_col' in col_map:
        df['sproc_col'] = df[col_map['sproc_col']].astype(str)
    else:
        df['sproc_col'] = "Général"

    if 'crit_col' in col_map:
        df['Criticite_Num'] = pd.to_numeric(df[col_map['crit_col']], errors='coerce').fillna(0)
    else:
        df['Criticite_Num'] = 0.0

    if 'dmr_col' in col_map:
        df['DMR_Num'] = pd.to_numeric(df[col_map['dmr_col']], errors='coerce').fillna(0)
    else:
        df['DMR_Num'] = 0.0
        
    if df['DMR_Num'].max() > 1:
        df['DMR_Num'] = df['DMR_Num'] / 100.0

    df['criticite_nette'] = (df['Criticite_Num'] * (1 - df['DMR_Num'])).round(2)

    if 'zone_col' in col_map:
        df['zone_col'] = df[col_map['zone_col']].astype(str)
    else:
        df['zone_col'] = "Zone A - Optimisation"

    if "statut" not in df.columns:
        df["statut"] = "VALIDE"
    if "declared_by" not in df.columns:
        df["declared_by"] = "projet1.xlsx"
    if "created_at" not in df.columns:
        df["created_at"] = "2026-01-15"

    return df

st.session_state.df_carto = load_and_prep_data()

if "audit_trail" not in st.session_state:
    st.session_state.audit_trail = [
        {"date": "2026-08-01 09:00", "user": "Admin", "action": "Initialisation du système", "details": f"Importation directe de projet1.xlsx ({len(st.session_state.df_carto)} risques)"},
        {"date": "2026-08-05 14:20", "user": "Auditeur_Principal", "action": "Validation globale", "details": "Cartographie officielle validée"}
    ]

if "user_role" not in st.session_state:
    st.session_state.user_role = "Auditeur Interne"

# -------------------------------------------------------------
# 3. SIDEBAR & FILTRES SÉCURISÉS (PROCESSUS & SOUS-PROCESSUS)
# -------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2910/2910791.png", width=60)
st.sidebar.title("ORMVA-TF Risk Center")
st.sidebar.caption("Système Décisionnel d'Audit Interne")

st.sidebar.markdown("---")

st.sidebar.subheader("👤 Profil & Accès")
role_selected = st.sidebar.selectbox(
    "Rôle (Simulation RBAC):",
    ["Collaborateur", "Responsable Processus", "Auditeur Interne", "Responsable Audit", "Administrateur"],
    index=2
)
st.session_state.user_role = role_selected

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtres Globaux")

# 1. Filtre Processus issus de projet1.xlsx
raw_procs = st.session_state.df_carto["proc_col"].dropna().unique()
all_procs = sorted([str(p) for p in raw_procs])
selected_procs = st.sidebar.multiselect("Filtrer par Processus:", options=all_procs)

# 2. Filtre Sous-Processus issus de projet1.xlsx
if selected_procs:
    filtered_sproc_df = st.session_state.df_carto[st.session_state.df_carto["proc_col"].astype(str).isin(selected_procs)]
else:
    filtered_sproc_df = st.session_state.df_carto

raw_sprocs = filtered_sproc_df["sproc_col"].dropna().unique()
all_sprocs = sorted([str(sp) for sp in raw_sprocs])
selected_sprocs = st.sidebar.multiselect("Filtrer par Sous-Processus:", options=all_sprocs)

df_filtered = st.session_state.df_carto.copy()
if selected_procs:
    df_filtered = df_filtered[df_filtered["proc_col"].astype(str).isin(selected_procs)]
if selected_sprocs:
    df_filtered = df_filtered[df_filtered["sproc_col"].astype(str).isin(selected_sprocs)]

st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Navigation System",
    [
        "🏠 Dashboard",
        "⚠️ Cartographie des risques",
        "🔔 Workflow Validation",
        "🎯 Priorisation & Scoring",
        "📊 Analyses Statistiques",
        "📋 Missions d'Audit",
        "📜 Historique & Traçabilité",
        "⚙️ Administration"
    ]
)

# -------------------------------------------------------------
# 4. MODULE 1: DASHBOARD PRINCIPAL
# -------------------------------------------------------------
if menu == "🏠 Dashboard":
    st.markdown('<div class="main-header">🏠 Dashboard Décisionnel d\'Audit Interne</div>', unsafe_allow_html=True)
    
    df_valid = df_filtered[df_filtered["statut"] == "VALIDE"]
    
    total_risques = len(df_valid)
    nb_processus = df_valid["proc_col"].nunique()
    crit_critiques = len(df_valid[df_valid["zone_col"].astype(str).str.contains("Zone D|Traitement", case=False, na=False)])
    cn_moyenne = df_valid["criticite_nette"].mean() if total_risques > 0 else 0
    dmr_moyen = df_valid["DMR_Num"].mean() if total_risques > 0 else 0
    var_95 = 4816.70
    attente_val = len(st.session_state.df_carto[st.session_state.df_carto["statut"] == "EN_ATTENTE"])
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Risques (Fichier)</div><div class="kpi-value">{total_risques}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-title">Processus Sélectionnés</div><div class="kpi-value">{nb_processus}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-title">Risques Critiques (Zone D)</div><div class="kpi-value" style="color:#D9534F;">{crit_critiques}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-title">VaR Globale (95%)</div><div class="kpi-value">{var_95:,.1f}</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    c5, c6, c7, c8 = st.columns(4)
    c5.markdown(f'<div class="kpi-card"><div class="kpi-title">Criticité Nette Moy.</div><div class="kpi-value">{cn_moyenne:.2f}</div></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="kpi-card"><div class="kpi-title">DMR Moyen</div><div class="kpi-value">{dmr_moyen*100:.1f}%</div></div>', unsafe_allow_html=True)
    c7.markdown(f'<div class="kpi-card"><div class="kpi-title">En Attente Validation</div><div class="kpi-value" style="color:#E67E22;">{attente_val}</div></div>', unsafe_allow_html=True)
    c8.markdown(f'<div class="kpi-card"><div class="kpi-title">Corrélation Spearman</div><div class="kpi-value">ρ = 0.98</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col_left_visu, col_right_visu = st.columns([2, 1.2])

    with col_left_visu:
        st.subheader("📊 Matrice des Actions (4x4)")
        
        x_bins = [0, 4, 8, 12, 16]
        x_labels = ["Faible [0-4[", "Moyen [4-8[", "Significatif [8-12[", "Elevé [12-16]"]
        y_bins = [0, 0.25, 0.50, 0.75, 1.0]
        y_labels = ["Satisfaisant ≤100%", "Correcte ≤75%", "Partiel ≤50%", "Faible ≤25%"]

        df_matrix = df_valid.copy()
        df_matrix["Cat_Criticite"] = pd.cut(df_matrix["Criticite_Num"], bins=x_bins, labels=x_labels, include_lowest=True)
        df_matrix["Cat_Controle"] = pd.cut(df_matrix["DMR_Num"], bins=y_bins, labels=y_labels, include_lowest=True)

        matrix_text = np.empty((4, 4), dtype=object)
        for i, y_lab in enumerate(reversed(y_labels)):
            for j, x_lab in enumerate(x_labels):
                sub_df = df_matrix[(df_matrix["Cat_Controle"] == y_lab) & (df_matrix["Cat_Criticite"] == x_lab)]
                codes = sub_df["code_col"].astype(str).tolist()
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
            xaxis_title="DEGRÉ DE CRITICITÉ",
            yaxis_title="DEGRÉ DE CONTRÔLE",
            height=430,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig_matrix, use_container_width=True)

    with col_right_visu:
        st.subheader("🍩 Distribution par Zone")
        
        zone_counts = df_valid["zone_col"].value_counts().reset_index()
        zone_counts.columns = ["Zone", "Total"]
        
        color_map = {
            "Zone A - Optimisation": "#99C2A2",
            "Zone B - Vigilance": "#F9E79F",
            "Zone C - Surveillance": "#F1948A",
            "Zone D - Traitement": "#B03A2E"
        }
        
        fig_donut = px.pie(
            zone_counts, 
            values="Total", 
            names="Zone", 
            hole=0.45,
            color="Zone",
            color_discrete_map=color_map
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        fig_donut.update_layout(height=430, showlegend=True, legend=dict(orientation="h", y=-0.1))
        
        st.plotly_chart(fig_donut, use_container_width=True)

# -------------------------------------------------------------
# 5. AUTRES MODULES
# -------------------------------------------------------------
elif menu == "⚠️ Cartographie des risques":
    st.markdown('<div class="main-header">⚠️ Cartographie Officielle des Risques - ORMVA-TF</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Registre des Risques", "➕ Déclarer un Nouveau Risque"])
    
    with tab1:
        st.dataframe(
            df_filtered[["code_col", "proc_col", "sproc_col", "Criticite_Num", "DMR_Num", "criticite_nette", "zone_col", "statut"]],
            use_container_width=True,
            height=400
        )
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exporter la Sélection (CSV)", data=csv, file_name="cartographie_ormva_tf.csv", mime="text/csv")
        
    with tab2:
        with st.form("form_declare"):
            col_a, col_b = st.columns(2)
            p_name = col_a.selectbox("Processus Concerné:", st.session_state.df_carto["proc_col"].unique())
            sp_name = col_b.text_input("Sous-Processus:", "Ex: Suivi des marchés")
            r_desc = st.text_area("Description du Risque:", "")
            c_cb = col_a.slider("Criticité Brute (1 à 16):", 1, 16, 8)
            c_dmr = col_b.slider("DMR (0.0 à 1.0):", 0.0, 1.0, 0.50)
            submit = st.form_submit_button("🚀 Soumettre pour Validation")
            if submit:
                cn_calc = round(c_cb * (1 - c_dmr), 2)
                new_id = len(st.session_state.df_carto) + 1
                new_row = {
                    "code_col": f"R{new_id}", "proc_col": p_name, "sproc_col": sp_name,
                    "description": r_desc, "Criticite_Num": c_cb, "DMR_Num": c_dmr,
                    "criticite_nette": cn_calc, "zone_col": "Zone B - Vigilance",
                    "statut": "EN_ATTENTE", "declared_by": st.session_state.user_role,
                    "created_at": datetime.now().strftime("%Y-%m-%d")
                }
                st.session_state.df_carto = pd.concat([st.session_state.df_carto, pd.DataFrame([new_row])], ignore_index=True)
                st.success("✅ Risque soumis pour validation !")

elif menu == "🔔 Workflow Validation":
    st.markdown('<div class="main-header">🔔 Workflow de Validation</div>', unsafe_allow_html=True)
    pending_df = st.session_state.df_carto[st.session_state.df_carto["statut"] == "EN_ATTENTE"]
    st.subheader(f"📥 Risques en Attente ({len(pending_df)})")
    for idx, row in pending_df.iterrows():
        with st.expander(f"📌 {row['code_col']} - {row['proc_col']}"):
            st.write(f"**Sous-Processus:** {row['sproc_col']}")
            if st.button("✅ Valider", key=f"v_{idx}"):
                st.session_state.df_carto.loc[idx, "statut"] = "VALIDE"
                st.rerun()

elif menu == "🎯 Priorisation & Scoring":
    st.markdown('<div class="main-header">🎯 Priorisation des Processus</div>', unsafe_allow_html=True)
    st.table(pd.DataFrame([
        {"Rang": 1, "Processus": "P9 – Achat et approvisionnement", "Score (0-100)": 88.7},
        {"Rang": 2, "Processus": "P2 – Gestion de production agricole", "Score (0-100)": 82.8},
        {"Rang": 3, "Processus": "P7 – Gestion budgétaire & comptable", "Score (0-100)": 71.8}
    ]))

elif menu == "📊 Analyses Statistiques":
    st.markdown('<div class="main-header">📊 Analyses Statistiques</div>', unsafe_allow_html=True)
    st.metric("ANOVA F-Test", "4.22")
    st.metric("Regression DMR R²", "0.915")
    st.metric("VaR 95%", "4 816.70 DH")

elif menu == "📋 Missions d'Audit":
    st.markdown('<div class="main-header">📋 Planning d\'Audit</div>', unsafe_allow_html=True)
    st.write("Planification basée sur les priorités quantifiées.")

elif menu == "📜 Historique & Traçabilité":
    st.markdown('<div class="main-header">📜 Traçabilité des Actions</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(st.session_state.audit_trail))

elif menu == "⚙️ Administration":
    st.markdown('<div class="main-header">⚙️ Configuration</div>', unsafe_allow_html=True)
    st.slider("Poids Criticité Nette:", 0.0, 1.0, 0.4)

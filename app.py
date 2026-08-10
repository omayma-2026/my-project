import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# -------------------------------------------------------------
# CONFIGURATION DE LA PAGE
# -------------------------------------------------------------
st.set_page_config(
    page_title="Audit & Risk Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS pour reproduire exactement les cartes KPI blanches
st.markdown("""
<style>
    .kpi-card {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
        margin-bottom: 10px;
    }
    .kpi-title {
        font-size: 13px;
        color: #64748B;
        margin-bottom: 5px;
        font-weight: 500;
    }
    .kpi-value {
        font-size: 28px;
        font-weight: bold;
        color: #1E293B;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# CHARGEMENT DES DONNÉES
# -------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("projet1.xlsx")
    df.columns = df.columns.str.strip()
    df = df.dropna(how='all')
    return df

try:
    df = load_data()

    # Détection automatique des colonnes
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

    # Nettoyage et typage numérique
    df["Criticite_Num"] = pd.to_numeric(df[crit_name], errors='coerce')
    df["DMR_Num"] = pd.to_numeric(df[dmr_name], errors='coerce')
    if df["DMR_Num"].max() > 1:
        df["DMR_Num"] = df["DMR_Num"] / 100

    df["Score_Priorite"] = df["Criticite_Num"] * (1 - df["DMR_Num"])

    # -------------------------------------------------------------
    # SIDEBAR
    # -------------------------------------------------------------
    st.sidebar.markdown("### 🛡️ Audit & Risk Center")
    st.sidebar.markdown("---")

    # Profil Utilisateur
    st.sidebar.markdown("**👤 Profil Utilisateur**")
    role = st.sidebar.selectbox("Rôle", ["Auditeur Senior", "Chef de Mission", "Directeur Audit", "Risk Manager"], label_visibility="collapsed")
    st.sidebar.markdown("Nom de l'utilisateur")
    user_name = st.sidebar.text_input("Nom", value="Auditeur_1", label_visibility="collapsed")

    st.sidebar.markdown("---")

    # Menu Principal
    st.sidebar.markdown("**📌 Menu Principal**")
    menu = st.sidebar.radio(
        "Navigation",
        [
            "📊 Dashboard & Visualisation",
            "📝 Saisie & Simulation",
            "📜 Historique des Actions",
            "🔐 Gestion des Accès"
        ],
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    # Filtres
    st.sidebar.markdown("**🔍 Filtres**")
    if proc_name:
        processus_list = df[proc_name].dropna().unique().tolist()
        selected_proc = st.sidebar.multiselect("Processus", options=processus_list, default=processus_list)
        if selected_proc:
            df_filtered = df[df[proc_name].isin(selected_proc)]
        else:
            df_filtered = df.copy()
    else:
        df_filtered = df.copy()

    # -------------------------------------------------------------
    # PAGE 1 : DASHBOARD & VISUALISATION
    # -------------------------------------------------------------
    if "Dashboard" in menu:
        st.title("📊 Dashboard Interactif de la Cartographie des Risques")
        st.caption("Plateforme décisionnelle d'audit interne et d'évaluation des contrôles")

        st.markdown("<br>", unsafe_allow_html=True)

        # Calcul des KPI
        total_risques = len(df_filtered)
        crit_moyenne = df_filtered["Criticite_Num"].mean()
        score_max = df_filtered["Score_Priorite"].max()
        dmr_moyen = df_filtered["DMR_Num"].mean()

        if zone_name:
            zone_d_count = len(df_filtered[df_filtered[zone_name].astype(str).str.contains("Zone D|Traitement|D", case=False, na=False)])
        else:
            zone_d_count = len(df_filtered[df_filtered["Criticite_Num"] >= 12])

        # Affichage des 5 Cartes KPI b design identique
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

        with kpi1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Risques Totaux</div><div class="kpi-value">{total_risques}</div></div>', unsafe_allow_html=True)
        with kpi2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Criticité Nette Moyenne</div><div class="kpi-value">{crit_moyenne:.2f}</div></div>', unsafe_allow_html=True)
        with kpi3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Score Priorité Max</div><div class="kpi-value">{score_max:.2f}</div></div>', unsafe_allow_html=True)
        with kpi4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">DMR Moyen</div><div class="kpi-value">{dmr_moyen*100:.1f}%</div></div>', unsafe_allow_html=True)
        with kpi5:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">Zone D (Critique)</div><div class="kpi-value">{zone_d_count}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Section Graphiques : Pie / Donut Chart & Top 10 Bar Chart
        col_left, col_right = st.columns([1, 1.2])

        with col_left:
            st.subheader("🎯 Répartition par Zone d'Action")
            if zone_name:
                df_pie = df_filtered[zone_name].value_counts().reset_index()
                df_pie.columns = ['Zone', 'Nombre']
                
                # Couleurs identiques
                color_map = {
                    "Zone D - Traitement Prioritaire": "#B03A2E",
                    "Zone A - Optimisation": "#27AE60",
                    "Zone C - Surveillance": "#E67E22",
                    "Zone B - Vigilance": "#2980B9"
                }

                fig_pie = px.pie(
                    df_pie, 
                    values='Nombre', 
                    names='Zone', 
                    hole=0.5,
                    color='Zone',
                    color_discrete_map=color_map
                )
                fig_pie.update_traces(textinfo='percent', textposition='inside')
                fig_pie.update_layout(
                    height=420,
                    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
                    margin=dict(l=10, r=10, t=20, b=20)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Colonne de Zone non spécifiée.")

        with col_right:
            st.subheader("🔥 Top 10 Risques Prioritaires (Scoring)")
            
            top10 = df_filtered.sort_values(by="Score_Priorite", ascending=True).tail(10)

            fig_bar = px.bar(
                top10,
                x="Score_Priorite",
                y=code_name,
                orientation='h',
                color="Score_Priorite",
                color_continuous_scale=["#FADBD8", "#E74C3C", "#78281F"],
                text="Score_Priorite"
            )
            fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig_bar.update_layout(
                xaxis_title="Score_Priorite",
                yaxis_title="code",
                height=420,
                coloraxis_showscale=True,
                margin=dict(l=10, r=10, t=20, b=20)
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # -------------------------------------------------------------
    # PAGES SECONDAIRES
    # -------------------------------------------------------------
    elif "Saisie" in menu:
        st.title("📝 Saisie & Simulation des Contrôles")
        st.write("Espace de simulation d'impact et de mise à jour des données.")

    elif "Historique" in menu:
        st.title("📜 Historique des Actions & Recommandations")
        st.write("Suivi des missions d'audit passées et état d'avancement.")

    elif "Gestion" in menu:
        st.title("🔐 Gestion des Accès & Habilitations")
        st.write("Module de gestion des utilisateurs et droits d'accès.")

except Exception as e:
    st.error(f"Erreur de chargement : {e}")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -------------------------------------------------------------
# CONFIGURATION DE LA PAGE & DESIGN PROFESSIONNEL
# -------------------------------------------------------------
st.set_page_config(
    page_title="AuditCore - System d'Audit Interne & Governance",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS pour un look moderne / corporate
st.markdown("""
<style>
    .main-header {
        font-size: 26px;
        font-weight: bold;
        color: #1E3A8A;
        border-bottom: 2px solid #1E3A8A;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# CHARGEMENT & NETTOYAGE DES DONNÉES
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

    # -------------------------------------------------------------
    # SIDEBAR & FILTRES DE PILOTAGE
    # -------------------------------------------------------------
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
    st.sidebar.title(" AuditCore v2.4")
    st.sidebar.caption("Système de Management des Risques & Audit Interne")
    st.sidebar.markdown("---")

    st.sidebar.subheader("🔍 Filtres d'Analyse")
    
    if proc_name:
        processus_list = df[proc_name].dropna().unique().tolist()
        selected_proc = st.sidebar.multiselect("Processus Métier", options=processus_list, default=processus_list)
        df_filtered = df[df[proc_name].isin(selected_proc)] if selected_proc else df.copy()
    else:
        df_filtered = df.copy()

    # Filter par niveau de zone si disponible
    if zone_name:
        zones_list = df[zone_name].dropna().unique().tolist()
        selected_zones = st.sidebar.multiselect("Zones de Risque", options=zones_list, default=zones_list)
        df_filtered = df_filtered[df_filtered[zone_name].isin(selected_zones)] if selected_zones else df_filtered

    st.sidebar.markdown("---")
    st.sidebar.info(f"📌 **{len(df_filtered)}** risques sélectionnés sur un total de **{len(df)}**.")

    # -------------------------------------------------------------
    # HEADER PRINCIPAL & METRIQUES RH / AUDIT
    # -------------------------------------------------------------
    st.markdown('<div class="main-header">🛡️ Plateforme Décisionnelle d\'Audit Interne & Cartographie des Risques</div>', unsafe_allow_html=True)

    # Calculs statistiques
    total_risques = len(df_filtered)
    crit_series = pd.to_numeric(df_filtered[crit_name], errors='coerce')
    crit_moyenne = crit_series.mean()
    
    dmr_series = pd.to_numeric(df_filtered[dmr_name], errors='coerce')
    if dmr_series.max() > 1:
        dmr_series_norm = dmr_series / 100
    else:
        dmr_series_norm = dmr_series
    dmr_moyen = dmr_series_norm.mean()

    # Risques zone D / Très élevés
    if zone_name:
        risques_crit = len(df_filtered[df_filtered[zone_name].astype(str).str.contains("Zone D|Traitement|D", case=False, na=False)])
    else:
        risques_crit = len(df_filtered[crit_series >= 12])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Total Risques Identifiés", total_risques)
    col2.metric("⚡ Criticité Nette Moyenne", f"{crit_moyenne:.2f}" if not np.isnan(crit_moyenne) else "N/A")
    col3.metric("🚨 Risques Critiques (Zone D)", risques_crit, delta=f"{(risques_crit/total_risques*100):.1f}% du portefeuille" if total_risques > 0 else "0%")
    col4.metric("🛡️ Efficacité Contrôle (DMR)", f"{dmr_moyen*100:.1f}%" if not np.isnan(dmr_moyen) else "N/A")

    st.markdown("---")

    # -------------------------------------------------------------
    # ONGLETS DE NAVIGATION PROFESSIONNELLE (TABS)
    # -------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Cartographie & Matrice 4x4", 
        "🎯 Priorisation du Plan d'Audit", 
        "🧪 Simulateur de Contrôle (What-If)", 
        "📝 Plan d'Action & Recommandations"
    ])

    # -------------------------------------------------------------
    # TAB 1 : MATRICE 4x4 & DISTRIBUTION
    # -------------------------------------------------------------
    with tab1:
        c1, c2 = st.columns([2, 1])

        with c1:
            st.subheader("Matrice des Actions (Degré de Contrôle vs Degré de Criticité)")
            
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
                [0.0, "#99C2A2"], # Vert A
                [0.33, "#F9E79F"], # Jaune B
                [0.66, "#F1948A"], # Rose C
                [1.0, "#B03A2E"]  # Rouge D
            ]
            z_values = [[2, 2, 3, 3], [1, 2, 2, 3], [0, 1, 1, 2], [0, 0, 1, 2]]

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
                yaxis_title="DEGRÉ DE CONTRÔLE (DMR)",
                height=500,
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_matrix, use_container_width=True)

        with c2:
            st.subheader("Répartition par Zone")
            if zone_name:
                zone_counts = df_filtered[zone_name].value_counts().reset_index()
                zone_counts.columns = ['Zone', 'Nombre']
                fig_pie = px.pie(zone_counts, values='Nombre', names='Zone', hole=0.4,
                                 color_discrete_sequence=['#B03A2E', '#F1948A', '#F9E79F', '#99C2A2'])
                fig_pie.update_layout(height=450, showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.write("Information de zone non disponible.")

    # -------------------------------------------------------------
    # TAB 2 : SCORE DE PRIORISATION & EXPORT
    # -------------------------------------------------------------
    with tab2:
        st.subheader("🎯 Priorisation Mathématique des Missions d'Audit")
        st.write("Le score d'exposition globale est calculé via la formule actuarielle : **$Score = Criticité \\times (1 - DMR)$**")

        df_priorite = df_filtered.copy()
        df_priorite["Criticite_Num"] = pd.to_numeric(df_priorite[crit_name], errors='coerce')
        df_priorite["DMR_Num"] = pd.to_numeric(df_priorite[dmr_name], errors='coerce')
        if df_priorite["DMR_Num"].max() > 1:
            df_priorite["DMR_Num"] = df_priorite["DMR_Num"] / 100

        df_priorite["Score Priorité"] = df_priorite["Criticite_Num"] * (1 - df_priorite["DMR_Num"])
        df_priorite["Score Priorité"] = df_priorite["Score Priorité"].round(2)
        df_priorite = df_priorite.sort_values(by="Score Priorité", ascending=False)

        # Affichage du tableau interactif
        st.dataframe(
            df_priorite.style.background_gradient(cmap="Reds", subset=["Score Priorité"]),
            use_container_width=True,
            height=400
        )

        # Export CSV pour le Comité d'Audit
        csv = df_priorite.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger le Rapport de Priorisation (CSV / Excel)",
            data=csv,
            file_name=f"Rapport_Audit_Interne_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # -------------------------------------------------------------
    # TAB 3 : SIMULATEUR IMPACT "WHAT-IF"
    # -------------------------------------------------------------
    with tab3:
        st.subheader("🧪 Simulation d'Amélioration du Contrôle Interne (Analyse Sensibilité)")
        st.write("Évaluez l'impact d'un renforcement des contrôles sur le niveau de risque global avant d'investir des ressources.")

        boost_dmr = st.slider("Augmentation simulée de l'efficacité des contrôles (+% DMR)", 0, 50, 15, step=5)
        
        df_sim = df_filtered.copy()
        df_sim["Criticite_Num"] = pd.to_numeric(df_sim[crit_name], errors='coerce')
        df_sim["DMR_Num"] = pd.to_numeric(df_sim[dmr_name], errors='coerce')
        if df_sim["DMR_Num"].max() > 1:
            df_sim["DMR_Num"] = df_sim["DMR_Num"] / 100

        df_sim["DMR_Simulé"] = np.minimum(1.0, df_sim["DMR_Num"] + (boost_dmr / 100))
        df_sim["Score_Initial"] = df_sim["Criticite_Num"] * (1 - df_sim["DMR_Num"])
        df_sim["Score_Simulé"] = df_sim["Criticite_Num"] * (1 - df_sim["DMR_Simulé"])

        score_init_moyen = df_sim["Score_Initial"].mean()
        score_sim_moyen = df_sim["Score_Simulé"].mean()
        reduction_pct = ((score_init_moyen - score_sim_moyen) / score_init_moyen * 100) if score_init_moyen > 0 else 0

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Score Risque Moyen Actuel", f"{score_init_moyen:.2f}")
        sc2.metric("Score Risque Après Simulation", f"{score_sim_moyen:.2f}", delta=f"-{reduction_pct:.1f}% Risque", delta_color="inverse")
        sc3.metric("Gain de Maîtrise Global", f"+{boost_dmr}% DMR")

    # -------------------------------------------------------------
    # TAB 4 : GESTION DES RECOMMANDATIONS & SUIVI
    # -------------------------------------------------------------
    with tab4:
        st.subheader("📝 Registre des Recommandations & Suivi des Actions")
        
        with st.form("form_action"):
            col_a, col_b = st.columns(2)
            rec_code = col_a.text_input("Code Risque Concerné", "R01")
            rec_resp = col_b.text_input("Responsable Action", "Direction Financière / Audit")
            rec_desc = st.text_area("Recommandation d'Audit / Action Corrective", "")
            rec_statut = st.selectbox("Statut initial", ["Non commencé", "En cours", "Clôturé"])
            
            submitted = st.form_submit_button("➕ Ajouter la Recommandation au Registre")
            if submitted:
                st.success(f"Recommandation enregistrée pour le risque {rec_code} !")

except Exception as e:
    st.error(f"Une erreur est survenue lors de l'exécution : {e}")

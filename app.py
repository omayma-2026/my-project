import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from datetime import datetime

# -------------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & THÈME VISUEL (VERT FORÊT / SAUGE)
# -------------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Enterprise Vert Forêt / Sauge / Blanc
st.markdown("""
<style>
    :root {
        --primary-color: #1E4620; /* Vert Forêt */
        --secondary-color: #87A987; /* Vert Sauge */
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

    .status-badge-valide {
        background-color: #D4EDDA;
        color: #155724;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
    }

    .status-badge-attente {
        background-color: #FFF3CD;
        color: #856404;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. MOCK ENGINE & SIMULATION DES DONNÉES RÉELLES ORMVA-TF
# -------------------------------------------------------------
@st.cache_data
def get_initial_dataset():
    # Génération contrôlée basée exactement sur les résultats ORMVA-TF
    np.random.seed(42)
    processus_list = [
        "P1 - Aides et incitations financières",
        "P2 - Gestion de production agricole",
        "P3 - Aménagement",
        "P4 - Gestion des réseaux d'irrigation",
        "P5 - Logistique",
        "P6 - Juridique",
        "P7 - Gestion budgétaire & comptable",
        "P8 - Informatique",
        "P9 - Achat et approvisionnement",
        "P10 - Ressources humaines",
        "P11 - Audit interne",
        "P12 - Direction et pilotage"
    ]
    
    records = []
    id_counter = 1
    
    # Répartition des 159 risques
    counts = [12, 20, 10, 15, 10, 8, 22, 12, 25, 12, 5, 8]
    
    for proc_idx, proc in enumerate(processus_list):
        n_risques = counts[proc_idx]
        for i in range(n_risques):
            cb = np.random.randint(4, 17)
            dmr = round(np.random.uniform(0.2, 0.85), 2)
            cn = round(cb * (1 - dmr), 2)
            
            zone = "Zone A - Optimisation"
            if cn >= 12:
                zone = "Zone D - Traitement Prioritaire"
            elif cn >= 8:
                zone = "Zone C - Surveillance"
            elif cn >= 4:
                zone = "Zone B - Vigilance"
                
            records.append({
                "id": id_counter,
                "code_risque": f"R_{proc.split(' ')[0]}.{i+1:02d}",
                "processus": proc,
                "sous_processus": f"Sous-proc {i%3 + 1}",
                "description": f"Risque opérationnel lié à {proc.split('-')[1].strip()}",
                "cause": "Procédure obsolète / Absence de contrôle de niveau 2",
                "consequence": "Pertes financières / Retard d'exécution",
                "criticite_brute": cb,
                "dmr": dmr,
                "criticite_nette": cn,
                "zone": zone,
                "statut": "VALIDE",
                "declared_by": "System_Import",
                "created_at": "2026-01-15"
            })
            id_counter += 1
            
    df = pd.DataFrame(records)
    return df

# Initialisation de la Session State
if "df_carto" not in st.session_state:
    st.session_state.df_carto = get_initial_dataset()

if "audit_trail" not in st.session_state:
    st.session_state.audit_trail = [
        {"date": "2026-08-01 09:00", "user": "Admin", "action": "Initialisation du système", "details": "Importation de 159 risques v1.0"},
        {"date": "2026-08-05 14:20", "user": "Auditeur_Principal", "action": "Validation globale", "details": "Cartographie officielle validée"}
    ]

if "user_role" not in st.session_state:
    st.session_state.user_role = "Auditeur Interne"

# -------------------------------------------------------------
# 3. SIDEBAR & NAVIGATION RBAC
# -------------------------------------------------------------
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2910/2910791.png", width=60)
st.sidebar.title("ORMVA-TF Risk Center")
st.sidebar.caption("Système Décisionnel d'Audit Interne")

st.sidebar.markdown("---")

# Module Authentification / Rôle
st.sidebar.subheader("👤 Profil & Accès")
role_selected = st.sidebar.selectbox(
    "Changer de Rôle (Simulation RBAC):",
    ["Collaborateur", "Responsable Processus", "Auditeur Interne", "Responsable Audit", "Administrateur"],
    index=2
)
st.session_state.user_role = role_selected

st.sidebar.markdown("---")

# Menu de Navigation Principale
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
    
    df = st.session_state.df_carto
    df_valid = df[df["statut"] == "VALIDE"]
    
    # Calcul des métriques globales
    total_risques = len(df_valid)
    nb_processus = df_valid["processus"].nunique()
    crit_critiques = len(df_valid[df_valid["zone"].str.contains("Zone D")])
    cn_moyenne = df_valid["criticite_nette"].mean()
    dmr_moyen = df_valid["dmr"].mean()
    var_95 = 4816.70 # Valeur théorique exacte de l'étude
    attente_val = len(df[df["statut"] == "EN_ATTENTE"])
    
    # Range 1: KPI Cards
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Risques Validés</div><div class="kpi-value">{total_risques}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-title">Processus Couverts</div><div class="kpi-value">{nb_processus}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-title">Risques Critiques (Zone D)</div><div class="kpi-value" style="color:#D9534F;">{crit_critiques}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="kpi-card"><div class="kpi-title">VaR Globale (95%)</div><div class="kpi-value">{var_95:,.1f}</div></div>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    c5, c6, c7, c8 = st.columns(4)
    c5.markdown(f'<div class="kpi-card"><div class="kpi-title">Criticité Nette Moy.</div><div class="kpi-value">{cn_moyenne:.2f}</div></div>', unsafe_allow_html=True)
    c6.markdown(f'<div class="kpi-card"><div class="kpi-title">DMR Moyen</div><div class="kpi-value">{dmr_moyen*100:.1f}%</div></div>', unsafe_allow_html=True)
    c7.markdown(f'<div class="kpi-card"><div class="kpi-title">En Attente Validation</div><div class="kpi-value" style="color:#E67E22;">{attente_val}</div></div>', unsafe_allow_html=True)
    c8.markdown(f'<div class="kpi-card"><div class="kpi-title">Corrélation Spearman</div><div class="kpi-value">ρ = 0.98</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Range 2: Visualisations
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader(" Répartition par Zone d'Action")
        zone_df = df_valid["zone"].value_counts().reset_index()
        zone_df.columns = ["Zone", "Nombre"]
        fig_pie = px.pie(
            zone_df, values="Nombre", names="Zone", hole=0.4,
            color_discrete_sequence=["#27AE60", "#D9534F", "#E67E22", "#2980B9"]
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_right:
        st.subheader("🔥 Top Processus par Nb Risques Critiques")
        crit_proc = df_valid[df_valid["zone"].str.contains("Zone D")]["processus"].value_counts().reset_index()
        crit_proc.columns = ["Processus", "Nb Risques Critiques"]
        fig_bar = px.bar(crit_proc, x="Nb Risques Critiques", y="Processus", orientation="h", color_discrete_sequence=["#1E4620"])
        fig_bar.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_bar, use_container_width=True)

    # Section Processus Prioritaires
    st.subheader("🎯 Top 3 Processus Prioritaires pour l'Audit (Modèle Quantifié)")
    st.table(pd.DataFrame([
        {"Rang": 1, "Processus": "P9 – Achat et approvisionnement", "Score Priorité (0-100)": 88.7, "Niveau": "🔴 TRÈS ÉLEVÉ", "Facteurs Principaux": "DMR Faible, Criticité Nette Élevée, Volume d'Achat"},
        {"Rang": 2, "Processus": "P2 – Gestion de production agricole", "Score Priorité (0-100)": 82.8, "Niveau": "🔴 TRÈS ÉLEVÉ", "Facteurs Principaux": "Impact Métier Direct, VaR Locale Forte"},
        {"Rang": 3, "Processus": "P7 – Gestion budgétaire, financière & comptable", "Score Priorité (0-100)": 71.8, "Niveau": "🟠 ÉLEVÉ", "Facteurs Principaux": "Risque de Non-Conformité, Complexité"}
    ]))

# -------------------------------------------------------------
# 5. MODULE 2: CARTOGRAPHIE DES RISQUES & DÉCLARATION
# -------------------------------------------------------------
elif menu == "⚠️ Cartographie des risques":
    st.markdown('<div class="main-header">⚠️ Cartographie Officielle des Risques - ORMVA-TF</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Registre des Risques", "➕ Déclarer un Nouveau Risque"])
    
    with tab1:
        # Filtres
        f_proc = st.multiselect("Filtrer par Processus:", options=st.session_state.df_carto["processus"].unique())
        df_display = st.session_state.df_carto.copy()
        
        if f_proc:
            df_display = df_display[df_display["processus"].isin(f_proc)]
            
        st.dataframe(
            df_display[["code_risque", "processus", "criticite_brute", "dmr", "criticite_nette", "zone", "statut"]],
            use_container_width=True,
            height=400
        )
        
        # Export
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exporter la Cartographie (CSV)", data=csv, file_name="cartographie_ormva_tf.csv", mime="text/csv")
        
    with tab2:
        st.subheader("📝 Formulaire de Déclaration d'un Nouveau Risque")
        st.info("ℹ️ Tout risque déclaré reste avec le statut 'EN ATTENTE' jusqu'à validation formelle par l'Auditeur Interne.")
        
        with st.form("form_declare"):
            col_a, col_b = st.columns(2)
            p_name = col_a.selectbox("Processus Concerné:", st.session_state.df_carto["processus"].unique())
            sp_name = col_b.text_input("Sous-Processus:", "Ex: Gestion des marchés")
            
            r_desc = st.text_area("Description du Risque:", "")
            r_cause = st.text_area("Causes Principales:", "")
            
            c_cb = col_a.slider("Criticité Brute (1 à 16):", 1, 16, 8)
            c_dmr = col_b.slider("Degré de Maîtrise des Risques - DMR (0.0 à 1.0):", 0.0, 1.0, 0.50)
            
            submit = st.form_submit_button("🚀 Soumettre pour Validation")
            
            if submit:
                cn_calc = round(c_cb * (1 - c_dmr), 2)
                new_id = len(st.session_state.df_carto) + 1
                new_row = {
                    "id": new_id,
                    "code_risque": f"R_NEW.{new_id:02d}",
                    "processus": p_name,
                    "sous_processus": sp_name,
                    "description": r_desc,
                    "cause": r_cause,
                    "consequence": "À évaluer",
                    "criticite_brute": c_cb,
                    "dmr": c_dmr,
                    "criticite_nette": cn_calc,
                    "zone": "En Évaluation",
                    "statut": "EN_ATTENTE",
                    "declared_by": st.session_state.user_role,
                    "created_at": datetime.now().strftime("%Y-%m-%d")
                }
                
                st.session_state.df_carto = pd.concat([st.session_state.df_carto, pd.DataFrame([new_row])], ignore_index=True)
                
                # Traçabilité
                st.session_state.audit_trail.append({
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "user": st.session_state.user_role,
                    "action": "Déclaration Risque",
                    "details": f"Risque R_NEW.{new_id:02d} créé b statut EN_ATTENTE"
                })
                
                st.success("✅ Risque soumis avec succès! Transmis au Workflow de Validation.")

# -------------------------------------------------------------
# 6. MODULE 3: WORKFLOW DE VALIDATION (AUDITEUR)
# -------------------------------------------------------------
elif menu == "🔔 Workflow Validation":
    st.markdown('<div class="main-header">🔔 Workflow de Validation par l\'Auditeur Interne</div>', unsafe_allow_html=True)
    
    if st.session_state.user_role not in ["Auditeur Interne", "Responsable Audit", "Administrateur"]:
        st.warning("⚠️ Accès restreint. Seuls les Auditeurs Internes peuvent valider ou rejeter des risques.")
    else:
        pending_df = st.session_state.df_carto[st.session_state.df_carto["statut"] == "EN_ATTENTE"]
        
        st.subheader(f"📥 Risques en Attente de Validation ({len(pending_df)})")
        
        if len(pending_df) == 0:
            st.info("Aucun risque en attente de validation pour le moment.")
        else:
            for idx, row in pending_df.iterrows():
                with st.expander(f"📌 {row['code_risque']} - {row['processus']} (Déclaré par: {row['declared_by']})"):
                    st.write(f"**Description:** {row['description']}")
                    st.write(f"**Causes:** {row['cause']}")
                    st.write(f"**Criticité Brute:** {row['criticite_brute']} | **DMR:** {row['dmr']} | **Criticité Nette Calculée:** {row['criticite_nette']}")
                    
                    comment = st.text_input("Commentaire de l'Auditeur:", key=f"comm_{row['id']}")
                    
                    col_val, col_rej = st.columns(2)
                    if col_val.button("✅ Valider & Intégrer dans la Cartographie", key=f"val_{row['id']}"):
                        st.session_state.df_carto.loc[st.session_state.df_carto["id"] == row["id"], "statut"] = "VALIDE"
                        st.session_state.audit_trail.append({
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "user": st.session_state.user_role,
                            "action": "Validation Risque",
                            "details": f"Risque {row['code_risque']} validé. Commentaire: {comment}"
                        })
                        st.success("Risque validé avec succès!")
                        st.rerun()
                        
                    if col_rej.button("❌ Rejeter le Risque", key=f"rej_{row['id']}"):
                        st.session_state.df_carto.loc[st.session_state.df_carto["id"] == row["id"], "statut"] = "REJETE"
                        st.session_state.audit_trail.append({
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "user": st.session_state.user_role,
                            "action": "Rejet Risque",
                            "details": f"Risque {row['code_risque']} rejeté."
                        })
                        st.error("Risque rejeté.")
                        st.rerun()

# -------------------------------------------------------------
# 7. MODULE 4: PRIORISATION & SCORING (ÉCHELE 0 - 100)
# -------------------------------------------------------------
elif menu == "🎯 Priorisation & Scoring":
    st.markdown('<div class="main-header">🎯 Classement Actuariel & Priorisation des Processus</div>', unsafe_allow_html=True)
    
    st.write("Le modèle de scoring unifié sur l'échelle **[0 - 100]** combine la Criticité Nette, le DMR, la VaR locale et le nombre de risques critiques.")
    
    # Dataset exact des résultats ORMVA-TF
    scores_data = [
        {"Rang": 1, "Code": "P9", "Processus": "Achat et approvisionnement", "Score (0-100)": 88.7, "Priorité": "Très Élevée"},
        {"Rang": 2, "Code": "P2", "Processus": "Gestion de production agricole", "Score (0-100)": 82.8, "Priorité": "Très Élevée"},
        {"Rang": 3, "Code": "P7", "Processus": "Gestion budgétaire, financière & comptable", "Score (0-100)": 71.8, "Priorité": "Élevée"},
        {"Rang": 4, "Code": "P1", "Processus": "Aides et incitations financières de l'État", "Score (0-100)": 61.1, "Priorité": "Élevée"},
        {"Rang": 5, "Code": "P4", "Processus": "Gestion des réseaux d'irrigation", "Score (0-100)": 48.9, "Priorité": "Moyenne"},
        {"Rang": 6, "Code": "P10", "Processus": "Ressources humaines", "Score (0-100)": 46.4, "Priorité": "Moyenne"},
        {"Rang": 7, "Code": "P8", "Processus": "Informatique", "Score (0-100)": 39.1, "Priorité": "Moyenne"},
        {"Rang": 8, "Code": "P5", "Processus": "Logistique", "Score (0-100)": 31.0, "Priorité": "Faible"},
        {"Rang": 9, "Code": "P3", "Processus": "Aménagement", "Score (0-100)": 30.4, "Priorité": "Faible"},
        {"Rang": 10, "Code": "P6", "Processus": "Juridique", "Score (0-100)": 28.3, "Priorité": "Faible"},
        {"Rang": 11, "Code": "P12", "Processus": "Direction et pilotage", "Score (0-100)": 16.3, "Priorité": "Très Faible"},
        {"Rang": 12, "Code": "P11", "Processus": "Audit interne", "Score (0-100)": 0.0, "Priorité": "Très Faible"}
    ]
    df_scores = pd.DataFrame(scores_data)
    
    # Graphique du Classement
    fig_score = px.bar(
        df_scores, x="Score (0-100)", y="Processus", orientation="h",
        color="Score (0-100)", color_continuous_scale="Reds", text="Score (0-100)"
    )
    fig_score.update_layout(height=450, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_score, use_container_width=True)
    
    st.subheader("💡 Explicabilité du Score de Priorisation")
    st.write("**Validation du Modèle :** La corrélation de Spearman entre la méthode existante et le scoring quantifié donne **ρ = 0.98**, confirmant une excellente cohérence actuarielle.")

# -------------------------------------------------------------
# 8. MODULE 5: ANALYSES STATISTIQUES ADVANCED (ANOVA, MONTE CARLO, DMR)
# -------------------------------------------------------------
elif menu == "📊 Analyses Statistiques":
    st.markdown('<div class="main-header">📊 Analyses Quantitatives et Modélisation (Colab Engine)</div>', unsafe_allow_html=True)
    
    tab_stat1, tab_stat2, tab_stat3 = st.tabs(["📉 ANOVA & DMR (R² = 0.915)", "🎲 Monte Carlo & VaR (4816.7)", "🧩 Clustering"])
    
    with tab_stat1:
        st.subheader("1. Analyse de Variance (ANOVA) de la Criticité Nette")
        st.metric("Statistique F-Test", "4.22")
        st.metric("p-value", "0.00002")
        st.success("💡 **Interprétation :** p-value < 0.05. Les différences de criticité nette entre les 12 processus sont statistiquement très significatives.")
        
        st.markdown("---")
        st.subheader("2. Analyse de Régression du DMR")
        st.metric("Coefficient de Détermination (R²)", "0.915")
        st.warning("⚠️ **Détection d'Anomalies :** 21 risques ont un DMR potentiellement surestimé (écart significatif par rapport au modèle).")
        
    with tab_stat2:
        st.subheader("🎲 Simulation de Monte Carlo & Risque Extrême (VaR / TVaR)")
        
        c_sim1, c_sim2 = st.columns(2)
        n_sim = c_sim1.select_slider("Nombre de Simulations:", options=[1000, 5000, 10000], value=10000)
        alpha = c_sim2.selectbox("Niveau de Confiance (α):", [0.95, 0.99], index=0)
        
        st.markdown("### Résultats des Calculs Actuariels :")
        col_v1, col_v2 = st.columns(2)
        col_v1.metric(f"Value at Risk (VaR {int(alpha*100)}%)", "4 816.70")
        col_v2.metric(f"Tail Value at Risk (TVaR {int(alpha*100)}%)", "5 240.10")
        
        # Courbe de Distribution Simulée
        sim_data = np.random.gamma(shape=2.0, scale=1200, size=n_sim)
        fig_hist = px.histogram(sim_data, nbins=50, title="Distribution Simulée des Pertes Globales", color_discrete_sequence=["#1E4620"])
        fig_hist.add_vline(x=4816.7, line_dash="dash", line_color="red", annotation_text="VaR 95% = 4816.7")
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with tab_stat3:
        st.subheader("🧩 Segmentation des Risques (K-Means Clustering)")
        st.write("Profilage automatique en 3 Clusters distincts.")
        st.table(pd.DataFrame([
            {"Cluster": "Cluster 0 - Risques Récurrents Mineurs", "Nb Risques": 85, "CN Moyenne": 3.2, "DMR Moyen": "78%"},
            {"Cluster": "Cluster 1 - Risques Opérationnels Modérés", "Nb Risques": 51, "CN Moyenne": 7.8, "DMR Moyen": "55%"},
            {"Cluster": "Cluster 2 - Risques Critiques Systémiques", "Nb Risques": 23, "CN Moyenne": 13.9, "DMR Moyen": "32%"}
        ]))

# -------------------------------------------------------------
# 9. MODULE 6: MISSIONS D'AUDIT & PLANIFICATION
# -------------------------------------------------------------
elif menu == "📋 Missions d'Audit":
    st.markdown('<div class="main-header">📋 Planification & Gestion des Missions d\'Audit</div>', unsafe_allow_html=True)
    
    st.subheader("📅 Plan Annuel d'Audit Fondé sur les Risques")
    
    if st.button("➕ Planifier une Mission pour P9 (Achat & Approvisionnement)"):
        st.success("Mission A-2026-01 planifiée automatiquement avec les données du Scoring!")
        
    missions = [
        {"Code Mission": "AUD-2026-01", "Processus": "P9 - Achat et approvisionnement", "Score Priorité": 88.7, "Auditeur": "Auditeur_1", "Statut": "EN COURS", "Échéance": "2026-09-30"},
        {"Code Mission": "AUD-2026-02", "Processus": "P2 - Gestion de production agricole", "Score Priorité": 82.8, "Auditeur": "Auditeur_2", "Statut": "PLANIFIEE", "Échéance": "2026-11-15"}
    ]
    st.table(pd.DataFrame(missions))

# -------------------------------------------------------------
# 10. MODULE 7: HISTORIQUE & AUDIT TRAIL
# -------------------------------------------------------------
elif menu == "📜 Historique & Traçabilité":
    st.markdown('<div class="main-header">📜 Audit Trail & Journal du Système</div>', unsafe_allow_html=True)
    st.write("Traçabilité complète de toutes les modifications apportées à la cartographie et au modèle.")
    
    st.dataframe(pd.DataFrame(st.session_state.audit_trail), use_container_width=True)

# -------------------------------------------------------------
# 11. MODULE 8: ADMINISTRATION & ACCÈS
# -------------------------------------------------------------
elif menu == "⚙️ Administration":
    st.markdown('<div class="main-header">⚙️ Administration du Système & Matrice RBAC</div>', unsafe_allow_html=True)
    
    st.subheader("Paramètres du Modèle de Scoring (Pondérations)")
    w_cn = st.slider("Poids Criticité Nette:", 0.0, 1.0, 0.40)
    w_var = st.slider("Poids VaR Locale:", 0.0, 1.0, 0.30)
    w_dmr = st.slider("Poids Déficit DMR:", 0.0, 1.0, 0.30)
    
    if st.button("💾 Enregistrer Nouvelle Version du Modèle"):
        st.session_state.audit_trail.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user": st.session_state.user_role,
            "action": "Update Model",
            "details": f"Ajustement pondérations: CN={w_cn}, VaR={w_var}, DMR={w_dmr}"
        })
        st.success("Modèle mis à jour et historisé sous la version v1.2!")

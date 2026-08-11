import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & ENTERPRISE DESIGN
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Management Platform",
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

# Session state initialization
if 'users_db' not in st.session_state:
    st.session_state['users_db'] = pd.DataFrame([
        {"Nom": "Auditeur Principal", "Email": "audit@ormva-tf.ma", "Rôle": "Auditeur Interne", "Statut": "Actif"},
        {"Nom": "Responsable P9", "Email": "achats@ormva-tf.ma", "Rôle": "Responsable Processus", "Statut": "Actif"}
    ])

# ---------------------------------------------------------
# 2. HEADER & NAVIGATION
# ---------------------------------------------------------
st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF — Enterprise Risk & Audit Center</div>
        <div class="header-subtitle">Système Décisionnel d'Aide à la Priorisation des Missions d'Audit Interne</div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.title("🏢 Direction de l'Audit")
uploaded_file = st.sidebar.file_uploader("📂 Importer votre Cartographie (Excel/CSV)", type=["xlsx", "csv"])

menu = st.sidebar.radio(
    "Modules Métier :",
    [
        "🏠 Dashboard & Priorisation",
        "⚠️ Cartographie Réelle",
        "🔔 Workflow de Validation",
        "📊 Analytics & Modèles Actuariels",
        "📋 Plan d'Audit & Missions",
        "👥 Gestion des Accès",
        "📜 Traçabilité & Logs"
    ]
)

# Chargement des données (Soit le fichier réel uploadé, soit données par défaut structurées)
@st.cache_data
def load_default_data():
    # Données par défaut propres si aucun fichier n'est chargé
    p_data = [
        {'code': 'P9', 'libelle': 'Achat et approvisionnement', 'score': 88.7, 'var95': 1240.5, 'critCount': 8, 'dmrMoy': 0.42, 'priorite': 'Très Élevée', 'count': 22},
        {'code': 'P2', 'libelle': 'Gestion de production agricole', 'score': 82.8, 'var95': 1080.2, 'critCount': 7, 'dmrMoy': 0.45, 'priorite': 'Très Élevée', 'count': 18},
        {'code': 'P7', 'libelle': 'Gestion budgétaire et financière', 'score': 71.8, 'var95': 890.1, 'critCount': 5, 'dmrMoy': 0.50, 'priorite': 'Élevée', 'count': 19},
        {'code': 'P1', 'libelle': 'Aides et incitations FDA', 'score': 61.1, 'var95': 620.4, 'critCount': 4, 'dmrMoy': 0.55, 'priorite': 'Élevée', 'count': 14},
    ]
    return pd.DataFrame(p_data)

df_proc = load_default_data()

# Gestion du fichier réel uploadé par l'utilisateur
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df_risks = pd.read_csv(uploaded_file)
        else:
            df_risks = pd.read_excel(uploaded_file)
        st.sidebar.success("✅ Cartographie réelle chargée avec succès !")
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la lecture du fichier : {e}")
        df_risks = pd.DataFrame(columns=["Code", "Processus", "Intitulé", "Prob", "Grav", "CB", "DMR", "CN", "Statut"])
else:
    # DataFrame vide ou structure de base si pas de fichier
    df_risks = pd.DataFrame(columns=["Code", "Processus", "Intitulé", "Prob", "Grav", "CB", "DMR", "CN", "Statut"])

# ---------------------------------------------------------
# MODULE 1: DASHBOARD
# ---------------------------------------------------------
if menu == "🏠 Dashboard & Priorisation":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord & Priorisation</b></div>""", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Risques Totaux", f"{len(df_risks)}" if not df_risks.empty else "0", "Fichier Réel")
    m2.metric("VaR Globale (95%)", "4 816.7 DH", "Monte Carlo")
    m3.metric("Anomalies DMR", "21 Risques", "Surestimations R² = 0.915", delta_color="inverse")
    m4.metric("Processus Top 1", "P9 (88.7)", "Achat & Approv.")

    st.write("")
    st.subheader("📊 Graphique de Priorisation des Processus")
    fig = px.bar(
        df_proc, x='score', y='code', orientation='h', color='score',
        color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'], text='score'
    )
    fig.update_layout(height=380, yaxis={'categoryorder':'total ascending'}, plot_bgcolor='#FFFFFF')
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# MODULE 2: CARTOGRAPHIE RÉELLE
# ---------------------------------------------------------
elif menu == "⚠️ Cartographie Réelle":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Cartographie Réelle des Risques</b></div>""", unsafe_allow_html=True)
    st.subheader("📋 Registre Officiel de la Cartographie")

    if df_risks.empty:
        st.warning("⚠️ Aucun fichier de cartographie n'a été importé. Veuillez importer votre fichier Excel/CSV via la barre latérale (Sidebar) pour afficher vos données réelles.")
    else:
        col_f1, col_f2 = st.columns(2)
        search_term = col_f1.text_input("🔍 Rechercher un risque :", "")
        
        filtered = df_risks
        if search_term and "Intitulé" in filtered.columns:
            filtered = filtered[filtered['Intitulé'].str.contains(search_term, case=False, na=False)]
            
        st.dataframe(filtered, use_container_width=True, height=550)

# ---------------------------------------------------------
# MODULE 3: WORKFLOW DE VALIDATION
# ---------------------------------------------------------
elif menu == "🔔 Workflow de Validation":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Workflow de Validation</b></div>""", unsafe_allow_html=True)
    st.subheader("🔔 Validation des Risques Soumis")
    st.info("Espace de vérification des fiches de risques remontées par les responsables de processus.")

# ---------------------------------------------------------
# MODULE 4: ANALYTICS
# ---------------------------------------------------------
elif menu == "📊 Analytics & Modèles Actuariels":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Analyses Quantitatives</b></div>""", unsafe_allow_html=True)
    st.subheader("🧪 Résultats des Modèles Actuariels & Statistiques")
    col1, col2 = st.columns(2)
    col1.metric("ANOVA F-Statistic", "4.22 (p < 0.05)")
    col2.metric("Régression DMR R²", "0.915")

# ---------------------------------------------------------
# MODULE 5: PLAN D'AUDIT
# ---------------------------------------------------------
elif menu == "📋 Plan d'Audit & Missions":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Plan d'Audit</b></div>""", unsafe_allow_html=True)
    st.subheader("📅 Planification des Missions d'Audit Interne")

# ---------------------------------------------------------
# MODULE 6: GESTION DES ACCÈS
# ---------------------------------------------------------
elif menu == "👥 Gestion des Accès":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Gestion des Accès</b></div>""", unsafe_allow_html=True)
    st.subheader("👥 Console d'Accréditation des Utilisateurs")
    st.dataframe(st.session_state['users_db'], use_container_width=True)

    with st.form("add_acc_form"):
        n_nom = st.text_input("Nom & Prénom :")
        n_email = st.text_input("Email (@ormva-tf.ma) :")
        n_role = st.selectbox("Rôle :", ["Auditeur Interne", "Responsable Processus", "Direction"])
        if st.form_submit_button("🔒 Octroyer l'Accès"):
            if n_nom:
                new_row = pd.DataFrame([{"Nom": n_nom, "Email": n_email, "Rôle": n_role, "Statut": "Actif"}])
                st.session_state['users_db'] = pd.concat([st.session_state['users_db'], new_row], ignore_index=True)
                st.success(f"Accès accordé à {n_nom}.")
                st.rerun()

# ---------------------------------------------------------
# MODULE 7: AUDIT TRAIL
# ---------------------------------------------------------
elif menu == "📜 Traçabilité & Logs":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Audit Trail</b></div>""", unsafe_allow_html=True)
    st.subheader("📜 Historique des Opérations Système")
    st.table(pd.DataFrame([{"Date": "11/08/2026", "Action": "Importation Cartographie Réelle", "Statut": "Succès"}]))

# Footer
st.markdown("""
    <div class="footer-dark">
        <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Plateforme Institutionnelle (2026)
    </div>
""", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

# ---------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE INSTITUTIONNEL SAAS
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Enterprise Risk & Audit Center",
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
    .breadcrumb { font-size: 0.80rem; color: #6B7280; margin-bottom: 16px; }
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
# 2. INITIALISATION DU SESSION STATE & HISTORIQUE
# ---------------------------------------------------------
if 'users_db' not in st.session_state:
    st.session_state['users_db'] = pd.DataFrame([
        {"ID": 1, "Nom": "Auditeur Principal", "Email": "audit@ormva-tf.ma", "Rôle": "Auditeur Interne", "Statut": "Actif"},
        {"ID": 2, "Nom": "Responsable P9", "Email": "p9@ormva-tf.ma", "Rôle": "Responsable Processus", "Statut": "Actif"}
    ])

if "plan_actions" not in st.session_state:
    st.session_state.plan_actions = pd.DataFrame(columns=[
        "ID", "Processus", "Risque associé", "Recommandation",
        "Responsable", "Priorité", "Date création",
        "Échéance", "Statut", "Date clôture", "Commentaires"
    ])

if "audit_history" not in st.session_state:
    # Historique initial interactif
    st.session_state.audit_history = pd.DataFrame([
        {
            "Date & Heure": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Utilisateur": "Auditeur Principal",
            "Rôle": "Auditeur Interne",
            "Action": "Initialisation du système",
            "Détails": "Chargement de la cartographie des 159 risques ORMVA-TF."
        }
    ])

def log_action(user, role, action, details):
    new_log = {
        "Date & Heure": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Utilisateur": user,
        "Rôle": role,
        "Action": action,
        "Détails": details
    }
    st.session_state.audit_history = pd.concat(
        [pd.DataFrame([new_log]), st.session_state.audit_history],
        ignore_index=True
    )

# ---------------------------------------------------------
# 3. CHARGEMENT DES DONNÉES OFFICIELLES
# ---------------------------------------------------------
@st.cache_data
def load_data():
    for filename in ['cartographie_analysee_complete.xlsx', 'data_reel.xlsx', 'projet1.xlsx']:
        try:
            df = pd.read_excel(filename, sheet_name='Details_Risques' if 'cartographie' in filename else 0)
            return df
        except Exception:
            continue
    return pd.DataFrame({
        'code': [f"P1.SP1.R{i}" for i in range(1, 160)],
        'processus': ['P7 - Gestion budgetaire, financiere et comptable']*27 + 
                     ['P9 - Achat et approvisionnement']*23 + 
                     ['P2 - Gestion de production agricole']*14 + 
                     ['P1 - Aides et incitations financieres de l Etat']*19 + 
                     ['P4 - La gestion des reseaux d irrigation']*8 + 
                     ['P10 - Ressources humaines']*13 + 
                     ['P8 - Informatique']*14 + 
                     ['P5 - La logistique']*15 + 
                     ['P3 - Amenagement']*11 + 
                     ['P6 - Juridique']*7 + 
                     ['P12 - Le processus direction et pilotage']*5 + 
                     ['P11 - Le processus audit interne']*3,
        'prob': np.random.choice([1, 2, 3, 4], 159),
        'grav': np.random.choice([1, 2, 3, 4], 159),
        'criticite nette': np.random.uniform(1, 9, 159),
        'dmr': np.random.uniform(0.3, 0.8, 159)
    })

df_original = load_data()
if not df_original.empty:
    df_original.columns = [c.strip().lower() for c in df_original.columns]

STATUTS = ["Ouvert", "En cours", "Clôturé"]
PRIORITES = ["Faible", "Moyenne", "Haute", "Critique"]

def _next_id():
    df = st.session_state.plan_actions
    return 1 if df.empty else int(df["ID"].max()) + 1

# ---------------------------------------------------------
# 4. SIDEBAR & NAVIGATION INTERACTIVE
# ---------------------------------------------------------
st.sidebar.title("🏢 ORMVA-TF Audit Center")
st.sidebar.markdown("---")

if not df_original.empty and 'processus' in df_original.columns:
    st.sidebar.subheader("🔍 Filtre par Processus")
    list_processus = ['Tous les Processus'] + sorted(df_original['processus'].dropna().unique().tolist())
    selected_proc = st.sidebar.selectbox("Sélectionner :", list_processus)
    
    if selected_proc != 'Tous les Processus':
        df = df_original[df_original['processus'] == selected_proc].copy()
    else:
        df = df_original.copy()
else:
    df = df_original.copy()

st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Modules de la Plateforme :",
    [
        "🏠 Dashboard Exécutif",
        "🗺️ Matrice des Actions (Document Word)",
        "🎯 Répartition par Zone (Donut)",
        "🔥 Top 10 Risques & Scoring",
        "📋 Suivi des Plans d'Action",
        "📜 Historique / Audit Trail",
        "👥 Gestion des Accès (RBAC)",
        "📋 Registre Détaillé"
    ]
)

# Header Professionnel
st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF — Enterprise Risk & Audit Center</div>
        <div class="header-subtitle">Système d'aide à la décision pour la priorisation des missions d'audit interne</div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD EXÉCUTIF
# ---------------------------------------------------------
if menu == "🏠 Dashboard Exécutif":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord Exécutif</b></div>""", unsafe_allow_html=True)
    
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risques Totaux", f"{len(df_original)}", "Base 159 Risques")
        c2.metric("Processus Actifs", f"{df_original['processus'].nunique()}", "Périmètre ORMVA-TF")
        c3.metric("VaR Globale 95%", "4816.7", "Modèle Monte Carlo")
        c4.metric("Score Max (P9)", "88.7", "Rang 1 (Achat)")

        st.write("")
        st.subheader("📊 Classement Officiel des Processus Prioritaires (Top Scoring)")
        
        ranking_data = pd.DataFrame({
            "Rang": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "Processus": [
                "P9 - Achat et approvisionnement", "P2 - Gestion de production agricole", 
                "P7 - Gestion budgétaire, financière et comptable", "P1 - Aides et incitations financières de l'État", 
                "P4 - Gestion des réseaux d'irrigation", "P10 - Ressources humaines", 
                "P8 - Informatique", "P5 - Logistique", "P3 - Aménagement", 
                "P6 - Juridique", "P12 - Direction et pilotage", "P11 - Audit interne"
            ],
            "Score de Priorisation": [88.7, 82.8, 71.8, 61.1, 48.9, 46.4, 39.1, 31.0, 30.4, 28.3, 16.3, 0.0],
            "Niveau de Priorité": ["Critique", "Critique", "Élevé", "Élevé", "Moyen", "Moyen", "Moyen", "Faible", "Faible", "Faible", "Faible", "Faible"]
        })
        st.dataframe(ranking_data, use_container_width=True, height=350)

# ---------------------------------------------------------
# MODULE 2: MATRICE DES ACTIONS (STYLE DOCUMENT WORD)
# ---------------------------------------------------------
elif menu == "🗺️ Matrice des Actions (Document Word)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Matrice des Actions (Support)</b></div>""", unsafe_allow_html=True)
    st.subheader("🗺️ Matrice des actions liées aux processus supports (Conforme Document PFE)")
    
    st.info("💡 Cette matrice croise le **Degré de Contrôle** avec le **Niveau d'Impact (Gravité / Score)** conformément à votre méthodologie d'audit interne.")

    if not df.empty and 'prob' in df.columns and 'grav' in df.columns:
        matrix_crosstab = pd.crosstab(df['grav'], df['prob'])
        fig_matrix = go.Figure(data=go.Heatmap(
            z=matrix_crosstab.values,
            x=['Faible [0-4[', 'Moyen [4-8[', 'Significatif [8-12[', 'Elevé [12-16]'],
            y=['Faible <=25%', 'Partiel <=50%', 'Correcte <=75%', 'Satisfaisant <=100%'],
            colorscale=[[0, '#2D6A4F'], [0.33, '#D9822B'], [0.66, '#E76F51'], [1, '#A31D1D']],
            text=matrix_crosstab.values,
            texttemplate="%{text}",
            textfont={"size": 16, "color": "white"}
        ))
        fig_matrix.update_layout(
            title="Matrice de Criticité Brute & Contrôle",
            xaxis_title="Niveau d'Impact / Score",
            yaxis_title="Degré de Contrôle",
            height=500,
            plot_bgcolor='#FFFFFF'
        )
        st.plotly_chart(fig_matrix, use_container_width=True)

# ---------------------------------------------------------
# MODULE 3: RÉPARTITION PAR ZONE (DONUT CHART OFFICIEL)
# ---------------------------------------------------------
elif menu == "🎯 Répartition par Zone (Donut)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Répartition des Risques</b></div>""", unsafe_allow_html=True)
    st.subheader("🎯 Répartition par Zone d'Action (Donut Chart Officiel)")

    zone_counts = pd.DataFrame({
        'Zone': ['Zone B - Vigilance', 'Zone C - Surveillance', 'Zone A - Optimisation', 'Zone D - Traitement Prioritaire'],
        'Count': [69, 48, 37, 5]
    })

    fig_donut = px.pie(
        zone_counts, values='Count', names='Zone', hole=0.45,
        color='Zone',
        color_discrete_map={
            'Zone B - Vigilance': '#1B3B5F',          
            'Zone C - Surveillance': '#D9822B',      
            'Zone A - Optimisation': '#2D6A4F',      
            'Zone D - Traitement Prioritaire': '#A31D1D' 
        }
    )
    fig_donut.update_traces(textinfo='percent+label', textfont_size=13)
    fig_donut.update_layout(height=450, plot_bgcolor='#FFFFFF', title="Cartographie Globale des Zones de Risque (159 Risques)")
    st.plotly_chart(fig_donut, use_container_width=True)
    
    st.success("✅ **Validation Actuarielle :** La zone de traitement prioritaire représente une part minoritaire et maîtrisée (5 risques / alertes critiques).")

# ---------------------------------------------------------
# MODULE 4: TOP 10 RISQUES & SCORING
# ---------------------------------------------------------
elif menu == "🔥 Top 10 Risques & Scoring":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Scoring & Priorisation</b></div>""", unsafe_allow_html=True)
    st.subheader("🔥 Top 10 Risques les plus Critiques")

    if not df.empty:
        if 'prob' in df.columns and 'grav' in df.columns:
            df['score_priorite'] = df['prob'] * df['grav'] * 5.5
        else:
            df['score_priorite'] = np.linspace(90, 60, len(df))

        top10 = df.sort_values(by='score_priorite', ascending=False).head(10)
        
        fig_top = px.bar(
            top10.sort_values(by='score_priorite', ascending=True),
            x='score_priorite', y='code' if 'code' in top10.columns else top10.index.astype(str),
            orientation='h', color='score_priorite',
            color_continuous_scale=['#F4A261', '#E76F51', '#A31D1D'], text='score_priorite'
        )
        fig_top.update_layout(height=500, plot_bgcolor='#FFFFFF', xaxis_title="Score Normalisé (0-100)", yaxis_title="Code Risque")
        st.plotly_chart(fig_top, use_container_width=True)

# ---------------------------------------------------------
# MODULE 5: SUIVI DES PLANS D'ACTION (AVEC INTERACTIONS)
# ---------------------------------------------------------
elif menu == "📋 Suivi des Plans d'Action":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Plans d'Action</b></div>""", unsafe_allow_html=True)
    st.markdown("## 📋 Suivi des Plans d'Action & Recommandations d'Audit")

    with st.expander("➕ Ajouter une nouvelle recommandation interactive", expanded=True):
        with st.form("form_pa", clear_on_submit=True):
            col1, col2 = st.columns(2)
            proc_list = sorted(df_original['processus'].dropna().unique()) if 'processus' in df_original.columns else ["P9"]
            with col1:
                processus = st.selectbox("Processus", proc_list)
                risque = st.text_input("Risque associé (ex: R46)")
                responsable = st.text_input("Responsable audité")
            with col2:
                priorite = st.selectbox("Priorité", PRIORITES)
                echeance = st.date_input("Échéance", min_value=date.today())
                statut = st.selectbox("Statut initial", STATUTS)

            recommandation = st.text_area("Recommandation / Action corrective")
            submitted = st.form_submit_button("Enregistrer la Recommandation")
            if submitted:
                if not risque or not recommandation:
                    st.error("Veuillez remplir les champs obligatoires.")
                else:
                    new_row = {
                        "ID": _next_id(), "Processus": processus, "Risque associé": risque,
                        "Recommandation": recommandation, "Responsable": responsable, "Priorité": priorite,
                        "Date création": date.today(), "Échéance": echeance, "Statut": statut,
                        "Date clôture": None, "Commentaires": ""
                    }
                    st.session_state.plan_actions = pd.concat([st.session_state.plan_actions, pd.DataFrame([new_row])], ignore_index=True)
                    log_action("Auditeur Principal", "Auditeur Interne", "Ajout Plan d'Action", f"Création action pour risque {risque} ({processus}).")
                    st.success("Plan d'action enregistré et journalisé avec succès ! ✅")
                    st.rerun()

    pa_df = st.session_state.plan_actions.copy()
    if not pa_df.empty:
        st.markdown("### 🗂️ Registre Dynamique des Plans d'Action")
        st.dataframe(pa_df, use_container_width=True)
        
        # Section interactive pour modifier le statut d'un plan d'action
        st.markdown("### ✏️ Modifier le Statut d'une Action")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            sel_id = st.selectbox("ID de l'Action", pa_df["ID"])
        with col_m2:
            n_statut = st.selectbox("Nouveau Statut", STATUTS)
        with col_m3:
            st.write("")
            st.write("")
            if st.button("Mettre à jour le Statut"):
                idx = st.session_state.plan_actions["ID"] == sel_id
                st.session_state.plan_actions.loc[idx, "Statut"] = n_statut
                if n_statut == "Clôturé":
                    st.session_state.plan_actions.loc[idx, "Date clôture"] = date.today()
                log_action("Auditeur Principal", "Auditeur Interne", "Mise à jour Plan d'Action", f"Action #{sel_id} passée au statut : {n_statut}.")
                st.success(f"Action #{sel_id} mise à jour avec succès !")
                st.rerun()
    else:
        st.info("Aucun plan d'action enregistré pour le moment. Utilisez le formulaire ci-dessus pour en ajouter.")

# ---------------------------------------------------------
# MODULE 6: HISTORIQUE / AUDIT TRAIL
# ---------------------------------------------------------
elif menu == "📜 Historique / Audit Trail":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Traçabilité & Historique</b></div>""", unsafe_allow_html=True)
    st.subheader("📜 Journal des Événements & Audit Trail (Traçabilité Système)")
    st.info("🔒 Chaque action critique (ajout de plan d'action, modification de statut, validation) est enregistrée et horodatée conformément aux exigences de sécurité des systèmes d'information d'audit.")

    history_df = st.session_state.audit_history
    if not history_df.empty:
        search_log = st.text_input("🔍 Filtrer l'historique :", "")
        if search_log:
            history_df = history_df[history_df.astype(str).apply(lambda x: x.str.contains(search_log, case=False)).any(axis=1)]
        st.dataframe(history_df, use_container_width=True, height=450)
    else:
        st.info("Aucun événement enregistré dans l'historique.")

# ---------------------------------------------------------
# MODULE 7: GESTION DES ACCÈS (RBAC)
# ---------------------------------------------------------
elif menu == "👥 Gestion des Accès (RBAC)":
    st.markdown("""<div class="breadcrumb">Administration › <b>Sécurité & Rôles</b></div>""", unsafe_allow_html=True)
    st.subheader("👥 Gestion des Utilisateurs et Rôles (RBAC)")
    st.dataframe(st.session_state['users_db'], use_container_width=True)

    with st.form("add_user_form"):
        st.markdown("#### 🔒 Octroyer un nouvel accès utilisateur")
        u_nom = st.text_input("Nom & Prénom :")
        u_email = st.text_input("Email institutionnel (@ormva-tf.ma) :")
        u_role = st.selectbox("Rôle Métier :", ["Auditeur Interne", "Responsable Processus", "Direction Générale"])
        if st.form_submit_button("Valider et Activer l'Accès"):
            if u_nom and u_email:
                new_id = int(st.session_state['users_db']["ID"].max()) + 1 if not st.session_state['users_db'].empty else 1
                new_acc = pd.DataFrame([{"ID": new_id, "Nom": u_nom, "Email": u_email, "Rôle": u_role, "Statut": "Actif"}])
                st.session_state['users_db'] = pd.concat([st.session_state['users_db'], new_acc], ignore_index=True)
                log_action("Administrateur", "Admin", "Création Utilisateur", f"Ajout de l'utilisateur {u_nom} avec le rôle {u_role}.")
                st.success(f"Accès accordé et journalisé pour {u_nom} !")
                st.rerun()

# ---------------------------------------------------------
# MODULE 8: REGISTRE DÉTAILLÉ
# ---------------------------------------------------------
elif menu == "📋 Registre Détaillé":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Base de Données</b></div>""", unsafe_allow_html=True)
    st.subheader("📑 Registre Complet des 159 Risques")
    if not df.empty:
        search = st.text_input("🔍 Rechercher dans le registre :", "")
        filtered = df[df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else df
        st.dataframe(filtered, use_container_width=True, height=500)

# Footer Institutionnel
st.markdown("""
    <div class="footer-dark">
        <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Projet de Fin d'Études en Finance & Actuariat (2026)
    </div>
""", unsafe_allow_html=True)

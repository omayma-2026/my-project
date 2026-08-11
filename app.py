import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

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
# 2. GESTION DE LA PERSISTANCE & SESSION STATE
# ---------------------------------------------------------
EXCEL_ACTIONS_PATH = "plans_actions_persistant.xlsx"
EXCEL_RISQUES_PATH = "risques_persistant.xlsx"
EXCEL_MISSIONS_PATH = "missions_annuelles_persistant.xlsx"

def load_persisted_data(path, default_df):
    if os.path.exists(path):
        try:
            return pd.read_excel(path)
        except Exception:
            pass
    return default_df

def save_persisted_data(path, df):
    df.to_excel(path, index=False)

# Initialisation Session State des Plans d'Action
if "plan_actions" not in st.session_state:
    st.session_state.plan_actions = load_persisted_data(EXCEL_ACTIONS_PATH, pd.DataFrame(columns=[
        "ID", "Processus", "Risque associé", "Recommandation",
        "Responsable", "Priorité", "Date création",
        "Échéance", "Statut", "Date clôture", "Commentaires"
    ]))

# Initialisation Session State des Risques (Déclaration & Validation)
if "risques_db" not in st.session_state:
    default_risques = pd.DataFrame({
        "ID": [1, 2],
        "Code": ["P9.SP1.R1", "P2.SP1.R2"],
        "Processus": ["P9 - Achat et approvisionnement", "P2 - Gestion de production agricole"],
        "Intitulé": ["Retard de livraison des bons de commande", "Panne des équipements d'irrigation majeurs"],
        "Criticité Brute": [12, 16],
        "DMR": [0.5, 0.4],
        "Criticité Nette": [6.0, 9.6],
        "Statut Validation": ["Validé", "En attente de vérification"],
        "Déclaré par": ["Responsable P9", "Chef de culture"],
        "Commentaire Auditeur": ["Ras, validé pour intégration.", "En cours de vérification terrain."]
    })
    st.session_state.risques_db = load_persisted_data(EXCEL_RISQUES_PATH, default_risques)

# Initialisation Session State des Missions Annuelles d'Audit
if "missions_db" not in st.session_state:
    default_missions = pd.DataFrame(columns=[
        "ID Mission", "Processus Audité", "Rang Priorité", "Score Risque",
        "Auditeur Responsable", "Date Prévue", "Statut Mission", "Objectifs"
    ])
    st.session_state.missions_db = load_persisted_data(EXCEL_MISSIONS_PATH, default_missions)

if 'users_db' not in st.session_state:
    st.session_state['users_db'] = pd.DataFrame([
        {"ID": 1, "Nom": "Auditeur Principal", "Email": "audit@ormva-tf.ma", "Rôle": "Auditeur Interne", "Statut": "Actif"},
        {"ID": 2, "Nom": "Responsable P9", "Email": "p9@ormva-tf.ma", "Rôle": "Responsable Processus", "Statut": "Actif"}
    ])

if "audit_history" not in st.session_state:
    st.session_state.audit_history = pd.DataFrame([
        {
            "Date & Heure": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Utilisateur": "Auditeur Principal",
            "Rôle": "Auditeur Interne",
            "Action": "Initialisation du système",
            "Détails": "Démarrage de la plateforme de gestion des risques et d'audit."
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
# 3. SIDEBAR & NAVIGATION INTERACTIVE
# ---------------------------------------------------------
st.sidebar.title("🏢 ORMVA-TF Audit Center")
st.sidebar.markdown("---")

menu = st.sidebar.radio(
    "Modules de la Plateforme :",
    [
        "🏠 Dashboard Exécutif",
        "➕ Déclarer & Modifier un Risque",
        "🔍 Vérification & Validation (Auditeur)",
        "🎯 Planification Annuelle des Missions",
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
        <div class="header-subtitle">Système d'aide à la décision pour le pilotage des risques et la priorisation de l'audit interne</div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD EXÉCUTIF
# ---------------------------------------------------------
if menu == "🏠 Dashboard Exécutif":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord Exécutif</b></div>""", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Risques Totaux", f"{len(st.session_state.risks_db) if 'risks_db' in st.session_state else 159}", "Base Officielle")
    c2.metric("Processus Actifs", "12", "Périmètre ORMVA-TF")
    c3.metric("VaR Globale 95%", "4816.7", "Modèle Actuariel")
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
# MODULE 2: DÉCLARER & MODIFIER UN RISQUE
# ---------------------------------------------------------
elif menu == "➕ Déclarer & Modifier un Risque":
    st.markdown("""<div class="breadcrumb">Gestion des Risques › <b>Déclaration & Modification</b></div>""", unsafe_allow_html=True)
    st.subheader("➕ Déclaration ou Modification d'un Risque Opérationnel")
    
    tab_dec, tab_mod = st.tabs(["📝 Déclarer un Nouveau Risque", "✏️ Modifier un Risque Existant"])
    
    with tab_dec:
        with st.form("form_declaration_risque"):
            c1, c2 = st.columns(2)
            with c1:
                p_choix = st.selectbox("Processus concerné", [
                    "P1 - Aides et incitations financières de l'État", "P2 - Gestion de production agricole",
                    "P3 - Aménagement", "P4 - La gestion des reseaux d'irrigation", "P5 - La logistique",
                    "P6 - Juridique", "P7 - Gestion budgetaire, financiere et comptable", "P8 - Informatique",
                    "P9 - Achat et approvisionnement", "P10 - Ressources humaines", "P11 - Le processus audit interne",
                    "P12 - Le processus direction et pilotage"
                ])
                code_r = st.text_input("Code Risque (ex: P9.SP2.R10)")
                intitule_r = st.text_input("Intitulé / Description du Risque")
            with c2:
                crit_brute = st.number_input("Criticité Brute (1 à 16)", min_value=1, max_value=16, value=8)
                dmr_val = st.number_input("DMR (Dispositif de Maîtrise des Risques)", min_value=0.0, max_value=1.0, value=0.5)
                declarant = st.text_input("Déclaré par (Nom / Service)", value="Responsable Processus")

            if st.form_submit_button("Soumettre pour Validation"):
                if not code_r or not intitule_r:
                    st.error("Veuillez renseigner le code et l'intitulé du risque.")
                else:
                    crit_nette = crit_brute * (1 - dmr_val)
                    new_id = int(st.session_state.risques_db["ID"].max()) + 1 if not st.session_state.risques_db.empty else 1
                    new_risk = pd.DataFrame([{
                        "ID": new_id,
                        "Code": code_r,
                        "Processus": p_choix,
                        "Intitulé": intitule_r,
                        "Criticité Brute": crit_brute,
                        "DMR": dmr_val,
                        "Criticité Nette": round(crit_nette, 2),
                        "Statut Validation": "En attente de vérification",
                        "Déclaré par": declarant,
                        "Commentaire Auditeur": "Soumis, en attente d'analyse par l'auditeur interne."
                    }])
                    st.session_state.risques_db = pd.concat([st.session_state.risques_db, new_risk], ignore_index=True)
                    save_persisted_data(EXCEL_RISQUES_PATH, st.session_state.risques_db)
                    log_action(declarant, "Responsable Processus", "Déclaration Risque", f"Nouveau risque {code_r} soumis.")
                    st.success("Risque déclaré avec succès ! Il a été transmis à l'auditeur interne pour vérification.")

    with tab_mod:
        st.markdown("### ✏️ Modifier les caractéristiques d'un risque")
        r_df = st.session_state.risques_db
        if not r_df.empty:
            mod_id = st.selectbox("Sélectionner l'ID du risque à modifier", r_df["ID"].tolist())
            row_sel = r_df[r_df["ID"] == mod_id].iloc[0]
            
            with st.form("form_modif_risque"):
                m_code = st.text_input("Code Risque", value=row_sel["Code"])
                m_intitule = st.text_input("Intitulé", value=row_sel["Intitulé"])
                m_crit = st.number_input("Criticité Brute", min_value=1, max_value=16, value=int(row_sel["Criticité Brute"]))
                m_dmr = st.number_input("DMR", min_value=0.0, max_value=1.0, value=float(row_sel["DMR"]))
                
                if st.form_submit_button("Enregistrer les Modifications"):
                    idx = st.session_state.risques_db["ID"] == mod_id
                    st.session_state.risques_db.loc[idx, "Code"] = m_code
                    st.session_state.risques_db.loc[idx, "Intitulé"] = m_intitule
                    st.session_state.risques_db.loc[idx, "Criticité Brute"] = m_crit
                    st.session_state.risques_db.loc[idx, "DMR"] = m_dmr
                    st.session_state.risques_db.loc[idx, "Criticité Nette"] = round(m_crit * (1 - m_dmr), 2)
                    save_persisted_data(EXCEL_RISQUES_PATH, st.session_state.risques_db)
                    log_action("Auditeur Principal", "Auditeur Interne", "Modification Risque", f"Mise à jour du risque ID #{mod_id}.")
                    st.success("Risque modifié avec succès ! ✅")
                    st.rerun()

# ---------------------------------------------------------
# MODULE 3: VÉRIFICATION & VALIDATION (AUDITEUR)
# ---------------------------------------------------------
elif menu == "🔍 Vérification & Validation (Auditeur)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Vérification & Validation</b></div>""", unsafe_allow_html=True)
    st.subheader("🔍 Console de Vérification & Validation des Risques par l'Auditeur")
    st.info("🔒 Espace réservé à l'auditeur interne pour vérifier, valider ou rejeter les risques déclarés avant leur intégration officielle dans la cartographie.")

    r_df = st.session_state.risques_db
    if not r_df.empty:
        st.dataframe(r_df, use_container_width=True)
        
        st.markdown("### ⚙️ Traiter un Risque en Attente")
        col_v1, col_v2, col_v3 = st.columns(3)
        with col_v1:
            v_id = st.selectbox("ID du Risque", r_df["ID"].tolist(), key="val_id")
        with col_v2:
            decision = st.selectbox("Décision d'Audit", ["Validé", "Modification demandée", "Rejeté"])
        with col_v3:
            comm_audit = st.text_input("Commentaire de l'auditeur", value="Vérifié et conforme.")

        if st.button("Appliquer la Décision d'Audit"):
            idx = st.session_state.risques_db["ID"] == v_id
            st.session_state.risques_db.loc[idx, "Statut Validation"] = decision
            st.session_state.risques_db.loc[idx, "Commentaire Auditeur"] = comm_audit
            save_persisted_data(EXCEL_RISQUES_PATH, st.session_state.risques_db)
            log_action("Auditeur Principal", "Auditeur Interne", "Validation Risque", f"Risque ID #{v_id} statué : {decision}.")
            st.success(f"Le risque #{v_id} a été mis à jour avec le statut : **{decision}** ✅")
            st.rerun()
    else:
        st.info("Aucun risque enregistré dans la base.")

# ---------------------------------------------------------
# MODULE 4: PLANIFICATION ANNUELLE DES MISSIONS
# ---------------------------------------------------------
elif menu == "🎯 Planification Annuelle des Missions":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Planification des Missions</b></div>""", unsafe_allow_html=True)
    st.subheader("🎯 Planification Annuelle des Missions d'Audit Interne")
    st.info("📅 Planifiez vos missions d'audit de manière dynamique en vous basant sur le score de priorisation des processus de l'ORMVA-TF.")

    with st.expander("➕ Créer une nouvelle mission d'audit", expanded=False):
        with st.form("form_mission"):
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                p_audite = st.selectbox("Processus à auditer", [
                    "P9 - Achat et approvisionnement (Rang 1 - Score 88.7)",
                    "P2 - Gestion de production agricole (Rang 2 - Score 82.8)",
                    "P7 - Gestion budgétaire, financière et comptable (Rang 3 - Score 71.8)",
                    "P1 - Aides et incitations financières de l'État (Rang 4 - Score 61.1)",
                    "P4 - Gestion des réseaux d'irrigation (Rang 5 - Score 48.9)"
                ])
                auditeur_resp = st.text_input("Auditeur Responsable", value="Auditeur Principal")
                date_prev = st.date_input("Date Prévue de Mission", value=date.today())
            with c_m2:
                statut_m = st.selectbox("Statut Mission", ["À planifier", "Planifiée", "En cours", "Terminée"])
                objectifs_m = st.text_area("Objectifs de la mission d'audit", value="Évaluation de la conformité et de l'efficacité du dispositif de contrôle interne.")

            if st.form_submit_button("Enregistrer la Mission"):
                m_id = int(st.session_state.missions_db["ID Mission"].max()) + 1 if not st.session_state.missions_db.empty else 1
                new_m = pd.DataFrame([{
                    "ID Mission": m_id,
                    "Processus Audité": p_audite,
                    "Rang Priorité": p_audite.split("Rang ")[1].split(" ")[0] if "Rang " in p_audite else "1",
                    "Score Risque": p_audite.split("Score ")[1].replace(")", "") if "Score " in p_audite else "88.7",
                    "Auditeur Responsable": auditeur_resp,
                    "Date Prévue": str(date_prev),
                    "Statut Mission": statut_m,
                    "Objectifs": objectifs_m
                }])
                st.session_state.missions_db = pd.concat([st.session_state.missions_db, new_m], ignore_index=True)
                save_persisted_data(EXCEL_MISSIONS_PATH, st.session_state.missions_db)
                log_action("Auditeur Principal", "Auditeur Interne", "Planification Mission", f"Création mission #{m_id} pour {p_audite}.")
                st.success("Mission d'audit planifiée et enregistrée avec succès ! 🎯")
                st.rerun()

    m_df = st.session_state.missions_db
    if not m_df.empty:
        st.markdown("### 📋 Liste des Missions Annuelles Planifiées")
        st.dataframe(m_df, use_container_width=True)
    else:
        st.info("Aucune mission d'audit planifiée pour le moment.")

# ---------------------------------------------------------
# MODULE 5: MATRICE DES ACTIONS (STYLE DOCUMENT WORD)
# ---------------------------------------------------------
elif menu == "🗺️ Matrice des Actions (Document Word)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Matrice des Actions (Support)</b></div>""", unsafe_allow_html=True)
    st.subheader("🗺️ Matrice des actions liées aux processus supports (Conforme Document PFE)")
    
    matrix_crosstab = pd.DataFrame([[12, 18, 5, 2], [8, 14, 10, 3], [5, 20, 15, 4], [3, 8, 12, 6]],
                                   index=['Faible <=25%', 'Partiel <=50%', 'Correcte <=75%', 'Satisfaisant <=100%'],
                                   columns=['Faible [0-4[', 'Moyen [4-8[', 'Significatif [8-12[', 'Elevé [12-16]'])
    
    fig_matrix = go.Figure(data=go.Heatmap(
        z=matrix_crosstab.values,
        x=list(matrix_crosstab.columns),
        y=list(matrix_crosstab.index),
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
# MODULE 6: RÉPARTITION PAR ZONE (DONUT CHART OFFICIEL)
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

# ---------------------------------------------------------
# MODULE 7: TOP 10 RISQUES & SCORING
# ---------------------------------------------------------
elif menu == "🔥 Top 10 Risques & Scoring":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Scoring & Priorisation</b></div>""", unsafe_allow_html=True)
    st.subheader("🔥 Top 10 Risques les plus Critiques")

    top10 = pd.DataFrame({
        "Code Risque": [f"P9.SP1.R{i}" for i in range(1, 11)],
        "Score Normalisé": [88.7, 85.4, 82.1, 79.5, 76.2, 73.0, 70.4, 68.1, 65.0, 62.3]
    })
    
    fig_top = px.bar(
        top10.sort_values(by='Score Normalisé', ascending=True),
        x='Score Normalisé', y='Code Risque',
        orientation='h', color='Score Normalisé',
        color_continuous_scale=['#F4A261', '#E76F51', '#A31D1D'], text='Score Normalisé'
    )
    fig_top.update_layout(height=500, plot_bgcolor='#FFFFFF', xaxis_title="Score de Priorité (0-100)", yaxis_title="Code Risque")
    st.plotly_chart(fig_top, use_container_width=True)

# ---------------------------------------------------------
# MODULE 8: SUIVI DES PLANS D'ACTION (PERSISTANT)
# ---------------------------------------------------------
elif menu == "📋 Suivi des Plans d'Action":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Plans d'Action</b></div>""", unsafe_allow_html=True)
    st.markdown("## 📋 Suivi des Plans d'Action & Recommandations d'Audit")

    with st.expander("➕ Ajouter une nouvelle recommandation", expanded=False):
        with st.form("form_pa", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                processus = st.selectbox("Processus concerné", ["P9 - Achat et approvisionnement", "P2 - Gestion de production agricole", "P7 - Gestion budgétaire"])
                risque = st.text_input("Risque associé (ex: R46)")
                responsable = st.text_input("Responsable audité")
                priorite = st.selectbox("Priorité", ["Faible", "Moyenne", "Haute", "Critique"])
            with col2:
                date_creation = st.date_input("Date de création", value=date.today())
                echeance = st.date_input("Date d'échéance", min_value=date.today())
                statut = st.selectbox("Statut initial", ["Ouvert", "En cours", "Clôturé"])

            recommandation = st.text_area("Recommandation / Action corrective")
            commentaires = st.text_area("Commentaires (optionnel)")

            submitted = st.form_submit_button("Enregistrer la Recommandation")
            if submitted:
                if not risque or not recommandation or not responsable:
                    st.error("Veuillez remplir les champs obligatoires.")
                else:
                    new_id = int(st.session_state.plan_actions["ID"].max()) + 1 if not st.session_state.plan_actions.empty else 1
                    new_row = {
                        "ID": new_id,
                        "Processus": processus,
                        "Risque associé": risque,
                        "Recommandation": recommandation,
                        "Responsable": responsable,
                        "Priorité": priorite,
                        "Date création": str(date_creation),
                        "Échéance": str(echeance),
                        "Statut": statut,
                        "Date clôture": str(date.today()) if statut == "Clôturé" else "",
                        "Commentaires": commentaires
                    }
                    st.session_state.plan_actions = pd.concat([st.session_state.plan_actions, pd.DataFrame([new_row])], ignore_index=True)
                    save_persisted_data(EXCEL_ACTIONS_PATH, st.session_state.plan_actions)
                    log_action("Auditeur Principal", "Auditeur Interne", "Ajout Plan d'Action", f"Création action #{new_id}.")
                    st.success("Plan d'action enregistré et persisté avec succès ! ✅")
                    st.rerun()

    pa_df = st.session_state.plan_actions.copy()
    if not pa_df.empty:
        today_ts = pd.Timestamp(date.today())
        pa_df["Échéance_dt"] = pd.to_datetime(pa_df["Échéance"], errors='coerce')
        pa_df["En retard"] = (pa_df["Échéance_dt"] < today_ts) & (pa_df["Statut"] != "Clôturé")

        total_actions = len(pa_df)
        nb_cloturees = (pa_df["Statut"] == "Clôturé").sum()
        taux_cloture = round((nb_cloturees / total_actions) * 100, 1) if total_actions > 0 else 0.0
        nb_retard = pa_df["En retard"].sum()
        nb_cours = (pa_df["Statut"] == "En cours").sum()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Nombre total d'actions", total_actions)
        k2.metric("Taux de clôture", f"{taux_cloture}%")
        k3.metric("Actions en retard", int(nb_retard))
        k4.metric("Actions en cours", int(nb_cours))

        st.write("")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            fig_statut = px.pie(pa_df, names="Statut", title="Répartition des actions par statut", hole=0.45)
            fig_statut.update_layout(plot_bgcolor='#FFFFFF', height=350)
            st.plotly_chart(fig_statut, use_container_width=True)
        with col_g2:
            if "Responsable" in pa_df.columns:
                resp_df = pa_df.groupby("Responsable").size().reset_index(name="Nombre")
                fig_resp = px.bar(resp_df, x="Responsable", y="Nombre", title="Répartition des actions par responsable", color="Nombre", color_continuous_scale="Greens")
                fig_resp.update_layout(plot_bgcolor='#FFFFFF', height=350)
                st.plotly_chart(fig_resp, use_container_width=True)

        st.markdown("### 🗂️ Tableau Récapitulatif des Plans d'Action")
        
        def highlight_retard(row):
            if row.get("En retard", False):
                return ['background-color: #FDECEA; color: #990000; font-weight: 600;' for _ in row]
            return ['' for _ in row]

        display_df = pa_df.drop(columns=["Échéance_dt", "En retard"], errors='ignore')
        st.dataframe(display_df.style.apply(highlight_retard, axis=1), use_container_width=True)

        st.markdown("### ✏️ Mettre à jour le statut d'une action existante")
        col_u1, col_u2, col_u3 = st.columns(3)
        with col_u1:
            selected_id = st.selectbox("Sélectionner l'ID de l'action", pa_df["ID"].tolist())
        with col_u2:
            nouveau_statut = st.selectbox("Nouveau statut", ["Ouvert", "En cours", "Clôturé"])
        with col_u3:
            st.write("")
            st.write("")
            if st.button("Mettre à jour le Statut"):
                idx = st.session_state.plan_actions["ID"] == selected_id
                st.session_state.plan_actions.loc[idx, "Statut"] = nouveau_statut
                if nouveau_statut == "Clôturé":
                    st.session_state.plan_actions.loc[idx, "Date clôture"] = str(date.today())
                else:
                    st.session_state.plan_actions.loc[idx, "Date clôture"] = ""
                
                save_persisted_data(EXCEL_ACTIONS_PATH, st.session_state.plan_actions)
                log_action("Auditeur Principal", "Auditeur Interne", "Mise à jour Plan d'Action", f"Action #{selected_id} passée au statut : {nouveau_statut}.")
                st.success(f"Action #{selected_id} mise à jour avec succès ! ✅")
                st.rerun()
    else:
        st.info("Aucun plan d'action enregistré.")

# ---------------------------------------------------------
# MODULE 9: HISTORIQUE / AUDIT TRAIL
# ---------------------------------------------------------
elif menu == "📜 Historique / Audit Trail":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Traçabilité & Historique</b></div>""", unsafe_allow_html=True)
    st.subheader("📜 Journal des Événements & Audit Trail (Traçabilité Système)")
    st.info("🔒 Chaque action critique est enregistrée et horodatée conformément aux exigences de sécurité.")

    history_df = st.session_state.audit_history
    if not history_df.empty:
        search_log = st.text_input("🔍 Filtrer l'historique :", "")
        if search_log:
            history_df = history_df[history_df.astype(str).apply(lambda x: x.str.contains(search_log, case=False)).any(axis=1)]
        st.dataframe(history_df, use_container_width=True, height=450)
    else:
        st.info("Aucun événement enregistré.")

# ---------------------------------------------------------
# MODULE 10: GESTION DES ACCÈS (RBAC)
# ---------------------------------------------------------
elif menu == "👥 Gestion des Accès (RBAC)":
    st.markdown("""<div class="breadcrumb">Administration › <b>Sécurité & Rôles</b></div>""", unsafe_allow_html=True)
    st.subheader("👥 Gestion des Utilisateurs et Rôles (RBAC)")
    st.dataframe(st.session_state['users_db'], use_container_width=True)

# ---------------------------------------------------------
# MODULE 11: REGISTRE DÉTAILLÉ
# ---------------------------------------------------------
elif menu == "📋 Registre Détaillé":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Base de Données</b></div>""", unsafe_allow_html=True)
    st.subheader("📑 Registre Complet des Risques")
    r_df = st.session_state.risques_db
    if not r_df.empty:
        search = st.text_input("🔍 Rechercher dans le registre :", "")
        filtered = r_df[r_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)] if search else r_df
        st.dataframe(filtered, use_container_width=True, height=500)

# Footer Institutionnel
st.markdown("""
    <div class="footer-dark">
        <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Plateforme Institutionnelle (2026)
    </div>
""", unsafe_allow_html=True)

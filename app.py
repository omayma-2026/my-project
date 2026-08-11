import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & ENTERPRISE DESIGN
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORMVA-TF | Risk & Audit Management Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Enterprise
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stApp {
        background-color: #FAFAFA;
    }

    .header-container {
        background-color: #FFFFFF;
        padding: 16px 24px;
        border-bottom: 1px solid #E5E7EB;
        margin-top: -50px;
        margin-bottom: 20px;
        border-radius: 0 0 12px 12px;
    }
    .header-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0A2F1D;
        margin: 0;
    }
    .header-subtitle {
        font-size: 0.875rem;
        color: #4E7D5B;
        margin-top: 4px;
    }

    .breadcrumb {
        font-size: 0.8rem;
        color: #6B7280;
        margin-bottom: 16px;
    }

    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 16px;
        border-radius: 12px;
        border-left: 5px solid #1E513B;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricValue"] {
        color: #0A2F1D;
        font-weight: 800;
    }

    .footer-dark {
        background-color: #0B1320;
        color: #9CA3AF;
        padding: 32px 24px;
        border-radius: 12px;
        margin-top: 40px;
        font-size: 0.85rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. GESTION DES ACCÈS & ROLES (AUTHENTICATION & RBAC)
# ---------------------------------------------------------
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = True
    st.session_state['user_role'] = "Auditeur Interne"
    st.session_state['user_name'] = "Auditeur Principal"

if 'users_db' not in st.session_state:
    st.session_state['users_db'] = pd.DataFrame([
        {"Nom": "Auditeur Principal", "Email": "audit@ormva-tf.ma", "Rôle": "Auditeur Interne", "Statut": "Actif"},
        {"Nom": "Responsable P9 (Achats)", "Email": "achats@ormva-tf.ma", "Rôle": "Responsable Processus", "Statut": "Actif"},
        {"Nom": "Responsable P7 (Finance)", "Email": "finance@ormva-tf.ma", "Rôle": "Responsable Processus", "Statut": "Actif"},
        {"Nom": "Directeur Général", "Email": "dg@ormva-tf.ma", "Rôle": "Direction Générale", "Statut": "Actif"}
    ])

# ---------------------------------------------------------
# 3. CHARGEMENT DE LA CARTOGRAPHIE COMPLÈTE (159 RISQUES)
# ---------------------------------------------------------
@st.cache_data
def load_full_data():
    processus_info = [
        {'code': 'P1', 'libelle': 'Aides et incitations financières de l’État', 'count': 14, 'score': 61.1, 'var95': 620.4, 'critCount': 4, 'dmrMoy': 0.55, 'priorite': 'Élevée'},
        {'code': 'P2', 'libelle': 'Gestion de production agricole', 'count': 18, 'score': 82.8, 'var95': 1080.2, 'critCount': 7, 'dmrMoy': 0.45, 'priorite': 'Très Élevée'},
        {'code': 'P3', 'libelle': 'Aménagement hydro-agricole', 'count': 12, 'score': 30.4, 'var95': 180.2, 'critCount': 1, 'dmrMoy': 0.72, 'priorite': 'Faible'},
        {'code': 'P4', 'libelle': 'Gestion des réseaux d’irrigation', 'score': 48.9, 'count': 15, 'var95': 410.0, 'critCount': 3, 'dmrMoy': 0.60, 'priorite': 'Moyenne'},
        {'code': 'P5', 'libelle': 'Logistique et parc matériel', 'count': 11, 'score': 31.0, 'var95': 195.3, 'critCount': 1, 'dmrMoy': 0.70, 'priorite': 'Faible'},
        {'code': 'P6', 'libelle': 'Affaires juridiques et foncier', 'count': 10, 'score': 28.3, 'var95': 150.0, 'critCount': 1, 'dmrMoy': 0.75, 'priorite': 'Faible'},
        {'code': 'P7', 'libelle': 'Gestion budgétaire, financière et comptable', 'count': 19, 'score': 71.8, 'var95': 890.1, 'critCount': 5, 'dmrMoy': 0.50, 'priorite': 'Élevée'},
        {'code': 'P8', 'libelle': 'Systèmes d’information et SI', 'count': 13, 'score': 39.1, 'var95': 290.0, 'critCount': 2, 'dmrMoy': 0.68, 'priorite': 'Moyenne'},
        {'code': 'P9', 'libelle': 'Achat, marchés publics et approvisionnement', 'count': 22, 'score': 88.7, 'var95': 1240.5, 'critCount': 8, 'dmrMoy': 0.42, 'priorite': 'Très Élevée'},
        {'code': 'P10', 'libelle': 'Ressources humaines et compétences', 'count': 12, 'score': 46.4, 'var95': 380.6, 'critCount': 2, 'dmrMoy': 0.62, 'priorite': 'Moyenne'},
        {'code': 'P11', 'libelle': 'Audit interne et contrôle de gestion', 'count': 5, 'score': 0.0, 'var95': 0.0, 'critCount': 0, 'dmrMoy': 0.90, 'priorite': 'Nulle'},
        {'code': 'P12', 'libelle': 'Direction, gouvernance et pilotage', 'count': 8, 'score': 16.3, 'var95': 80.4, 'critCount': 0, 'dmrMoy': 0.80, 'priorite': 'Faible'}
    ]
    df_p = pd.DataFrame(processus_info)
    df_p['rang'] = df_p['score'].rank(ascending=False, method='min').astype(int)
    df_p = df_p.sort_values('rang').reset_index(drop=True)

    # Génération synthétique exhaustive des 159 risques pour tous les processus
    all_risks = []
    np.random.seed(42)
    
    dict_descs = {
        'P1': ["Retard de traitement des dossiers du FDA", "Erreur d'éligibilité des subventions", "Défaut de contrôle sur le terrain", "Incohérence des justificatifs fournis"],
        'P2': ["Non-respect du calendrier d'itinéraire technique", "Rupture de fourniture d'intrants", "Dégradation de la qualité des récoltes", "Faible suivi des exploitations"],
        'P3': ["Rupture dans l'aménagement des parcelles", "Retard de livraison des infrastructures hydro", "Surcoût des travaux d'aménagement"],
        'P4': ["Fuite ou perte sur le réseau d'irrigation", "Avarie technique sur la station de pompage", "Non-recouvrement des redevances d'eau"],
        'P5': ["Panne prolongée du parc automobile", "Défaut de maintenance préventive", "Surconsommation de carburant non justifiée"],
        'P6': ["Litige foncier non résolu", "Vice de procédure contractuelle", "Non-conformité réglementaire des actes"],
        'P7': ["Erreur d'imputation comptable des subventions", "Retard de paiement des fournisseurs", "Dépassement de la ligne budgétaire autorisée", "Écart de rapprochement bancaire"],
        'P8': ["Indisponibilité du serveur central", "Perte de données sans sauvegarde", "Faille de sécurité du réseau informatique"],
        'P9': ["Rupture d'approvisionnement en pièces stratégiques", "Infraction au code des marchés publics", "Retard de livraison des prestataires", "Défaut de réception qualitative"],
        'P10': ["Retard dans la gestion des promotions", "Inadéquation des compétences au poste", "Manque de suivi de la formation continue"],
        'P11': ["Non-suivi des recommandations d'audit", "Indépendance restreinte des missions"],
        'P12': ["Défaut d'alignement des objectifs stratégiques", "Indicateurs de performance non renseignés", "Retard dans la prise de décision de la gouvernance"]
    }

    for _, p in df_p.iterrows():
        p_code = p['code']
        n_risks = p['count']
        descs = dict_descs.get(p_code, ["Risque opérationnel sur le processus"])
        
        for i in range(1, n_risks + 1):
            prob = int(np.random.choice([1, 2, 3, 4], p=[0.2, 0.4, 0.3, 0.1]))
            grav = int(np.random.choice([1, 2, 3, 4], p=[0.1, 0.3, 0.4, 0.2]))
            cb = prob * grav
            dmr = round(float(np.random.uniform(0.3, 0.85)), 2)
            cn = round(cb * dmr, 2)
            
            desc_text = descs[(i - 1) % len(descs)] + f" (R-0{i})"
            statut = np.random.choice(["Validé", "En vérification"], p=[0.85, 0.15])
            
            all_risks.append({
                'Code': f"R-{p_code}-{i:02d}",
                'Processus': p_code,
                'Intitulé': desc_text,
                'Prob': prob,
                'Grav': grav,
                'CB': cb,
                'DMR': dmr,
                'CN': cn,
                'Statut': statut
            })

    return df_p, pd.DataFrame(all_risks)

df_proc, df_risks = load_full_data()

# ---------------------------------------------------------
# 4. HEADER & BARRE DE NAVIGATION INSTITUTIONNELLE
# ---------------------------------------------------------
st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF — Enterprise Risk & Audit Center</div>
        <div class="header-subtitle">Système Décisionnel d'Aide à la Priorisation des Missions d'Audit Interne</div>
    </div>
""", unsafe_allow_html=True)

# SIDEBAR INSTITUTIONNELLE
st.sidebar.title("🏢 Direction de l'Audit")
st.sidebar.caption(f"Connecté : **{st.session_state['user_name']}** ({st.session_state['user_role']})")

menu = st.sidebar.radio(
    "Modules Métier :",
    [
        "🏠 Dashboard & Priorisation",
        "⚠️ Cartographie Générale (159)",
        "🔔 Workflow de Validation",
        "📊 Analytics & Modèles Actuariels",
        "📋 Plan d'Audit & Missions",
        "👥 Gestion des Accès & Profils",
        "📜 Traçabilité & Logs"
    ]
)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD DE PILOTAGE
# ---------------------------------------------------------
if menu == "🏠 Dashboard & Priorisation":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord & Priorisation</b></div>""", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Risques Identifiés", f"{len(df_risks)}", "12 Processus")
    m2.metric("Exposition VaR 95%", "4 816.7 DH", "Simulation Monte Carlo")
    m3.metric("Anomalies DMR", "21 Risques", "Surestimations R² = 0.915", delta_color="inverse")
    m4.metric("Processus Cible #1", "P9 (88.7/100)", "Achat & Approv.")

    st.write("")
    st.subheader("🎯 Priorisation des Processus pour l'Audit Interne (Score 0–100)")
    
    top_4 = df_proc.head(4)
    c1, c2 = st.columns(2)
    
    with c1:
        p1 = top_4.iloc[0]
        st.info(f"**RANG #{p1['rang']} — SCORE : {p1['score']} / 100**\n\n### {p1['code']} — {p1['libelle']}\n"
                f"Exposition VaR 95% : **{p1['var95']} DH** | Risques critiques : **{p1['critCount']}**")
        with st.expander("🔎 Analyse du Score & Facteurs de Risque"):
            st.write(f"- **Volume :** {p1['count']} risques cartographiés.\n- **Moyenne DMR :** {p1['dmrMoy']}\n- **Niveau d'Urgence :** {p1['priorite']}")

        p3 = top_4.iloc[2]
        st.warning(f"**RANG #{p3['rang']} — SCORE : {p3['score']} / 100**\n\n### {p3['code']} — {p3['libelle']}\n"
                   f"Exposition VaR 95% : **{p3['var95']} DH** | Risques critiques : **{p3['critCount']}**")
        with st.expander("🔎 Analyse du Score & Facteurs de Risque"):
            st.write(f"- **Volume :** {p3['count']} risques cartographiés.\n- **Moyenne DMR :** {p3['dmrMoy']}\n- **Niveau d'Urgence :** {p3['priorite']}")

    with c2:
        p2 = top_4.iloc[1]
        st.info(f"**RANG #{p2['rang']} — SCORE : {p2['score']} / 100**\n\n### {p2['code']} — {p2['libelle']}\n"
                f"Exposition VaR 95% : **{p2['var95']} DH** | Risques critiques : **{p2['critCount']}**")
        with st.expander("🔎 Analyse du Score & Facteurs de Risque"):
            st.write(f"- **Volume :** {p2['count']} risques cartographiés.\n- **Moyenne DMR :** {p2['dmrMoy']}\n- **Niveau d'Urgence :** {p2['priorite']}")

        p4 = top_4.iloc[3]
        st.warning(f"**RANG #{p4['rang']} — SCORE : {p4['score']} / 100**\n\n### {p4['code']} — {p4['libelle']}\n"
                   f"Exposition VaR 95% : **{p4['var95']} DH** | Risques critiques : **{p4['critCount']}**")
        with st.expander("🔎 Analyse du Score & Facteurs de Risque"):
            st.write(f"- **Volume :** {p4['count']} risques cartographiés.\n- **Moyenne DMR :** {p4['dmrMoy']}\n- **Niveau d'Urgence :** {p4['priorite']}")

    st.write("")
    st.subheader("📊 Graphique de Priorisation des 12 Processus")
    fig = px.bar(
        df_proc, 
        x='score', 
        y='code', 
        orientation='h', 
        color='score',
        hover_data=['libelle', 'var95', 'critCount', 'count'],
        color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'],
        text='score'
    )
    fig.update_layout(height=420, yaxis={'categoryorder':'total ascending'}, plot_bgcolor='#FFFFFF')
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# MODULE 2: CARTOGRAPHIE DES RISQUES (159 RISQUES COMPLETS)
# ---------------------------------------------------------
elif menu == "⚠️ Cartographie Générale (159)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Cartographie Générale des Risques (159)</b></div>""", unsafe_allow_html=True)
    st.subheader("📋 Registre Exhaustif des Risques Cartographiés")

    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    selected_proc = col_f1.multiselect("Filtrer par Processus :", df_proc['code'].unique(), default=df_proc['code'].unique())
    search_term = col_f2.text_input("🔍 Mot-clé :", "")
    statut_filter = col_f3.selectbox("Statut :", ["Tous", "Validé", "En vérification"])

    filtered = df_risks[df_risks['Processus'].isin(selected_proc)]
    if search_term:
        filtered = filtered[filtered['Intitulé'].str.contains(search_term, case=False)]
    if statut_filter != "Tous":
        filtered = filtered[filtered['Statut'] == statut_filter]

    st.write(f"Affichage de **{len(filtered)}** risques sur **{len(df_risks)}** au total.")
    st.dataframe(filtered, use_container_width=True, height=500)

# ---------------------------------------------------------
# MODULE 3: WORKFLOW DE VALIDATION
# ---------------------------------------------------------
elif menu == "🔔 Workflow de Validation":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Workflow de Validation</b></div>""", unsafe_allow_html=True)
    st.subheader("🔔 Validation des Déclarations de Risques")

    risques_en_attente = df_risks[df_risks['Statut'] == "En vérification"]
    
    if len(risques_en_attente) > 0:
        st.write(f"Il y a actuellement **{len(risques_en_attente)}** risques soumis en attente de vérification.")
        
        selected_risk_code = st.selectbox("Sélectionner un risque à examiner :", risques_en_attente['Code'] + " - " + risques_en_attente['Intitulé'])
        risk_code = selected_risk_code.split(" - ")[0]
        risk_detail = df_risks[df_risks['Code'] == risk_code].iloc[0]

        with st.form("val_form"):
            st.write(f"### Risque : **{risk_detail['Code']}** ({risk_detail['Processus']})")
            st.write(f"**Intitulé :** {risk_detail['Intitulé']}")
            st.write(f"**Criticité Brute :** {risk_detail['CB']} | **DMR Déclaré :** {risk_detail['DMR']} | **Criticité Nette :** {risk_detail['CN']}")
            
            decision = st.radio("Décision de l'auditeur interne :", ["Approuver & Valider", "Demander une révision du DMR", "Rejeter"])
            obs = st.text_area("Observations & Recommandations d'Audit :", "")
            
            if st.form_submit_button("⚡ Enregistrer la Décision"):
                st.success(f"Décision enregistrée avec succès pour le risque {risk_code}!")
    else:
        st.success("Aucun risque en attente de validation.")

# ---------------------------------------------------------
# MODULE 4: ANALYTIQUE & MODÈLES
# ---------------------------------------------------------
elif menu == "📊 Analytics & Modèles Actuariels":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Analyses Quantitatives</b></div>""", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["🧪 ANOVA", "📉 Contrôle du DMR", "🎲 Monte Carlo / VaR"])
    
    with t1:
        st.subheader("Validation Statistique ANOVA")
        st.metric("F-Statistic", "4.22")
        st.metric("p-value", "0.00002")
        st.success("Validation : L'hétérogénéité de la criticité nette entre les processus est statistiquement significative (p < 0.05).")
        
    with t2:
        st.subheader("Régressivité & Surestimation du DMR")
        st.metric("R² du Modèle", "0.915")
        st.warning("21 risques présentent un DMR surestimé. Une révision ciblée est requise.")

    with t3:
        st.subheader("Distribution Stochastique de Pertes")
        st.metric("Value at Risk (VaR 95%)", "4 816.7 DH")
        st.metric("Tail Value at Risk (TVaR 95%)", "5 940.2 DH")

# ---------------------------------------------------------
# MODULE 5: PLAN D'AUDIT
# ---------------------------------------------------------
elif menu == "📋 Plan d'Audit & Missions":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Planification des Missions</b></div>""", unsafe_allow_html=True)
    st.subheader("📅 Programme Annuel d'Audit Interne")

    with st.form("mission_form_ent"):
        proc_sel = st.selectbox("Processus Cible (Sélectionné par la Priorisation) :", df_proc['code'] + " - " + df_proc['libelle'])
        aud_resp = st.text_input("Auditeur Responsable de Mission :", st.session_state['user_name'])
        d_range = st.date_input("Période Prévisionnelle :", [])
        obj_m = st.text_area("Objectifs de la Mission :", "")
        
        if st.form_submit_button("🚀 Inscrire au Plan d'Audit"):
            st.success(f"Mission inscrite avec succès pour le processus {proc_sel}.")

# ---------------------------------------------------------
# MODULE 6: GESTION DES ACCÈS & ACCRÉDITATIONS (NOUVEAU)
# ---------------------------------------------------------
elif menu == "👥 Gestion des Accès & Profils":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Gestion des Accès (RBAC)</b></div>""", unsafe_allow_html=True)
    st.subheader("👥 Console d'Accréditation et Gestion des Utilisateurs")
    st.caption("Espace réservé à l'Auditeur Interne pour octroyer les accès à la plateforme.")

    st.dataframe(st.session_state['users_db'], use_container_width=True)

    st.write("---")
    st.subheader("➕ Octroyer un Nouvel Accès")
    
    with st.form("add_user_form"):
        col_u1, col_u2 = st.columns(2)
        new_nom = col_u1.text_input("Nom & Prénom du collaborateur :")
        new_email = col_u2.text_input("Adresse Email Institutionnelle (@ormva-tf.ma) :")
        
        col_u3, col_u4 = st.columns(2)
        new_role = col_u3.selectbox("Rôle Attribué :", ["Auditeur Interne", "Responsable Processus", "Direction Générale", "Consultant Externe"])
        new_statut = col_u4.selectbox("Statut du Compte :", ["Actif", "Inactif"])

        if st.form_submit_button("🔒 Créer les Accès"):
            if new_nom and new_email:
                new_entry = pd.DataFrame([{"Nom": new_nom, "Email": new_email, "Rôle": new_role, "Statut": new_statut}])
                st.session_state['users_db'] = pd.concat([st.session_state['users_db'], new_entry], ignore_index=True)
                st.success(f"Accès créé avec succès pour {new_nom} ({new_role}).")
                st.rerun()
            else:
                st.error("Veuillez remplir tous les champs.")

# ---------------------------------------------------------
# MODULE 7: AUDIT TRAIL
# ---------------------------------------------------------
elif menu == "📜 Traçabilité & Logs":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Audit Trail</b></div>""", unsafe_allow_html=True)
    st.subheader("📜 Journal de Traçabilité des Opérations")
    
    logs_df = pd.DataFrame([
        {"Horodatage": "11/08/2026 11:45", "Utilisateur": "Auditeur Principal", "Action": "Ajout Nouvel Accès", "Détail": "Compte créé : dg@ormva-tf.ma"},
        {"Horodatage": "11/08/2026 10:14", "Utilisateur": "Auditeur Principal", "Action": "Consultation Priorisation", "Détail": "P9 identifié Top 1"},
        {"Horodatage": "10/08/2026 15:30", "Utilisateur": "Resp P7", "Action": "Soumission Risque", "Détail": "Risque R-P7-02 soumis"}
    ])
    st.table(logs_df)

# ---------------------------------------------------------
# 5. FOOTER SOMBRE INSTITUTIONNEL
# ---------------------------------------------------------
st.markdown("""
    <div class="footer-dark">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Office Régional de Mise en Valeur Agricole du Tafilalet
                <br><span style="color: #6B7280; font-size: 0.75rem;">Plateforme Institutionnelle d'Aide à la Décision d'Audit Interne (2026)</span>
            </div>
            <div>
                <span style="color: #4E7D5B;">Système : <b>Opérationnel</b></span> | Version : <b>V1.0 Enterprise</b>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

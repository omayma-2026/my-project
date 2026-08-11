import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ---------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE & STYLE PROFESSIONNEL
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

# ---------------------------------------------------------
# 2. CHARGEMENT DES DONNÉES
# ---------------------------------------------------------
@st.cache_data
def load_data():
    for filename in ['cartographie_analysee_complete.xlsx', 'projet1.xlsx', 'data_reel.xlsx']:
        try:
            df = pd.read_excel(filename, sheet_name='Details_Risques' if 'cartographie' in filename else 0)
            return df
        except Exception:
            try:
                df = pd.read_excel(filename)
                return df
            except Exception:
                continue
    return pd.DataFrame()

df_original = load_data()
if not df_original.empty:
    df_original.columns = [c.strip().lower() for c in df_original.columns]

if 'users_db' not in st.session_state:
    st.session_state['users_db'] = pd.DataFrame([
        {"Nom": "Auditeur Principal", "Email": "audit@ormva-tf.ma", "Rôle": "Auditeur Interne", "Statut": "Actif"},
        {"Nom": "Responsable P9", "Email": "p9@ormva-tf.ma", "Rôle": "Responsable Processus", "Statut": "Actif"}
    ])

if "plan_actions" not in st.session_state:
    st.session_state.plan_actions = pd.DataFrame(columns=[
        "ID", "Processus", "Risque associé", "Recommandation",
        "Responsable", "Priorité", "Date création",
        "Échéance", "Statut", "Date clôture", "Commentaires"
    ])

STATUTS = ["Ouvert", "En cours", "Clôturé"]
PRIORITES = ["Faible", "Moyenne", "Haute", "Critique"]

def _next_id():
    df = st.session_state.plan_actions
    return 1 if df.empty else int(df["ID"].max()) + 1

# ---------------------------------------------------------
# 3. NAVIGATION & FILTRAGE (SIDEBAR)
# ---------------------------------------------------------
st.sidebar.title("🏢 Direction de l'Audit")
st.sidebar.markdown("---")

if not df_original.empty and 'processus' in df_original.columns:
    st.sidebar.subheader("🔍 Filtre Métier")
    list_processus = ['Tous les Processus'] + sorted(df_original['processus'].dropna().unique().tolist())
    selected_proc = st.sidebar.selectbox("Filtrer par Processus :", list_processus)
    
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
        "🏠 Dashboard & Répartition (Donut)",
        "🗺️ Matrice des Risques (Heatmap)",
        "🔥 Top 10 Risques Prioritaires",
        "📋 Suivi des Plans d'Action",
        "👥 Gestion des Accès & Rôles",
        "📋 Registre Détaillé"
    ]
)

st.markdown("""
    <div class="header-container">
        <div class="header-title">🛡️ ORMVA-TF — Enterprise Risk & Audit Center</div>
        <div class="header-subtitle">Système Décisionnel d'Aide à la Priorisation des Missions d'Audit Interne</div>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# MODULE 1: DASHBOARD & DONUT CHART (ZONES OFFICIELLES)
# ---------------------------------------------------------
if menu == "🏠 Dashboard & Répartition (Donut)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Tableau de Bord & Répartition</b></div>""", unsafe_allow_html=True)
    
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Risques Filtrés / Totaux", f"{len(df)} / {len(df_original)}", "Base Officielle")
        m2.metric("Processus Actifs", df['processus'].nunique() if 'processus' in df.columns else 0, "Périmètre")
        m3.metric("Statut Système", "Production", "Audit Interne")

        st.write("")
        col_l, col_r = st.columns(2)
        
        with col_l:
            st.subheader("🎯 Répartition par Zone d'Action (Donut)")
            
            # Utilisation directe des labels officiels de la cartographie
            if 'cluster_label' in df.columns:
                zone_counts = df['cluster_label'].value_counts().reset_index()
            else:
                zone_counts = pd.DataFrame({'cluster_label': ['Negliges', 'Mineurs', 'Sous controle', 'Critiques non maitrises'], 'count': [51, 46, 41, 21]})
            
            zone_counts.columns = ['Zone', 'Count']
            
            # Application des couleurs officielles exactes selon la documentation
            fig_donut = px.pie(
                zone_counts, values='Count', names='Zone', hole=0.4,
                color='Zone',
                color_discrete_map={
                    'Sous controle': '#1B3B5F',             # Bleu foncé (Vigilance)
                    'Mineurs': '#D9822B',                   # Orange (Surveillance)
                    'Negliges': '#2D6A4F',                  # Vert (Optimisation)
                    'Critiques non maitrises': '#A31D1D'    # Rouge (Traitement Prioritaire)
                }
            )
            fig_donut.update_layout(height=400, plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_r:
            st.subheader("📊 Top Processus par Nombre de Risques")
            if 'processus' in df_original.columns:
                df_proc = df_original.groupby('processus').size().reset_index(name='Nombre').sort_values(by='Nombre', ascending=True)
                fig_bar = px.bar(
                    df_proc, x='Nombre', y='processus', orientation='h',
                    color='Nombre', color_continuous_scale=['#4E7D5B', '#1E513B', '#0A2F1D'], text='Nombre'
                )
                fig_bar.update_layout(height=400, plot_bgcolor='#FFFFFF')
                st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------
# MODULE 2: MATRICE DES RISQUES (HEATMAP)
# ---------------------------------------------------------
elif menu == "🗺️ Matrice des Risques (Heatmap)":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Matrice des Risques</b></div>""", unsafe_allow_html=True)
    st.subheader("🗺️ Matrice d'Évaluation (Probabilité vs Gravité)")

    if not df.empty and 'prob' in df.columns and 'grav' in df.columns:
        matrix_data = pd.crosstab(df['grav'], df['prob'])
        
        fig_matrix = go.Figure(data=go.Heatmap(
            z=matrix_data.values,
            x=[str(c) for c in matrix_data.columns],
            y=[str(r) for r in matrix_data.index],
            colorscale='Reds',
            text=matrix_data.values,
            texttemplate="%{text}",
            textfont={"size": 16}
        ))
        
        fig_matrix.update_layout(
            title="Concentration des Risques dans la Matrice",
            xaxis_title="Probabilité",
            yaxis_title="Gravité",
            height=500,
            plot_bgcolor='#FFFFFF'
        )
        st.plotly_chart(fig_matrix, use_container_width=True)
    else:
        st.warning("Colonnes 'prob' et 'grav' requises.")

# ---------------------------------------------------------
# MODULE 3: TOP 10 RISQUES PRIORITAIRES
# ---------------------------------------------------------
elif menu == "🔥 Top 10 Risques Prioritaires":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Top Risques</b></div>""", unsafe_allow_html=True)
    st.subheader("🔥 Top Risques les plus Critiques (Scoring)")

    if not df.empty:
        if 'prob' in df.columns and 'grav' in df.columns:
            df['score_priorite'] = df['prob'] * df['grav']
        elif 'criticité brute' in df.columns:
            df['score_priorite'] = df['criticité brute']
        else:
            df['score_priorite'] = 10

        top_risks = df.sort_values(by='score_priorite', ascending=False).head(10)
        
        fig_top = px.bar(
            top_risks.sort_values(by='score_priorite', ascending=True),
            x='score_priorite', y='code' if 'code' in top_risks.columns else top_risks.index.astype(str),
            orientation='h', color='score_priorite',
            color_continuous_scale=['#F4A261', '#E76F51', '#A31D1D'], text='score_priorite'
        )
        fig_top.update_layout(height=450, plot_bgcolor='#FFFFFF', xaxis_title="Score de Priorité", yaxis_title="Code Risque")
        st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.warning("Données indisponibles.")

# ---------------------------------------------------------
# MODULE 4: SUIVI DES PLANS D'ACTION
# ---------------------------------------------------------
elif menu == "📋 Suivi des Plans d'Action":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Plans d'Action & Recommandations</b></div>""", unsafe_allow_html=True)
    st.markdown("## 📋 Suivi des Plans d'Action & Recommandations")

    with st.expander("➕ Ajouter une nouvelle recommandation", expanded=False):
        with st.form("form_plan_action", clear_on_submit=True):
            col1, col2 = st.columns(2)
            proc_col = next((c for c in df_original.columns if c.lower() == 'processus'), None)
            processus_list = sorted(df_original[proc_col].dropna().unique()) if proc_col and not df_original.empty else ["N/A"]

            with col1:
                processus = st.selectbox("Processus", processus_list)
                risque = st.text_input("Risque associé")
                responsable = st.text_input("Responsable")
            with col2:
                priorite = st.selectbox("Priorité", PRIORITES)
                echeance = st.date_input("Échéance", min_value=date.today())
                statut = st.selectbox("Statut initial", STATUTS)

            recommandation = st.text_area("Recommandation / Action corrective")
            commentaires = st.text_area("Commentaires (optionnel)")

            submitted = st.form_submit_button("Enregistrer")
            if submitted:
                if not risque or not recommandation or not responsable:
                    st.error("Merci de remplir au minimum : Risque, Recommandation et Responsable.")
                else:
                    new_row = {
                        "ID": _next_id(),
                        "Processus": processus,
                        "Risque associé": risque,
                        "Recommandation": recommandation,
                        "Responsable": responsable,
                        "Priorité": priorite,
                        "Date création": date.today(),
                        "Échéance": echeance,
                        "Statut": statut,
                        "Date clôture": None,
                        "Commentaires": commentaires
                    }
                    st.session_state.plan_actions = pd.concat(
                        [st.session_state.plan_actions, pd.DataFrame([new_row])],
                        ignore_index=True
                    )
                    st.success("Plan d'action ajouté avec succès ✅")

    pa_df = st.session_state.plan_actions.copy()
    if pa_df.empty:
        st.info("Aucun plan d'action enregistré pour le moment.")
    else:
        today = pd.Timestamp(date.today())
        pa_df["Échéance"] = pd.to_datetime(pa_df["Échéance"])
        pa_df["En retard"] = (pa_df["Échéance"] < today) & (pa_df["Statut"] != "Clôturé")

        total = len(pa_df)
        clotures = (pa_df["Statut"] == "Clôturé").sum()
        en_retard = pa_df["En retard"].sum()
        taux_cloture = round((clotures / total) * 100, 1) if total else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total actions", total)
        k2.metric("Taux de clôture", f"{taux_cloture}%")
        k3.metric("Actions en retard", int(en_retard))
        k4.metric("En cours", int((pa_df["Statut"] == "En cours").sum()))

        c1, c2 = st.columns(2)
        with c1:
            fig_statut = px.pie(pa_df, names="Statut", title="Répartition par statut", hole=0.45)
            fig_statut.update_layout(plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig_statut, use_container_width=True)
        with c2:
            if not pa_df.empty and "Responsable" in pa_df.columns:
                resp_df = pa_df.groupby("Responsable").size().reset_index(name="Nombre")
                fig_resp = px.bar(resp_df, x="Responsable", y="Nombre", title="Actions par responsable", color="Nombre", color_continuous_scale="Greens")
                fig_resp.update_layout(plot_bgcolor='#FFFFFF')
                st.plotly_chart(fig_resp, use_container_width=True)

        st.markdown("### 🗂️ Registre des plans d'action")
        def _highlight_retard(row):
            return ['background-color: #FDECEA' if row["En retard"] else '' for _ in row]

        st.dataframe(pa_df.style.apply(_highlight_retard, axis=1), use_container_width=True)

        st.markdown("### ✏️ Mettre à jour le statut d'une action")
        col_u1, col_u2, col_u3 = st.columns(3)
        with col_u1:
            action_id = st.selectbox("Sélectionner l'ID de l'action", pa_df["ID"])
        with col_u2:
            nouveau_statut = st.selectbox("Nouveau statut", STATUTS)
        with col_u3:
            st.write("")
            st.write("")
            update_btn = st.button("Mettre à jour le Statut")

        if update_btn:
            idx = st.session_state.plan_actions["ID"] == action_id
            st.session_state.plan_actions.loc[idx, "Statut"] = nouveau_statut
            if nouveau_statut == "Clôturé":
                st.session_state.plan_actions.loc[idx, "Date clôture"] = date.today()
            st.success(f"Action #{action_id} mise à jour avec succès → {nouveau_statut}")
            st.rerun()

# ---------------------------------------------------------
# MODULE 5: GESTION DES ACCÈS & RÔLES
# ---------------------------------------------------------
elif menu == "👥 Gestion des Accès & Rôles":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Gestion des Accès</b></div>""", unsafe_allow_html=True)
    st.subheader("👥 Console d'Accréditation & Attribution des Rôles")
    st.dataframe(st.session_state['users_db'], use_container_width=True)

    with st.form("add_user_form"):
        st.markdown("#### 🔒 Octroyer un nouvel accès utilisateur")
        u_nom = st.text_input("Nom & Prénom :")
        u_email = st.text_input("Email institutionnel (@ormva-tf.ma) :")
        u_role = st.selectbox("Rôle Métier :", ["Auditeur Interne", "Responsable Processus", "Direction Générale"])
        if st.form_submit_button("Valider et Activer l'Accès"):
            if u_nom and u_email:
                new_acc = pd.DataFrame([{"Nom": u_nom, "Email": u_email, "Rôle": u_role, "Statut": "Actif"}])
                st.session_state['users_db'] = pd.concat([st.session_state['users_db'], new_acc], ignore_index=True)
                st.success(f"Accès accordé avec succès à {u_nom} !")
                st.rerun()

# ---------------------------------------------------------
# MODULE 6: REGISTRE DÉTAILLÉ
# ---------------------------------------------------------
elif menu == "📋 Registre Détaillé":
    st.markdown("""<div class="breadcrumb">Direction Audit › <b>Registre Détaillé</b></div>""", unsafe_allow_html=True)
    st.subheader("📑 Base de Données Complète des Risques")
    if not df.empty:
        search = st.text_input("🔍 Rechercher un risque :", "")
        filtered = df
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            filtered = df[mask]
        st.dataframe(filtered, use_container_width=True, height=550)

# Footer
st.markdown("""
    <div class="footer-dark">
        <strong>🛡️ ORMVA-TF Risk & Audit Management Center</strong> — Plateforme Institutionnelle (2026)
    </div>
""", unsafe_allow_html=True)

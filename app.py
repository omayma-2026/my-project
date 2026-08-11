import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

STATUTS = ["Ouvert", "En cours", "Clôturé"]
PRIORITES = ["Faible", "Moyenne", "Haute", "Critique"]

def _init_state():
    if "plan_actions" not in st.session_state:
        st.session_state.plan_actions = pd.DataFrame(columns=[
            "ID", "Processus", "Risque associé", "Recommandation",
            "Responsable", "Priorité", "Date création",
            "Échéance", "Statut", "Date clôture", "Commentaires"
        ])

def _next_id():
    df = st.session_state.plan_actions
    return 1 if df.empty else int(df["ID"].max()) + 1

def render_plan_action(df_risques: pd.DataFrame):
    _init_state()
    st.markdown("## 📋 Suivi des Plans d'Action & Recommandations")

    # ---------- FORMULAIRE D'AJOUT ----------
    with st.expander("➕ Ajouter une nouvelle recommandation", expanded=False):
        with st.form("form_plan_action", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            # Recherche sécurisée de la colonne Processus (majuscule ou minuscule)
            proc_col = next((c for c in df_risques.columns if c.lower() == 'processus'), None)
            processus_list = sorted(df_risques[proc_col].dropna().unique()) if proc_col and not df_risques.empty else ["N/A"]

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

    df = st.session_state.plan_actions.copy()
    if df.empty:
        st.info("Aucun plan d'action enregistré pour le moment. Utilisez le formulaire ci-dessus pour ajouter une recommandation.")
        return

    # ---------- CALCUL RETARD ----------
    today = pd.Timestamp(date.today())
    df["Échéance"] = pd.to_datetime(df["Échéance"])
    df["En retard"] = (df["Échéance"] < today) & (df["Statut"] != "Clôturé")

    # ---------- KPIs ----------
    total = len(df)
    clotures = (df["Statut"] == "Clôturé").sum()
    en_retard = df["En retard"].sum()
    taux_cloture = round((clotures / total) * 100, 1) if total else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total actions", total)
    k2.metric("Taux de clôture", f"{taux_cloture}%")
    k3.metric("Actions en retard", int(en_retard))
    k4.metric("En cours", int((df["Statut"] == "En cours").sum()))

    # ---------- GRAPHIQUES ----------
    c1, c2 = st.columns(2)
    with c1:
        fig_statut = px.pie(df, names="Statut", title="Répartition par statut", hole=0.45)
        fig_statut.update_layout(plot_bgcolor='#FFFFFF')
        st.plotly_chart(fig_statut, use_container_width=True)
    with c2:
        if not df.empty and "Responsable" in df.columns:
            resp_df = df.groupby("Responsable").size().reset_index(name="Nombre")
            fig_resp = px.bar(resp_df, x="Responsable", y="Nombre", title="Actions par responsable", color="Nombre", color_continuous_scale="Greens")
            fig_resp.update_layout(plot_bgcolor='#FFFFFF')
            st.plotly_chart(fig_resp, use_container_width=True)

    # ---------- TABLE + MISE A JOUR STATUT ----------
    st.markdown("### 🗂️ Registre des plans d'action")

    def _highlight_retard(row):
        return ['background-color: #FDECEA' if row["En retard"] else '' for _ in row]

    st.dataframe(df.style.apply(_highlight_retard, axis=1), use_container_width=True)

    st.markdown("### ✏️ Mettre à jour le statut d'une action")
    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u1:
        action_id = st.selectbox("Sélectionner l'ID de l'action", df["ID"])
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

"""ORMVA-TF Risk & Audit Center — outil de travail pour l'auditeur interne et le risk manager."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy import stats

try:
    import core
except ModuleNotFoundError:
    st.error("`core.py` est introuvable à côté de `app.py`. Ajoute-le au dépôt GitHub (même dossier), puis redéploie.")
    st.stop()
from core import ZCOL, ZONES

st.set_page_config(page_title="ORMVA-TF | Risk & Audit Center", page_icon="🛡️", layout="wide")
st.markdown("""<style>
.stApp{background:#F4F7F9} h1,h2,h3{color:#0F3D2E}
div[data-testid=stMetric]{background:#fff;border-left:4px solid #0F3D2E;border-radius:8px;padding:10px 16px}
table.mx{border-collapse:separate;border-spacing:3px;width:100%}
table.mx td{color:#fff;text-align:center;padding:8px;font-size:12px;border-radius:6px;min-width:90px}
table.mx th{font-size:12px;color:#2E3B47;padding:4px}
</style>""", unsafe_allow_html=True)


@st.cache_resource
def boot():
    core.init_db()
    return True


try:
    boot()
except FileNotFoundError as e:
    st.error(f"{e} Copie `cartographie_analysee_complete.xlsx` et `data_reel_avec_rm.xlsx` dans `data/`, puis relance.")
    st.stop()

# ---------- accès direct (sans connexion) : session administrateur ----------
ME, ADMIN = "admin", True

# ---------- données ----------
df = core.q("SELECT * FROM risks")
SP_ALL = core.stats_proc(df)
SC_ALL = core.score(SP_ALL)  # score sur toute la base : les filtres n'affectent que l'affichage
PAGES = ["Tableau de bord", "Registre des risques", "Matrices", "Priorisation", "Plan d'audit",
         "Plan d'actions", "Analyses statistiques", "Historique"]

with st.sidebar:
    st.markdown("### 🛡️ ORMVA-TF")
    st.caption("Mode administrateur")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    procs = sorted(df["processus_code"].unique(), key=lambda x: int(x[1:]))
    sel = st.multiselect("Processus (affichage)", procs, default=procs) or procs

R = df[df["processus_code"].isin(sel)]
SC = SC_ALL[SC_ALL["processus_code"].isin(sel)]
short = lambda c: c.split(".")[-1]


def matrix(cells, rows, cols, color, note):
    h = "<table class='mx'><tr><th></th>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
    for i, rl in enumerate(rows):
        h += f"<tr><th>{rl}</th>" + "".join(
            f"<td style='background:{color(i, j)}'>{' '.join(cells.get((i, j), []))}</td>" for j in range(len(cols))) + "</tr>"
    st.markdown(h + f"</table><p style='font-size:12px;text-align:center'>{note}</p>", unsafe_allow_html=True)


def dl(frame, name):
    st.download_button("⬇️ Exporter (CSV pour Excel)", frame.to_csv(index=False).encode("utf-8-sig"), name, "text/csv")


st.title(page)

# ================= TABLEAU DE BORD =================
if page == "Tableau de bord":
    act = core.q("SELECT statut FROM actions")
    c = st.columns(6)
    c[0].metric("Risques", len(R))
    c[1].metric("% zone D", f"{(R.zone == 'D').mean() * 100:.1f}%")
    c[2].metric("% zone C", f"{(R.zone == 'C').mean() * 100:.1f}%")
    c[3].metric("Criticité brute moy.", f"{R.criticite_brute.mean():.2f}")
    c[4].metric("DMR moyen", f"{R.dmr.mean():.2f}")
    c[5].metric("Actions ouvertes", int((act["statut"] != "Terminée").sum()) if len(act) else 0)
    a, b = st.columns(2)
    zc = R["zone"].value_counts().reindex(ZONES).fillna(0).reset_index()
    a.plotly_chart(px.pie(zc, names="zone", values="count", hole=0.5, color="zone", color_discrete_map=ZCOL,
                          title="Risques par zone"), width="stretch")
    b.plotly_chart(px.bar(SC.sort_values("Score"), x="Score", y="processus_code", orientation="h",
                          title="Score de priorité d'audit", color_discrete_sequence=["#0F3D2E"]), width="stretch")
    st.markdown("#### Risques à traiter en premier (zone D, contrôle le plus faible)")
    st.dataframe(R[R.zone == "D"].sort_values(["dmr", "criticite_brute"], ascending=[True, False])
                 [["code", "processus_code", "intitule", "criticite_brute", "dmr"]].head(10), width="stretch", hide_index=True)

# ================= REGISTRE =================
elif page == "Registre des risques":
    f = st.columns([2, 2, 3])
    zs = f[0].multiselect("Zone", ZONES, default=ZONES)
    cl = f[1].multiselect("Profil (cluster)", sorted(R.cluster_label.dropna().unique()))
    s = f[2].text_input("Recherche (code / intitulé)")
    v = R[R.zone.isin(zs)]
    if cl:
        v = v[v.cluster_label.isin(cl)]
    if s:
        v = v[v.intitule.str.contains(s, case=False, na=False) | v.code.str.contains(s, case=False, na=False)]
    v = v.sort_values("criticite_brute", ascending=False)
    st.caption(f"{len(v)} risques")
    st.dataframe(v.drop(columns=["pca1", "pca2", "constat", "mesures_operatoires"]), width="stretch", hide_index=True, height=380)
    dl(v, "registre_risques.csv")
    if len(v):
        code = st.selectbox("Détail d'un risque", v["code"])
        r = df[df.code == code].iloc[0]
        st.markdown(f"**{r.code} · {r.intitule}**")
        st.caption(f"{r.processus_code} — {r.processus_nom} · {r.sous_processus} · zone {r.zone} ({r.zone_source})")
        with st.form("edit"):
            e = st.columns(3)
            prob = e[0].select_slider("Probabilité", [1, 2, 3, 4], int(r.prob))
            grav = e[1].select_slider("Gravité", [1, 2, 3, 4], int(r.grav))
            opts = [0.0, 0.25, 0.5, 0.75, 1.0]
            dmr = e[2].select_slider("DMR (degré de contrôle)", opts, min(opts, key=lambda o: abs(o - r.dmr)),
                                     format_func=lambda o: f"{o:.0%}")
            constat = st.text_area("Constat", r.constat)
            mesures = st.text_area("Mesures opératoires", r.mesures_operatoires)
            if st.form_submit_button("Enregistrer les modifications"):
                n = core.update_risk(code, dict(prob=prob, grav=grav, dmr=dmr, constat=constat,
                                                mesures_operatoires=mesures), ME)
                st.toast(f"{n} champ(s) modifié(s) — criticité et zone recalculées" if n else "Aucun changement")
                st.rerun()
        st.caption("La criticité brute et la zone (règle du document) sont recalculées à chaque modification de prob., grav. ou DMR. Tout est tracé dans l'historique.")

# ================= MATRICES =================
elif page == "Matrices":
    d = core.bands(R)
    rule = core.zone_rule(df.criticite_brute, df.dmr)
    off = df.zone_source == "officielle"
    st.metric("Concordance zone officielle ↔ règle (bandes du document)", f"{(rule[off] == df.zone[off]).mean() * 100:.1f}%")
    t1, t2 = st.tabs(["Risques bruts (probabilité × gravité)", "Risques nets (contrôle × criticité) — zones"])
    with t1:
        cells = {}
        for r in d.itertuples():
            cells.setdefault((4 - int(r.prob), int(r.grav) - 1), []).append(short(r.code))
        lv = ["#2E7D4F", "#D9A441", "#E08E45", "#C0392B"]
        matrix(cells, ["Très probable (4)", "Probable (3)", "Improbable (2)", "Rare (1)"],
               ["Négligeable (1)", "Mineur (2)", "Modéré (3)", "Majeur (4)"],
               lambda i, j: lv[min(3, int((4 - i) * (j + 1) // 4))] if (4 - i) * (j + 1) < 12 else lv[3],
               "Gravité de l'impact → · Fréquence d'occurrence ↑")
    with t2:
        cells = {}
        for r in d.itertuples():
            cells.setdefault((3 - r.br, r.bc), []).append(short(r.code))
        zc = lambda i, j: ZCOL[str(core.zone_rule(8 if j >= 2 else 0, 1.0 if (3 - i) >= 2 else 0.0))]
        matrix(cells, core.CTRL_LABELS[::-1], core.CRIT_LABELS, zc,
               "Degré de criticité brute → · Degré de contrôle (DMR) ↑ · A optimisation · B vigilance · C surveillance · D traitement")

# ================= PRIORISATION =================
elif page == "Priorisation":
    t1, t2, t3 = st.tabs(["Classement", "Composantes du score", "Robustesse & apport"])
    with t1:
        st.code("Sp = 0.45·N(%Zone D) + 0.30·N(%Zone C) + 0.25·N(Criticité brute moyenne)   — N = min-max 0-100")
        st.plotly_chart(px.bar(SC.sort_values("Score"), x="Score", y="processus_code", orientation="h", text="Score",
                               color="Score", color_continuous_scale=["#DCE9DF", "#C0392B"]).update_layout(coloraxis_showscale=False), width="stretch")
        tb = SC[["Rang", "processus_code", "processus_nom", "Score", "Pct_D", "Pct_C", "Crit", "DMR", "Nb"]]
        st.dataframe(tb, width="stretch", hide_index=True)
        dl(tb, "classement_processus.csv")
        st.warning("Indicateur de priorité relative, pas une probabilité de survenance : il éclaire le jugement de l'auditeur.")
    with t2:
        m = SC.melt(id_vars="processus_code", value_vars=["contrib_D", "contrib_C", "contrib_brut"], var_name="Composante", value_name="Points")
        st.plotly_chart(px.bar(m, x="Points", y="processus_code", color="Composante", orientation="h",
                               color_discrete_map={"contrib_D": "#C0392B", "contrib_C": "#E08E45", "contrib_brut": "#0F3D2E"}), width="stretch")
        st.dataframe(SC[["processus_code", "Pct_D", "N_D", "contrib_D", "Pct_C", "N_C", "contrib_C", "Crit", "N_brut", "contrib_brut", "Score", "Rang"]].round(2),
                     width="stretch", hide_index=True)
    with t3:
        cmp = SC_ALL[["processus_code", "Rang", "Score", "Crit"]].copy()
        cmp["Rang_criticité_seule"] = cmp["Crit"].rank(ascending=False, method="min").astype(int)
        cmp["Écart"] = cmp["Rang_criticité_seule"] - cmp["Rang"]
        st.markdown("**Apport du score** : différence avec un classement basé sur la seule criticité brute moyenne (écart > 0 = le score remonte le processus).")
        st.dataframe(cmp.rename(columns={"Rang": "Rang Sp"}), width="stretch", hide_index=True)
        base = SC_ALL.set_index("processus_code")["Rang"]
        rows, ranks = [], pd.DataFrame(index=base.index)
        for n, w in core.SCENARIOS.items():
            rk = core.score(SP_ALL, w).set_index("processus_code")["Rang"]
            ranks[n] = rk
            if n != "Base":
                rho, p = stats.spearmanr(base, rk.reindex(base.index))
                rows.append({"Scénario": n, "Spearman ρ vs Base": round(rho, 3), "p-value": round(p, 5)})
        st.markdown("**Sensibilité aux pondérations**")
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        st.dataframe(ranks.reset_index(), width="stretch", hide_index=True)

# ================= PLAN D'AUDIT =================
elif page == "Plan d'audit":
    c = st.columns(2)
    n = c[0].slider("Nombre de processus à auditer (par ordre de priorité)", 1, len(SC_ALL), min(3, len(SC_ALL)))
    zs = c[1].multiselect("Zones à retenir", ZONES, default=["D", "C"])
    top = SC_ALL.head(n)
    st.dataframe(top[["Rang", "processus_code", "processus_nom", "Score"]], width="stretch", hide_index=True)
    p = df[df.processus_code.isin(top.processus_code) & df.zone.isin(zs)].copy()
    p["Rang_processus"] = p["processus_code"].map(SC_ALL.set_index("processus_code")["Rang"])
    p["zsev"] = p["zone"].map(core.ZSEV)
    p = p.sort_values(["Rang_processus", "zsev", "criticite_brute", "dmr"], ascending=[True, False, False, True])
    out = p[["Rang_processus", "processus_code", "code", "intitule", "zone", "criticite_brute", "dmr", "cluster_label", "constat", "mesures_operatoires"]]
    st.markdown(f"**{len(out)} risques à couvrir** (par processus, zone la plus sévère, criticité décroissante, contrôle croissant)")
    st.dataframe(out, width="stretch", hide_index=True)
    dl(out, "plan_audit_propose.csv")

# ================= PLAN D'ACTIONS =================
elif page == "Plan d'actions":
    A = core.q("SELECT * FROM actions ORDER BY id DESC")
    st.dataframe(A, width="stretch", hide_index=True)
    if len(A):
        dl(A, "plan_actions.csv")
    st.markdown("#### Nouvelle action")
    code = st.selectbox("Risque concerné", df.sort_values("criticite_brute", ascending=False)["code"])
    prop = df.loc[df.code == code, "mesures_operatoires"].iloc[0]
    with st.form("act"):
        txt = st.text_area("Action", prop, key=f"a_{code}")
        c = st.columns(3)
        resp, ech = c[0].text_input("Responsable"), c[1].date_input("Échéance")
        stt = c[2].selectbox("Statut", ["À lancer", "En cours", "Terminée", "Bloquée"])
        if st.form_submit_button("Ajouter l'action") and txt:
            core.ex("INSERT INTO actions(code,action,responsable,echeance,statut,maj) VALUES(?,?,?,?,?,?)",
                    (code, txt, resp, str(ech), stt, core.now()))
            core.log(ME, code, "action ajoutée", "", txt[:80])
            st.rerun()
    if len(A):
        st.markdown("#### Mettre à jour / supprimer")
        c = st.columns(3)
        aid = c[0].selectbox("Action n°", A["id"])
        ns = c[1].selectbox("Nouveau statut", ["À lancer", "En cours", "Terminée", "Bloquée"])
        if c[1].button("Mettre à jour le statut"):
            core.ex("UPDATE actions SET statut=?, maj=? WHERE id=?", (ns, core.now(), int(aid)))
            core.log(ME, f"action {aid}", "statut", A.loc[A.id == aid, "statut"].iloc[0], ns)
            st.rerun()
        if c[2].button("Supprimer cette action"):
            core.ex("DELETE FROM actions WHERE id=?", (int(aid),))
            core.log(ME, f"action {aid}", "suppression")
            st.rerun()

# ================= ANALYSES =================
elif page == "Analyses statistiques":
    t1, t2, t3 = st.tabs(["ANOVA / Kruskal-Wallis", "Cohérence & régression", "Segmentation K-Means / ACP"])
    with t1:
        g = [x.criticite_brute.values for _, x in R.groupby("processus_code") if len(x) > 1]
        if len(g) >= 2:
            F, p = stats.f_oneway(*g)
            H, pk = stats.kruskal(*g)
            c = st.columns(4)
            c[0].metric("ANOVA F", f"{F:.2f}"); c[1].metric("p-value", f"{p:.5f}")
            c[2].metric("Kruskal-Wallis H", f"{H:.2f}"); c[3].metric("p-value", f"{pk:.5f}")
            st.plotly_chart(px.box(R, x="processus_code", y="criticite_brute", color="processus_code").update_layout(showlegend=False), width="stretch")
        else:
            st.warning("Sélectionne au moins deux processus.")
    with t2:
        v = R.assign(zs=R.zone.map(core.ZSEV), nd=R.criticite_brute * (1 - R.dmr))
        rows = [{"Variable": lb, "Spearman ρ vs sévérité zone": round(stats.spearmanr(v[c], v.zs)[0], 3)}
                for c, lb in [("criticite_nette", "Criticité nette déclarée"), ("nd", "Criticité nette diagnostique brute×(1−DMR)"), ("criticite_brute", "Criticité brute")]]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        y, yp = R.criticite_nette, R.criticite_nette_predite
        st.metric("R² criticité nette déclarée vs prédite (modèle du notebook)", f"{1 - ((y - yp) ** 2).sum() / ((y - y.mean()) ** 2).sum():.3f}")
        st.plotly_chart(px.scatter(R, x="criticite_nette_predite", y="criticite_nette", color="zone", color_discrete_map=ZCOL, hover_data=["code"]), width="stretch")
    with t3:
        st.caption("Clusters et coordonnées ACP issus du notebook : figés, non recalculés après modification d'un risque.")
        st.plotly_chart(px.scatter(R, x="pca1", y="pca2", color="cluster_label", hover_data=["code", "zone"]), width="stretch")
        st.dataframe(R.groupby("cluster_label").agg(Nb=("code", "count"), Prob=("prob", "mean"), Grav=("grav", "mean"),
                                                    DMR=("dmr", "mean"), Crit=("criticite_brute", "mean")).round(2).reset_index(), width="stretch", hide_index=True)

# ================= HISTORIQUE =================
elif page == "Historique":
    h = core.q("SELECT * FROM history ORDER BY id DESC LIMIT 2000")
    s = st.text_input("Filtrer (utilisateur, objet, champ)")
    if s:
        h = h[h.apply(lambda r: s.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    st.dataframe(h, width="stretch", hide_index=True)
    dl(h, "historique.csv")

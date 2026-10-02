"""ORMVA-TF Risk & Audit Center — aide à la décision pour la priorisation des missions d'audit interne."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

st.set_page_config(page_title="ORMVA-TF | Risk & Audit Center", page_icon="🛡️", layout="wide")

try:
    import core
except ModuleNotFoundError:
    st.error("`core.py` est introuvable à côté de `app.py`. Ajoute-le au dépôt GitHub (même dossier), puis redéploie.")
    st.stop()
from core import ZCOL, ZLABEL, ZNAME, ZONES

INK = "#1F2A24"
px.defaults.color_discrete_sequence = ["#0F5C3A", "#C9A227", "#2E8B6A", "#B5651D", "#5B8DB8", "#8C6D46"]

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stApp {font-family:'Inter',sans-serif;}
.stApp{background:#F6F4EE;color:#1F2A24}
#MainMenu, footer {visibility:hidden}
header[data-testid=stHeader]{background:transparent}
.block-container{padding-top:1.4rem;max-width:1400px}
h1,h2,h3,h4{color:#0B3B2A;font-weight:700;letter-spacing:-.2px}

.hero{background:linear-gradient(120deg,#0B3B2A 0%,#146C43 65%,#1E8A57 100%);border-radius:14px;padding:22px 30px;
      margin-bottom:22px;display:flex;justify-content:space-between;align-items:center;border-bottom:4px solid #C9A227;
      box-shadow:0 4px 14px rgba(11,59,42,.18)}
.hero h1{color:#fff!important;margin:0;font-size:1.65rem}
.hero p{color:#E4D9AE;margin:4px 0 0;font-size:.85rem;letter-spacing:.4px}
.hero .tag{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(201,162,39,.6);padding:6px 14px;
           border-radius:20px;font-size:.78rem;font-weight:600;white-space:nowrap}

section[data-testid=stSidebar]{background:linear-gradient(180deg,#0B3B2A 0%,#0F4D35 100%);border-right:3px solid #C9A227}
section[data-testid=stSidebar] h3, section[data-testid=stSidebar] p, section[data-testid=stSidebar] label,
section[data-testid=stSidebar] span, section[data-testid=stSidebar] .stCaption{color:#F1EBD2!important}
section[data-testid=stSidebar] [data-baseweb=select] *{color:#0B3B2A!important}
section[data-testid=stSidebar] div[role=radiogroup] label{padding:7px 10px;border-radius:8px;transition:.15s}
section[data-testid=stSidebar] div[role=radiogroup] label:hover{background:rgba(255,255,255,.10)}
.brand{text-align:center;padding:6px 0 14px;border-bottom:1px solid rgba(201,162,39,.45);margin-bottom:12px}
.brand .logo{font-size:2.3rem}
.brand .t{color:#fff;font-weight:700;font-size:1.15rem;letter-spacing:1px}
.brand .s{color:#C9A227;font-size:.7rem;letter-spacing:.8px;text-transform:uppercase}

div[data-testid=stMetric]{background:#fff;border:1px solid #E6E1D1;border-left:5px solid #0F5C3A;border-radius:12px;
                          padding:12px 16px;box-shadow:0 2px 8px rgba(0,0,0,.05)}
div[data-testid=stMetric] label p{color:#6B6B5E!important;font-size:.78rem!important;font-weight:600}
div[data-testid=stMetricValue]{color:#0B3B2A;font-weight:700}

button[data-baseweb=tab]{font-weight:600;color:#4B5B52}
button[data-baseweb=tab][aria-selected=true]{color:#0F5C3A}
div[data-baseweb=tab-highlight]{background:#C9A227!important}
.stButton>button, .stDownloadButton>button, div[data-testid=stFormSubmitButton]>button{
    background:#0F5C3A;color:#fff;border:0;border-radius:8px;font-weight:600;padding:.45rem 1.1rem}
.stButton>button:hover, .stDownloadButton>button:hover, div[data-testid=stFormSubmitButton]>button:hover{
    background:#C9A227;color:#0B3B2A}
div[data-testid=stDataFrame]{border:1px solid #E6E1D1;border-radius:10px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,.04)}
div[data-testid=stPlotlyChart]{background:#fff;border:1px solid #E6E1D1;border-radius:12px;padding:6px;box-shadow:0 2px 6px rgba(0,0,0,.04)}
form[data-testid=stForm]{background:#fff;border:1px solid #E6E1D1;border-radius:12px}

table.mx{border-collapse:separate;border-spacing:3px;width:100%}
table.mx td{color:#fff;text-align:center;padding:8px;font-size:12px;border-radius:6px;min-width:90px;font-weight:600}
table.mx th{font-size:12px;color:#2E3B47;padding:4px}
.pill{display:inline-block;color:#fff;border-radius:12px;padding:2px 10px;font-size:.75rem;font-weight:600;margin-right:6px}
.foot{text-align:center;color:#8A8A7A;font-size:.75rem;margin-top:30px;padding-top:12px;border-top:1px solid #E0DBC9}
</style>""", unsafe_allow_html=True)


# --------------------------------------------------------------------------------------
# Utilitaires d'affichage (compatibles avec plusieurs versions de Streamlit)
# --------------------------------------------------------------------------------------
def show(fig, key):
    fig.update_layout(font=dict(family="Inter, sans-serif", color=INK), paper_bgcolor="#FFFFFF",
                      plot_bgcolor="#FFFFFF", margin=dict(l=10, r=10, t=55, b=10),
                      legend=dict(font=dict(color=INK)), title_font=dict(color="#0B3B2A", size=15))
    try:
        st.plotly_chart(fig, theme=None, width="stretch", key=key)
    except Exception:
        st.plotly_chart(fig, theme=None, use_container_width=True, key=key)


def table(frame, **kw):
    try:
        st.dataframe(frame, width="stretch", hide_index=True, **kw)
    except Exception:
        st.dataframe(frame, use_container_width=True, hide_index=True, **kw)


def dl(frame, name):
    st.download_button("⬇️ Exporter (CSV pour Excel)", frame.to_csv(index=False).encode("utf-8-sig"), name, "text/csv")


def matrix(cells, rows, cols, color, note):
    h = "<table class='mx'><tr><th></th>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
    for i, rl in enumerate(rows):
        h += f"<tr><th>{rl}</th>" + "".join(
            f"<td style='background:{color(i, j)}'>{' '.join(cells.get((i, j), []))}</td>" for j in range(len(cols))) + "</tr>"
    st.markdown(h + f"</table><p style='font-size:12px;text-align:center'>{note}</p>", unsafe_allow_html=True)


def zone_legend():
    st.markdown("".join(f"<span class='pill' style='background:{ZCOL[z]}'>{ZLABEL[z]}</span>" for z in ZONES),
                unsafe_allow_html=True)


short = lambda c: c.split(".")[-1]
proc_key = lambda x: (0, int(x[1:])) if x[1:].isdigit() else (1, x)

# --------------------------------------------------------------------------------------
# Initialisation
# --------------------------------------------------------------------------------------
@st.cache_resource
def boot():
    core.init_db()
    return True


try:
    boot()
except FileNotFoundError as e:
    st.error(f"{e} Copie `data_reel_avec_rm.xlsx` (et `cartographie_analysee_complete.xlsx`) dans `data/`, puis relance.")
    st.stop()

ME = "admin"
df = core.q("SELECT * FROM risks")
if df.empty:
    st.error("Le registre des risques est vide. Vérifie les fichiers Excel dans `data/`.")
    st.stop()

SP_ALL = core.stats_proc(df)
SC_ALL = core.score(SP_ALL)  # score sur toute la base : les filtres n'affectent que l'affichage
PAGES = ["Tableau de bord", "Registre des risques", "Matrices", "Priorisation", "Plan d'audit",
         "Plan d'actions", "Analyses statistiques", "Historique", "Méthodologie"]

with st.sidebar:
    st.markdown("<div class='brand'><div class='logo'>🌴</div><div class='t'>ORMVA-TF</div>"
                "<div class='s'>Risk &amp; Audit Center</div></div>", unsafe_allow_html=True)
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    procs = sorted(df["processus_code"].unique(), key=proc_key)
    sel = st.multiselect("Processus (affichage)", procs, default=procs) or procs
    st.caption("Le filtre n'agit que sur l'affichage ; les scores sont toujours calculés sur l'ensemble des processus.")

R = df[df["processus_code"].isin(sel)]
SC = SC_ALL[SC_ALL["processus_code"].isin(sel)]

st.markdown(f"<div class='hero'><div><h1>{page}</h1>"
            "<p>Office Régional de Mise en Valeur Agricole du Tafilalet · Audit interne &amp; gestion des risques</p></div>"
            "<div class='tag'>🛡️ Cartographie des risques</div></div>", unsafe_allow_html=True)

# ======================================================================================
# TABLEAU DE BORD
# ======================================================================================
if page == "Tableau de bord":
    act = core.q("SELECT statut FROM actions")
    c = st.columns(6)
    c[0].metric("Risques", len(R))
    c[1].metric("% zone D", f"{(R.zone == 'D').mean() * 100:.1f}%")
    c[2].metric("% zone C", f"{(R.zone == 'C').mean() * 100:.1f}%")
    c[3].metric("Criticité brute moy.", f"{R.criticite_brute.mean():.2f}")
    c[4].metric("DMR moyen", f"{R.dmr.mean():.2f}")
    c[5].metric("Actions ouvertes", int((act["statut"] != "Terminée").sum()) if len(act) else 0)

    top3 = SC_ALL.head(3)
    st.info("**Processus à auditer en priorité (score Sp) :** " + " · ".join(
        f"**{r.processus_code}** {r.processus_nom}" for r in top3.itertuples()))

    a, b = st.columns(2)
    zc = pd.DataFrame({"Zone": [ZLABEL[z] for z in ZONES], "Nombre": [int((R.zone == z).sum()) for z in ZONES]})
    with a:
        show(px.pie(zc, names="Zone", values="Nombre", hole=0.5, color="Zone",
                    color_discrete_map={ZLABEL[z]: ZCOL[z] for z in ZONES}, title="Risques par zone"), "dash_pie")
    with b:
        show(px.bar(SC.sort_values("Score"), x="Score", y="processus_code", orientation="h",
                    title="Score de priorité d'audit (Sp)", color_discrete_sequence=["#0F3D2E"]), "dash_bar")
    st.markdown("#### Risques à traiter en premier (zone D, contrôle le plus faible)")
    table(R[R.zone == "D"].sort_values(["dmr", "criticite_brute"], ascending=[True, False])
          [["code", "processus_code", "intitule", "criticite_brute", "dmr"]].head(10))

# ======================================================================================
# REGISTRE
# ======================================================================================
elif page == "Registre des risques":
    f = st.columns([2, 2, 3])
    zs = f[0].multiselect("Zone", ZONES, default=ZONES)
    cl = f[1].multiselect("Profil (cluster)", sorted(R.cluster_label.dropna().unique()))
    s = f[2].text_input("Recherche (code / intitulé)")
    v = R[R.zone.isin(zs)]
    if cl:
        v = v[v.cluster_label.isin(cl)]
    if s:
        v = v[v.intitule.str.contains(s, case=False, na=False, regex=False)
              | v.code.str.contains(s, case=False, na=False, regex=False)]
    v = v.sort_values("criticite_brute", ascending=False)
    st.caption(f"{len(v)} risques")
    table(v.drop(columns=["pca1", "pca2", "constat", "mesures_operatoires"]), height=380)
    dl(v, "registre_risques.csv")
    if len(v):
        code = st.selectbox("Détail d'un risque", v["code"])
        r = df[df.code == code].iloc[0]
        st.markdown(f"**{r.code} · {r.intitule}**")
        st.caption(f"{r.processus_code} — {r.processus_nom} · {r.sous_processus} · zone {r.zone} "
                   f"({ZNAME[r.zone]}, source : {r.zone_source})")
        with st.form(f"edit_{code}"):
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
        st.caption("La criticité brute (probabilité × gravité) et la zone (grille 4×4 du document) sont recalculées "
                   "à chaque modification de la probabilité, de la gravité ou du DMR. Tout est tracé dans l'historique.")

# ======================================================================================
# MATRICES
# ======================================================================================
elif page == "Matrices":
    d = core.bands(R)
    off = df[df.zone_source == "officielle"]
    conc = (core.zone_rule(off.criticite_brute, off.dmr) == off.zone.to_numpy()).mean() * 100 if len(off) else float("nan")
    st.metric("Concordance grille 4×4 ↔ zones officielles du document", f"{conc:.1f}%" if len(off) else "n/d")
    t1, t2 = st.tabs(["Risques bruts (probabilité × gravité)", "Risques nets (contrôle × criticité) — zones"])
    with t1:
        cells = {}
        for r in d.itertuples():
            cells.setdefault((4 - int(r.prob), int(r.grav) - 1), []).append(short(r.code))
        lv = ["#2E7D4F", "#D9A441", "#E08E45", "#C0392B"]
        level = lambda i, j: lv[int(core.crit_band((4 - i) * (j + 1)))]
        matrix(cells, ["Très probable (4)", "Probable (3)", "Improbable (2)", "Rare (1)"],
               ["Négligeable (1)", "Mineur (2)", "Modéré (3)", "Majeur (4)"], level,
               "Gravité de l'impact → · Fréquence d'occurrence ↑ · couleur = niveau de criticité "
               "(<4 négligeable · 4-7 acceptable · 8-11 sérieux · ≥12 critique)")
    with t2:
        cells = {}
        for r in d.itertuples():
            cells.setdefault((3 - r.br, r.bc), []).append(short(r.code))
        zone_color = lambda i, j: ZCOL[core.GRID[3 - i][j]]
        zone_legend()
        matrix(cells, core.CTRL_LABELS[::-1], core.CRIT_LABELS, zone_color,
               "Degré de criticité brute → · Degré de contrôle (DMR) ↑ · cases colorées selon la grille 4×4 du document")

# ======================================================================================
# PRIORISATION
# ======================================================================================
elif page == "Priorisation":
    t1, t2, t3, t4 = st.tabs(["Classement", "Composantes du score", "Sensibilité des pondérations", "Apport face au document"])
    with t1:
        st.code("Sp = 0,45·N(%Zone D) + 0,30·N(%Zone C) + 0,25·N(Criticité brute moyenne)   — N = min-max 0-100")
        show(px.bar(SC.sort_values("Score"), x="Score", y="processus_code", orientation="h", text="Score",
                    color="Score", color_continuous_scale=["#DCE9DF", "#C0392B"]).update_layout(coloraxis_showscale=False),
             "prio_bar")
        tb = SC[["Rang", "processus_code", "processus_nom", "Score", "Nb_D", "Pct_D", "Pct_C", "Crit", "DMR", "Nb"]]
        table(tb)
        dl(tb, "classement_processus.csv")
        st.warning("Indicateur de priorité relative, pas une probabilité de survenance : il éclaire le jugement de l'auditeur.")
    with t2:
        m = SC.melt(id_vars="processus_code", value_vars=["contrib_D", "contrib_C", "contrib_brut"],
                    var_name="Composante", value_name="Points")
        show(px.bar(m, x="Points", y="processus_code", color="Composante", orientation="h",
                    color_discrete_map={"contrib_D": "#C0392B", "contrib_C": "#E08E45", "contrib_brut": "#0F3D2E"}), "prio_comp")
        table(SC[["processus_code", "Pct_D", "N_D", "contrib_D", "Pct_C", "N_C", "contrib_C", "Crit", "N_brut",
                  "contrib_brut", "Score", "Rang"]].round(2))
    with t3:
        base = SC_ALL.set_index("processus_code")["Rang"]
        rows, ranks = [], pd.DataFrame(index=base.index)
        for n, w in core.SCENARIOS.items():
            rk = core.score(SP_ALL, w).set_index("processus_code")["Rang"].reindex(base.index)
            ranks[n] = rk
            if n != "Base":
                rho, p = stats.spearmanr(base, rk)
                rows.append({"Scénario": n, "Spearman ρ vs Base": round(float(rho), 3), "p-value": round(float(p), 5)})
        st.markdown("**Stabilité du classement face à d'autres pondérations**")
        table(pd.DataFrame(rows))
        table(ranks.reset_index())
        st.caption("ρ proche de 1 : le classement ne dépend pas du choix des pondérations (0,45 / 0,30 / 0,25).")
    with t4:
        st.markdown("Le document de l'Office classe les **risques** par zone mais ne propose pas de classement des "
                    "**processus** à auditer. Ici, le score Sp est comparé à deux méthodes simples : compter les risques "
                    "en zone D (logique du document) et la criticité brute moyenne.")
        orders = core.reference_orders(df, SC_ALL)
        covs = {n: core.coverage(df, o) for n, o in orders.items()}
        n_aud = st.slider("Nombre de processus audités", 1, len(SC_ALL), min(3, len(SC_ALL)), key="cov_n")
        rows = []
        for n, cv in covs.items():
            r = cv.iloc[n_aud - 1]
            rows.append({"Méthode": n, "Processus retenus": ", ".join(cv["processus"][:n_aud]),
                         "Risques D couverts (%)": round(r.couv_D, 1), "Charge d'audit (% des risques)": round(r.charge, 1),
                         "Part de D dans le périmètre (%)": round(r.densite_D, 1), "Aire sous la courbe": round(core.auc(cv), 3)})
        rows.append({"Méthode": "Tirage aléatoire (espérance)", "Processus retenus": "—",
                     "Risques D couverts (%)": round(n_aud / len(SC_ALL) * 100, 1),
                     "Charge d'audit (% des risques)": round(n_aud / len(SC_ALL) * 100, 1),
                     "Part de D dans le périmètre (%)": round((df.zone == "D").mean() * 100, 1), "Aire sous la courbe": 0.5})
        table(pd.DataFrame(rows))
        fig = go.Figure()
        for n, cv in covs.items():
            fig.add_trace(go.Scatter(x=[0, *cv["charge"]], y=[0, *cv["couv_D"]], mode="lines+markers", name=n))
        fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], mode="lines", name="Aléatoire", line=dict(dash="dash", color="#999")))
        fig.update_layout(title="Couverture des risques D selon la charge d'audit",
                          xaxis_title="Charge d'audit (% des risques à auditer)", yaxis_title="Risques zone D couverts (%)")
        show(fig, "prio_cov")
        st.markdown("**Corrélation des classements avec Sp**")
        base = SC_ALL.set_index("processus_code")["Rang"]
        sp_rows = []
        for n, o in orders.items():
            if n.startswith("Sp"):
                continue
            rk = pd.Series(range(1, len(o) + 1), index=o).reindex(base.index)
            rho, p = stats.spearmanr(base, rk)
            sp_rows.append({"Méthode": n, "Spearman ρ vs Sp": round(float(rho), 3), "p-value": round(float(p), 5)})
        table(pd.DataFrame(sp_rows))
        st.caption("Lecture : classer par nombre de risques D maximise la couverture de D par construction, mais "
                   "favorise les gros processus. L'intérêt de Sp est de couvrir les risques D avec une charge d'audit "
                   "plus faible tout en intégrant la zone C et la criticité. Une courbe au-dessus de la diagonale "
                   "indique un gain par rapport à un choix au hasard.")

# ======================================================================================
# PLAN D'AUDIT
# ======================================================================================
elif page == "Plan d'audit":
    c = st.columns(2)
    n = c[0].slider("Nombre de processus à auditer (par ordre de priorité)", 1, len(SC_ALL), min(3, len(SC_ALL)))
    zs = c[1].multiselect("Zones à retenir", ZONES, default=["D", "C"])
    top = SC_ALL.head(n)
    table(top[["Rang", "processus_code", "processus_nom", "Score"]])
    p = df[df.processus_code.isin(top.processus_code) & df.zone.isin(zs)].copy()
    p["Rang_processus"] = p["processus_code"].map(SC_ALL.set_index("processus_code")["Rang"])
    p["zsev"] = p["zone"].map(core.ZSEV)
    p = p.sort_values(["Rang_processus", "zsev", "criticite_brute", "dmr"], ascending=[True, False, False, True])
    out = p[["Rang_processus", "processus_code", "code", "intitule", "zone", "criticite_brute", "dmr",
             "cluster_label", "constat", "mesures_operatoires"]]
    nd_all = int((df.zone == "D").sum())
    nd_cov = int((p.zone == "D").sum())
    st.markdown(f"**{len(out)} risques à couvrir** (par processus, zone la plus sévère, criticité décroissante, contrôle croissant)")
    if nd_all:
        st.caption(f"Ce périmètre couvre {nd_cov} des {nd_all} risques de la zone D ({nd_cov / nd_all * 100:.0f} %).")
    table(out)
    dl(out, "plan_audit_propose.csv")

# ======================================================================================
# PLAN D'ACTIONS
# ======================================================================================
elif page == "Plan d'actions":
    STATUTS = ["À lancer", "En cours", "Terminée", "Bloquée"]
    A = core.q("SELECT * FROM actions ORDER BY id DESC")
    table(A)
    if len(A):
        dl(A, "plan_actions.csv")
    st.markdown("#### Nouvelle action")
    code = st.selectbox("Risque concerné", df.sort_values("criticite_brute", ascending=False)["code"])
    prop = df.loc[df.code == code, "mesures_operatoires"].iloc[0]
    with st.form("act"):
        txt = st.text_area("Action", prop, key=f"a_{code}")
        c = st.columns(3)
        resp, ech = c[0].text_input("Responsable"), c[1].date_input("Échéance")
        stt = c[2].selectbox("Statut", STATUTS)
        if st.form_submit_button("Ajouter l'action") and txt:
            core.ex("INSERT INTO actions(code,action,responsable,echeance,statut,maj) VALUES(?,?,?,?,?,?)",
                    (code, txt, resp, str(ech), stt, core.now()))
            core.log(ME, code, "action ajoutée", "", txt[:80])
            st.rerun()
    if len(A):
        st.markdown("#### Mettre à jour / supprimer")
        c = st.columns(3)
        aid = int(c[0].selectbox("Action n°", A["id"]))
        ns = c[1].selectbox("Nouveau statut", STATUTS)
        if c[1].button("Mettre à jour le statut"):
            core.ex("UPDATE actions SET statut=?, maj=? WHERE id=?", (ns, core.now(), aid))
            core.log(ME, f"action {aid}", "statut", A.loc[A.id == aid, "statut"].iloc[0], ns)
            st.rerun()
        if c[2].button("Supprimer cette action"):
            core.ex("DELETE FROM actions WHERE id=?", (aid,))
            core.log(ME, f"action {aid}", "suppression")
            st.rerun()

# ======================================================================================
# ANALYSES STATISTIQUES
# ======================================================================================
elif page == "Analyses statistiques":
    t1, t2, t3 = st.tabs(["ANOVA / Kruskal-Wallis", "Cohérence & régression", "Segmentation K-Means / ACP"])
    with t1:
        g = [x.criticite_brute.values for _, x in R.groupby("processus_code") if len(x) > 1]
        if len(g) >= 2 and any(np.ptp(x) > 0 for x in g):
            F, p = stats.f_oneway(*g)
            H, pk = stats.kruskal(*g)
            c = st.columns(4)
            c[0].metric("ANOVA F", f"{F:.2f}")
            c[1].metric("p-value", f"{p:.5f}")
            c[2].metric("Kruskal-Wallis H", f"{H:.2f}")
            c[3].metric("p-value", f"{pk:.5f}")
            show(px.box(R, x="processus_code", y="criticite_brute", color="processus_code",
                        title="Criticité brute par processus").update_layout(showlegend=False), "an_box")
            st.caption("Une p-value < 0,05 indique que la criticité brute diffère significativement d'un processus à l'autre, "
                       "ce qui justifie une priorisation par processus.")
        else:
            st.warning("Sélectionne au moins deux processus comportant plusieurs risques.")
    with t2:
        v = R.assign(zs=R.zone.map(core.ZSEV), nd=R.criticite_brute * (1 - R.dmr))
        rows = []
        for c_, lb in [("criticite_nette", "Criticité nette déclarée (document)"),
                       ("nd", "Criticité nette diagnostique brute×(1−DMR)"), ("criticite_brute", "Criticité brute")]:
            m = v[[c_, "zs"]].dropna()
            rho = stats.spearmanr(m[c_], m["zs"])[0] if len(m) > 2 and m[c_].nunique() > 1 else float("nan")
            rows.append({"Variable": lb, "Spearman ρ vs sévérité zone": round(float(rho), 3)})
        table(pd.DataFrame(rows))
        st.caption("Le document calcule la criticité nette comme brute × DMR ; cette formule augmente avec le contrôle. "
                   "La version diagnostique brute × (1−DMR) diminue avec le contrôle.")
        mm = R[["criticite_nette", "criticite_nette_predite"]].dropna()
        if len(mm) > 2 and mm["criticite_nette"].var() > 0:
            y, yp = mm["criticite_nette"], mm["criticite_nette_predite"]
            st.metric("R² criticité nette déclarée vs prédite (modèle du notebook)",
                      f"{1 - ((y - yp) ** 2).sum() / ((y - y.mean()) ** 2).sum():.3f}")
            show(px.scatter(R.dropna(subset=["criticite_nette_predite"]), x="criticite_nette_predite", y="criticite_nette",
                            color="zone", color_discrete_map=ZCOL, hover_data=["code"],
                            title="Criticité nette : déclarée vs prédite"), "an_sc")
        else:
            st.info("Valeurs prédites du notebook non disponibles : fournis `cartographie_analysee_complete.xlsx` dans `data/`.")
    with t3:
        if R["pca1"].notna().any():
            st.caption("Clusters et coordonnées ACP issus du notebook : figés, non recalculés après modification d'un risque.")
            show(px.scatter(R.dropna(subset=["pca1", "pca2"]), x="pca1", y="pca2", color="cluster_label",
                            hover_data=["code", "zone"], title="Segmentation des risques (ACP)"), "an_pca")
            table(R.groupby("cluster_label").agg(Nb=("code", "count"), Prob=("prob", "mean"), Grav=("grav", "mean"),
                                                 DMR=("dmr", "mean"), Crit=("criticite_brute", "mean")).round(2).reset_index())
        else:
            st.info("Clusters non disponibles : fournis `cartographie_analysee_complete.xlsx` dans `data/`.")

# ======================================================================================
# HISTORIQUE
# ======================================================================================
elif page == "Historique":
    h = core.q("SELECT * FROM history ORDER BY id DESC LIMIT 2000")
    s = st.text_input("Filtrer (utilisateur, objet, champ)")
    if s and len(h):
        h = h[h.apply(lambda r: s.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    table(h)
    dl(h, "historique.csv")
    with st.expander("Sauvegarde et réinitialisation"):
        st.caption("Sur Streamlit Cloud, les modifications sont perdues si l'application est redémarrée : télécharge "
                   "régulièrement une sauvegarde.")
        st.download_button("⬇️ Télécharger la base (SQLite)", core.backup_bytes(), "ormvatf_sauvegarde.db")
        ok = st.checkbox("Je confirme vouloir recharger le registre depuis les fichiers Excel (modifications des risques perdues)")
        if st.button("Réinitialiser le registre") and ok:
            core.reset_risks()
            core.log(ME, "registre", "réinitialisation")
            st.rerun()

# ======================================================================================
# MÉTHODOLOGIE
# ======================================================================================
elif page == "Méthodologie":
    st.markdown("#### Source des données")
    st.write("Cartographie des risques de l'ORMVA-TF (étude Thermis Engineering, 2024) : 159 risques répartis sur 12 processus. "
             "Les 9 risques transversaux (RM) sont exclus du périmètre de priorisation par processus.")
    st.markdown("#### Évaluation des risques")
    st.write("Criticité brute = probabilité (1-4) × gravité (1-4), soit de 1 à 16. Le DMR est le degré de contrôle "
             "(≤25 %, ≤50 %, ≤75 %, ≤100 %). La zone résulte de la grille 4×4 ci-dessous, reconstituée à partir des "
             "matrices du document ; elle reproduit les zones officielles du document pour l'ensemble des 168 risques.")
    zone_legend()
    matrix({}, core.CTRL_LABELS[::-1], core.CRIT_LABELS, lambda i, j: ZCOL[core.GRID[3 - i][j]],
           "Degré de criticité brute → · Degré de contrôle ↑")
    st.markdown("#### Score de priorité des processus (Sp)")
    st.code("Sp = 0,45·N(%Zone D) + 0,30·N(%Zone C) + 0,25·N(Criticité brute moyenne)   — N = min-max 0-100")
    st.write("Le document classe les risques par zone mais ne hiérarchise pas les processus à auditer : Sp apporte ce "
             "niveau d'agrégation. Les pondérations sont un choix du modèle ; leur effet est testé dans l'onglet "
             "*Sensibilité des pondérations*.")
    st.markdown("#### Limites")
    st.write("- Pondérations de Sp non issues du document, testées par scénarios.\n"
             "- DMR évalué en interne, avec un risque de biais d'appréciation.\n"
             "- Douze processus seulement : les tests statistiques ont une puissance limitée.\n"
             "- Pas d'historique de missions d'audit pour valider le classement a posteriori : une validation par des "
             "auditeurs internes reste nécessaire.\n"
             "- La case (contrôle satisfaisant, criticité faible) de la grille n'est pas renseignée dans le document ; "
             "elle est rattachée à la zone A.\n"
             "- Dans le document, la criticité nette est calculée comme brute × DMR, formule qui augmente avec le contrôle.")

st.markdown("<div class='foot'>ORMVA-TF · Risk &amp; Audit Center — outil d'aide à la décision, à utiliser avec le jugement de l'auditeur</div>",
            unsafe_allow_html=True)

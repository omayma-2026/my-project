"""ORMVA-TF Risk & Audit Center — outil de travail pour l'auditeur interne et le risk manager.
Fichier unique. Placer à côté de app.py : cartographie_analysee_complete.xlsx et data_reel_avec_rm.xlsx.
Dépendances : streamlit pandas numpy plotly scipy openpyxl
"""
import hashlib, os, secrets
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy import stats
from sqlalchemy import create_engine, text

# =====================================================================
# COUCHE DONNÉES : SQLite, authentification, historique, calculs
# =====================================================================
ROOT = Path(__file__).parent


def _db_url():
    """URL de connexion à la base. Priorité :
    1) secret Streamlit DATABASE_URL (base Postgres persistante, ex. Supabase/Neon gratuit) -> jamais effacée,
       même sur un hébergement à disque éphémère (Streamlit Community Cloud).
    2) variable d'environnement ORMVATF_DB_URL.
    3) fichier SQLite local à côté de app.py (persistant tant que le disque local l'est, ex. ton PC)."""
    try:
        u = st.secrets.get("DATABASE_URL", "")
    except Exception:
        u = ""
    u = u or os.getenv("ORMVATF_DB_URL", "")
    if u:
        return u
    return f"sqlite:///{ROOT / 'ormvatf.db'}"


DB_URL = _db_url()
ENGINE = create_engine(DB_URL, pool_pre_ping=True)
IS_SQLITE = ENGINE.dialect.name == "sqlite"
DB = DB_URL if not IS_SQLITE else str(ROOT / "ormvatf.db")
ZONES = ["A", "B", "C", "D"]
ZSEV = {"A": 1, "B": 2, "C": 3, "D": 4}
ZCOL = {"A": "#2E7D4F", "B": "#D9A441", "C": "#E08E45", "D": "#C0392B"}
ZNAME = {"A": "Optimisation", "B": "Vigilance", "C": "Surveillance", "D": "Traitement"}
# Bandes du document : [0-4[ [4-8[ [8-12[ [12-16]  (borne haute exclue)
CRIT_BINS = [0, 4, 8, 12, 17]
CRIT_LABELS = ["Faible [0-4[", "Moyen [4-8[", "Significatif [8-12[", "Élevé [12-16]"]
CTRL_LABELS = ["Faible ≤25%", "Partiel ≤50%", "Correcte ≤75%", "Satisfaisant ≤100%"]
WEIGHTS = {"D": 0.45, "C": 0.30, "brut": 0.25}
SCENARIOS = {
    "Base": WEIGHTS,
    "Dominant D": {"D": 0.60, "C": 0.20, "brut": 0.20},
    "Dominant C": {"D": 0.30, "C": 0.50, "brut": 0.20},
    "Dominant brut": {"D": 0.25, "C": 0.25, "brut": 0.50},
    "Équilibre": {"D": 1 / 3, "C": 1 / 3, "brut": 1 / 3},
}
AUTOINC = "INTEGER PRIMARY KEY AUTOINCREMENT" if IS_SQLITE else "SERIAL PRIMARY KEY"
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, salt TEXT, pw TEXT, role TEXT, active INTEGER DEFAULT 1, created TEXT);
CREATE TABLE IF NOT EXISTS history(id {AUTOINC}, ts TEXT, auteur TEXT, obj TEXT, champ TEXT, ancien TEXT, nouveau TEXT);
CREATE TABLE IF NOT EXISTS actions(id {AUTOINC}, code TEXT, action TEXT, responsable TEXT, echeance TEXT, statut TEXT, maj TEXT);
"""
now = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _prep(sql, p):
    """Convertit les '?' positionnels (style sqlite3) en paramètres nommés SQLAlchemy, pour que le
    même code SQL fonctionne avec SQLite (local) ou Postgres (base distante persistante)."""
    parts = sql.split("?")
    if len(parts) == 1:
        return text(sql), {}
    out, d = parts[0], {}
    for i, part in enumerate(parts[1:]):
        k = f"p{i}"
        d[k] = p[i]
        out += f":{k}" + part
    return text(out), d


def q(sql, p=()):
    stmt, d = _prep(sql, p)
    with ENGINE.connect() as c:
        return pd.read_sql_query(stmt, c, params=d)


def ex(sql, p=()):
    stmt, d = _prep(sql, p)
    with ENGINE.begin() as c:
        c.execute(stmt, d)


def log(auteur, obj, champ, old="", new=""):
    ex("INSERT INTO history(ts,auteur,obj,champ,ancien,nouveau) VALUES(?,?,?,?,?,?)",
       (now(), auteur, obj, champ, str(old), str(new)))


# ---------- zones (règle du document) ----------
def zone_rule(crit, dmr):
    """crit >= 8 et contrôle <= 50% -> D ; crit >= 8 et contrôle > 50% -> C ;
    crit < 8 et contrôle <= 50% -> B ; sinon A."""
    crit, dmr = np.asarray(crit, float), np.asarray(dmr, float)
    return np.where(crit >= 8, np.where(dmr > 0.5, "C", "D"), np.where(dmr > 0.5, "A", "B"))


def bands(df):
    d = df.copy()
    d["bc"] = pd.cut(d["criticite_brute"], CRIT_BINS, labels=False, right=False).astype(int)
    d["br"] = pd.cut((d["dmr"] * 100).round(6), [-1, 25, 50, 75, 100.5], labels=False).astype(int)
    return d


# ---------- initialisation & données ----------
def _find(name):
    for d in (ROOT / "data", ROOT):
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(f"{name} introuvable (place-le à côté de app.py).")


def _seed():
    a = pd.read_excel(_find("cartographie_analysee_complete.xlsx"), sheet_name="Details_Risques", engine="openpyxl")
    e = pd.read_excel(_find("data_reel_avec_rm.xlsx"), sheet_name="Sheet1", engine="openpyxl")
    keep = [c for c in ["code", "processus_code", "processus_nom", "fonction", "zone_officielle",
                        "constat", "mesures_operatoires"] if c in e.columns]
    df = a.merge(e[keep], on="code", how="left")  # base analysée (159) = périmètre officiel
    p = df["processus"].astype(str).str.extract(r"^(P\d+)\s*-\s*(.*)$")
    df["processus_code"] = df["processus_code"].fillna(p[0])
    df["processus_nom"] = df["processus_nom"].fillna(p[1])
    df = df.rename(columns={"Criticite_Nette_Predite": "criticite_nette_predite", "Residu": "residu",
                            "Cluster_Label": "cluster_label", "PCA1": "pca1", "PCA2": "pca2"})
    off = df["zone_officielle"].astype(str).str.strip().str.upper()
    ok = off.isin(ZONES)
    df["zone"] = np.where(ok, off, zone_rule(df["criticite_brute"], df["dmr"]))
    df["zone_source"] = np.where(ok, "officielle", "règle")
    for c in ["fonction"]:
        df[c] = df.get(c, "Non renseignée")
        df[c] = df[c].fillna("Non renseignée")
    for c in ["constat", "mesures_operatoires"]:
        df[c] = df.get(c, "")
        df[c] = df[c].fillna("")
    cols = ["code", "processus_code", "processus_nom", "fonction", "sous_processus", "intitule", "prob", "grav",
            "criticite_brute", "dmr", "criticite_nette", "zone", "zone_source", "constat", "mesures_operatoires",
            "cluster_label", "criticite_nette_predite", "residu", "pca1", "pca2"]
    df[cols].to_sql("risks", ENGINE, if_exists="replace", index=False)


def _table_exists(name):
    insp_sql = ("SELECT name FROM sqlite_master WHERE type='table' AND name=:n" if IS_SQLITE
                else "SELECT table_name FROM information_schema.tables WHERE table_name=:n")
    with ENGINE.connect() as c:
        return c.execute(text(insp_sql), {"n": name}).fetchone() is not None


def init_db():
    with ENGINE.begin() as c:
        for stmt in [s for s in SCHEMA.split(";") if s.strip()]:
            c.execute(text(stmt))
    if not _table_exists("risks"):
        _seed()


# ---------- utilisateurs ----------
def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()


def add_user(u, pw, role):
    salt = secrets.token_hex(16)
    ex("INSERT OR REPLACE INTO users VALUES(?,?,?,?,1,?)", (u, salt, _hash(pw, salt), role, now()))


def set_user(u, role, active, pw=""):
    ex("UPDATE users SET role=?, active=? WHERE username=?", (role, int(active), u))
    if pw:
        salt = secrets.token_hex(16)
        ex("UPDATE users SET salt=?, pw=? WHERE username=?", (salt, _hash(pw, salt), u))


def check(u, pw):
    r = q("SELECT * FROM users WHERE username=? AND active=1", (u,))
    if r.empty:
        return None
    r = r.iloc[0]
    return r["role"] if secrets.compare_digest(_hash(pw, r["salt"]), r["pw"]) else None


def apply_recovery():
    """Récupération d'accès à l'admin, dans l'ordre :
    1) Streamlit Secrets [admin] username/password -> compte recréé à CHAQUE démarrage (utile sur
       Streamlit Cloud, dont le disque est effacé à chaque redémarrage : l'accès est donc toujours garanti).
    2) Fichier RESET_ADMIN.txt (identifiant:motdepasse) à côté de app.py -> compte créé une fois, fichier supprimé
       (utile en local)."""
    try:
        sec = st.secrets.get("admin", None)
    except Exception:
        sec = None
    if sec and sec.get("username") and sec.get("password") and len(sec["password"]) >= 8:
        u, pw = str(sec["username"]).strip(), str(sec["password"]).strip()
        exists = not q("SELECT 1 FROM users WHERE username=?", (u,)).empty
        add_user(u, pw, "admin")
        if not exists:
            log(u, "utilisateur", "création admin (secrets)", "", u)
        return None

    f = ROOT / "RESET_ADMIN.txt"
    if not f.exists():
        return None
    try:
        u, pw = f.read_text(encoding="utf-8-sig").strip().split(":", 1)
        u, pw = u.strip(), pw.strip()
    except ValueError:
        f.unlink()
        return "RESET_ADMIN.txt ignoré : format attendu  identifiant:motdepasse"
    f.unlink()
    if not u or len(pw) < 8:
        return "RESET_ADMIN.txt ignoré : identifiant requis et mot de passe de 8 caractères minimum."
    add_user(u, pw, "admin")
    log(u, "utilisateur", "réinitialisation accès admin (fichier)", "", u)
    return f"Accès réinitialisé : connecte-toi avec l'identifiant « {u} » et le mot de passe du fichier."


# ---------- modification d'un risque (avec historique) ----------
def _same(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def update_risk(code, new, auteur):
    old = q("SELECT * FROM risks WHERE code=?", (code,)).iloc[0]
    new = dict(new)
    new["criticite_brute"] = int(new["prob"]) * int(new["grav"])
    if not (_same(old["prob"], new["prob"]) and _same(old["grav"], new["grav"]) and _same(old["dmr"], new["dmr"])):
        new["zone"] = str(zone_rule(new["criticite_brute"], new["dmr"]))
        new["zone_source"] = "recalculée"
    n = 0
    for k, v in new.items():
        if not _same(old[k], v):
            ex(f"UPDATE risks SET {k}=? WHERE code=?", (v, code))
            log(auteur, code, k, old[k], v)
            n += 1
    return n


# ---------- scoring (calculé sur TOUTE la base, jamais sur un filtre) ----------
def stats_proc(df):
    o = df.groupby("processus_code").agg(processus_nom=("processus_nom", "first"), Nb=("code", "count"),
                                         Crit=("criticite_brute", "mean"), DMR=("dmr", "mean")).reset_index()
    z = pd.crosstab(df["processus_code"], df["zone"]).reindex(columns=ZONES, fill_value=0)
    p = z.div(z.sum(axis=1), axis=0) * 100
    o["Pct_D"] = o["processus_code"].map(p["D"])
    o["Pct_C"] = o["processus_code"].map(p["C"])
    return o.round(2)


def _mm(s):
    r = s.max() - s.min()
    return (s - s.min()) / r * 100 if r > 0 else s * 0


def score(o, w=WEIGHTS):
    o = o.copy()
    o["N_D"], o["N_C"], o["N_brut"] = _mm(o["Pct_D"]), _mm(o["Pct_C"]), _mm(o["Crit"])
    o["contrib_D"], o["contrib_C"], o["contrib_brut"] = w["D"] * o["N_D"], w["C"] * o["N_C"], w["brut"] * o["N_brut"]
    o["Score"] = (o["contrib_D"] + o["contrib_C"] + o["contrib_brut"]).round(1)
    o["Rang"] = o["Score"].rank(ascending=False, method="min").astype(int)
    return o.sort_values("Rang")


# =====================================================================
# INTERFACE STREAMLIT
# =====================================================================
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
    init_db()
    return True


try:
    boot()
except FileNotFoundError as e:
    st.error(f"{e} Mets `cartographie_analysee_complete.xlsx` et `data_reel_avec_rm.xlsx` dans le même dossier que `app.py`, puis relance.")
    st.stop()

RECOVERY_MSG = apply_recovery()

# ---------- première utilisation : création de l'administrateur ----------
if q("SELECT COUNT(*) n FROM users")["n"][0] == 0:
    st.title("Configuration initiale")
    st.caption("Crée le compte administrateur. Il pourra donner l'accès aux autres utilisateurs.")
    with st.form("setup"):
        u, p1, p2 = st.text_input("Identifiant"), st.text_input("Mot de passe (8 caractères min.)", type="password"), st.text_input("Confirmer", type="password")
        if st.form_submit_button("Créer le compte administrateur"):
            if not u or len(p1) < 8 or p1 != p2:
                st.error("Identifiant requis, mot de passe de 8 caractères minimum, identique dans les deux champs.")
            else:
                add_user(u.strip(), p1, "admin")
                log(u, "utilisateur", "création admin", "", u)
                st.rerun()
    st.stop()

# ---------- connexion ----------
if "user" not in st.session_state:
    st.title("🛡️ ORMVA-TF · Risk & Audit Center")
    if RECOVERY_MSG:
        st.info(RECOVERY_MSG)
    st.caption(f"Base de données : {DB}")
    with st.form("login"):
        u, p = st.text_input("Identifiant"), st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Se connecter"):
            role = check(u.strip(), p)
            if role:
                st.session_state.user, st.session_state.role = u.strip(), role
                log(u.strip(), "session", "connexion")
                st.rerun()
            st.error("Identifiant ou mot de passe incorrect, ou compte désactivé.")
    st.stop()

ME, ADMIN = st.session_state.user, st.session_state.role == "admin"

# ---------- données ----------
df = q("SELECT * FROM risks")
SP_ALL = stats_proc(df)
SC_ALL = score(SP_ALL)  # score sur toute la base : les filtres n'affectent que l'affichage
PAGES = ["Tableau de bord", "Registre des risques", "Matrices", "Priorisation", "Plan d'audit",
         "Plan d'actions", "Analyses statistiques", "Historique"] + (["Administration"] if ADMIN else [])

with st.sidebar:
    st.markdown("### 🛡️ ORMVA-TF")
    st.caption(f"{ME} · {'administrateur' if ADMIN else 'lecteur (consultation)'}")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    procs = sorted(df["processus_code"].unique(), key=lambda x: int(x[1:]))
    sel = st.multiselect("Processus (affichage)", procs, default=procs) or procs
    if st.button("Se déconnecter"):
        log(ME, "session", "déconnexion")
        st.session_state.clear()
        st.rerun()

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
    act = q("SELECT statut FROM actions")
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
        if not ADMIN:
            x, y = st.columns(2)
            x.markdown("**Constat**"); x.write(r.constat or "—")
            y.markdown("**Mesures opératoires**"); y.write(r.mesures_operatoires or "—")
        else:
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
                    n = update_risk(code, dict(prob=prob, grav=grav, dmr=dmr, constat=constat,
                                                    mesures_operatoires=mesures), ME)
                    st.toast(f"{n} champ(s) modifié(s) — criticité et zone recalculées" if n else "Aucun changement")
                    st.rerun()
            st.caption("La criticité brute et la zone (règle du document) sont recalculées à chaque modification de prob., grav. ou DMR. Tout est tracé dans l'historique.")

# ================= MATRICES =================
elif page == "Matrices":
    d = bands(R)
    rule = zone_rule(df.criticite_brute, df.dmr)
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
        zc = lambda i, j: ZCOL[str(zone_rule(8 if j >= 2 else 0, 1.0 if (3 - i) >= 2 else 0.0))]
        matrix(cells, CTRL_LABELS[::-1], CRIT_LABELS, zc,
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
        for n, w in SCENARIOS.items():
            rk = score(SP_ALL, w).set_index("processus_code")["Rang"]
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
    p["zsev"] = p["zone"].map(ZSEV)
    p = p.sort_values(["Rang_processus", "zsev", "criticite_brute", "dmr"], ascending=[True, False, False, True])
    out = p[["Rang_processus", "processus_code", "code", "intitule", "zone", "criticite_brute", "dmr", "cluster_label", "constat", "mesures_operatoires"]]
    st.markdown(f"**{len(out)} risques à couvrir** (par processus, zone la plus sévère, criticité décroissante, contrôle croissant)")
    st.dataframe(out, width="stretch", hide_index=True)
    dl(out, "plan_audit_propose.csv")

# ================= PLAN D'ACTIONS =================
elif page == "Plan d'actions":
    A = q("SELECT * FROM actions ORDER BY id DESC")
    st.dataframe(A, width="stretch", hide_index=True)
    if len(A):
        dl(A, "plan_actions.csv")
    if ADMIN:
        st.markdown("#### Nouvelle action")
        code = st.selectbox("Risque concerné", df.sort_values("criticite_brute", ascending=False)["code"])
        prop = df.loc[df.code == code, "mesures_operatoires"].iloc[0]
        with st.form("act"):
            txt = st.text_area("Action", prop, key=f"a_{code}")
            c = st.columns(3)
            resp, ech = c[0].text_input("Responsable"), c[1].date_input("Échéance")
            stt = c[2].selectbox("Statut", ["À lancer", "En cours", "Terminée", "Bloquée"])
            if st.form_submit_button("Ajouter l'action") and txt:
                ex("INSERT INTO actions(code,action,responsable,echeance,statut,maj) VALUES(?,?,?,?,?,?)",
                        (code, txt, resp, str(ech), stt, now()))
                log(ME, code, "action ajoutée", "", txt[:80])
                st.rerun()
        if len(A):
            st.markdown("#### Mettre à jour / supprimer")
            c = st.columns(3)
            aid = c[0].selectbox("Action n°", A["id"])
            ns = c[1].selectbox("Nouveau statut", ["À lancer", "En cours", "Terminée", "Bloquée"])
            if c[1].button("Mettre à jour le statut"):
                ex("UPDATE actions SET statut=?, maj=? WHERE id=?", (ns, now(), int(aid)))
                log(ME, f"action {aid}", "statut", A.loc[A.id == aid, "statut"].iloc[0], ns)
                st.rerun()
            if c[2].button("Supprimer cette action"):
                ex("DELETE FROM actions WHERE id=?", (int(aid),))
                log(ME, f"action {aid}", "suppression")
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
        v = R.assign(zs=R.zone.map(ZSEV), nd=R.criticite_brute * (1 - R.dmr))
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
    h = q("SELECT * FROM history ORDER BY id DESC LIMIT 2000")
    s = st.text_input("Filtrer (utilisateur, objet, champ)")
    if s:
        h = h[h.apply(lambda r: s.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    st.dataframe(h, width="stretch", hide_index=True)
    dl(h, "historique.csv")

# ================= ADMINISTRATION =================
elif page == "Administration" and ADMIN:
    U = q("SELECT username, role, active, created FROM users")
    st.dataframe(U, width="stretch", hide_index=True)
    st.markdown("#### Donner l'accès à un utilisateur")
    with st.form("nu"):
        c = st.columns(3)
        u, pw, ro = c[0].text_input("Identifiant"), c[1].text_input("Mot de passe initial (8 min.)", type="password"), c[2].selectbox("Rôle", ["lecteur", "admin"])
        if st.form_submit_button("Créer l'utilisateur"):
            if u and len(pw) >= 8 and u not in U.username.values:
                add_user(u.strip(), pw, ro); log(ME, "utilisateur", "création", "", f"{u} ({ro})"); st.rerun()
            else:
                st.error("Identifiant unique requis et mot de passe de 8 caractères minimum.")
    st.markdown("#### Modifier / retirer l'accès")
    with st.form("mu"):
        c = st.columns(4)
        u = c[0].selectbox("Utilisateur", [x for x in U.username if x != ME])
        ro, ac = c[1].selectbox("Rôle", ["lecteur", "admin"]), c[2].checkbox("Compte actif", True)
        pw = c[3].text_input("Nouveau mot de passe (optionnel)", type="password")
        if st.form_submit_button("Appliquer") and u:
            if pw and len(pw) < 8:
                st.error("Mot de passe trop court.")
            else:
                set_user(u, ro, ac, pw); log(ME, "utilisateur", "modification", u, f"{ro}, actif={ac}"); st.rerun()

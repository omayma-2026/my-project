"""Couche données : SQLite, authentification, historique, calculs (score, zones, matrices)."""
import hashlib, os, secrets, sqlite3
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DB = Path(os.getenv("ORMVATF_DB", ROOT / "ormvatf.db"))
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
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, salt TEXT, pw TEXT, role TEXT, active INTEGER DEFAULT 1, created TEXT);
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, auteur TEXT, obj TEXT, champ TEXT, ancien TEXT, nouveau TEXT);
CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, action TEXT, responsable TEXT, echeance TEXT, statut TEXT, maj TEXT);
"""
now = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def q(sql, p=()):
    c = sqlite3.connect(DB)
    try:
        return pd.read_sql_query(sql, c, params=p)
    finally:
        c.close()


def ex(sql, p=()):
    c = sqlite3.connect(DB)
    try:
        c.execute(sql, p)
        c.commit()
    finally:
        c.close()


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
    raise FileNotFoundError(f"{name} introuvable (place-le dans le dossier data/).")


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
    c = sqlite3.connect(DB)
    df[cols].to_sql("risks", c, if_exists="replace", index=False)
    c.close()


def init_db():
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    c.commit()
    has = c.execute("SELECT name FROM sqlite_master WHERE name='risks'").fetchone()
    c.close()
    if not has:
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

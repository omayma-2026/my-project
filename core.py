"""ORMVA-TF Risk & Audit Center — couche données et calculs.

Contenu : base SQLite, historique des modifications, zones de risque (grille 4×4 du document
« Cartographie des Risques de l'ORMVA/TF 2024 »), score de priorité des processus et
indicateurs de couverture pour comparer les méthodes de priorisation.
"""
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DB = Path(os.getenv("ORMVATF_DB", ROOT / "ormvatf.db"))

# --------------------------------------------------------------------------------------
# Constantes métier
# --------------------------------------------------------------------------------------
ZONES = ["A", "B", "C", "D"]
ZSEV = {"A": 1, "B": 2, "C": 3, "D": 4}
ZCOL = {"A": "#2E7D4F", "B": "#D9A441", "C": "#E08E45", "D": "#C0392B"}
ZNAME = {"A": "Optimisation", "B": "Vigilance", "C": "Surveillance", "D": "Traitement"}
ZLABEL = {z: f"{z} · {ZNAME[z]}" for z in ZONES}

# Bandes de criticité du document : [0-4[ [4-8[ [8-12[ [12-16]
CRIT_LABELS = ["Faible [0-4[", "Moyen [4-8[", "Significatif [8-12[", "Élevé [12-16]"]
# Degré de contrôle (DMR) : ≤25 %, ≤50 %, ≤75 %, ≤100 %
CTRL_LABELS = ["Faible ≤25%", "Partiel ≤50%", "Correcte ≤75%", "Satisfaisant ≤100%"]

# Grille 4×4 (lignes = degré de contrôle du plus faible au plus fort ; colonnes = bande de criticité).
# Reconstituée à partir des matrices d'actions du document : elle reproduit 168/168 zones officielles.
# NB : la case (Satisfaisant, Faible) est vide dans le document ; elle est rattachée à A par continuité.
GRID = [
    ["C", "C", "D", "D"],
    ["B", "B", "C", "D"],
    ["A", "B", "B", "C"],
    ["A", "A", "B", "C"],
]

WEIGHTS = {"D": 0.45, "C": 0.30, "brut": 0.25}
SCENARIOS = {
    "Base": WEIGHTS,
    "Dominant D": {"D": 0.60, "C": 0.20, "brut": 0.20},
    "Dominant C": {"D": 0.30, "C": 0.50, "brut": 0.20},
    "Dominant brut": {"D": 0.25, "C": 0.25, "brut": 0.50},
    "Équilibre": {"D": 1 / 3, "C": 1 / 3, "brut": 1 / 3},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, auteur TEXT, obj TEXT, champ TEXT, ancien TEXT, nouveau TEXT);
CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, action TEXT, responsable TEXT, echeance TEXT, statut TEXT, maj TEXT);
"""


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------------------
# Accès base de données
# --------------------------------------------------------------------------------------
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
       (now(), str(auteur), str(obj), str(champ), str(old), str(new)))


# --------------------------------------------------------------------------------------
# Zones de risque (grille 4×4 du document)
# --------------------------------------------------------------------------------------
def ctrl_band(dmr):
    """Ligne de la grille : 0 = Faible (≤25 %), 1 = Partiel (≤50 %), 2 = Correcte (≤75 %), 3 = Satisfaisant."""
    d = np.asarray(dmr, dtype=float) - 1e-9
    return np.select([d <= 0.25, d <= 0.50, d <= 0.75], [0, 1, 2], default=3)


def crit_band(crit):
    """Colonne de la grille : 0 = [0-4[, 1 = [4-8[, 2 = [8-12[, 3 = [12-16]."""
    c = np.asarray(crit, dtype=float)
    return np.select([c < 4, c < 8, c < 12], [0, 1, 2], default=3)


def zone_rule(crit, dmr):
    """Zone A/B/C/D selon la grille du document (accepte scalaires ou séries)."""
    return np.array(GRID)[ctrl_band(dmr), crit_band(crit)]


def zone_of(crit, dmr):
    return str(zone_rule(crit, dmr))


def bands(df):
    d = df.copy()
    d["bc"] = crit_band(d["criticite_brute"]).astype(int)
    d["br"] = ctrl_band(d["dmr"]).astype(int)
    return d


# --------------------------------------------------------------------------------------
# Initialisation et chargement des données
# --------------------------------------------------------------------------------------
def _find(name):
    for d in (ROOT / "data", ROOT):
        if (d / name).exists():
            return d / name
    raise FileNotFoundError(f"{name} introuvable (place-le dans le dossier data/).")


def _load_sources():
    e = pd.read_excel(_find("data_reel_avec_rm.xlsx"), engine="openpyxl")
    e = e.rename(columns={"criticite_brute_declaree": "criticite_brute",
                          "criticite_nette_declaree": "criticite_nette"})
    # périmètre = 159 risques de processus ; les 9 risques transversaux (RM) sont exclus
    e = e[~e["code"].astype(str).str.startswith("RM") & (e["processus_code"].astype(str) != "PM")]
    try:
        a = pd.read_excel(_find("cartographie_analysee_complete.xlsx"), sheet_name="Details_Risques", engine="openpyxl")
    except (FileNotFoundError, ValueError):
        a = None
    return e, a


def _build_risks():
    e, a = _load_sources()
    if a is not None:
        a = a.rename(columns={"Criticite_Nette_Predite": "criticite_nette_predite", "Residu": "residu",
                              "Cluster_Label": "cluster_label", "PCA1": "pca1", "PCA2": "pca2"})
        extra = {c: c + "_e" for c in e.columns if c != "code" and c in a.columns}
        df = a.merge(e.rename(columns=extra), on="code", how="left")
        for c, c2 in extra.items():
            df[c] = df[c].where(df[c].notna(), df[c2])
            df = df.drop(columns=c2)
    else:
        df = e.copy()

    if "processus" in df.columns:
        p = df["processus"].astype(str).str.extract(r"^(P\d+)\s*-\s*(.*)$")
        if "processus_code" not in df.columns:
            df["processus_code"] = np.nan
        if "processus_nom" not in df.columns:
            df["processus_nom"] = np.nan
        df["processus_code"] = df["processus_code"].fillna(p[0])
        df["processus_nom"] = df["processus_nom"].fillna(p[1])

    for c in ["prob", "grav", "dmr", "criticite_brute", "criticite_nette"]:
        df[c] = pd.to_numeric(df[c] if c in df.columns else np.nan, errors="coerce")
    df = df.dropna(subset=["code", "processus_code", "prob", "grav", "dmr"]).drop_duplicates("code").copy()
    df["prob"], df["grav"] = df["prob"].astype(int), df["grav"].astype(int)
    df["criticite_brute"] = df["criticite_brute"].fillna(df["prob"] * df["grav"]).astype(int)
    df["criticite_nette"] = df["criticite_nette"].fillna(df["criticite_brute"] * df["dmr"])

    off = df.get("zone_officielle", pd.Series(index=df.index, dtype=object)).astype(str).str.strip().str.upper()
    ok = off.isin(ZONES)
    df["zone"] = np.where(ok, off, zone_rule(df["criticite_brute"], df["dmr"]))
    df["zone_source"] = np.where(ok, "officielle", "grille")

    for c, default in [("fonction", "Non renseignée"), ("sous_processus", ""), ("intitule", ""),
                       ("processus_nom", ""), ("constat", ""), ("mesures_operatoires", ""),
                       ("cluster_label", "Non disponible")]:
        if c not in df.columns:
            df[c] = default
        df[c] = df[c].fillna(default).astype(str)
    for c in ["criticite_nette_predite", "residu", "pca1", "pca2"]:
        df[c] = pd.to_numeric(df[c] if c in df.columns else np.nan, errors="coerce")

    cols = ["code", "processus_code", "processus_nom", "fonction", "sous_processus", "intitule", "prob", "grav",
            "criticite_brute", "dmr", "criticite_nette", "zone", "zone_source", "constat", "mesures_operatoires",
            "cluster_label", "criticite_nette_predite", "residu", "pca1", "pca2"]
    return df[cols]


def _seed():
    df = _build_risks()
    c = sqlite3.connect(DB)
    try:
        df.to_sql("risks", c, if_exists="replace", index=False)
    finally:
        c.close()


def init_db():
    c = sqlite3.connect(DB)
    try:
        c.executescript(SCHEMA)
        c.commit()
        has = c.execute("SELECT name FROM sqlite_master WHERE name='risks'").fetchone()
    finally:
        c.close()
    if not has:
        _seed()


def reset_risks():
    """Recharge le registre depuis les fichiers Excel (l'historique et le plan d'actions sont conservés)."""
    _seed()


def backup_bytes():
    """Copie de la base SQLite (pour téléchargement)."""
    tmp = DB.with_suffix(".bak")
    shutil.copyfile(DB, tmp)
    try:
        return tmp.read_bytes()
    finally:
        tmp.unlink(missing_ok=True)


# --------------------------------------------------------------------------------------
# Modification d'un risque (avec historique)
# --------------------------------------------------------------------------------------
def _same(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def update_risk(code, new, auteur):
    old = q("SELECT * FROM risks WHERE code=?", (code,)).iloc[0]
    new = dict(new)
    new["prob"], new["grav"], new["dmr"] = int(new["prob"]), int(new["grav"]), float(new["dmr"])
    new["criticite_brute"] = new["prob"] * new["grav"]
    if not all(_same(old[k], new[k]) for k in ("prob", "grav", "dmr")):
        new["zone"] = zone_of(new["criticite_brute"], new["dmr"])
        new["zone_source"] = "recalculée"
    n = 0
    for k, v in new.items():
        if not _same(old[k], v):
            ex(f"UPDATE risks SET {k}=? WHERE code=?", (v, code))
            log(auteur, code, k, old[k], v)
            n += 1
    return n


# --------------------------------------------------------------------------------------
# Score de priorité des processus (calculé sur toute la base, jamais sur un filtre)
# --------------------------------------------------------------------------------------
def stats_proc(df):
    g = df.groupby("processus_code")
    o = g.agg(processus_nom=("processus_nom", "first"), Nb=("code", "count"),
              Crit=("criticite_brute", "mean"), DMR=("dmr", "mean")).reset_index()
    z = pd.crosstab(df["processus_code"], df["zone"]).reindex(columns=ZONES, fill_value=0)
    p = z.div(z.sum(axis=1), axis=0) * 100
    o["Nb_D"] = o["processus_code"].map(z["D"]).astype(int)
    o["Nb_C"] = o["processus_code"].map(z["C"]).astype(int)
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
    return o.sort_values(["Rang", "processus_code"])


# --------------------------------------------------------------------------------------
# Comparaison des méthodes de priorisation (couverture des risques de la zone D)
# --------------------------------------------------------------------------------------
def reference_orders(df, sc):
    """Ordres d'audit des processus selon trois méthodes."""
    s = stats_proc(df).set_index("processus_code")
    o = pd.DataFrame({"nd": s["Nb_D"], "nc": s["Nb_C"], "crit": s["Crit"]})
    return {
        "Sp (modèle proposé)": list(sc["processus_code"]),
        "Nb de risques en zone D (logique du document)": list(o.sort_values(["nd", "nc", "crit"], ascending=False).index),
        "Criticité brute moyenne": list(o.sort_values("crit", ascending=False).index),
    }


def coverage(df, order):
    """Courbe cumulée : charge d'audit (% des risques) et couverture (% des risques D) selon l'ordre donné."""
    nb = df.groupby("processus_code").size().reindex(order)
    nd = (df["zone"] == "D").groupby(df["processus_code"]).sum().reindex(order)
    cum_nb, cum_nd = nb.cumsum().to_numpy(float), nd.cumsum().to_numpy(float)
    return pd.DataFrame({
        "k": np.arange(1, len(order) + 1),
        "processus": order,
        "charge": cum_nb / nb.sum() * 100,
        "couv_D": cum_nd / max(nd.sum(), 1) * 100,
        "densite_D": cum_nd / cum_nb * 100,
    })


def auc(cov):
    """Aire sous la courbe couverture(charge), normalisée entre 0 et 1 (0,5 = tirage aléatoire)."""
    x = np.r_[0.0, cov["charge"].to_numpy()] / 100
    y = np.r_[0.0, cov["couv_D"].to_numpy()] / 100
    return float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2))

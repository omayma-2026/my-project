
"""ORMVA-TF Risk & Audit Center — couche données et calculs."""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DB = Path(os.getenv("ORMVATF_DB", str(ROOT / "ormvatf.db")))

# --------------------------------------------------------------------------------------
# Constantes métier
# --------------------------------------------------------------------------------------

ZONES = ["A", "B", "C", "D"]

ZSEV = {"A": 1, "B": 2, "C": 3, "D": 4}
ZCOL = {
    "A": "#2E7D4F",
    "B": "#D9A441",
    "C": "#E08E45",
    "D": "#C0392B"
}
ZNAME = {
    "A": "Optimisation",
    "B": "Vigilance",
    "C": "Surveillance",
    "D": "Traitement"
}
ZLABEL = {z: f"{z} · {ZNAME[z]}" for z in ZONES}

CRIT_LABELS = [
    "Faible [0-4[",
    "Moyen [4-8[",
    "Significatif [8-12[",
    "Élevé [12-16]"
]

CTRL_LABELS = [
    "Faible ≤25%",
    "Partiel ≤50%",
    "Correcte ≤75%",
    "Satisfaisant ≤100%"
]

# Grille 4x4 du document
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
CREATE TABLE IF NOT EXISTS history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    auteur TEXT,
    obj TEXT,
    champ TEXT,
    ancien TEXT,
    nouveau TEXT
);

CREATE TABLE IF NOT EXISTS actions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    action TEXT,
    responsable TEXT,
    echeance TEXT,
    statut TEXT,
    maj TEXT
);
"""


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------------------
# Accès base de données
# --------------------------------------------------------------------------------------

def q(sql, p=()):
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    try:
        return pd.read_sql_query(sql, c, params=p)
    finally:
        c.close()


def ex(sql, p=()):
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    try:
        c.execute(sql, p)
        c.commit()
    finally:
        c.close()


def log(auteur, obj, champ, old="", new=""):
    ex(
        "INSERT INTO history(ts,auteur,obj,champ,ancien,nouveau) "
        "VALUES(?,?,?,?,?,?)",
        (now(), str(auteur), str(obj), str(champ), str(old), str(new))
    )


# --------------------------------------------------------------------------------------
# Zones de risque
# --------------------------------------------------------------------------------------

def ctrl_band(dmr):
    """Classe le DMR dans l'une des quatre bandes de contrôle."""
    d = np.asarray(dmr, dtype=float) - 1e-9
    return np.select(
        [d <= 0.25, d <= 0.50, d <= 0.75],
        [0, 1, 2],
        default=3
    )


def crit_band(crit):
    """Classe la criticité brute dans l'une des quatre bandes."""
    c = np.asarray(crit, dtype=float)
    return np.select(
        [c < 4, c < 8, c < 12],
        [0, 1, 2],
        default=3
    )


def zone_rule(crit, dmr):
    """Détermine la zone A/B/C/D selon la grille."""
    return np.array(GRID)[ctrl_band(dmr), crit_band(crit)]


def zone_of(crit, dmr):
    return str(zone_rule(crit, dmr))


def bands(df):
    d = df.copy()
    d["bc"] = crit_band(d["criticite_brute"]).astype(int)
    d["br"] = ctrl_band(d["dmr"]).astype(int)
    return d


# --------------------------------------------------------------------------------------
# Chargement des fichiers Excel
# --------------------------------------------------------------------------------------

def _find(name):
    for folder in (ROOT / "data", ROOT):
        path = folder / name
        if path.exists():
            return path

    raise FileNotFoundError(
        f"{name} introuvable. Place le fichier dans le dossier data/."
    )


def _load_sources():

    # Fichier de cartographie source
    e = pd.read_excel(
        _find("data_reel_avec_rm.xlsx"),
        engine="openpyxl"
    )

    e = e.rename(columns={
        "criticite_brute_declaree": "criticite_brute",
        "criticite_nette_declaree": "criticite_nette"
    })

    if "code" not in e.columns:
        raise ValueError(
            "La colonne 'code' est absente de data_reel_avec_rm.xlsx."
        )

    e["code"] = e["code"].astype(str).str.strip()

    # Exclusion des risques RM et du processus PM
    e = e[
        ~e["code"].str.startswith("RM") &
        (e["processus_code"].astype(str).str.strip() != "PM")
    ].copy()

    # Fichier d'analyse issu de Google Colab
    a = pd.read_excel(
        _find("cartographie_analysee_complete.xlsx"),
        sheet_name="Details_Risques",
        engine="openpyxl"
    )

    a = a.rename(columns={
        "Cluster_Label": "cluster_label",
        "PCA1": "pca1",
        "PCA2": "pca2"
    })

    if "code" not in a.columns:
        raise ValueError(
            "La colonne 'code' est absente de Details_Risques."
        )

    a["code"] = a["code"].astype(str).str.strip()

    return e, a


# --------------------------------------------------------------------------------------
# Construction du registre des risques
# --------------------------------------------------------------------------------------

def _build_risks():

    e, a = _load_sources()

    # Vérification des doublons avant la fusion
    if e["code"].duplicated().any():
        duplicates = e.loc[e["code"].duplicated(), "code"].tolist()
        raise ValueError(
            f"Codes dupliqués dans le fichier source : {duplicates[:10]}"
        )

    if a["code"].duplicated().any():
        duplicates = a.loc[a["code"].duplicated(), "code"].tolist()
        raise ValueError(
            f"Codes dupliqués dans le fichier d'analyse : {duplicates[:10]}"
        )

    # Les résultats d'analyse sont la table principale.
    # Les colonnes communes du fichier source sont suffixées par _source.
    extra = {
        c: c + "_source"
        for c in e.columns
        if c != "code" and c in a.columns
    }

    df = a.merge(
        e.rename(columns=extra),
        on="code",
        how="left",
        validate="one_to_one"
    )

    # Récupération des valeurs source lorsque la colonne d'analyse est vide
    for c, c2 in extra.items():
        df[c] = df[c].where(df[c].notna(), df[c2])
        df = df.drop(columns=[c2])

    # Vérifier que chaque ligne d'analyse correspond au fichier source
    if df["processus_code"].isna().any():
        missing = df.loc[
            df["processus_code"].isna(), "code"
        ].tolist()

        raise ValueError(
            "Certains codes du fichier d'analyse ne correspondent pas "
            f"au fichier source : {missing[:10]}"
        )

    # Exclusion définitive des risques RM et PM après la fusion
    df = df[
        ~df["code"].astype(str).str.startswith("RM") &
        (df["processus_code"].astype(str).str.strip() != "PM")
    ].copy()

    # Vérification des résultats K-Means et ACP importés depuis Excel
    required_analysis = ["cluster_label", "pca1", "pca2"]

    for col in required_analysis:
        if col not in df.columns:
            raise ValueError(
                f"La colonne {col} est absente du fichier Excel d'analyse."
            )

    if df["cluster_label"].isna().any():
        raise ValueError(
            "Des labels de clusters sont manquants dans le fichier Excel."
        )

    # Conversion numérique des coordonnées ACP
    df["pca1"] = pd.to_numeric(df["pca1"], errors="coerce")
    df["pca2"] = pd.to_numeric(df["pca2"], errors="coerce")

    if df[["pca1", "pca2"]].isna().any().any():
        raise ValueError(
            "Des coordonnées PCA1 ou PCA2 sont manquantes ou non numériques."
        )

    if df["code"].duplicated().any():
        raise ValueError("Des codes de risques sont dupliqués après fusion.")

    # Vérification du périmètre attendu
    if len(df) != 159:
        raise ValueError(
            f"Nombre de risques incorrect : {len(df)} au lieu de 159. "
            "Vérifie les fichiers Excel et les exclusions PM/RM."
        )

    # Compléter les informations processus si nécessaire
    if "processus" in df.columns:

        p = df["processus"].astype(str).str.extract(
            r"^(P\d+)\s*-\s*(.*)$"
        )

        if "processus_code" not in df.columns:
            df["processus_code"] = np.nan

        if "processus_nom" not in df.columns:
            df["processus_nom"] = np.nan

        df["processus_code"] = df["processus_code"].fillna(p[0])
        df["processus_nom"] = df["processus_nom"].fillna(p[1])

    # Vérification des variables indispensables
    required = [
        "code",
        "processus_code",
        "prob",
        "grav",
        "dmr"
    ]

    for col in required:
        if col not in df.columns:
            raise ValueError(
                f"La colonne obligatoire '{col}' est absente des fichiers Excel."
            )

    # Conversion des variables numériques
    numeric_cols = [
        "prob",
        "grav",
        "dmr",
        "criticite_brute",
        "criticite_nette"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    df = df.dropna(
        subset=["code", "processus_code", "prob", "grav", "dmr"]
    ).copy()

    df["prob"] = df["prob"].astype(int)
    df["grav"] = df["grav"].astype(int)

    # Vérification des valeurs métier
    if not df["prob"].between(1, 4).all():
        raise ValueError("La probabilité doit être comprise entre 1 et 4.")

    if not df["grav"].between(1, 4).all():
        raise ValueError("La gravité doit être comprise entre 1 et 4.")

    if not df["dmr"].between(0, 1).all():
        raise ValueError(
            "Le DMR doit être exprimé entre 0 et 1, par exemple 0.75."
        )

    # Calcul des valeurs manquantes uniquement
    df["criticite_brute"] = (
        df["criticite_brute"]
        .fillna(df["prob"] * df["grav"])
    )

    df["criticite_nette"] = (
        df["criticite_nette"]
        .fillna(df["criticite_brute"] * df["dmr"])
    )

    # Zone officielle si disponible, sinon grille du document
    off = df.get(
        "zone_officielle",
        pd.Series(index=df.index, dtype=object)
    ).astype(str).str.strip().str.upper()

    ok = off.isin(ZONES)

    df["zone"] = np.where(
        ok,
        off,
        zone_rule(df["criticite_brute"], df["dmr"])
    )

    df["zone_source"] = np.where(
        ok,
        "officielle",
        "grille"
    )

    # Colonnes textuelles facultatives
    defaults = [
        ("fonction", "Non renseignée"),
        ("sous_processus", ""),
        ("intitule", ""),
        ("processus_nom", ""),
        ("constat", ""),
        ("mesures_operatoires", ""),
        ("cluster_label", "Non disponible")
    ]

    for col, default in defaults:
        if col not in df.columns:
            df[col] = default

        df[col] = df[col].fillna(default).astype(str)

    # Vérification finale des coordonnées ACP
    for col in ["pca1", "pca2"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Ordre final des colonnes dans SQLite
    cols = [
        "code",
        "processus_code",
        "processus_nom",
        "fonction",
        "sous_processus",
        "intitule",
        "prob",
        "grav",
        "criticite_brute",
        "dmr",
        "criticite_nette",
        "zone",
        "zone_source",
        "constat",
        "mesures_operatoires",
        "cluster_label",
        "pca1",
        "pca2"
    ]

    return df[cols].reset_index(drop=True)


# --------------------------------------------------------------------------------------
# Initialisation et synchronisation SQLite
# --------------------------------------------------------------------------------------

def _seed():

    df = _build_risks()

    DB.parent.mkdir(parents=True, exist_ok=True)

    c = sqlite3.connect(DB)

    try:
        df.to_sql(
            "risks",
            c,
            if_exists="replace",
            index=False
        )
        c.commit()
    finally:
        c.close()


def init_db():

    DB.parent.mkdir(parents=True, exist_ok=True)

    c = sqlite3.connect(DB)

    try:
        c.executescript(SCHEMA)
        c.commit()

        has = c.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='risks'"
        ).fetchone()

    finally:
        c.close()

    # Première initialisation uniquement
    if not has:
        _seed()


def reset_risks():
    """
    Recharge le registre depuis les fichiers Excel.
    L'historique et le plan d'actions sont conservés.
    Les modifications manuelles des risques sont remplacées.
    """
    _seed()


def backup_bytes():

    tmp = DB.with_suffix(".bak")

    shutil.copyfile(DB, tmp)

    try:
        return tmp.read_bytes()
    finally:
        tmp.unlink(missing_ok=True)


# --------------------------------------------------------------------------------------
# Modification d'un risque avec historique
# --------------------------------------------------------------------------------------

def _same(a, b):

    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def update_risk(code, new, auteur):

    old_df = q(
        "SELECT * FROM risks WHERE code=?",
        (code,)
    )

    if old_df.empty:
        raise ValueError(f"Risque introuvable : {code}")

    old = old_df.iloc[0]
    new = dict(new)

    new["prob"] = int(new["prob"])
    new["grav"] = int(new["grav"])
    new["dmr"] = float(new["dmr"])

    new["criticite_brute"] = new["prob"] * new["grav"]

    if not all(
        _same(old[k], new[k])
        for k in ("prob", "grav", "dmr")
    ):

        new["zone"] = zone_of(
            new["criticite_brute"],
            new["dmr"]
        )

        new["zone_source"] = "recalculée"

        new["criticite_nette"] = (
            new["criticite_brute"] * new["dmr"]
        )

    n = 0

    for k, v in new.items():

        if k not in old.index:
            continue

        if not _same(old[k], v):

            ex(
                f"UPDATE risks SET {k}=? WHERE code=?",
                (v, code)
            )

            log(auteur, code, k, old[k], v)

            n += 1

    return n


# --------------------------------------------------------------------------------------
# Score de priorité des processus
# --------------------------------------------------------------------------------------

def stats_proc(df):

    g = df.groupby("processus_code")

    o = g.agg(
        processus_nom=("processus_nom", "first"),
        Nb=("code", "count"),
        Crit=("criticite_brute", "mean"),
        DMR=("dmr", "mean")
    ).reset_index()

    z = pd.crosstab(
        df["processus_code"],
        df["zone"]
    ).reindex(columns=ZONES, fill_value=0)

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

    o["N_D"] = _mm(o["Pct_D"])
    o["N_C"] = _mm(o["Pct_C"])
    o["N_brut"] = _mm(o["Crit"])

    o["contrib_D"] = w["D"] * o["N_D"]
    o["contrib_C"] = w["C"] * o["N_C"]
    o["contrib_brut"] = w["brut"] * o["N_brut"]

    o["Score"] = (
        o["contrib_D"] +
        o["contrib_C"] +
        o["contrib_brut"]
    ).round(1)

    o["Rang"] = o["Score"].rank(
        ascending=False,
        method="min"
    ).astype(int)

    return o.sort_values(["Rang", "processus_code"])


# --------------------------------------------------------------------------------------
# Comparaison des méthodes de priorisation
# --------------------------------------------------------------------------------------

def reference_orders(df, sc):

    """Ordres d'audit des processus selon trois méthodes."""

    s = stats_proc(df).set_index("processus_code")

    o = pd.DataFrame({
        "nd": s["Nb_D"],
        "nc": s["Nb_C"],
        "crit": s["Crit"]
    })

    return {
        "Sp (modèle proposé)": list(sc["processus_code"]),

        "Nb de risques en zone D (logique du document)": list(
            o.sort_values(
                ["nd", "nc", "crit"],
                ascending=False
            ).index
        ),

        "Criticité brute moyenne": list(
            o.sort_values(
                "crit",
                ascending=False
            ).index
        )
    }


def coverage(df, order):

    """Charge d'audit et couverture cumulée des risques de zone D."""

    nb = df.groupby("processus_code").size().reindex(order)

    nd = (
        (df["zone"] == "D")
        .groupby(df["processus_code"])
        .sum()
        .reindex(order)
    )

    cum_nb = nb.cumsum().to_numpy(float)
    cum_nd = nd.cumsum().to_numpy(float)

    total_nb = nb.sum()
    total_nd = max(nd.sum(), 1)

    return pd.DataFrame({
        "k": np.arange(1, len(order) + 1),
        "processus": order,
        "charge": cum_nb / total_nb * 100,
        "couv_D": cum_nd / total_nd * 100,
        "densite_D": cum_nd / cum_nb * 100
    })


def auc(cov):

    """Aire sous la courbe couverture/charge, normalisée entre 0 et 1."""

    x = np.r_[0.0, cov["charge"].to_numpy()] / 100
    y = np.r_[0.0, cov["couv_D"].to_numpy()] / 100

    return float(
        np.sum(
            (x[1:] - x[:-1]) *
            (y[1:] + y[:-1]) / 2
        )
    )

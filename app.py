# ----------------------------------------------------------------------------
# 1. CHARGEMENT DES DONNÉES EXCEL
# ----------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data"

# Fichiers possibles, classés par priorité
DATA_FILES = [
    DATA_DIR / "cartographie_analysee_complet.xlsx",
    DATA_DIR / "ORMVATF_cartographie_risques_extraite.xlsx",
]

def is_valid_xlsx(path: Path) -> bool:
    """
    Vérifie qu'un fichier est réellement un classeur XLSX valide.
    Un XLSX est une archive ZIP contenant [Content_Types].xml.
    """
    if not path.exists():
        return False

    if path.stat().st_size < 2048:
        return False

    try:
        import zipfile

        if not zipfile.is_zipfile(path):
            return False

        with zipfile.ZipFile(path, "r") as z:
            names = z.namelist()

        return "[Content_Types].xml" in names

    except Exception:
        return False


def find_valid_excel_file():
    """
    Recherche automatiquement le premier fichier XLSX valide.
    Le fichier cartographie_analysee_complete.xlsx de 1 octet
    est volontairement ignoré.
    """

    # 1. Priorité aux fichiers connus
    for path in DATA_FILES:
        if is_valid_xlsx(path):
            return path

    # 2. Si aucun fichier prioritaire n'est trouvé,
    #    rechercher n'importe quel XLSX valide dans data/
    for path in sorted(DATA_DIR.glob("*.xlsx")):
        if is_valid_xlsx(path):
            return path

    return None


DATA_FILE = find_valid_excel_file()


def diagnose_data_files():
    """
    Retourne l'état de tous les fichiers Excel présents dans data/.
    """
    results = []

    if not DATA_DIR.exists():
        return ["❌ Le dossier data/ n'existe pas."]

    for path in sorted(DATA_DIR.glob("*.xlsx")):

        size = path.stat().st_size

        try:
            with open(path, "rb") as f:
                header = f.read(8)

            valid = is_valid_xlsx(path)

            if valid:
                results.append(
                    f"✅ {path.name} → Excel XLSX valide | "
                    f"Taille : {size:,} octets"
                )
            else:
                results.append(
                    f"❌ {path.name} → fichier XLSX invalide | "
                    f"Taille : {size:,} octets | "
                    f"Header : {header!r}"
                )

        except Exception as e:
            results.append(
                f"❌ {path.name} → erreur de lecture : {e}"
            )

    return results


@st.cache_data(show_spinner="Chargement de la cartographie des risques...")
def load_data(path_str):

    path = Path(path_str)

    if not is_valid_xlsx(path):
        raise ValueError(
            f"Le fichier sélectionné n'est pas un véritable fichier XLSX : "
            f"{path.name}"
        )

    import openpyxl

    # ------------------------------------------------------------------
    # Recherche de la feuille Details_Risques
    # ------------------------------------------------------------------

    try:
        excel_file = pd.ExcelFile(
            path,
            engine="openpyxl"
        )

        sheets = excel_file.sheet_names

    except Exception as e:
        raise ValueError(
            f"Impossible d'ouvrir le fichier Excel '{path.name}' : {e}"
        )

    # Priorité à Details_Risques
    if "Details_Risques" in sheets:
        sheet_name = "Details_Risques"

    else:
        # Recherche insensible à la casse
        details_candidates = [
            s for s in sheets
            if s.strip().lower() == "details_risques"
        ]

        if details_candidates:
            sheet_name = details_candidates[0]

        else:
            raise KeyError(
                f"La feuille 'Details_Risques' est absente de "
                f"'{path.name}'.\n\n"
                f"Feuilles disponibles : {sheets}"
            )

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------

    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        engine="openpyxl"
    )

    # Nettoyage des noms de colonnes
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    # ------------------------------------------------------------------
    # Colonnes attendues
    # ------------------------------------------------------------------

    rename_map = {
        "code": "code",
        "processus_code": "processus_code",
        "processus_nom": "processus_nom",
        "fonction": "fonction",
        "sous_processus": "sous_processus",
        "prob": "prob",
        "grav": "grav",
        "criticite_brute_declaree": "criticite_brute",
        "criticite_brute": "criticite_brute",
        "dmr": "dmr",
        "criticite_nette_declaree": "criticite_nette_declaree",
        "zone_officielle": "zone",
        "zone": "zone",
    }

    # Renommer uniquement les colonnes présentes
    existing_rename = {
        old: new
        for old, new in rename_map.items()
        if old in df.columns
    }

    df = df.rename(columns=existing_rename)

    # ------------------------------------------------------------------
    # Vérification des colonnes obligatoires
    # ------------------------------------------------------------------

    required_columns = [
        "code",
        "processus_code",
        "sous_processus",
        "prob",
        "grav",
        "criticite_brute",
        "dmr",
        "criticite_nette_declaree",
        "zone",
    ]

    missing = [
        c for c in required_columns
        if c not in df.columns
    ]

    if missing:
        raise KeyError(
            f"Colonnes obligatoires absentes de '{sheet_name}' : "
            f"{missing}\n\n"
            f"Colonnes trouvées : {list(df.columns)}"
        )

    # ------------------------------------------------------------------
    # Colonnes facultatives
    # ------------------------------------------------------------------

    if "processus_nom" not in df.columns:
        df["processus_nom"] = df["processus_code"].astype(str)

    if "fonction" not in df.columns:
        df["fonction"] = "—"

    # ------------------------------------------------------------------
    # Conversion numérique
    # ------------------------------------------------------------------

    numeric_columns = [
        "prob",
        "grav",
        "criticite_brute",
        "dmr",
        "criticite_nette_declaree",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    # ------------------------------------------------------------------
    # Nettoyage du DMR
    # ------------------------------------------------------------------

    # Si le DMR est exprimé en pourcentage (ex: 75 au lieu de 0.75),
    # on le ramène entre 0 et 1.
    if df["dmr"].dropna().max() > 1:
        df["dmr"] = df["dmr"] / 100

    df["dmr"] = df["dmr"].clip(0, 1)

    # ------------------------------------------------------------------
    # Variables dérivées
    # ------------------------------------------------------------------

    df["degre_controle_pct"] = df["dmr"] * 100

    df["criticite_nette_diagnostique"] = (
        df["criticite_brute"] *
        (1 - df["dmr"])
    )

    # ------------------------------------------------------------------
    # Nettoyage des zones officielles
    # ------------------------------------------------------------------

    df["zone"] = (
        df["zone"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Supprimer les valeurs invalides
    df.loc[
        ~df["zone"].isin(ZONE_ORDER),
        "zone"
    ] = np.nan

    df["zone_severite"] = df["zone"].map(
        ZONE_SEVERITY
    )

    # ------------------------------------------------------------------
    # Suppression des lignes totalement vides
    # ------------------------------------------------------------------

    df = df.dropna(
        subset=[
            "code",
            "processus_code"
        ]
    ).copy()

    # ------------------------------------------------------------------
    # Réinitialisation de l'index
    # ------------------------------------------------------------------

    df = df.reset_index(drop=True)

    return df


# ----------------------------------------------------------------------------
# DIAGNOSTIC DES FICHIERS
# ----------------------------------------------------------------------------

file_status = diagnose_data_files()

# Affichage uniquement dans la page si nécessaire
with st.expander("🔎 Vérification des fichiers Excel", expanded=False):

    for status in file_status:
        if status.startswith("✅"):
            st.success(status)
        else:
            st.warning(status)


# ----------------------------------------------------------------------------
# SÉLECTION DU FICHIER VALIDE
# ----------------------------------------------------------------------------

if DATA_FILE is None:

    st.error(
        """
        ⚠️ **Aucun fichier Excel valide trouvé dans le dossier `data/`.**

        Les fichiers doivent être de vrais classeurs `.xlsx`.

        Fichiers actuellement détectés :
        """
    )

    for status in file_status:
        st.write(status)

    st.stop()


# ----------------------------------------------------------------------------
# CHARGEMENT
# ----------------------------------------------------------------------------

try:

    RISQUES = load_data(
        str(DATA_FILE)
    )

except FileNotFoundError:

    st.error(
        f"""
        ⚠️ Le fichier `{DATA_FILE.name}` est introuvable.

        Vérifiez que le fichier est bien présent dans :

        `data/`
        """
    )

    st.stop()

except KeyError as e:

    st.error(
        f"""
        ⚠️ **Structure Excel incorrecte**

        {e}
        """
    )

    st.stop()

except Exception as e:

    st.error(
        f"""
        ⚠️ **Erreur lors du chargement de la base Excel**

        Fichier utilisé :
        `{DATA_FILE.name}`

        Erreur :
        `{e}`
        """
    )

    st.stop()


# ----------------------------------------------------------------------------
# CONTRÔLE FINAL DE LA BASE
# ----------------------------------------------------------------------------

if RISQUES.empty:

    st.error(
        f"⚠️ Le fichier `{DATA_FILE.name}` a été ouvert mais "
        "ne contient aucune observation exploitable."
    )

    st.stop()


# ----------------------------------------------------------------------------
# INFORMATIONS SUR LA SOURCE UTILISÉE
# ----------------------------------------------------------------------------

st.sidebar.success(
    f"📁 Source : {DATA_FILE.name}"
)

st.sidebar.caption(
    f"{len(RISQUES)} observations chargées"
)


# ----------------------------------------------------------------------------
# VARIABLES GLOBALES
# ----------------------------------------------------------------------------

ALL_PROCESSUS = sorted(
    RISQUES["processus_code"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

ALL_FONCTIONS = sorted(
    RISQUES["fonction"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

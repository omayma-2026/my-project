from pathlib import Path
import zipfile
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

st.write("### 🔎 Vérification des fichiers Excel")

for file in DATA_DIR.glob("*.xlsx"):

    size = file.stat().st_size

    try:
        with open(file, "rb") as f:
            header = f.read(8)

        if header[:2] != b"PK":
            st.error(
                f"❌ {file.name} → PAS un vrai XLSX | "
                f"Taille: {size:,} octets | Header: {header!r}"
            )
            continue

        with zipfile.ZipFile(file, "r") as z:
            bad = z.testzip()

        if bad is None:
            st.success(
                f"✅ {file.name} → Excel valide | "
                f"Taille: {size:,} octets"
            )
        else:
            st.error(
                f"❌ {file.name} → ZIP/XLSX corrompu : {bad}"
            )

    except Exception as e:
        st.error(
            f"❌ {file.name} → ERREUR : {e}"
        )

st.stop()

import streamlit as st
from pathlib import Path
import pandas as pd
import shutil

from pipeline_search import run_search_pipeline
from pipeline_validation import run_full_validation_pipeline
from pipeline_images import run_image_pipeline


st.set_page_config(
    page_title="Stamp AI Assistant",
    layout="wide"
)

st.title("Stamp & Metadata AI Assistant")


BASE_DIR = Path(__file__).resolve().parent

PDF_INPUT_DIR = BASE_DIR / "pdf_input"
PDF_INPUT_DIR.mkdir(exist_ok=True)

PIPELINE_DIR = BASE_DIR / "images_pipeline"
PIPELINE_DIR.mkdir(exist_ok=True)


# ==========================================================
# CLEAR WORKSPACE
# ==========================================================
def clear_selected_outputs():

    # 1. Clear pdf_input folder
    if PDF_INPUT_DIR.exists():
        shutil.rmtree(PDF_INPUT_DIR, ignore_errors=True)
    PDF_INPUT_DIR.mkdir(exist_ok=True)

    # 2. Clear images_pipeline folder
    if PIPELINE_DIR.exists():
        shutil.rmtree(PIPELINE_DIR, ignore_errors=True)
    PIPELINE_DIR.mkdir(exist_ok=True)

    # 3. Delete generated Excel / CSV files
    generated_files = [
        "raw_extraction.xlsx",
        "cleaning_file.xlsx",
        "revision_extraction.xlsx",
        "raw_validated.xlsx",
        "validation_file.xlsx",
        "validation_file.csv"
    ]

    for fname in generated_files:
        fpath = BASE_DIR / fname
        if fpath.exists():
            fpath.unlink()

    # 4. Delete debug folders
    debug_folders = [
        BASE_DIR / "images_stamp",
        BASE_DIR / "debug_crops",
        BASE_DIR / "revision_extraction",
        BASE_DIR / "rev_crops"
    ]

    for folder in debug_folders:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

    # 5. Delete SQLite database
    from sqlalchemy import create_engine, text

    db_file = BASE_DIR / "metadata.db"

    if db_file.exists():
        try:
            engine = create_engine(f"sqlite:///{db_file}")
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS validation_file"))
            engine.dispose()
        except Exception as e:
            print("Failed to clear SQLite table:", e)


# ==========================================================
# SAVE PDFS
# ==========================================================
def save_uploaded_pdfs(uploaded_pdfs):
    for pdf in uploaded_pdfs:
        with open(PDF_INPUT_DIR / pdf.name, "wb") as f:
            f.write(pdf.getbuffer())


# ==========================================================
# SIDEBAR
# ==========================================================
st.sidebar.title("Actions")
st.sidebar.divider()

# 🔥 Important: dynamic uploader key
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

uploaded_pdfs = st.sidebar.file_uploader(
    "Upload Drawing PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state['uploader_key']}"
)

if uploaded_pdfs:
    save_uploaded_pdfs(uploaded_pdfs)
    st.sidebar.success(f"{len(uploaded_pdfs)} PDFs loaded")

if st.sidebar.button("Clear Workspace"):
    clear_selected_outputs()

    # 🔥 Reset uploader widget
    st.session_state["uploader_key"] += 1

    st.sidebar.success("Workspace Cleared")
    st.rerun()


VALID_COLUMNS = [
    "Image",
    "LEVERANTOR_1","LEVERANTOR_2",
    "SKAPAD_AV","GRANSKAD_AV","GODKAND_AV",
    "DATUM",
    "AVDELNING","UPPDRAGSNUMMER","LEVERANS_ANDRINGS_PM",
    "KONSTRUKTIONSNUMMER",
    "TITLE",
    "BESKRIVNING_ROW_1","BESKRIVNING_ROW_2",
    "BESKRIVNING_ROW_3","BESKRIVNING_ROW_4",
    "SKALA","FORMAT",
    "RITNINGSNUMMER_FORVALTNING","RITNINGSNUMMER_PROJEKT",
    "TEKNIKOMRADE",
    "GRANSKNINGSSTATUS_SYFTE","HANDLINGSTYP","ANLAGGNINGSTYP",
    "KILOMETER_METER",
    "BANDEL","BLAD","NASTA_BLAD",
    "ANDR",
    "FINAL_REV"
]

action = st.sidebar.radio(
    "Choose operation",
    [
        "Validate Drawings",
        "View Stamps",
        "Search Metadata"
    ]
)

# ==========================================================
# VALIDATE DRAWINGS
# ==========================================================
if action == "Validate Drawings":

    st.subheader("Drawing Validation")

    if st.button("Run Full Validation Pipeline"):

        with st.spinner("Running validation pipeline..."):
            try:
                result_file = run_full_validation_pipeline(
                    PROJECT_DIR=BASE_DIR,
                    auto_clean=False
                )

                st.success("Validation Complete")

                df_result = pd.read_excel(result_file, dtype=str, keep_default_na=False)
                df_result = df_result[[c for c in VALID_COLUMNS if c in df_result.columns]]

                st.dataframe(df_result, use_container_width=True)

                with open(result_file, "rb") as f:
                    st.download_button(
                        label="Download Validation Excel",
                        data=f,
                        file_name=Path(result_file).name
                    )

            except Exception as e:
                st.error(f"Pipeline Error: {str(e)}")

# ==========================================================
# VIEW STAMPS
# ==========================================================
elif action == "View Stamps":

    st.subheader("Stamp Preview")

    if st.button("Generate Stamp Images"):

        with st.spinner("Generating stamps..."):
            try:
                run_image_pipeline(
                    PDF_FOLDER=PDF_INPUT_DIR,
                    OUTPUT_DIR=PIPELINE_DIR
                )
                st.success("Stamps Generated")

            except Exception as e:
                st.error(f"Stamp Pipeline Error: {str(e)}")

    drawing_folders = [p for p in PIPELINE_DIR.iterdir() if p.is_dir()]

    if not drawing_folders:
        st.warning("No stamp folders found")

    for folder in drawing_folders:

        st.divider()
        st.subheader(f"Drawing: {folder.name}")

        stamp28  = folder / "stamp28.png"
        stampREV = folder / "stampREV.png"

        col1, col2 = st.columns(2)

        with col1:
            st.write("28-Label Stamp")
            if stamp28.exists():
                st.image(str(stamp28))
            else:
                st.warning("Missing stamp28.png")

        with col2:
            st.write("Revision Stamp")
            if stampREV.exists():
                st.image(str(stampREV))
            else:
                st.warning("Missing stampREV.png")

# ==========================================================
# SEARCH METADATA
# ==========================================================
elif action == "Search Metadata":

    st.subheader("Metadata Search")

    df_check = run_search_pipeline("1=1", top_n=5)

    if df_check.empty:
        st.warning("No validated metadata found")
        st.stop()

    column = st.selectbox("Choose column", VALID_COLUMNS)
    value  = st.text_input("Enter value")

    if st.button("Search"):

        safe_value = value.replace("'", "''")
        where_clause = f"{column} = '{safe_value}'"

        df = run_search_pipeline(where_clause, top_n=200)

        if df.empty:
            st.warning("No matching drawings")
        else:
            df = df[[c for c in VALID_COLUMNS if c in df.columns]]
            st.success(f"Found {len(df)} drawings")
            st.dataframe(df, use_container_width=True)
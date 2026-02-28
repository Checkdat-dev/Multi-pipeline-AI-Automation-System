import subprocess
import sys
from pathlib import Path
import pandas as pd


# ==========================================================
# RUN EXTERNAL SCRIPT SAFELY (FORCE WORKING DIRECTORY)
# ==========================================================
def run_script(script_path: Path, project_dir: Path):

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    subprocess.run(
        [sys.executable, str(script_path)],
        check=True,
        cwd=str(project_dir)
    )


# ==========================================================
# MAIN FULL VALIDATION PIPELINE
# ==========================================================
def run_full_validation_pipeline(PROJECT_DIR: Path, auto_clean=False):

    # 🔥 import moved here (break circular import)
    from pipeline_sql import update_sql_table

    PROJECT_DIR = PROJECT_DIR.resolve()

    print("\nFULL VALIDATION PIPELINE STARTED")
    print("PROJECT_DIR:", PROJECT_DIR)

    # ------------------------------------------------------
    # Script Paths (UPDATED TO YOUR NEW STRUCTURE)
    # ------------------------------------------------------
    PDF_TO_STAMP_SCRIPT = PROJECT_DIR / "step1_pdf_2_image.py"
    EXTRACT_28_SCRIPT   = PROJECT_DIR / "step2_extract.py"
    CLEAN_SCRIPT        = PROJECT_DIR / "step3_cleaning.py"

    PDF_TO_IMAGE_REV_SCRIPT = PROJECT_DIR / "step4_pdf_2_img.py"
    REV_EXTRACT_SCRIPT      = PROJECT_DIR / "step5_andr_ext.py"
    COMPARE_SCRIPT          = PROJECT_DIR / "step6_comparerev.py"

    MASTER_VALIDATE_SCRIPT  = PROJECT_DIR / "step7_validate_against_master.py"

    # Expected files (KEEP YOUR ORIGINAL OUTPUT STRUCTURE)
    RAW_VALIDATED_FILE = PROJECT_DIR / "raw_validated.xlsx"
    FINAL_EXCEL        = PROJECT_DIR / "validation_file.xlsx"

    try:

        print("\nStep 1: PDF → Stamp Images")
        run_script(PDF_TO_STAMP_SCRIPT, PROJECT_DIR)

        print("\nStep 2: 28 Label Extraction")
        run_script(EXTRACT_28_SCRIPT, PROJECT_DIR)

        print("\nStep 3: Cleaning")
        run_script(CLEAN_SCRIPT, PROJECT_DIR)

        print("\nStep 4: Convert PDFs for Revision")
        run_script(PDF_TO_IMAGE_REV_SCRIPT, PROJECT_DIR)

        print("\nStep 5: Revision Extraction")
        run_script(REV_EXTRACT_SCRIPT, PROJECT_DIR)

        print("\nStep 6: Compare Revision vs Main")
        run_script(COMPARE_SCRIPT, PROJECT_DIR)

        if not RAW_VALIDATED_FILE.exists():
            raise FileNotFoundError(
                f"Step 6 failed. File not created: {RAW_VALIDATED_FILE}"
            )

        print("\nStep 7: Master Validation")
        run_script(MASTER_VALIDATE_SCRIPT, PROJECT_DIR)

        if not FINAL_EXCEL.exists():
            raise FileNotFoundError(
                f"Final validation file not created: {FINAL_EXCEL}"
            )

        print("\nVALIDATION COMPLETE")
        print("Output:", FINAL_EXCEL)

        # --------------------------------------------------
        # Update SQLite
        # --------------------------------------------------
        df = pd.read_excel(FINAL_EXCEL, dtype=str, keep_default_na=False)
        update_sql_table(df)

        print("SQLite table updated successfully")

        # --------------------------------------------------
        # Optional cleanup
        # --------------------------------------------------
        if auto_clean:
            print("\nAUTO CLEANUP STARTED")

            db_file = PROJECT_DIR / "metadata.db"
            if db_file.exists():
                db_file.unlink()

            print("Workspace Reset Complete")

        return FINAL_EXCEL

    except Exception as e:

        print("\nPIPELINE FAILED")
        print(e)
        raise e
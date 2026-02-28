from sqlalchemy import create_engine
from pathlib import Path
import pandas as pd


# ==========================================================
# SQLITE CONFIG (LOCAL DB)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "metadata.db"

TABLE = "validation_file"

engine = create_engine(f"sqlite:///{DB_PATH}")


# ==========================================================
# UPDATE TABLE
# ==========================================================
def update_sql_table(df: pd.DataFrame):

    if df is None or df.empty:
        raise ValueError("DataFrame is empty. SQL update aborted.")

    try:
        df.to_sql(
            TABLE,
            engine,
            if_exists="replace",
            index=False
        )

        print(f"SQLite table '{TABLE}' updated successfully.")

    except Exception as e:
        print("SQLite update failed:", e)
        raise e
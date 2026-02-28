from sqlalchemy import create_engine
import pandas as pd
from pathlib import Path


# ==========================================================
# DATABASE CONFIG (SQLITE)
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "metadata.db"

TABLE = "validation_file"

# Create SQLite engine (file-based DB)
engine = create_engine(f"sqlite:///{DB_PATH}")


# ==========================================================
# LOAD DATA FUNCTION
# ==========================================================
def load_validation_data(limit=5):

    try:
        query = f"""
        SELECT *
        FROM {TABLE}
        LIMIT {limit}
        """

        df = pd.read_sql(query, engine)

        print("DATA LOADED SUCCESSFULLY")
        return df

    except Exception as e:
        print("SQLITE ERROR:", e)
        return pd.DataFrame()
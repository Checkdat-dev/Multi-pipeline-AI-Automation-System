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
# SQL INJECTION PROTECTION (UNCHANGED)
# ==========================================================
FORBIDDEN_SQL = [";", "--", "DROP", "DELETE", "INSERT", "UPDATE"]

def is_safe_clause(clause: str) -> bool:
    clause_upper = clause.upper()
    return not any(token in clause_upper for token in FORBIDDEN_SQL)


# ==========================================================
# MAIN SEARCH FUNCTION
# ==========================================================
def run_search_pipeline(where_clause: str = "", top_n: int = 50) -> pd.DataFrame:

    where_clause = (where_clause or "").strip()

    if where_clause and not is_safe_clause(where_clause):
        print("Unsafe SQL blocked")
        return pd.DataFrame()

    try:

        if where_clause:
            sql = f"SELECT * FROM {TABLE} WHERE {where_clause} LIMIT {top_n}"
        else:
            sql = f"SELECT * FROM {TABLE} LIMIT {top_n}"

        df = pd.read_sql(sql, engine)
        return df

    except Exception as e:
        print("SQL ERROR:", e)
        return pd.DataFrame()
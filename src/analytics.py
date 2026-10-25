from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.loader.load import connect

SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "analytics"

QUERIES = {
    "kpi_daily": "01_kpi_daily.sql",
    "funnel_by_category": "02_funnel_by_category.sql",
    "category_wow": "03_category_wow.sql",
    "deviation_check": "04_deviation_check.sql",
}


def run_query(name: str, schema: str = "raw", conn=None) -> pd.DataFrame:
    sql = (SQL_DIR / QUERIES[name]).read_text()
    own = conn is None
    conn = conn or connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET search_path TO {schema}")
            cur.execute(sql)
            cols = [c.name for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        if own:
            conn.close()

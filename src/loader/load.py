from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
LOAD_ORDER = ["users", "listings", "events", "deals"]


def connect(**overrides) -> psycopg.Connection:
    params = dict(
        host=os.getenv("PGHOST", "localhost"), port=os.getenv("PGPORT", "5432"),
        user=os.getenv("PGUSER", "mp"), password=os.getenv("PGPASSWORD", "mp"),
        dbname=os.getenv("PGDATABASE", "marketplace"),
    )
    params.update(overrides)
    return psycopg.connect(**params)


def apply_schema(conn: psycopg.Connection) -> None:
    conn.execute((ROOT / "sql" / "schema.sql").read_text())
    conn.commit()


def copy_csv(conn: psycopg.Connection, table: str, path: Path, schema: str = "raw") -> int:
    with conn.cursor() as cur:
        with path.open("rb") as f, cur.copy(
            f"COPY {schema}.{table} FROM STDIN WITH (FORMAT csv, HEADER true)"
        ) as copy:
            while chunk := f.read(1 << 20):
                copy.write(chunk)
        cur.execute(f"SELECT count(*) FROM {schema}.{table}")
        return cur.fetchone()[0]


def load_all(data_dir: Path) -> dict[str, int]:
    counts = {}
    with connect() as conn:
        apply_schema(conn)
        conn.execute("TRUNCATE raw.users, raw.listings, raw.events, raw.deals")
        for name in LOAD_ORDER:
            counts[name] = copy_csv(conn, name, data_dir / f"{name}.csv")
            print(f"raw.{name:9s} {counts[name]:>9,} rows")
        conn.commit()
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "data"))
    load_all(Path(ap.parse_args().data))

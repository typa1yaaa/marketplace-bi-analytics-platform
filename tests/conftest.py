import uuid

import pytest

from src.loader.load import apply_schema, connect


@pytest.fixture(scope="session")
def pg():
    try:
        conn = connect(connect_timeout=3)
    except Exception as exc:
        pytest.skip(f"PostgreSQL is not available: {exc}")
    apply_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def schema(pg):
    name = f"t_{uuid.uuid4().hex[:8]}"
    pg.execute(f"CREATE SCHEMA {name}")
    for t in ("users", "listings", "events", "deals"):
        pg.execute(f"CREATE TABLE {name}.{t} (LIKE raw.{t} INCLUDING DEFAULTS)")
    pg.commit()
    yield name
    pg.execute(f"DROP SCHEMA {name} CASCADE")
    pg.commit()

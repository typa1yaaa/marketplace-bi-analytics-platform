"""Stage 2 check: every analytics query is verified on a tiny dataset with hand-computed answers."""
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from src.analytics import run_query


class Builder:
    """Helper to insert hand-made rows into a throw-away schema."""

    def __init__(self, conn, schema):
        self.conn, self.s, self.eid, self.did = conn, schema, 0, 0

    def listing(self, lid, category, price=100):
        self.conn.execute(
            f"INSERT INTO {self.s}.listings VALUES (%s,1,%s,'Moscow',%s,'2026-06-01')", (lid, category, price))

    def events(self, day, lid, etype, n):
        ids = []
        rows = []
        for i in range(n):
            self.eid += 1
            ids.append(self.eid)
            rows.append((self.eid, datetime.combine(day, datetime.min.time()) + timedelta(seconds=i), 1, lid, etype, "web"))
        with self.conn.cursor() as cur:
            cur.executemany(f"INSERT INTO {self.s}.events VALUES (%s,%s,%s,%s,%s,%s)", rows)
        return ids

    def deal(self, day, lid, contact_id, amount, status):
        self.did += 1
        self.conn.execute(
            f"INSERT INTO {self.s}.deals VALUES (%s,%s,1,%s,%s,%s,%s)",
            (self.did, lid, contact_id, datetime.combine(day, datetime.min.time()), amount, status))


D1, D2 = date(2026, 7, 1), date(2026, 7, 2)


@pytest.fixture()
def tiny(pg, schema):
    b = Builder(pg, schema)
    b.listing(1, "Electronics")
    b.listing(2, "Clothing")
    # day 1
    b.events(D1, 1, "impression", 10); b.events(D1, 1, "view", 5); e1, e2 = b.events(D1, 1, "contact", 2)
    b.events(D1, 2, "impression", 10); b.events(D1, 2, "view", 4); (c1,) = b.events(D1, 2, "contact", 1)
    # day 2
    b.events(D2, 1, "impression", 10); b.events(D2, 1, "view", 6); _, _, e5 = b.events(D2, 1, "contact", 3)
    b.deal(D1, 1, e1, 1000, "completed")
    b.deal(D2, 1, e2, 500, "cancelled")   # contact on day 1, deal created on day 2
    b.deal(D1, 2, c1, 200, "completed")
    b.deal(D2, 1, e5, 300, "completed")
    pg.commit()
    return schema


def test_kpi_daily(pg, tiny):
    df = run_query("kpi_daily", tiny, pg).set_index("day")
    d1, d2 = df.loc[D1], df.loc[D2]
    assert (d1.impressions, d1.views, d1.contacts) == (20, 9, 3)
    assert (d1.deals_created, d1.deals_completed, float(d1.gmv)) == (2, 2, 1200.0)
    assert float(d1.contact_rate) == pytest.approx(3 / 9, abs=1e-4)
    assert float(d1.view_rate) == pytest.approx(9 / 20, abs=1e-4)
    # cohort: contacts of day 1 produced 3 deals, 2 of them completed -> 2/3 per contact
    assert float(d1.completed_per_contact) == pytest.approx(2 / 3, abs=1e-4)
    assert (d2.impressions, d2.views, d2.contacts) == (10, 6, 3)
    assert (d2.deals_created, d2.deals_completed, float(d2.gmv)) == (2, 1, 300.0)
    assert float(d2.completed_per_contact) == pytest.approx(1 / 3, abs=1e-4)
    # 7-day window = ratio of sums: (3+3) / (9+6)
    assert float(d2.contact_rate_7d) == pytest.approx(6 / 15, abs=1e-4)


def test_funnel_by_category(pg, tiny):
    df = run_query("funnel_by_category", tiny, pg).set_index("category")
    e, c = df.loc["Electronics"], df.loc["Clothing"]
    assert (e.impressions, e.views, e.contacts, e.deals, e.deals_completed, float(e.gmv)) == (20, 11, 5, 3, 2, 1300.0)
    assert (c.impressions, c.views, c.contacts, c.deals, c.deals_completed, float(c.gmv)) == (10, 4, 1, 1, 1, 200.0)
    assert float(e.deal_rate) == pytest.approx(3 / 5, abs=1e-4)
    assert list(df.index) == ["Electronics", "Clothing"]  # ordered by GMV desc


def test_category_wow(pg, schema):
    b = Builder(pg, schema)
    b.listing(1, "Electronics")
    monday = date(2026, 7, 6)
    for d in range(14):  # two full weeks: 1 deal/day in week 1, 2 deals/day in week 2
        for _ in range(1 if d < 7 else 2):
            b.deal(monday + timedelta(days=d), 1, 0, 100, "completed")
    b.deal(monday + timedelta(days=14), 1, 0, 999, "completed")  # incomplete 3rd week must be dropped
    pg.commit()
    df = run_query("category_wow", schema, pg)
    assert len(df) == 2
    w1, w2 = df.iloc[0], df.iloc[1]
    assert float(w1.gmv) == 700
    assert pd.isna(w1.gmv_wow_pct)  # no previous week
    assert float(w2.gmv) == 1400 and float(w2.gmv_wow_pct) == 100.0
    assert float(w2.gmv_share_pct) == 100.0


def test_deviation_check_flags_only_the_drop(pg, schema):
    b = Builder(pg, schema)
    b.listing(1, "Electronics")
    start = date(2026, 7, 1)
    for d in range(40):
        day = start + timedelta(days=d)
        b.events(day, 1, "view", 100)
        b.events(day, 1, "contact", 9 if d % 2 else 11)
    drop_day = start + timedelta(days=40)
    b.events(drop_day, 1, "view", 100)
    b.events(drop_day, 1, "contact", 2)
    pg.commit()
    df = run_query("deviation_check", schema, pg)
    flagged = df[df.status == "anomaly"]
    assert list(flagged.day) == [drop_day]
    row = flagged.iloc[0]
    assert float(row.z_score) < -5
    assert float(row.lost_contacts) == pytest.approx(8.0, abs=0.6)  # 100 views * ~10% baseline - 2

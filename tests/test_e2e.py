import pandas as pd
import pytest

from src.analytics import run_query


def _q(pg, sql):
    with pg.cursor() as cur:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


@pytest.fixture(scope="module")
def marts(pg):
    exists = _q(pg, "select to_regclass('analytics.mart_contact_rate_attribution') is not null as ok").ok[0]
    if not exists:
        pytest.skip("dbt marts are not built (run `make dbt` first)")
    return pg


def test_attribution_localises_incident_to_electronics_category(marts):
    df = _q(marts, "select * from analytics.mart_contact_rate_attribution where dimension = 'category'")
    top = df.sort_values("lost_contacts", ascending=False).iloc[0]
    assert top.segment == "Electronics"
    assert float(top.share_of_loss_pct) > 90
    assert -55 < float(top.rate_change_pct) < -35


def test_region_and_platform_are_not_blamed(marts):
    df = _q(marts, "select * from analytics.mart_contact_rate_attribution where dimension in ('region','platform')")

    assert df.groupby("dimension").share_of_loss_pct.max().astype(float).lt(60).all()


def test_detector_fires_on_first_incident_days(marts):
    a = _q(marts, """select event_date from analytics.mart_metric_anomalies
                     where category='Electronics' and metric='contact_rate' and status='anomaly'""")
    days = set(pd.to_datetime(a.event_date).dt.date.astype(str))
    assert "2026-09-15" in days 
    assert len(days & {f"2026-09-{d}" for d in range(15, 21)}) >= 3


def test_dbt_and_plain_sql_detectors_agree(marts):
    sql = run_query("deviation_check", "raw", marts)
    sql_set = set(zip(sql[sql.status == "anomaly"].day.astype(str), sql[sql.status == "anomaly"].category))
    dbt = _q(marts, "select event_date::text d, category from analytics.mart_metric_anomalies "
                    "where metric='contact_rate' and status='anomaly'")
    assert sql_set == set(zip(dbt.d, dbt.category))


def test_data_quality_is_clean_on_clean_data(marts):
    df = _q(marts, "select status, count(*) n from analytics.mart_data_quality group by 1")
    assert dict(zip(df.status, df.n)) == {"ok": 90}

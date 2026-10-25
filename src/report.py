from __future__ import annotations

import pandas as pd

from src.loader.load import connect

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)


def q(conn, sql: str) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql)
        return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def main() -> None:
    with connect() as c:
        kpi = q(c, "select * from analytics.mart_kpi_daily order by event_date")
        
        last, base = kpi.tail(14), kpi.iloc[-42:-14]
        print("== KPI per day: last 14 days vs the 28 days before ==")
        for col in ["impressions", "views", "contacts", "deals_completed", "gmv"]:
            a, b = float(last[col].mean()), float(base[col].mean())
            print(f"{col:16s} {a:>14,.0f}  ({(a / b - 1) * 100:+.1f}%)")
        a = last.contacts.sum() / last.views.sum(); b = base.contacts.sum() / base.views.sum()
        print(f"{'contact rate':16s} {a:>14.2%}  ({(a / b - 1) * 100:+.1f}%)")

        print("\n== Deviations in the last 14 days ==")
        an = q(c, """select event_date, category, metric, value, baseline, z_score, lost_numerator
                     from analytics.mart_metric_anomalies
                     where status = 'anomaly' and event_date > (select max(event_date) - 14 from analytics.mart_kpi_daily)
                     order by event_date, category""")
        print(an.to_string(index=False) if len(an) else "none")

        print("\n== Where is the loss? (recent window vs baseline) ==")
        att = q(c, """select dimension, segment, rate_base, rate_recent, rate_change_pct, lost_contacts, share_of_loss_pct
                      from analytics.mart_contact_rate_attribution order by dimension, lost_contacts desc""")
        for dim, g in att.groupby("dimension"):
            print(f"\n-- by {dim}"); print(g.drop(columns="dimension").head(3).to_string(index=False))

        print("\n== Data quality ==")
        print(q(c, "select status, count(*) as days from analytics.mart_data_quality group by 1").to_string(index=False))


if __name__ == "__main__":
    main()

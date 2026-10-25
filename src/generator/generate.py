from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

START_DATE = "2026-07-01"


CATEGORIES = {
    "Electronics": (0.25, 0.120, 0.20, 15_000),
    "Auto": (0.10, 0.070, 0.08, 350_000),
    "Real estate": (0.10, 0.060, 0.05, 60_000),
    "Clothing": (0.25, 0.100, 0.25, 4_000),
    "Home & garden": (0.20, 0.090, 0.18, 9_000),
    "Services": (0.10, 0.080, 0.15, 5_000),
}
REGIONS = {"Moscow": 0.30, "Saint Petersburg": 0.15, "Novosibirsk": 0.08,
           "Yekaterinburg": 0.08, "Kazan": 0.07, "Other": 0.32}

PLATFORMS = {"android": (0.45, 0.35), "ios": (0.35, 0.38), "web": (0.20, 0.30)}
DEAL_STATUSES = {"completed": 0.72, "cancelled": 0.22, "refunded": 0.06}


def _choice(rng, mapping, n, weights=None):
    keys = list(mapping)
    p = np.array([mapping[k] if np.isscalar(mapping[k]) else mapping[k][0] for k in keys], dtype=float)
    return rng.choice(keys, size=n, p=p / p.sum())


def generate(days: int = 90, n_users: int = 2000, n_listings: int = 500,
             impressions_per_day: int = 10_000, anomaly_days: int = 14,
             anomaly_factor: float = 0.55, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(START_DATE)
    end = start + pd.Timedelta(days=days)

    users = pd.DataFrame({
        "user_id": np.arange(1, n_users + 1),
        "region": _choice(rng, REGIONS, n_users),
        "platform": _choice(rng, PLATFORMS, n_users),
        "registered_at": start - pd.to_timedelta(rng.integers(1, 700, n_users), unit="D"),
    })

    cats = _choice(rng, {k: v[0] for k, v in CATEGORIES.items()}, n_listings)
    listings = pd.DataFrame({
        "listing_id": np.arange(1, n_listings + 1),
        "seller_id": rng.integers(1, n_users + 1, n_listings),
        "category": cats,
        "region": _choice(rng, REGIONS, n_listings),
        "price": [round(float(rng.lognormal(np.log(CATEGORIES[c][3]), 0.6)), 2) for c in cats],
        "created_at": start - pd.to_timedelta(rng.integers(1, 120, n_listings), unit="D"),
    })
    popularity = rng.lognormal(0, 0.8, n_listings)
    popularity /= popularity.sum()

    daily = np.array([rng.poisson(impressions_per_day * (1.12 if (start + pd.Timedelta(days=d)).weekday() >= 5 else 1.0))
                      for d in range(days)])
    day_idx = np.repeat(np.arange(days), daily)
    n = len(day_idx)
    ts = start + pd.to_timedelta(day_idx, unit="D") + pd.to_timedelta(rng.integers(0, 86_400, n), unit="s")
    uid = rng.integers(1, n_users + 1, n)
    lid = rng.choice(listings["listing_id"].to_numpy(), size=n, p=popularity)
    plat = users["platform"].to_numpy()[uid - 1]
    cat = listings["category"].to_numpy()[lid - 1]
    imp = pd.DataFrame({"event_ts": ts, "user_id": uid, "listing_id": lid, "event_type": "impression",
                        "platform": plat, "_cat": cat, "_day": day_idx})

    p_view = pd.Series(plat).map({k: v[1] for k, v in PLATFORMS.items()}).to_numpy()
    views = imp[rng.random(n) < p_view].copy()
    views["event_type"] = "view"
    views["event_ts"] += pd.to_timedelta(rng.integers(1, 60, len(views)), unit="s")

    p_contact = views["_cat"].map({k: v[1] for k, v in CATEGORIES.items()}).to_numpy().copy()
    incident = (views["_cat"].to_numpy() == "Electronics") & (views["_day"].to_numpy() >= days - anomaly_days)
    p_contact[incident] *= anomaly_factor
    contacts = views[rng.random(len(views)) < p_contact].copy()
    contacts["event_type"] = "contact"
    contacts["event_ts"] += pd.to_timedelta(rng.integers(10, 600, len(contacts)), unit="s")

    events = pd.concat([imp, views, contacts], ignore_index=True)
    events = events[events["event_ts"] < end].sort_values("event_ts", kind="stable").reset_index(drop=True)
    events.insert(0, "event_id", np.arange(1, len(events) + 1))

    c = events[events["event_type"] == "contact"]
    p_deal = c["_cat"].map({k: v[2] for k, v in CATEGORIES.items()}).to_numpy()
    d = c[rng.random(len(c)) < p_deal]
    price = listings["price"].to_numpy()[d["listing_id"].to_numpy() - 1]
    deals = pd.DataFrame({
        "listing_id": d["listing_id"].to_numpy(),
        "buyer_id": d["user_id"].to_numpy(),
        "contact_event_id": d["event_id"].to_numpy(),
        "created_at": (d["event_ts"] + pd.to_timedelta(rng.exponential(18, len(d)), unit="h")).dt.floor("s").to_numpy(),
        "amount": (price * rng.uniform(0.9, 1.0, len(d))).round(2),
        "status": _choice(rng, DEAL_STATUSES, len(d)),
    })
    deals = deals[deals["created_at"] < end].sort_values("created_at", kind="stable").reset_index(drop=True)
    deals.insert(0, "deal_id", np.arange(1, len(deals) + 1))

    events = events.drop(columns=["_cat", "_day"])
    return {"users": users, "listings": listings, "events": events, "deals": deals}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--impressions-per-day", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tables = generate(days=a.days, impressions_per_day=a.impressions_per_day, seed=a.seed)
    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)
        print(f"{name:9s} {len(df):>9,} rows -> {out / f'{name}.csv'}")


if __name__ == "__main__":
    main()

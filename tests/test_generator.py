import pandas as pd
import pytest

from src.generator.generate import generate


@pytest.fixture(scope="module")
def data():
    return generate(days=40, n_users=300, n_listings=80, impressions_per_day=3000, anomaly_days=14, seed=7)


def test_reproducible():
    a = generate(days=5, impressions_per_day=200, seed=1)["events"]
    b = generate(days=5, impressions_per_day=200, seed=1)["events"]
    pd.testing.assert_frame_equal(a, b)


def test_keys_and_references(data):
    ev, deals, listings, users = data["events"], data["deals"], data["listings"], data["users"]
    assert ev.event_id.is_unique and deals.deal_id.is_unique
    assert set(ev.listing_id) <= set(listings.listing_id)
    assert set(ev.user_id) <= set(users.user_id)
    assert set(deals.contact_event_id) <= set(ev.loc[ev.event_type == "contact", "event_id"])
    assert set(deals.status) <= {"completed", "cancelled", "refunded"}
    assert (deals.amount > 0).all()


def test_funnel_is_monotonic(data):
    counts = data["events"].event_type.value_counts()
    assert counts["impression"] > counts["view"] > counts["contact"] > len(data["deals"])


def test_controlled_incident_only_hits_electronics(data):
    ev = data["events"].merge(data["listings"][["listing_id", "category"]], on="listing_id")
    ev["day"] = ev.event_ts.dt.floor("D")
    cutoff = ev.day.min() + pd.Timedelta(days=40 - 14)
    ev["period"] = (ev.day >= cutoff).map({False: "before", True: "incident"})

    def contact_rate(cat):
        s = ev[ev.category == cat].groupby(["period", "event_type"]).size().unstack(fill_value=0)
        return (s["contact"] / s["view"]).to_dict()

    el = contact_rate("Electronics")
    assert el["incident"] / el["before"] < 0.7
    cl = contact_rate("Clothing")
    assert 0.8 < cl["incident"] / cl["before"] < 1.2

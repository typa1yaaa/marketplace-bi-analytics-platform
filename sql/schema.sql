CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.users (
    user_id INTEGER PRIMARY KEY,
    region TEXT NOT NULL,
    platform TEXT NOT NULL,
    registered_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.listings (
    listing_id INTEGER PRIMARY KEY,
    seller_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    region TEXT NOT NULL,
    price NUMERIC(14,2) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.events (
    event_id BIGINT NOT NULL,
    event_ts TIMESTAMP NOT NULL,
    user_id INTEGER NOT NULL,
    listing_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    platform TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.deals (
    deal_id BIGINT PRIMARY KEY,
    listing_id INTEGER NOT NULL,
    buyer_id INTEGER NOT NULL,
    contact_event_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_events_ts ON raw.events (event_ts);
CREATE INDEX IF NOT EXISTS ix_events_listing ON raw.events (listing_id);
CREATE INDEX IF NOT EXISTS ix_deals_created ON raw.deals (created_at);

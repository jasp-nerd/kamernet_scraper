-- Kamernet Dashboard Database Schema
-- Run against Vercel Postgres (Neon) to create tables

-- Core listings table
CREATE TABLE listings (
    listing_id              INTEGER PRIMARY KEY,
    street                  TEXT,
    city                    TEXT,
    city_slug               TEXT,
    street_slug             TEXT,
    postal_code             TEXT,
    house_number            TEXT,
    house_number_addition   TEXT,
    listing_type            SMALLINT,
    furnishing_id           SMALLINT,
    total_rental_price      INTEGER,
    surface_area            INTEGER,
    deposit                 INTEGER,
    utilities_included      BOOLEAN,
    num_bedrooms            SMALLINT,
    num_rooms               SMALLINT,
    energy_label_id         SMALLINT,
    pets_allowed            BOOLEAN,
    smoking_allowed         BOOLEAN,
    registration_allowed    BOOLEAN,
    min_age                 SMALLINT,
    max_age                 SMALLINT,
    suitable_for_persons    SMALLINT,
    availability_start      DATE,
    availability_end        DATE,
    detailed_title          TEXT,
    detailed_description    TEXT,
    thumbnail_url           TEXT,
    full_preview_image_url  TEXT,
    additional_images       JSONB,
    landlord_name           TEXT,
    landlord_verified       BOOLEAN DEFAULT FALSE,
    landlord_response_rate  SMALLINT,
    landlord_response_time  TEXT,
    landlord_member_since   TIMESTAMPTZ,
    landlord_last_seen      TIMESTAMPTZ,
    landlord_active_listings SMALLINT,
    create_date             TIMESTAMPTZ,
    publish_date            TIMESTAMPTZ,
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disappeared_at          TIMESTAMPTZ,
    is_new_advert           BOOLEAN DEFAULT FALSE,
    is_top_advert           BOOLEAN DEFAULT FALSE,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_listings_price ON listings (total_rental_price);
CREATE INDEX idx_listings_type ON listings (listing_type);
CREATE INDEX idx_listings_city ON listings (city);
CREATE INDEX idx_listings_first_seen ON listings (first_seen_at);
CREATE INDEX idx_listings_last_seen ON listings (last_seen_at);
CREATE INDEX idx_listings_active ON listings (disappeared_at) WHERE disappeared_at IS NULL;
CREATE INDEX idx_listings_surface_area ON listings (surface_area);

-- Price change tracking
CREATE TABLE listing_snapshots (
    id                  SERIAL PRIMARY KEY,
    listing_id          INTEGER NOT NULL REFERENCES listings(listing_id),
    total_rental_price  INTEGER,
    surface_area        INTEGER,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_snapshots_listing ON listing_snapshots (listing_id);
CREATE INDEX idx_snapshots_captured ON listing_snapshots (captured_at);

-- Telegram subscriber management
CREATE TABLE telegram_subscribers (
    chat_id             BIGINT PRIMARY KEY,
    username            TEXT,
    first_name          TEXT,
    subscribed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- AI scoring columns (added via migration)
-- ALTER TABLE listings ADD COLUMN ai_score INTEGER;
-- ALTER TABLE listings ADD COLUMN ai_score_reasoning TEXT;
-- CREATE INDEX idx_listings_ai_score ON listings (ai_score) WHERE ai_score IS NOT NULL;

-- Scraper observability
CREATE TABLE scrape_runs (
    id              SERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    total_found     INTEGER DEFAULT 0,
    new_found       INTEGER DEFAULT 0,
    errors          TEXT
);

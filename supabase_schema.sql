-- ============================================
-- eBay Market Pricing Intelligence — Supabase Schema
-- Pivot: active listings (Browse API), bukan sold listings
-- ============================================

-- 1. RAW TABLE — simpan full response Browse API, tak dedup
CREATE TABLE raw_ebay_listings (
    id SERIAL PRIMARY KEY,
    item_id TEXT,
    raw_json JSONB,
    scraped_at TIMESTAMP DEFAULT NOW()
);

-- 2. CLEAN TABLE — hasil transform, dedup by item_id + snapshot_date
-- Guna composite key sebab listing sama boleh muncul lagi esok (price tracking over time)
CREATE TABLE ebay_listings (
    id SERIAL PRIMARY KEY,
    item_id TEXT NOT NULL,
    listing_title TEXT,
    category TEXT,
    price NUMERIC,
    shipping_cost NUMERIC,
    total_price NUMERIC,          -- price + shipping_cost
    condition TEXT,
    seller_location TEXT,
    item_creation_date DATE,      -- bila listing pertama dibuat (dari API)
    snapshot_date DATE NOT NULL,  -- tarikh scrape run (untuk trend over time)
    price_bucket TEXT,            -- Low/Mid/High, compute lepas price clean
    scraped_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (item_id, snapshot_date)  -- elak duplicate row untuk hari sama
);

-- Index untuk query cepat (Power BI filter by category/date selalu)
CREATE INDEX idx_ebay_category ON ebay_listings (category);
CREATE INDEX idx_ebay_snapshot_date ON ebay_listings (snapshot_date);

-- ============================================
-- Nota field mapping (sold → active pivot):
-- sold_price       -> price
-- sold_date        -> snapshot_date (tarikh scrape, bukan tarikh jual)
-- sold_month/year  -> derive dari snapshot_date dalam Power BI (DAX), tak perlu column sendiri
-- ============================================

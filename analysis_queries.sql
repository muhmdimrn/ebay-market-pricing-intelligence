-- ============================================
-- eBay Market Pricing Intelligence — Analysis Queries
-- Tunjuk skill: JOIN, CTE, Window Function, Aggregate, Subquery
-- ============================================

-- 1. RANK kategori by average price (Window Function)
-- Guna kalau nak tahu ranking kategori ikut harga tanpa perlu sort manual
SELECT
    category,
    ROUND(AVG(price), 2) AS avg_price,
    RANK() OVER (ORDER BY AVG(price) DESC) AS price_rank
FROM ebay_listings
GROUP BY category
ORDER BY price_rank;


-- 2. Price percentile per kategori (Window Function - NTILE)
-- Segmentasi listing dalam setiap kategori jadi 4 quartile ikut harga
SELECT
    item_id,
    listing_title,
    category,
    price,
    NTILE(4) OVER (PARTITION BY category ORDER BY price) AS price_quartile
FROM ebay_listings;


-- 3. Day-over-day price change per kategori (CTE + Window Function LAG)
-- Compare avg price hari ni vs hari sebelum, per kategori
WITH daily_avg AS (
    SELECT
        category,
        snapshot_date,
        ROUND(AVG(price), 2) AS avg_price
    FROM ebay_listings
    GROUP BY category, snapshot_date
)
SELECT
    category,
    snapshot_date,
    avg_price,
    LAG(avg_price) OVER (PARTITION BY category ORDER BY snapshot_date) AS previous_avg_price,
    ROUND(
        (avg_price - LAG(avg_price) OVER (PARTITION BY category ORDER BY snapshot_date))
        / NULLIF(LAG(avg_price) OVER (PARTITION BY category ORDER BY snapshot_date), 0) * 100,
        2
    ) AS pct_change
FROM daily_avg
ORDER BY category, snapshot_date;


-- 4. JOIN raw dan clean table — audit berapa row hilang semasa transform
-- Berguna untuk data quality check (berapa row raw yang tak lepas clean)
SELECT
    r.item_id AS raw_item_id,
    r.raw_json->>'price' AS raw_price,
    c.item_id AS clean_item_id,
    c.price AS clean_price
FROM raw_ebay_listings r
LEFT JOIN ebay_listings c
    ON r.item_id = c.item_id
    AND (r.raw_json->>'snapshot_date') = c.snapshot_date::text
WHERE c.item_id IS NULL;  -- row yang ada dalam raw tapi tak masuk clean (invalid/skip)


-- 5. Top 3 listing termahal per kategori (Window Function + Subquery)
-- Guna ROW_NUMBER untuk ambik top N per group
WITH ranked_listings AS (
    SELECT
        item_id,
        listing_title,
        category,
        price,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC) AS rn
    FROM ebay_listings
)
SELECT item_id, listing_title, category, price
FROM ranked_listings
WHERE rn <= 3
ORDER BY category, price DESC;


-- 6. Kategori dengan price spread paling tinggi (Aggregate + HAVING)
-- Cari kategori yang ada variasi harga paling besar (max - min)
SELECT
    category,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    MAX(price) - MIN(price) AS price_spread,
    COUNT(*) AS total_listing
FROM ebay_listings
GROUP BY category
HAVING COUNT(*) > 100  -- elak kategori dengan sample size terlalu kecil
ORDER BY price_spread DESC;


-- 7. Correlation semak: adakah free shipping ada kaitan dengan harga tinggi?
-- (Subquery + CASE WHEN)
SELECT
    CASE
        WHEN shipping_cost = 0 THEN 'Free Shipping'
        ELSE 'Paid Shipping'
    END AS shipping_type,
    ROUND(AVG(price), 2) AS avg_price,
    COUNT(*) AS total_listing
FROM ebay_listings
GROUP BY shipping_type;

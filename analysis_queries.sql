-- ============================================
-- eBay Market Pricing Intelligence, Analysis Queries
-- Demonstrates: JOIN, CTE, Window Functions, Aggregate, Subquery
-- ============================================

-- 1. Rank categories by average price (Window Function)
-- Useful for ranking categories by price without manual sorting
SELECT
    category,
    ROUND(AVG(price), 2) AS avg_price,
    RANK() OVER (ORDER BY AVG(price) DESC) AS price_rank
FROM ebay_listings
GROUP BY category
ORDER BY price_rank;


-- 2. Price percentile within each category (Window Function, NTILE)
-- Splits listings within each category into 4 quartiles by price
SELECT
    item_id,
    listing_title,
    category,
    price,
    NTILE(4) OVER (PARTITION BY category ORDER BY price) AS price_quartile
FROM ebay_listings;


-- 3. Day-over-day price change per category (CTE + Window Function LAG)
-- Compares today's average price to the previous day, per category
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


-- 4. JOIN raw and clean tables, data quality audit
-- Finds rows that exist in raw but did not make it into the clean table
SELECT
    r.item_id AS raw_item_id,
    r.raw_json->>'price' AS raw_price,
    c.item_id AS clean_item_id,
    c.price AS clean_price
FROM raw_ebay_listings r
LEFT JOIN ebay_listings c
    ON r.item_id = c.item_id
    AND (r.raw_json->>'snapshot_date') = c.snapshot_date::text
WHERE c.item_id IS NULL;  -- rows present in raw but skipped during transform


-- 5. Top 3 highest priced listings per category (Window Function + CTE)
-- Uses ROW_NUMBER to get the top N rows per group
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


-- 6. Category with the widest price spread (Aggregate + HAVING)
-- Finds which category has the biggest gap between its cheapest and most expensive listing
SELECT
    category,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    MAX(price) - MIN(price) AS price_spread,
    COUNT(*) AS total_listing
FROM ebay_listings
GROUP BY category
HAVING COUNT(*) > 100  -- exclude categories with too small a sample size
ORDER BY price_spread DESC;


-- 7. Does free shipping correlate with higher prices? (CASE WHEN + Aggregate)
SELECT
    CASE
        WHEN shipping_cost = 0 THEN 'Free Shipping'
        ELSE 'Paid Shipping'
    END AS shipping_type,
    ROUND(AVG(price), 2) AS avg_price,
    COUNT(*) AS total_listing
FROM ebay_listings
GROUP BY shipping_type;

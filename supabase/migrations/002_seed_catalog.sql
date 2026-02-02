-- Seed catalog adjustments for no-scrape mode

-- Allow unknown price/stock for parts (no scraping)
ALTER TABLE parts
  ALTER COLUMN price_cents DROP NOT NULL,
  ALTER COLUMN stock_status DROP NOT NULL,
  ALTER COLUMN stock_status SET DEFAULT 'unknown';

-- Optional curated metadata fields for seed catalog
ALTER TABLE parts
  ADD COLUMN IF NOT EXISTS canonical_url TEXT,
  ADD COLUMN IF NOT EXISTS install_summary TEXT,
  ADD COLUMN IF NOT EXISTS common_symptoms TEXT[],
  ADD COLUMN IF NOT EXISTS notes TEXT;

-- Backfill canonical_url from product_url when available
UPDATE parts
SET canonical_url = product_url
WHERE canonical_url IS NULL AND product_url IS NOT NULL;


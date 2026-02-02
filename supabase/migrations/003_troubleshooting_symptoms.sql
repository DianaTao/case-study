-- Add troubleshooting symptoms support to parts table
-- This allows us to map symptoms to parts for intelligent recommendations

-- Add troubleshooting_symptoms column (array of strings)
ALTER TABLE parts ADD COLUMN IF NOT EXISTS troubleshooting_symptoms TEXT[];

-- Add manufactured_by column
ALTER TABLE parts ADD COLUMN IF NOT EXISTS manufactured_by TEXT;

-- Create index for symptom searches
CREATE INDEX IF NOT EXISTS idx_parts_troubleshooting_symptoms 
ON parts USING GIN (troubleshooting_symptoms);

-- Create a normalized symptoms table for better querying
CREATE TABLE IF NOT EXISTS part_symptoms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    partselect_number TEXT NOT NULL REFERENCES parts(partselect_number) ON DELETE CASCADE,
    symptom TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE(partselect_number, symptom)
);

-- Index for fast symptom lookup
CREATE INDEX IF NOT EXISTS idx_part_symptoms_symptom ON part_symptoms(symptom);
CREATE INDEX IF NOT EXISTS idx_part_symptoms_ps_number ON part_symptoms(partselect_number);

-- Function to normalize symptom text for matching
CREATE OR REPLACE FUNCTION normalize_symptom(symptom_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN LOWER(TRIM(REGEXP_REPLACE(symptom_text, '\s+', ' ', 'g')));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- View for symptom-to-part reverse index
CREATE OR REPLACE VIEW symptom_part_index AS
SELECT 
    normalize_symptom(ps.symptom) as normalized_symptom,
    ps.symptom as original_symptom,
    ps.partselect_number,
    p.name as part_name,
    p.appliance_type,
    p.brand,
    p.price_cents,
    p.stock_status
FROM part_symptoms ps
JOIN parts p ON ps.partselect_number = p.partselect_number;

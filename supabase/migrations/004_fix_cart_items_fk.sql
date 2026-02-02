-- Add foreign key constraint from cart_items to parts
-- This allows proper joins and maintains referential integrity

-- Add foreign key if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'cart_items_partselect_number_fkey'
    ) THEN
        ALTER TABLE cart_items 
        ADD CONSTRAINT cart_items_partselect_number_fkey 
        FOREIGN KEY (partselect_number) 
        REFERENCES parts(partselect_number) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_cart_items_partselect_number 
ON cart_items(partselect_number);

-- Verify the constraint exists
SELECT 
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE conname = 'cart_items_partselect_number_fkey';

"""
Add availability keywords tracking table.
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        # Create table for tracking availability keywords
        """
        CREATE TABLE availability_keywords (
            id SERIAL PRIMARY KEY,
            retailer_id INTEGER NOT NULL REFERENCES retailers(id) ON DELETE CASCADE,
            keyword TEXT NOT NULL,
            language VARCHAR(10),
            indicates_in_stock BOOLEAN,
            first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            occurrence_count INTEGER DEFAULT 1,
            is_configured BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(retailer_id, keyword)
        );

        -- Create index for faster lookups
        CREATE INDEX idx_availability_keywords_retailer ON availability_keywords(retailer_id);
        
        -- Create function to update last_seen_at and occurrence_count
        CREATE OR REPLACE FUNCTION update_availability_keyword() RETURNS trigger AS $$
        BEGIN
            UPDATE availability_keywords 
            SET last_seen_at = CURRENT_TIMESTAMP,
                occurrence_count = occurrence_count + 1
            WHERE retailer_id = NEW.retailer_id AND keyword = NEW.keyword;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        -- Create trigger to update last_seen_at and occurrence_count
        CREATE TRIGGER tr_update_availability_keyword
        AFTER INSERT ON availability_keywords
        FOR EACH ROW
        WHEN (NEW.id IS NOT NULL)
        EXECUTE FUNCTION update_availability_keyword();
        """,
        # Rollback
        """
        DROP TRIGGER IF EXISTS tr_update_availability_keyword ON availability_keywords;
        DROP FUNCTION IF EXISTS update_availability_keyword();
        DROP TABLE IF EXISTS availability_keywords;
        """
    )
] 
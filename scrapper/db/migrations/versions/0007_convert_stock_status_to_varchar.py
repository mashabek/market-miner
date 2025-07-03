from yoyo import step

__depends__ = {'0006_add_availability_keywords'}

steps = [
    step(
        """
        -- First, alter the column to be VARCHAR while preserving the existing values
        ALTER TABLE scraped_data 
        ALTER COLUMN stock_status TYPE VARCHAR(20) 
        USING stock_status::text;

        -- Then drop the enum type as it's no longer needed
        DROP TYPE stock_status;
        """,
        """
        -- Recreate the enum type
        CREATE TYPE stock_status AS ENUM ('IN_STOCK', 'OUT_OF_STOCK', 'UNKNOWN');
        
        -- Convert the column back to enum type
        ALTER TABLE scraped_data 
        ALTER COLUMN stock_status TYPE stock_status 
        USING stock_status::stock_status;
        """
    )
] 
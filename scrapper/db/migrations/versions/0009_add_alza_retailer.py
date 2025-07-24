from yoyo import step

__depends__ = {'0008_update_stock_info_schema'}

steps = [
    step(
        # Apply SQL - insert Alza retailer
        """
        INSERT INTO retailers (name, type, country)
        VALUES ('Alza', 'DIRECT_RETAILER', 'HU')
        ON CONFLICT (name) DO UPDATE 
        SET 
            type = EXCLUDED.type,
            country = EXCLUDED.country,
            updated_at = CURRENT_TIMESTAMP;
        """,
        # Rollback SQL - delete Alza retailer
        """
        DELETE FROM retailers 
        WHERE name = 'Alza';
        """
    )
] 
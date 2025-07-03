from yoyo import step

__depends__ = {'0001_init_schema'}

steps = [
    step(
        # Apply SQL - insert retailers
        """
        INSERT INTO retailers (name, type, country)
        VALUES 
            ('Datart', 'DIRECT_RETAILER', 'CZ'),
            ('Euronics', 'DIRECT_RETAILER', 'CZ'),
            ('MediaMarkt', 'DIRECT_RETAILER', 'HU'),
            ('Pilulka', 'DIRECT_RETAILER', 'CZ'),
            ('Planeo', 'DIRECT_RETAILER', 'CZ'),
            ('Telekom', 'DIRECT_RETAILER', 'CZ'),
            ('Zbozi', 'PRICE_COMPARER', 'CZ')
        ON CONFLICT (name) DO UPDATE 
        SET 
            type = EXCLUDED.type,
            country = EXCLUDED.country,
            updated_at = CURRENT_TIMESTAMP;
        """,
        # Rollback SQL - delete retailers
        """
        DELETE FROM retailers 
        WHERE name IN (
            'Datart', 'Euronics', 'MediaMarkt', 'Pilulka', 
            'Planeo', 'Telekom', 'Zbozi'
        );
        """
    )
] 
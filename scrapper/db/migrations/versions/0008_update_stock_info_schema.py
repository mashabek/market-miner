"""
Migration to update stock info schema.
Removes stock_status and stock_quantity columns, adds stock_info JSONB column.
"""

from yoyo import step

__depends__ = {'0007_convert_stock_status_to_varchar'}

steps = [
    # Add new stock_info column
    step(
        "ALTER TABLE scraped_data ADD COLUMN stock_info JSONB DEFAULT '[]'::jsonb",
        "ALTER TABLE scraped_data DROP COLUMN stock_info"
    ),
    
    # Copy data from old columns to new format
    step("""
        UPDATE scraped_data 
        SET stock_info = jsonb_build_array(
            jsonb_build_object(
                'status', stock_status,
                'delivery_method', 'HOME_DELIVERY',
                'store_count', stock_quantity
            )
        )
        WHERE stock_status IS NOT NULL OR stock_quantity IS NOT NULL
    """),
    
    # Drop old columns
    step(
        """
        ALTER TABLE scraped_data 
        DROP COLUMN stock_status,
        DROP COLUMN stock_quantity
        """,
        """
        ALTER TABLE scraped_data 
        ADD COLUMN stock_status VARCHAR(50),
        ADD COLUMN stock_quantity INTEGER
        """
    )
] 
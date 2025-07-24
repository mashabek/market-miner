from yoyo import step

__depends__ = {'0011_add_urls_column'}

steps = [
    step(
        """
        -- Drop old tables in correct order (dependencies first)
        DROP TABLE IF EXISTS scraped_data CASCADE;
        DROP TABLE IF EXISTS product_retailers CASCADE; 
        DROP TABLE IF EXISTS products CASCADE;
        """,
        """
        -- Rollback: Recreate basic structure (minimal - data will be lost)
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            brand VARCHAR(100),
            category_id INTEGER REFERENCES categories(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE scraped_data (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            retailer_id INTEGER NOT NULL REFERENCES retailers(id),
            url TEXT NOT NULL,
            success BOOLEAN NOT NULL DEFAULT false,
            name VARCHAR(255) NOT NULL,
            price DECIMAL(12, 2),
            currency VARCHAR(10),
            stock_info JSONB DEFAULT '[]'::jsonb,
            extended_info JSONB,
            scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
]

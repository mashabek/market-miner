from yoyo import step

__depends__ = {'0012_drop_old_tables'}

steps = [
    step(
        """
        -- Create retailer_products table (primary entity)
        CREATE TABLE retailer_products (
            id SERIAL PRIMARY KEY,
            retailer_id INTEGER NOT NULL REFERENCES retailers(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            retailer_sku VARCHAR(100),
            
            -- Product information as provided by retailer
            name VARCHAR(500) NOT NULL,
            brand VARCHAR(100),
            description TEXT,
            category_path VARCHAR(500), -- Raw category from retailer
            category_id INTEGER REFERENCES categories(id), -- Normalized category (optional)
            
            -- Current pricing and availability
            current_price DECIMAL(12, 2),
            currency VARCHAR(3),
            stock_info JSONB DEFAULT '[]'::jsonb,
            
            -- Product attributes as provided by retailer
            specifications JSONB DEFAULT '{}'::jsonb,
            images TEXT[],
            
            -- Product variants (colors, sizes, etc.)
            variants JSONB DEFAULT '[]'::jsonb,
            
            -- Retailer-specific metadata
            retailer_metadata JSONB DEFAULT '{}'::jsonb, -- ratings, reviews, etc.
            
            -- Status tracking
            is_active BOOLEAN DEFAULT true,
            last_scraped_at TIMESTAMP WITH TIME ZONE,
            last_successful_scrape_at TIMESTAMP WITH TIME ZONE,
            scrape_error_count INTEGER DEFAULT 0,
            
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            
            CONSTRAINT unique_retailer_url UNIQUE (retailer_id, url)
        );

        -- Create indexes for performance
        CREATE INDEX idx_retailer_products_retailer_id ON retailer_products(retailer_id);
        CREATE INDEX idx_retailer_products_brand ON retailer_products(brand);
        CREATE INDEX idx_retailer_products_category ON retailer_products(category_id);
        CREATE INDEX idx_retailer_products_active ON retailer_products(is_active);
        CREATE INDEX idx_retailer_products_last_scraped ON retailer_products(last_scraped_at);
        CREATE INDEX idx_retailer_products_name ON retailer_products USING gin(to_tsvector('english', name));
        """,
        """
        DROP INDEX IF EXISTS idx_retailer_products_name;
        DROP INDEX IF EXISTS idx_retailer_products_last_scraped;
        DROP INDEX IF EXISTS idx_retailer_products_active;
        DROP INDEX IF EXISTS idx_retailer_products_category;
        DROP INDEX IF EXISTS idx_retailer_products_brand;
        DROP INDEX IF EXISTS idx_retailer_products_retailer_id;
        DROP TABLE IF EXISTS retailer_products CASCADE;
        """
    )
]

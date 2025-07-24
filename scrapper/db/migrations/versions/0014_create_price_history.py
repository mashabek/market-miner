from yoyo import step

__depends__ = {'0013_create_retailer_products'}

steps = [
    step(
        """
        -- Create price_history table for time series data
        CREATE TABLE price_history (
            id SERIAL PRIMARY KEY,
            retailer_product_id INTEGER NOT NULL REFERENCES retailer_products(id) ON DELETE CASCADE,
            price DECIMAL(12, 2),
            currency VARCHAR(3),
            stock_info JSONB DEFAULT '[]'::jsonb,
            offers JSONB DEFAULT '[]'::jsonb, -- For aggregators with multiple offers
            scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
            
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );

        -- Optimize for time series queries
        CREATE INDEX idx_price_history_product_time ON price_history(retailer_product_id, scraped_at DESC);
        CREATE INDEX idx_price_history_scraped_at ON price_history(scraped_at DESC);
        """,
        """
        DROP INDEX IF EXISTS idx_price_history_scraped_at;
        DROP INDEX IF EXISTS idx_price_history_product_time;
        DROP TABLE IF EXISTS price_history CASCADE;
        """
    )
]

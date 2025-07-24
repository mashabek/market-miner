from yoyo import step

__depends__ = {'0009_add_alza_retailer'}

steps = [
    step(
        '''
        CREATE TABLE product_retailers (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            retailer_id INTEGER NOT NULL REFERENCES retailers(id) ON DELETE CASCADE,
            retailer_sku VARCHAR(100),
            url TEXT,
            extra_data JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_product_retailer UNIQUE (product_id, retailer_id)
        );
        CREATE INDEX idx_product_retailers_product_id ON product_retailers(product_id);
        CREATE INDEX idx_product_retailers_retailer_id ON product_retailers(retailer_id);
        ''',
        '''
        DROP INDEX IF EXISTS idx_product_retailers_product_id;
        DROP INDEX IF EXISTS idx_product_retailers_retailer_id;
        DROP TABLE IF EXISTS product_retailers;
        '''
    )
]

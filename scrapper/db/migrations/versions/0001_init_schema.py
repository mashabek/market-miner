from yoyo import step

__depends__ = {}

steps = [
    # Enable ltree extension
    step(
        "CREATE EXTENSION IF NOT EXISTS ltree",
        "DROP EXTENSION IF EXISTS ltree"
    ),

    # Create enum types
    step(
        """
        CREATE TYPE retailer_type AS ENUM ('DIRECT_RETAILER', 'PRICE_COMPARER');
        CREATE TYPE currency AS ENUM ('HUF', 'CZK');
        CREATE TYPE stock_status AS ENUM ('IN_STOCK', 'OUT_OF_STOCK', 'UNKNOWN');
        """,
        """
        DROP TYPE IF EXISTS stock_status;
        DROP TYPE IF EXISTS currency;
        DROP TYPE IF EXISTS retailer_type;
        """
    ),

    # Create retailers table
    step(
        """
        CREATE TABLE retailers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            type retailer_type NOT NULL,
            country CHAR(2) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "DROP TABLE IF EXISTS retailers;"
    ),

    # Create categories table
    step(
        """
        CREATE TABLE categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            parent_id INTEGER REFERENCES categories(id),
            path ltree NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_name_within_parent UNIQUE (name, parent_id)
        );
        CREATE INDEX idx_categories_path ON categories USING GIST (path);
        """,
        """
        DROP INDEX IF EXISTS idx_categories_path;
        DROP TABLE IF EXISTS categories;
        """
    ),

    # Create products table
    step(
        """
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            brand VARCHAR(100),
            category_id INTEGER REFERENCES categories(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_products_category_id ON products(category_id);
        """,
        """
        DROP INDEX IF EXISTS idx_products_category_id;
        DROP TABLE IF EXISTS products;
        """
    ),

    # Create scraped_data table
    step(
        """
        CREATE TABLE scraped_data (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            retailer_id INTEGER NOT NULL REFERENCES retailers(id),
            url TEXT NOT NULL UNIQUE,
            success BOOLEAN NOT NULL DEFAULT false,
            error_info JSONB,
            name VARCHAR(255) NOT NULL,
            brand VARCHAR(100),
            raw_category VARCHAR(100),
            category_id INTEGER REFERENCES categories(id),
            price DECIMAL(12, 2),
            currency currency,
            stock_status stock_status,
            stock_quantity INTEGER,
            delivery_info JSONB,
            offers JSONB,
            extended_info JSONB,
            scraped_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            
            CONSTRAINT valid_price CHECK (price > 0),
            CONSTRAINT valid_stock_quantity CHECK (stock_quantity IS NULL OR stock_quantity >= 0)
        );
        
        CREATE INDEX idx_scraped_data_product_id ON scraped_data(product_id);
        CREATE INDEX idx_scraped_data_retailer_id ON scraped_data(retailer_id);
        CREATE INDEX idx_scraped_data_category_id ON scraped_data(category_id);
        CREATE INDEX idx_scraped_data_success ON scraped_data(success);
        CREATE INDEX idx_scraped_data_scraped_at ON scraped_data(scraped_at);
        CREATE INDEX idx_scraped_data_url ON scraped_data(url);
        """,
        """
        DROP INDEX IF EXISTS idx_scraped_data_url;
        DROP INDEX IF EXISTS idx_scraped_data_scraped_at;
        DROP INDEX IF EXISTS idx_scraped_data_success;
        DROP INDEX IF EXISTS idx_scraped_data_category_id;
        DROP INDEX IF EXISTS idx_scraped_data_retailer_id;
        DROP INDEX IF EXISTS idx_scraped_data_product_id;
        DROP TABLE IF EXISTS scraped_data;
        """
    ),

    # Create timestamp update function and triggers
    step(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        CREATE TRIGGER update_retailers_updated_at
            BEFORE UPDATE ON retailers
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        CREATE TRIGGER update_categories_updated_at
            BEFORE UPDATE ON categories
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        CREATE TRIGGER update_products_updated_at
            BEFORE UPDATE ON products
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        CREATE TRIGGER update_scraped_data_updated_at
            BEFORE UPDATE ON scraped_data
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """,
        """
        DROP TRIGGER IF EXISTS update_scraped_data_updated_at ON scraped_data;
        DROP TRIGGER IF EXISTS update_products_updated_at ON products;
        DROP TRIGGER IF EXISTS update_categories_updated_at ON categories;
        DROP TRIGGER IF EXISTS update_retailers_updated_at ON retailers;
        DROP FUNCTION IF EXISTS update_updated_at_column();
        """
    )
] 
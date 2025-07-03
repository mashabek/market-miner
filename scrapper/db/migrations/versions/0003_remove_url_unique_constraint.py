from yoyo import step

__depends__ = {'0002_add_retailers'}

steps = [
    step(
        """
        DROP INDEX IF EXISTS idx_scraped_data_url;
        ALTER TABLE scraped_data DROP CONSTRAINT IF EXISTS scraped_data_url_key;
        """,
        """
        CREATE UNIQUE INDEX idx_scraped_data_url ON scraped_data(url);
        ALTER TABLE scraped_data DROP CONSTRAINT scraped_data_url_key UNIQUE (url);
        """
    )
] 
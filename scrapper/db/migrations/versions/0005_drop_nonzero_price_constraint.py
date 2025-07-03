from yoyo import step

__depends__ = {'0001_init_schema'}

steps = [
    step(
        """
        ALTER TABLE scraped_data DROP CONSTRAINT valid_price;
        """,
        """
        ALTER TABLE scraped_data ADD CONSTRAINT valid_price CHECK (price > 0);
        """
    )
] 
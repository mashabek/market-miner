from yoyo import step

__depends__ = {'0001_init_schema'}

steps = [
    step(
        """
        ALTER TABLE categories ALTER COLUMN path DROP NOT NULL;
        """,
        """
        ALTER TABLE categories ALTER COLUMN path SET NOT NULL;
        """
    )
] 
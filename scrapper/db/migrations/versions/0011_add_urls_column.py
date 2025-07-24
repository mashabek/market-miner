from yoyo import step

__depends__ = {'0010_add_product_retailers'}

steps = [
    step(
        '''
        ALTER TABLE scraped_data ADD COLUMN IF NOT EXISTS image_urls TEXT[];
        ALTER TABLE product_retailers ADD COLUMN IF NOT EXISTS image_urls TEXT[];
        ''',
        '''
        ALTER TABLE scraped_data DROP COLUMN IF EXISTS image_urls;
        ALTER TABLE product_retailers DROP COLUMN IF EXISTS image_urls;
        '''
    )
]

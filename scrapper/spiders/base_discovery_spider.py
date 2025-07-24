import scrapy
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Set, Optional, Generator

class BaseDiscoverySpider(scrapy.Spider):
    """
    Base class for discovery spiders. Handles common attributes, reporting, and utilities.
    Configure output folder and file naming via class attributes.
    """
    # Configurable output
    output_folder = 'output'
    report_filename = '{spider_name}_discovery_report.json'
    products_filename = '{spider_name}_products.json'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.discovered_products = set()
        self.discovered_categories = set()
        self.product_urls = []
        self.discovery_methods = {
            'sitemap': 0,
            'category_traversal': 0,
            'pattern_recognition': 0,
            'search_discovery': 0
        }
        # Ensure output folder exists
        os.makedirs(self.output_folder, exist_ok=True)

    def is_product_url(self, url: str) -> bool:
        """Override in subclass: Check if URL is a product page."""
        raise NotImplementedError

    def is_category_url(self, url: str) -> bool:
        """Override in subclass: Check if URL is a category page."""
        raise NotImplementedError

    def get_timestamp(self) -> str:
        return datetime.now().isoformat()

    def closed(self, reason: str) -> None:
        """Generate discovery report and save all discovered product data."""
        total_products = len(self.discovered_products)
        total_categories = len(self.discovered_categories)
        spider_name = getattr(self, 'name', 'discovery_spider')
        # Prepare report
        report = {
            'spider_name': spider_name,
            'close_reason': reason,
            'discovery_summary': {
                'total_products_discovered': total_products,
                'total_categories_discovered': total_categories,
                'discovery_methods': self.discovery_methods,
            },
            'discovered_categories': list(self.discovered_categories),
            'sample_products': list(self.discovered_products)[:50],
            'finished_at': self.get_timestamp(),
        }
        # Save report
        report_path = os.path.join(self.output_folder, self.report_filename.format(spider_name=spider_name))
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        # Save all discovered product data
        products_path = os.path.join(self.output_folder, self.products_filename.format(spider_name=spider_name))
        with open(products_path, 'w', encoding='utf-8') as f:
            json.dump(self.product_urls, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Discovery completed: {total_products} products, {total_categories} categories")
        self.logger.info(f"Discovery methods: {self.discovery_methods}")
        self.logger.info(f"Reports saved to: {report_path} and {products_path}") 
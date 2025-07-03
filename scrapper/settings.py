# Scrapy settings for scrapper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import logging
from dotenv import load_dotenv
import scrapy
import scrapy.downloadermiddlewares
import scrapy.downloadermiddlewares.redirect
import os

from scrapper.utils.logger_config import setup_logging

base_dir = os.path.dirname(__file__)
env_path = os.path.join(base_dir, ".env")
# Load environment variables
load_dotenv(env_path, encoding="utf-8")
setup_logging(log_level="INFO")

LOG_ENABLED = False
BOT_NAME = "scrapper"

SPIDER_MODULES = ["scrapper.spiders"]


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# Obey robots.txt rules - set to False since we're scraping specific product pages
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy
CONCURRENT_REQUESTS = 4

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True

HTTPERROR_ALLOWED_CODES = [300, 301, 302]

# Configure retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Configure redirect settings
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5
REDIRECT_PRIORITY_ADJUST = +2  # Give redirects slightly higher priority

# Enable cookies
COOKIES_ENABLED = True

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Configure default request headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "scrapper.middlewares.ScrapperSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.redirect.RedirectMiddleware": 550,
    "scrapper.middlewares.SeleniumMiddleware": 590,
    "scrapper.middlewares.CloudflareMiddleware": 600,
    # "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 700,
    # "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 750
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
ITEM_PIPELINES = {
   "scrapper.pipelines.ProductValidationPipeline": 300,
   "scrapper.pipelines.DatabasePipeline": 400,
}

# Enable AutoThrottle
AUTOTHROTTLE_ENABLED = False
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
FEED_EXPORT_INDENT = 2  # Pretty print JSON output

# Spider-specific settings
SPIDER_SETTINGS = {
    'mediamarkt': {
        'DOWNLOAD_DELAY': 0.3,
        'CONCURRENT_REQUESTS': 1,
    },
    'zbozi': {
        'DOWNLOAD_DELAY': 0.1,
        'CONCURRENT_REQUESTS': 8,
        'RETRY_TIMES': 5,  # More retries for aggregator site
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403],
    }
}

# # Configure output files per spider
# FEEDS = {
#     'output/%(name)s.json': {
#         'format': 'json',
#         'encoding': 'utf-8',
#         'indent': 2,
#         'overwrite': True,
#     }
# }

# Sentry Configuration
SENTRY_DSN = os.getenv('SENTRY_DSN')
SENTRY_ENVIRONMENT = os.getenv('SENTRY_ENVIRONMENT', 'development')
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '1.0'))
SENTRY_PROFILES_SAMPLE_RATE = float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '1.0'))

# Initialize Sentry
from .utils.sentry import init_sentry
init_sentry(
    dsn=SENTRY_DSN,
    environment=SENTRY_ENVIRONMENT,
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
    profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE
)

# Increase timeouts for Selenium
DOWNLOAD_TIMEOUT = 60

# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter

import logging
import time
import random
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


class ScrapperSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn't have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class ScrapperDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class CloudflareMiddleware:
    """Middleware to handle Cloudflare's anti-bot protection."""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.logger = logging.getLogger(__name__)
        
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
        
    def process_response(self, request, response, spider):
        # Check if we hit a Cloudflare challenge page
        if b'Enable JavaScript and cookies to continue' in response.body:
            self.logger.warning(f"Cloudflare protection detected on {request.url}")
            # Add a delay before retrying
            time.sleep(random.uniform(5, 10))
            # Set special headers and cookies for retry
            request.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            })
            # Don't forget to return the request to retry it
            return request
        return response


class SeleniumMiddleware:
    """Middleware to handle JavaScript-rendered pages using Selenium."""
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.driver = None
        self.logger = logging.getLogger(__name__)
        
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls(crawler)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware
    
    def _setup_driver(self):
        if not self.driver:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0')
            
            self.driver = webdriver.Firefox(options=options)
            self.driver.set_page_load_timeout(30)
    
    def process_request(self, request, spider):
        if not request.meta.get('selenium', False):
            return None
            
        try:
            if not self.driver:
                self._setup_driver()
                
            self.driver.get(request.url)
            # Wait for the page to load
            time.sleep(5)  # Give JavaScript some time to execute
            
            body = self.driver.page_source
            return HtmlResponse(
                url=request.url,
                body=body.encode('utf-8'),
                encoding='utf-8',
                request=request
            )
        except Exception as e:
            self.logger.error(f"Selenium error for {request.url}: {str(e)}")
            return None
    
    def spider_closed(self):
        """Clean up when spider closes."""
        if self.driver:
            self.driver.quit()
            self.driver = None

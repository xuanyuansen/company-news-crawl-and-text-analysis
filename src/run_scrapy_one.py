import os

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from SpiderWithScrapy.net_ease_spider import NetEaseSpider
from SpiderWithScrapy.shanghai_stock_spider import ShanghaiStockSpider
from Utils import config

if __name__ == "__main__":
    os.environ["SCRAPY_SETTINGS_MODULE"] = f"settings"
    settings = get_project_settings()
    _process = CrawlerProcess(settings)

    # _process.crawl(ShanghaiStockSpider, **config.SHANG_HAI_STOCK_COMPANY_KUAI_XUN_NEWS)
    _process.crawl(NetEaseSpider, **config.NET_EASE_MARKET_NEWS)

    _process.start()

    pass

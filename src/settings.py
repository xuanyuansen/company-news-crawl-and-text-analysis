# -*- coding: utf-8 -*-
import platform

BOT_NAME = "spider"

PYTHONHASHSEED = 10

SPIDER_MODULES = ["MarketNewsSpiderWithScrapy"]
NEWSPIDER_MODULE = "MarketNewsSpiderWithScrapy"

ROBOTSTXT_OBEY = False

# change cookie to yours
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:61.0) Gecko/20100101 Firefox/61.0"
}
# https://www.cnblogs.com/zwq-/p/10592190.html
CONCURRENT_REQUESTS = 50
COOKIES_ENABLED = False

DOWNLOAD_TIMEOUT = 3

DOWNLOAD_DELAY = 1

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": None,
    "scrapy.downloadermiddlewares.redirect.RedirectMiddleware": None,
    # 'middlewares.IPProxyMiddleware': 100,
    "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 101,
}

ITEM_PIPELINES = {
    "pipelines.MongoDBPipeline": 300,
}

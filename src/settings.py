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

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2224.3 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0; Avant Browser; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0)',
    'Mozilla/5.0 (X11; Linux i686; rv:64.0) Gecko/20100101 Firefox/64.0',
    'Mozilla/5.0 (X11; Linux i586; rv:63.0) Gecko/20100101 Firefox/63.0',
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# JQK_COOKIE="Hm_lvt_69929b9dce4c22a060bd22d703b2a280=1768203376; HMACCOUNT=AFD0AE2F27D43B12; _ga=GA1.1.1587122822.1768203378; Hm_lvt_78c58f01938e4d85eaf619eae71b4ed1=1768204342; Hm_lvt_da7579fd91e2c6fa5aeb9d1620a9b333=1768206774; Hm_lvt_d5635ca6bd339ec9a4d30e9d2be39202=1768206774; v_c=n5vqnn12wvz7exax4tow11ofcg; Hm_lpvt_69929b9dce4c22a060bd22d703b2a280=1768281365; log=; _ga_H2RK0R0681=GS2.1.s1768281354$o3$g1$t1768281817$j60$l0$h0; Hm_lpvt_da7579fd91e2c6fa5aeb9d1620a9b333=1768281970; Hm_lpvt_78c58f01938e4d85eaf619eae71b4ed1=1768281970; Hm_lpvt_d5635ca6bd339ec9a4d30e9d2be39202=1768281970; v=A3cQXpIa0ivCOVanbib6TfUsBmDEPEuYJRDPEskkk8ateJke0Qzb7jXgX2va"  
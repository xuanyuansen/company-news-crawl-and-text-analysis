# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from ComTools.buildstocknewsdb import GenStockNewsDB
from Utils import config
from scrapy import Spider
from scrapy.http import Request
import logging
# from functools import wraps


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


# def singleton(f):
#     instance = {}
#
#     @wraps(f)
#     def get_instance(*args, **kwargs):
#         if f not in instance:
#             instance[f] = f(*args, **kwargs)
#         return instance[f]
#
#     return get_instance
#
#
# @singleton
class BaseSpider(Spider):
    def __init__(self,):
        self.GenStockNewsDB = GenStockNewsDB(force_train_model=False)
        self.name_code_df = self.GenStockNewsDB.database.get_data(
            config.STOCK_DATABASE_NAME,
            config.COLLECTION_NAME_STOCK_BASIC_INFO,
            keys=["name", "code"],
        )
        super().__init__()

    def start_requests(self):
        start_url = getattr(self, 'start_url')
        end_page = getattr(self, 'end_page')
        logging.info(start_url)
        url_start = [start_url]
        urls_plus = [start_url.replace(".html", "_{0}.html".format(xid)) for xid in range(1, end_page)]
        urls = url_start + urls_plus
        for url in urls:
            yield Request(url, callback=self.parse)

    def parse(self, response):
        pass


pass

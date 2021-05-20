# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import time
import logging
from Utils import config
from MarketNewsSpider.StockInfoSpyder import StockInfoSpyder
import os
import sys

sys.path.append(os.getcwd())


cn_stock_info_spyder = StockInfoSpyder(config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO)
logging.info("start crawling {} ...".format(
    "stock code info"
))
cn_stock_info_spyder.get_stock_code_info()
logging.info("finished ...")
time.sleep(30)

# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import logging

from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
from Utils import config
import sys

hk_stock_info_spyder = StockInfoSpyder(
    config.HK_STOCK_DATABASE_NAME,
    config.COLLECTION_NAME_STOCK_BASIC_INFO_HK,
    joint_quant_on=False,
)
# get all name and code
max_date_hk = hk_stock_info_spyder.db_obj.find_max(
    config.HK_STOCK_DATABASE_NAME, "00156", "date"
)
logging.info("max date is {}".format(max_date_hk))

hk_stock_info_spyder.get_historical_hk_stock_daily_price(start_date=max_date_hk, start_symbol='00036')

cn_stock_info_spyder = StockInfoSpyder(
    config.STOCK_DATABASE_NAME,
    config.COLLECTION_NAME_STOCK_BASIC_INFO,
    joint_quant_on=False,
)
max_date_cn = cn_stock_info_spyder.db_obj.find_max(
    config.STOCK_DATABASE_NAME, "sz002181", "date"
)
logging.info("max date cn is {}".format(max_date_cn))
# hk_stock_info_spyder.get_historical_hk_stock_daily_price(start_symbol='00156')

# stock_info_spyder.update_cn_stock_money_column_using_joint_quant()
# stock_info_spyder.get_historical_price_cn_stock(start_date=sys.argv[1])
# stock_info_spyder.get_all_stock_code_info()

# stock_info_spyder.get_today_price()
pass
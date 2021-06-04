# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
from Utils import config
import sys

stock_info_spyder = StockInfoSpyder(
    config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO, joint_quant_on=True
)
# get all name and code
# stock_info_spyder.get_historical_hk_stock_daily_price(start_symbol='00156')
stock_info_spyder.update_cn_stock_money_column_using_joint_quant()
# stock_info_spyder.get_historical_price_cn_stock(start_date=sys.argv[1])
# stock_info_spyder.get_all_stock_code_info()

# stock_info_spyder.get_today_price()
pass

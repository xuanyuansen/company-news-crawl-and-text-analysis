# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from MarketNewsSpider.StockInfoSpyder import StockInfoSpyder
from Utils import config

stock_info_spyder = StockInfoSpyder(
    config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO
)
# get all name and code
stock_info_spyder.get_historical_hk_stock_daily_price(start_symbol='00156')
exit(0)
stock_info_spyder.get_all_stock_code_info()

# 指定时间段，获取历史数据，如：stock_info_spyder.get_historical_news(start_date="20150101", end_date="20201204")
# 如果没有指定时间段，且数据库已存在部分数据，则从最新的数据时间开始获取直到现在，比如数据库里已有sh600000价格数据到
# 2020-12-03号，如不设定具体时间，则从自动获取sh600000自2020-12-04至当前的价格数据
# get history price
stock_info_spyder.get_historical_price()

# get latest price
stock_info_spyder.get_today_price()
pass

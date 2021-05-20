# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import redis
from Utils import config
from MarketNewsSpider.StockInfoSpyder import StockInfoSpyder


redis_client = redis.StrictRedis(
    config.REDIS_IP,
    port=config.REDIS_PORT,
    db=config.CACHE_RECORED_OPENED_PYTHON_PROGRAM_DB_ID,
)
redis_client.lpush(
    config.CACHE_RECORED_OPENED_PYTHON_PROGRAM_VAR, "realtime_starter_stock_price.py"
)

stock_info_spyder = StockInfoSpyder(
    config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO
)
stock_info_spyder.get_realtime_news()

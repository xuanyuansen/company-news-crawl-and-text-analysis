# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --installimport redis
from Utils import config
import redis
from MarketNewsSpider.JrjSpyder import JrjSpyder


redis_client = redis.StrictRedis(
    config.REDIS_IP,
    port=config.REDIS_PORT,
    db=config.CACHE_RECORED_OPENED_PYTHON_PROGRAM_DB_ID,
)
redis_client.lpush(
    config.CACHE_RECORED_OPENED_PYTHON_PROGRAM_VAR, "realtime_starter_jrj.py"
)

jrj_spyder = JrjSpyder(config.DATABASE_NAME, config.COLLECTION_NAME_JRJ)
# jrj_spyder.get_historical_news(config.WEBSITES_LIST_TO_BE_CRAWLED_JRJ)  # 补充爬虫数据到最新日期
jrj_spyder.get_realtime_news()

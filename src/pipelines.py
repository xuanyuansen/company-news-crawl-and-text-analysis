# -*- coding: utf-8 -*-
import pymongo
from pymongo.errors import DuplicateKeyError

from Utils import config
from settings import MONGO_HOST, MONGO_PORT
import logging


class MongoDBPipeline(object):
    def __init__(self):
        client = pymongo.MongoClient(MONGO_HOST, MONGO_PORT)
        self.db_stcn = client["stcn"]
        self.db_jrj = client["jrj_news"]  # 金融界
        self.db_nbd = client["nbd_news"]  # 每经网
        self.db_net_ease = client[config.NET_EASE_STOCK_NEWS_DB]  # 163
        self.db_east_money = client[config.EAST_MONEY_NEWS_DB]  # east money
        self.db_shanghai_cn_stock = client[config.SHANG_HAI_STOCK_NEWS_DB]  # shanghai

    def process_item(self, item, spider):
        col_name = str(spider.name).replace("spider", "data")
        if str(spider.name).startswith("jrj"):
            self.insert_item(self.db_jrj[col_name], item)
        elif str(spider.name).startswith("stcn"):
            self.insert_item(self.db_stcn[col_name], item)
        elif str(spider.name).startswith("nbd"):
            self.insert_item(self.db_nbd[col_name], item)
        elif str(spider.name).startswith("net_ease"):
            self.insert_item(self.db_net_ease[col_name], item)
        elif str(spider.name).startswith("east_money"):
            self.insert_item(self.db_east_money[col_name], item)
        elif str(spider.name).startswith("shanghai"):
            self.insert_item(self.db_shanghai_cn_stock[col_name], item)
        else:
            logging.info("wrong")

        return item

    @staticmethod
    def insert_item(collection, item):
        try:
            collection.insert(dict(item))
        except DuplicateKeyError:
            logging.warning("already in data base, {0}".format(dict(item)))
            pass

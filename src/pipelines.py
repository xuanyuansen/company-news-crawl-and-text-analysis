# -*- coding: utf-8 -*-
from pymongo.errors import DuplicateKeyError
from Utils import config
from Utils.database import Database
import logging


class MongoDBPipeline(object):
    def __init__(self):
        db = Database()
        client = db.conn
        self.db_stcn = client[config.STCN_NEWS_DB]  # stcn
        self.db_jrj = client[config.JRJ_NEWS_DB]  # 金融界
        self.db_nbd = client[config.NBD_STOCK_NEWS_DB]  # 每经网
        self.db_net_ease = client[config.NET_EASE_STOCK_NEWS_DB]  # 163
        self.db_east_money = client[config.EAST_MONEY_NEWS_DB]  # east money
        self.db_shanghai_cn_stock = client[config.SHANG_HAI_STOCK_NEWS_DB]  # shanghai
        self.db_zhong_jin_cn_stock = client[config.ZHONG_JIN_STOCK_NEWS_DB]  # zhong jin 中金

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
        elif str(spider.name).startswith("zhong_jin"):
            self.insert_item(self.db_zhong_jin_cn_stock[col_name], item)
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

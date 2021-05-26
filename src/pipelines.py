# -*- coding: utf-8 -*-
import pymongo
from pymongo.errors import DuplicateKeyError
from settings import MONGO_HOST, MONGO_PORT
import logging

class MongoDBPipeline(object):
    def __init__(self):
        client = pymongo.MongoClient(MONGO_HOST, MONGO_PORT)
        db = client['stcn']
        self.djjd = db["stcn_djjd"]
        self.jigou = db["stcn_jigou"]
        self.data = db["stcn_data"]
        self.egs = db["stcn_egs_kuai_xun"]
        self.report = db["stcn_report_yan_bao"]
        self.company_trends = db["stcn_company_trends"]
        self.company_news = db["stcn_company_news"]
        self.company_deep_news = db["stcn_deep_news"]

    def process_item(self, item, spider):
        if spider.name == 'djjd_spider':
            self.insert_item(self.djjd, item)
        if spider.name == 'jigou_spider':
            self.insert_item(self.jigou, item)
        if spider.name == 'djsj_spider':
            self.insert_item(self.data, item)
        if spider.name == 'egs_spider':
            self.insert_item(self.egs, item)
        if spider.name == 'report_spider':
            self.insert_item(self.report, item)
        if spider.name == 'company_trends_spider':
            self.insert_item(self.company_trends, item)
        if spider.name == 'company_news_spider':
            self.insert_item(self.company_news, item)
        if spider.name == 'company_deep_spider':
            self.insert_item(self.company_deep_news, item)
        return item

    @staticmethod
    def insert_item(collection, item):
        try:
            collection.insert(dict(item))
        except DuplicateKeyError:
            logging.warning('already in data base, {0}'.format(dict(item)))
            pass

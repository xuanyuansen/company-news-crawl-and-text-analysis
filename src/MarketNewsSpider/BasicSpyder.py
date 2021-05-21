# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import logging

from Utils.database import Database
from NlpUtils.tokenization import Tokenization
import redis
from Utils import config
import time
import json


class Spyder(object):
    def __init__(self, database_name, collection_name):
        self.is_article_prob = 0.5
        self.db_obj = Database()
        self.col = self.db_obj.conn[database_name].get_collection(collection_name)
        self.db_name = database_name
        self.col_name = collection_name
        self.terminated_amount = 0
        self.tokenization = Tokenization(
            import_module=config.SEG_METHOD, user_dict=config.USER_DEFINED_DICT_PATH
        )
        self.redis_client = redis.StrictRedis(
            host=config.REDIS_IP,
            port=config.REDIS_PORT,
            db=config.CACHE_NEWS_REDIS_DB_ID,
        )
        self.max_rej_amounts = 0
        self.record_fail_path = None
        self.name_code_df = self.db_obj.get_data(
            config.STOCK_DATABASE_NAME,
            config.COLLECTION_NAME_STOCK_BASIC_INFO,
            keys=["name", "code"],
        )
        self.name_code_dict = dict(self.name_code_df.values)

    def fail_scrap(self, url):
        self.terminated_amount += 1
        if self.terminated_amount > self.max_rej_amounts:
            # 始终无法爬取的URL保存起来
            with open(
                self.record_fail_path,
                "a+",
            ) as file:
                file.write("{}\n".format(url))
            logging.warning(
                "rejected by remote server longer than {} minutes, "
                "and the failed url has been written in path {}".format(
                    self.max_rej_amounts,
                    self.record_fail_path,
                )
            )
            return True
        else:
            return False

    def fail_sleep(self, url):
        logging.info(
            "rejected by remote server, request {} again after "
            "{} seconds...".format(
                url, 60 * self.terminated_amount
            )
        )
        time.sleep(60 * self.terminated_amount)

    def process_article(self, init_result, url, title, date, category_chn=None, is_real_time: bool = False):
        # 有返回但是article为null的情况
        article_specific_date, article = init_result
        child_method = getattr(self, 'get_url_info')  # 获取子类的out()方法
        while article == "" and self.is_article_prob >= 0.1:
            self.is_article_prob -= 0.1
            # 执行子类的get_url_info()方法
            result = child_method(url, date)  # url a["href"]
            while not result:
                terminated = self.fail_scrap(url)
                if terminated:
                    break
                self.fail_sleep(url)
                result = child_method(url, date)

            article_specific_date, article = result

        self.is_article_prob = 0.5
        if article != "":
            related_stock_codes_list, cut_words_json = \
                self.tokenization.find_relevant_stock_codes_in_article(
                    article, self.name_code_dict
                )
            old_data = {
                "Date": article_specific_date,
                "Url": url,
                "Title": title,
                "Article": article,
                "RelatedStockCodes": " ".join(
                    related_stock_codes_list
                ),
                "WordsFrequent": cut_words_json,
            }
            # result_f = self.col.find_one(old_data)
            logging.info(cut_words_json)
            if self.col_name == config.COLLECTION_NAME_CNSTOCK:
                plus_data = {
                    "Category": category_chn,
                }
                # if result_f is not None:
                # logging.info("id is {0}".format(result_f["_id"]))
                # self.db_obj.update_row(self.db_name, self.col_name, old_data, new_data)
                # else:
                self.db_obj.insert_data(
                        self.db_name, self.col_name, dict(old_data, **plus_data)
                    )
            else:
                self.db_obj.insert_data(
                    self.db_name, self.col_name, dict(old_data)
                )
            logging.info(
                "[SUCCESS] {} {} {}".format(
                    article_specific_date,
                    title,
                    url,
                )
            )
            if is_real_time:
                data = dict({
                    "Date": article_specific_date,
                    "Url": url,
                    "Title": title,
                    "Article": article,
                    "RelatedStockCodes": " ".join(
                        related_stock_codes_list
                    ),
                    "OriDB": config.DATABASE_NAME,
                    "OriCOL": self.col_name,
                    "WordsFrequent": cut_words_json,
                })
                if self.col_name == config.COLLECTION_NAME_CNSTOCK:
                    plus = dict({
                        "Category": category_chn,
                    })
                    data = dict(data, **plus)
                self.redis_client.lpush(
                    config.CACHE_NEWS_LIST_NAME,
                    json.dumps(
                        data, ensure_ascii=False
                    ),
                )
                logging.info(
                    "[SUCCESS] {} {} {}".format(
                        article_specific_date,
                        title,
                        url,
                    )
                )
        pass

    def extract_data(self, tag_list):
        data = list()
        for tag in tag_list:
            exec(tag + " = self.col.distinct('" + tag + "')")
            exec("data.append(" + tag + ")")
        return data

    def query_news(self, _key, param):
        # 模糊查询
        return self.col.find({_key: {"$regex": ".*{}.*".format(param)}})

    def get_url_info(self, url, specific_date):
        pass

    def get_historical_news(self, url):
        pass

    def get_realtime_news(self, url):
        pass

# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import json
import redis
import logging
import datetime
from NlpModel.information_extract import InformationExtract
from Utils import config, utils
from NlpModel.tokenization import Tokenization

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class GenStockNewsDB(object):
    def __init__(self, force_train_model: bool = False):
        self.information_extractor = InformationExtract()
        self.information_extractor.build_2_class_classify_model()
        self.database = self.information_extractor.db_obj
        # used by redis
        self.name_code_df = self.database.get_data(config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO)
        self.col_names = []
        # 获取从1990-12-19至2020-12-31股票交易日数据
        # self.trade_date = ak.tool_trade_date_hist_sina()["trade_date"].tolist()
        self.redis_client = redis.StrictRedis(
            host=config.REDIS_IP,
            port=config.REDIS_PORT,
            db=config.CACHE_NEWS_REDIS_DB_ID,
        )
        self.redis_client.set(
            "today_date", datetime.datetime.now().strftime("%Y-%m-%d")
        )
        self.redis_client.delete(
            "stock_news_num_over_{}".format(config.MINIMUM_STOCK_NEWS_NUM_FOR_ML)
        )
        self._stock_news_nums_stat()

    def get_current_all_stock(self):
        self.col_names = self.database.connect_database(
            config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE
        ).list_collection_names(session=None)
        return True

    def __insert_data_to_db(self, database_name, collection_name, row, stock_code, is_redis: bool = False):
        symbol = 'sh{0}'.format(stock_code) if int(stock_code) >= 600000 \
            else 'sz{0}'.format(stock_code)
        _collection = self.database.get_collection(config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE, symbol)
        url_list = list(_collection.find({"Url": row["Url"]}))
        if len(url_list) > 0:
            # logging.warning("{0} news already in db {1}, res is {2}, skip".format(row["Url"], stock_code, url_list))
            return False, len(url_list), dict()
        _judge = self.information_extractor.predict_score(row["Title"] + row["Article"])
        if is_redis:
            _data = {
                "Date": row["Date"],
                "Url": row["Url"],
                "Title": row["Title"],
                "Article": row["Article"],
                "OriDB": row["OriDB"],
                "OriCOL": row["OriCOL"],
                "Symbol": symbol,
                "Code": stock_code,
                "Label": _judge[0],
                "Score": _judge[1],
            }
        else:
            _data = {
                "Date": row["Date"],
                "Url": row["Url"],
                "Title": row["Title"],
                "Article": row["Article"],
                "OriDB": database_name,
                "OriCOL": collection_name,
                "Symbol": symbol,
                "Code": stock_code,
                "Label": _judge[0],
                "Score": _judge[1],
            }
        _collection.insert_one(_data)
        return True, 0, _data

    def get_all_news_about_specific_stock(self, database_name, collection_name, start_date=None):
        # 获取collection_name的key值，看是否包含RelatedStockCodes，如果没有说明，没有做将新闻中所涉及的
        # 股票代码保存在新的一列
        _keys_list = list(
            next(
                self.database.get_collection(database_name, collection_name).find()
            ).keys()
        )
        logging.info("all_news_keys_cnt in {0} is {1}".format(collection_name, len(_keys_list)))
        if "RelatedStockCodes" not in _keys_list:
            tokenization = Tokenization(import_module="jieba", user_dict="./info/finance_dict.txt")
            tokenization.update_news_database_rows(database_name, collection_name)

        # 迭代器
        _tmp_num_stat = 0
        already_in_news_cnt = 0
        if start_date:
            data_to_process = self.database.get_collection(database_name, collection_name) \
                .find({"Date": {"$gt": start_date}})
        else:
            data_to_process = self.database.get_collection(database_name, collection_name).find()
        for row in data_to_process:
            # logging.info(row)
            # 先去遍历原始数据
            if row["RelatedStockCodes"] == "":
                logging.warning("{0} no related code in {1}".format(row["RelatedStockCodes"], row["Url"]))
                continue
            for stock_code in row["RelatedStockCodes"].split(" "):
                # 将新闻分别送进相关股票数据库
                res = self.__insert_data_to_db(database_name, collection_name, row, stock_code)
                if res[0]:
                    _tmp_num_stat += 1
                else:
                    already_in_news_cnt += res[1]

        logging.info("there are {0} news mentioned in {1} collection insert ... already_in_news_cnt {2}"
                     .format(_tmp_num_stat, collection_name, already_in_news_cnt))

    def listen_redis_queue(self):
        # 监听redis消息队列，当新的实时数据过来时，根据"RelatedStockCodes"字段，将新闻分别保存到对应的股票数据库
        # e.g.:缓存新的一条数据中，"RelatedStockCodes"字段数据为"603386 603003 600111 603568"，则将该条新闻分别
        # 都存进这四支股票对应的数据库中
        crawled_url_today = set()
        # 每20条信息，发送邮件一封邮件。
        mail_list = []
        while self.redis_client.llen(config.CACHE_NEWS_LIST_NAME) != 0:
            date_now = datetime.datetime.now().strftime("%Y-%m-%d")
            if date_now != self.redis_client.get("today_date").decode():
                crawled_url_today = set()
                self.redis_client.set("today_date", date_now)

            row = json.loads(
                self.redis_client.lindex(config.CACHE_NEWS_LIST_NAME, -1)
            )

            if row["Url"] not in crawled_url_today:  # 排除重复插入冗余文本
                crawled_url_today.update({row["Url"]})
                if row["RelatedStockCodes"] != "":
                    names = []
                    score = 0.0
                    label = "unknown"
                    insert_one = False
                    for stock_code in row["RelatedStockCodes"].split(" "):
                        # 将新闻分别送进相关股票数据库， 重复数据则不插入也不发送
                        res = self.__insert_data_to_db("database_name", "collection_name", row, stock_code, True)
                        if res[0]:
                            insert_one = True
                            score = dict(res[2]).get('Score')
                            label = dict(res[2]).get('Label')
                            logging.info(
                                "the real-time fetched news {}, which was saved in [DB:{} - COL:{}] ...".format(
                                    row["Title"],
                                    config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE,
                                    stock_code,
                                )
                            )
                            name_df = self.name_code_df[self.name_code_df['code'] == dict(res[2]).get('Code')]
                            # print(name_df)
                            name = name_df['name'].values[0]
                            names.append(name)
                    if insert_one:
                        mail_list.append(dict({'Name': ", ".join(names),
                                               "Date": row["Date"],
                                               "Url": row["Url"],
                                               "Title": row["Title"],
                                               "Article": row["Article"],
                                               "Code": row["RelatedStockCodes"],
                                               "Label": label,
                                               "Score": score,
                                               }))

            logging.info("new info mail content size is {0}".format(len(mail_list)))
            self.redis_client.rpop(config.CACHE_NEWS_LIST_NAME)
            logging.info(
                    "now pop {} from redis queue of [DB:{} - KEY:{}] ...".format(
                        row["Title"],
                        config.CACHE_NEWS_REDIS_DB_ID,
                        config.CACHE_NEWS_LIST_NAME,
                    )
            )
        if len(mail_list) > 0:
            utils.send_mail(", ".join([ele.get('Name') for ele in mail_list]),
                            "\n".join([str(ele) for ele in mail_list]))
            mail_list.clear()
            logging.info("send mail done")
        pass

    def _stock_news_nums_stat(self):
        cols_list = self.database.connect_database(
            config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE
        ).list_collection_names(session=None)
        for sym in cols_list:
            if (
                    self.database.get_collection(
                        config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE, sym
                    ).estimated_document_count()
                    > config.MINIMUM_STOCK_NEWS_NUM_FOR_ML
            ):
                self.redis_client.lpush(
                    "stock_news_num_over_{}".format(
                        config.MINIMUM_STOCK_NEWS_NUM_FOR_ML
                    ),
                    sym,
                )

    # gen_stock_news_db.listen_redis_queue()

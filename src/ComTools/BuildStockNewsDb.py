# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import hashlib
import json
from NlpModel.information_extract import InformationExtract
from Utils import config, utils
from NlpModel.tokenization import Tokenization
import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)


class GenStockNewsDB(object):
    def __init__(
        self,
        force_update_model: bool = False,
        force_update_score_using_model: bool = False,
        generate_report: bool = False,
    ):
        self.logger = utils.get_logger()
        self.information_extractor = InformationExtract(force_update_model)
        self.information_extractor.build_2_class_classify_model()
        self.database = self.information_extractor.db_obj
        self.name_code_df = self.database.get_data(
            config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO
        )
        self.force_update_score_using_model = force_update_score_using_model
        self.col_names = []
        self.generate_report = generate_report
        self.latest_news_report = dict()
        self.news_report_raw_version = list()

    def get_report_raw_version(self):
        return self.news_report_raw_version

    def get_report(self, db_name, col_name):
        return self.latest_news_report.get("{}_{}".format(db_name, col_name))

    def get_current_all_stock(self):
        self.col_names = self.database.connect_database(
            config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE
        ).list_collection_names(session=None)
        return True

    def __insert_data_to_db(
        self,
        database_name,
        collection_name,
        row,
        stock_code,
        stock_name,
        is_redis: bool = False,
    ):
        symbol = (
            "sh{0}".format(stock_code)
            if int(stock_code) >= 600000
            else "sz{0}".format(stock_code)
        )
        _collection = self.database.get_collection(
            config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE, symbol
        )

        _id_md5 = hashlib.md5(
            ("{0} {1}".format(row["Date"], row["Url"])).encode(encoding="utf-8")
        ).hexdigest()

        if is_redis:
            _data = {
                "_id": _id_md5,
                "Date": row["Date"],
                "Url": row["Url"],
                "Title": row["Title"],
                "Article": row["Article"],
                "OriDB": row["OriDB"],
                "OriCOL": row["OriCOL"],
                "Symbol": symbol,
                "Code": stock_code,
                "Name": stock_name,
                "Label": row["Label"],
                "Score": row["Score"],
            }
        else:
            _data = {
                "_id": _id_md5,
                "Date": row["Date"],
                "Url": row["Url"],
                "Title": row["Title"],
                "Article": row["Article"],
                "OriDB": database_name,
                "OriCOL": collection_name,
                "Symbol": symbol,
                "Name": stock_name,
                "Code": stock_code,
                "Label": row["Label"],
                "Score": row["Score"],
            }
        if self.force_update_score_using_model:
            _judge = self.information_extractor.predict_score(
                row["Title"] + row["Article"]
            )
            _data = dict(_data, **dict({"NewLabel": _judge[0], "NewScore": _judge[1]}))

        _id_list = _collection.find_one({"_id": _id_md5})

        if _id_list is not None:
            # self.logger.warning("{0} news already in db {1},
            # res is {2}, skip".format(row["Url"], stock_code, url_list))
            return False, 1, _data
        else:
            _collection.insert_one(_data)
            return True, 0, _data

    def get_all_news_about_specific_stock(
        self, database_name, collection_name, start_date=None
    ):
        # 获取collection_name的key值，看是否包含RelatedStockCodes，如果没有说明，没有做将新闻中所涉及的
        # 股票代码保存在新的一列
        _keys_list = list(
            next(
                self.database.get_collection(database_name, collection_name).find()
            ).keys()
        )
        self.logger.info(
            "all_news_keys_cnt in {0} is {1}".format(collection_name, len(_keys_list))
        )
        if "RelatedStockCodes" not in _keys_list:
            tokenization = Tokenization(
                import_module="jieba", user_dict=config.USER_DEFINED_WEIGHT_DICT_PATH
            )
            tokenization.update_news_database_rows(database_name, collection_name)

        # 迭代器
        _tmp_num_stat = 0
        already_in_news_cnt = 0
        if start_date:
            data_to_process = self.database.get_collection(
                database_name, collection_name
            ).find({"Date": {"$gt": start_date}})
        else:
            data_to_process = self.database.get_collection(
                database_name, collection_name
            ).find()
        find_news_cnt = 0
        try:
            for row in data_to_process:
                find_news_cnt += 1
                # logging.info(row)
                # 先去遍历原始数据
                if row["RelatedStockCodes"] == "{}":
                    self.logger.warning(
                        "{0} no related code in {1}".format(
                            row["RelatedStockCodes"], row["Url"]
                        )
                    )
                    continue
                self.news_report_raw_version.append(row)
                for name, stock_code in json.loads(row["RelatedStockCodes"]).items():
                    # 将新闻分别送进相关股票数据库
                    res = self.__insert_data_to_db(
                        database_name, collection_name, row, stock_code, name
                    )
                    if self.generate_report:
                        _key = "{}_{}".format(database_name, collection_name)
                        if self.latest_news_report.get(_key) is None:
                            _value = [res[2]]
                            self.latest_news_report[_key] = _value
                        else:
                            _value = self.latest_news_report.get(_key)
                            _value.append(res[2])
                            self.latest_news_report[_key] = _value
                    if res[0]:
                        _tmp_num_stat += 1
                    else:
                        already_in_news_cnt += res[1]

                    # self.logger.info(
                    #     "current stock code {0} {1}".format(stock_code, res)
                    # )
        except Exception as e:
            logger.error(e)
        self.logger.info(
            "find news cnt is: {3}, there are {0} news mentioned in {1} collection insert ... already_in_news_cnt {2}".format(
                _tmp_num_stat, collection_name, already_in_news_cnt, find_news_cnt
            )
        )
    pass

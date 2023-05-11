# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
https://www.akshare.xyz/zh_CN/latest/
"""
# import redis
import random
import datetime
import logging
import time
import pymongo
from pandas import DataFrame
from MongoDbComTools.JointQuantTool import JointQuantTool
from jqdatasdk import get_price, get_query_count
from MarketPriceSpiderWithScrapy import StockInfoUtils
from MarketPriceSpiderWithScrapy.BasicSpyder import Spyder
from pandas._libs.tslibs.timestamps import Timestamp
from Utils import config, utils
from Utils.database import Database
import hashlib
import akshare as ak
from Utils.utils import today_date


class StockInfoSpyder(Spyder):
    def __init__(self, joint_quant_on: bool = False):
        super().__init__()
        self.db_obj = Database()
        # cn stock market
        self.database_name_cn = config.STOCK_DATABASE_NAME
        self.collection_name_cn = config.COLLECTION_NAME_STOCK_BASIC_INFO
        self.col_basic_info_cn = self.db_obj.get_collection(
            self.database_name_cn, self.collection_name_cn
        )

        self.base_stock_info_df = self.db_obj.get_data(
            self.database_name_cn, self.collection_name_cn
        )
        # self.base_stock_info_df["code"] = self.base_stock_info_df.progress_apply(
        #    lambda row: "{0}".format(row["code"]),
        #    axis=1,
        # )

        # hk stock market
        self.database_name_hk = config.HK_STOCK_DATABASE_NAME
        self.collection_name_hk = config.COLLECTION_NAME_STOCK_BASIC_INFO_HK
        self.col_basic_info_hk = self.db_obj.get_collection(
            self.database_name_hk, self.collection_name_hk
        )
        # us stock market
        self.database_name_us = config.US_STOCK_DATABASE_NAME
        self.collection_name_us = config.COLLECTION_NAME_STOCK_BASIC_INFO_US
        self.col_basic_info_us = self.db_obj.get_collection(
            self.database_name_us, self.collection_name_us
        )
        # "stock_us_zh_spot"  # 中国概念股行情
        # "stock_us_zh_daily"  # 中国概念股历史数据
        self.collection_name_us_zh = config.COLLECTION_NAME_STOCK_BASIC_INFO_US_ZH
        self.col_basic_info_us_zh = self.db_obj.get_collection(
            self.database_name_us, self.collection_name_us_zh
        )

        self.cn_industry_file = config.CN_STOCK_INDUSTRY_DICT_FILE
        self.cn_concept_file = config.CN_STOCK_CONCEPT_DICT_FILE

        if joint_quant_on:
            self.joint_quant_tool = JointQuantTool()
        else:
            self.joint_quant_tool = None

    def get_target_stock_info_by_code(self, stock_code):
        print(
            "shape is {}, sample is {}".format(
                self.base_stock_info_df.shape, self.base_stock_info_df[:10]
            )
        )
        print("data type is {}".format(self.base_stock_info_df.dtypes))

        query_res = self.base_stock_info_df[
            self.base_stock_info_df["code"] == stock_code
        ]
        return query_res

    def gen_cn_stock_embedding_file(self):
        c_data = ak.stock_fund_flow_concept(symbol="3日排行")
        with open(self.cn_concept_file, "w") as concept_file:
            content = []
            for index, row in c_data.iterrows():
                content.append(row["行业"])
            concept_file.writelines("\n".join(content))

        i_data = ak.stock_fund_flow_industry(symbol="3日排行")
        with open(self.cn_industry_file, "w") as industry_file:
            content = []
            for index, row in i_data.iterrows():
                content.append(row["行业"])
            industry_file.writelines("\n".join(content))
        return True

    # 获取股票所属的概念，可能有多个概念，所以用List存储
    def update_stock_concept(self):
        data = ak.stock_fund_flow_concept(symbol="3日排行")
        print(data[:100])
        for index, row in data.iterrows():
            self.logger.info(index)
            self.logger.info("\n {}".format(row))
            try:
                detail = ak.stock_board_concept_cons_ths(symbol=row["行业"])  # 同花顺-成份股
                for sub_index, sub_row in detail.iterrows():
                    _data: dict = self.col_basic_info_cn.find_one(
                        {"code": sub_row["代码"]}
                    )
                    if _data.get("concept") is None:
                        insert = True
                        new_concept = row["行业"]
                    else:
                        _concept = _data["concept"].split(",")
                        if row["行业"] in _concept:
                            insert = False
                            new_concept = _data["concept"]
                        else:
                            insert = True
                            _concept.append(row["行业"])
                            new_concept = ",".join(_concept)

                    if insert:  # _data['concept'] = ','.join(_concept)
                        res = self.col_basic_info_cn.update_one(
                            {"_id": _data["_id"]}, {"$set": {"concept": new_concept}}
                        )
                        self.logger.info("modify count {}".format(res.modified_count))
                        new_data: dict = self.col_basic_info_cn.find_one(
                            {"code": sub_row["代码"]}
                        )
                        self.logger.info(new_data)
            except Exception as e:
                self.logger.error(e)
                continue

        return True

    def update_stock_industry(self):
        data = ak.stock_fund_flow_industry(symbol="3日排行")
        print(data[:100])

        for index, row in data.iterrows():
            self.logger.info(index)
            self.logger.info(row)
            detail = ak.stock_board_industry_cons_ths(symbol=row["行业"])
            # print(detail)
            for sub_index, sub_row in detail.iterrows():
                res = self.db_obj.update_row(
                    self.database_name_cn,
                    self.collection_name_cn,
                    query={"code": sub_row["代码"]},
                    new_values={"industry": row["行业"]},
                )
                self.logger.info("{} {}".format(res.modified_count, res.upserted_id))
                # find_res = self.col_basic_info_cn.find_one({'code': sub_row['代码']})
                # print(find_res)

        self.logger.info("update industry done!")

        return True

    def update_cn_stock_money_column_using_joint_quant(self):
        sd = today_date.split("-")
        # 获得所以要更新的股票列表
        code_joint_quant_symbol = self.db_obj.get_data(
            config.STOCK_DATABASE_NAME,
            config.COLLECTION_NAME_STOCK_BASIC_INFO,
            keys=["symbol", "joint_quant_code"],
            query={
                "end_date": {
                    "$gt": datetime.datetime(
                        int(sd[0]), int(sd[1]), int(sd[2]), 0, 0, 0, 000000
                    )
                }
            },
        )
        for index, row in code_joint_quant_symbol.iterrows():
            _col = self.db_obj.get_collection(config.STOCK_DATABASE_NAME, row["symbol"])
            start_date = _col.find_one(sort=[("date", pymongo.ASCENDING)]).get("date")
            self.logger.info("current row is {}".format(row))
            start_date_ymd = start_date.strftime("%Y-%m-%d")
            joint_data: DataFrame = get_price(
                row["joint_quant_code"],
                start_date=start_date_ymd,
                end_date=today_date,
                frequency="daily",
                fields=["money"],
            )
            modify_cnt = 0
            for _index, _row in joint_data.iterrows():
                id_md5 = hashlib.md5(
                    ("{0} {1}".format(row["symbol"], _index)).encode(encoding="utf-8")
                ).hexdigest()
                result = _col.update_one(
                    {"_id": id_md5}, {"$set": {"money": _row["money"]}}
                )
                modify_cnt += result.modified_count

            self.logger.info(
                "modify count in {} is {}".format(row["symbol"], modify_cnt)
            )
            self.logger.info("joint quant usage {}".format(get_query_count()))
        return True

    def get_cn_stock_week_data_from_joint_quant(self):
        jq_stock_symbol_list = self.col_basic_info_cn.distinct("joint_quant_code")
        week_col_names = self.db_obj.connect_database(
            self.database_name_cn
        ).list_collection_names(session=None)
        for symbol in jq_stock_symbol_list:
            if "{}_week".format(symbol) in week_col_names:
                self.logger.info("already down data {}".format(symbol))
                continue
            data = self.__get_week_data_from_joint_quant_of_one_cn_stock(symbol)
            if data is None:
                self.logger.warning("{} no data, continue".format(symbol))
                continue

            _col = self.db_obj.get_collection(
                self.database_name_cn, "{}_week".format(symbol)
            )
            self.insert_data_to_col_from_dataframe(_col, symbol, data)
            self.logger.info(
                "{} finished saving from {} to {} ... last day data is {}".format(
                    symbol,
                    data.iloc[0, 6],  # start date
                    data.iloc[data.shape[0] - 1, 6],  # end date
                    data[data.shape[0] - 1 :],
                )
            )
        return True

    def get_daily_price_data_of_specific_stock(
        self,
        symbol,
        market_type: str,
        start_date: str = None,
        end_date: str = None,
        _keys: list = None,
    ):
        if market_type == "cn":
            db_name = self.database_name_cn
        elif market_type == "hk":
            db_name = self.database_name_hk
        elif market_type == "us":
            db_name = self.database_name_us
        else:
            raise Exception("unknown market type")

        if start_date is None:
            stock_data = self.db_obj.get_data(db_name, symbol)
        else:
            sd = start_date.split("-")
            _query = (
                {
                    "date": {
                        "$gte": datetime.datetime(
                            int(sd[0]), int(sd[1]), int(sd[2]), 0, 0, 0, 000000
                        )
                    }
                }
                if market_type == "cn"
                else {"date": {"$gte": start_date}}
            )
            if end_date is not None and market_type == "cn":
                e_d = end_date.split("-")
                _query = {
                    "date": {
                        "$gte": datetime.datetime(
                            int(sd[0]), int(sd[1]), int(sd[2]), 0, 0, 0, 000000
                        ),
                        "$lte": datetime.datetime(
                            int(e_d[0]), int(e_d[1]), int(e_d[2]), 0, 0, 0, 000000
                        ),
                    }
                }

            stock_data = self.db_obj.get_data(
                db_name,
                symbol,
                query=_query,
                keys=_keys,
            )
        if stock_data is None:
            return False, DataFrame()
        # to do 用joint quant的数据来更新money数据。
        stock_data["money"] = stock_data.apply(
            lambda row: 0.25
            * (row["open"] + row["close"] + row["high"] + row["low"])
            * row["volume"],
            axis=1,
        )
        if market_type == "hk":
            stock_data["date_time_index"] = stock_data.apply(
                lambda row: datetime.datetime.strptime(row["date"], "%Y-%m-%d"), axis=1
            )
            stock_data.index = stock_data["date_time_index"]
        else:
            stock_data.index = stock_data["date"]
        return True, stock_data

    def get_week_data_stock(
        self,
        symbol,
        market_type: str,
        start_date: str = None,
        end_date=None,
        _keys: list = None,
    ):
        print("symbol is {}, market type is {}".format(symbol, market_type))
        res, stock_data = self.get_daily_price_data_of_specific_stock(
            symbol, market_type, start_date, end_date, _keys
        )
        if not res:
            print("get data fail!")
            return False, DataFrame()
        df2 = stock_data.resample("W").agg(
            {
                "open": "first",
                "close": "last",
                "high": "max",
                "low": "min",
                "money": "sum",
                "volume": "sum",
                "date": "first",
            }
        )

        df2 = df2[df2["open"].notnull()]
        df2.index = df2["date"]
        # print(df2)
        return True, df2

    # https://www.joinquant.com/view/community/detail/738214d7db9b1c03de504177f4e94690
    def __get_week_data_from_joint_quant_of_one_cn_stock(self, t_stock):
        try:
            stock_data = get_price(
                t_stock,
                start_date="2015-01-01",
                end_date=utils.today_date,
                frequency="1d",
                skip_paused=True,
                fq="pre",
            )
            stock_data["date"] = stock_data.index
            # print(stock_data[:100])
            # 直接使用resample方法搞定, pandas niu!!!
            df2 = stock_data.resample("W").agg(
                {
                    "open": "first",
                    "close": "last",
                    "high": "max",
                    "low": "min",
                    "money": "sum",
                    "volume": "sum",
                    "date": "first",
                }
            )
            # 主要是让索引使用我们定义的每周第一个交易日，而不是星期日
            # 把索引的别名删了，保持数据视图一致性
            df2 = df2[df2["open"].notnull()]
            df2.reset_index(inplace=True)

            df2.set_index("date", inplace=True)
            del df2["index"]
            df2["date"] = df2.index
            return df2
        # del df2.index.name
        # 打印信息
        # print(df2)
        except Exception as e:
            self.logger.error("error info is {}".format(e))
            return None

    @staticmethod
    def __get_single_hk_stock_data(symbol, adjust="qfq"):
        data = ak.stock_hk_daily(symbol=symbol, adjust=adjust)
        return data

    def get_historical_us_stock_daily_price(
        self, start_date=None, symbols: list = None
    ):
        if symbols is None:
            stock_symbol_list = self.col_basic_info_us.distinct("symbol")
        else:
            stock_symbol_list = symbols
        for symbol in stock_symbol_list:
            stock_us_daily_qfq_df = ak.stock_us_daily(symbol)
            stock_us_daily_qfq_df["date"] = stock_us_daily_qfq_df.index
            # stock_us_daily_qfq_df["date_py"] = stock_us_daily_qfq_df.apply(lambda row: row['date'].to_pydatetime(), axis=1)
            self.logger.info(
                "start processing {}, from date {}".format(symbol, start_date)
            )
            if start_date is not None:
                try:
                    stock_us_daily_qfq_df = stock_us_daily_qfq_df[
                        stock_us_daily_qfq_df["date"]
                        >= datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    ]
                except Exception as e:
                    self.logger.error(e)
                    # print(self.__get_single_hk_stock_data(symbol))
                    continue

            self.logger.info(stock_us_daily_qfq_df.shape)
            self.logger.info(stock_us_daily_qfq_df[:10])

            _col = self.db_obj.get_collection(self.database_name_us, symbol)

            for index, row in stock_us_daily_qfq_df.iterrows():
                _tmp_dict = row.to_dict()
                # print(_tmp_dict)
                _date_ = row["date"].strftime("%Y-%m-%d")

                id_md5 = hashlib.md5(
                    ("{0} {1}".format(symbol, _date_)).encode(encoding="utf-8")
                ).hexdigest()

                if _col.find_one({"_id": id_md5}) is not None:
                    self.logger.info(
                        "id already exist {0} {1} {2} {3}".format(
                            id_md5, _tmp_dict, symbol, _date_
                        )
                    )
                    continue
                else:
                    _col.insert_one(_tmp_dict)
            self.logger.info(
                "{} insert data done, count {}".format(
                    symbol, stock_us_daily_qfq_df.shape[0]
                )
            )
            time.sleep(random.randint(5, 10))
            # break
        return True

    def get_historical_us_zh_stock_daily_price(self, symbols: list = None):
        if symbols is None:
            stock_symbol_list = self.col_basic_info_us_zh.distinct("symbol")
        else:
            stock_symbol_list = symbols

        for symbol in stock_symbol_list:
            stock_us_zh_daily_qfq_df = ak.stock_us_zh_daily(symbol)
            print(stock_us_zh_daily_qfq_df.shape)
            print(stock_us_zh_daily_qfq_df[:100])
            _col = self.db_obj.get_collection(self.database_name_us, symbol)
            for index, row in stock_us_zh_daily_qfq_df.iterrows():
                # print(row)
                # print(type(row['时间']))
                _tmp_dict = stock_us_zh_daily_qfq_df.iloc[index].to_dict()
                date_raw = _tmp_dict.get("时间")
                _date_time = datetime.datetime.strptime(date_raw, "%Y%m%d")
                _date_ = _date_time.strftime("%Y-%m-%d")
                # 时间 # 前收盘价 # 开盘价 # 收盘价 # 最高价 # 最低价 # 成交量
                id_md5 = hashlib.md5(
                    ("{0} {1}".format(symbol, _date_)).encode(encoding="utf-8")
                ).hexdigest()
                if _col.find_one({"_id": id_md5}) is not None:
                    self.logger.info(
                        "id already exist {0} {1} {2} {3}".format(
                            id_md5, _tmp_dict, symbol, _date_
                        )
                    )
                    continue
                else:
                    _insert_data = {
                        "_id": id_md5,
                        "date": _date_time,
                        "open": _tmp_dict["开盘价"],
                        "close": _tmp_dict["收盘价"],
                        "high": _tmp_dict["最高价"],
                        "low": _tmp_dict["最低价"],
                        "pre_close": _tmp_dict["前收盘价"],
                        "volume": float(_tmp_dict["成交量"]),
                    }
                    _col.insert_one(_insert_data)
            self.logger.info(
                "{} insert data done, count {}".format(
                    symbol, stock_us_zh_daily_qfq_df.shape[0]
                )
            )
            time.sleep(random.randint(5, 10))
        return True

    # 获取港股历史行情
    def get_historical_hk_stock_daily_price(
        self,
        start_date=None,
        # end_date=None,
        start_symbol: str = None,
        symbols: list = None,
    ):
        if symbols is None:
            stock_symbol_list = self.col_basic_info_hk.distinct("symbol")
            print(
                "stock_symbol_list is {}, type is {}".format(
                    stock_symbol_list, type(stock_symbol_list)
                )
            )
            if 0 == len(stock_symbol_list):
                print("empty hk stock symbols, should get symbols first!")
                self.get_all_stock_code_info_of_hk()
                stock_symbol_list = self.col_basic_info_hk.distinct("symbol")
                print(
                    "stock_symbol_list has {} stock symbols".format(
                        len(stock_symbol_list)
                    )
                )
            if start_symbol is not None:
                new_list = []
                for element in stock_symbol_list:
                    if element >= start_symbol:
                        new_list.append(element)
                stock_symbol_list = new_list
        else:
            stock_symbol_list = symbols
        for symbol in stock_symbol_list:
            stock_hk_a_daily_hfq_df = self.__get_single_hk_stock_data(symbol)
            if start_date is not None:
                try:
                    stock_hk_a_daily_hfq_df["date"] = stock_hk_a_daily_hfq_df.apply(
                        lambda row: row["date"].strftime("%Y-%m-%d")
                        if isinstance(row["date"], datetime.date)
                        else row["date"],
                        axis=1,
                    )
                    stock_hk_a_daily_hfq_df = stock_hk_a_daily_hfq_df[
                        stock_hk_a_daily_hfq_df["date"] >= start_date
                    ]
                except Exception as e:
                    logging.error(e)
                    print(self.__get_single_hk_stock_data(symbol))
                    continue
            _col = self.db_obj.get_collection(self.database_name_hk, symbol)

            for _idx in range(stock_hk_a_daily_hfq_df.shape[0]):
                _tmp_dict = stock_hk_a_daily_hfq_df.iloc[_idx].to_dict()

                if isinstance(_tmp_dict["date"], datetime.date):
                    _tmp_dict["date"] = str(_tmp_dict["date"])

                id_md5 = hashlib.md5(
                    ("{0} {1}".format(symbol, _tmp_dict["date"])).encode(
                        encoding="utf-8"
                    )
                ).hexdigest()
                if _col.find_one({"_id": id_md5}) is not None:
                    self.logger.info(
                        "id already exist {0} {1}".format(id_md5, _tmp_dict)
                    )
                    continue
                _tmp_dict["_id"] = id_md5
                # _tmp_dict.pop("turnover")
                # ERROR trace cannot encode object: datetime.date(2021, 5, 7),
                # of type: <class 'datetime.date'>, symbol 00042
                # 这里要把(2021, 5, 7)改成(2021, 05, 07)才可以。next to do
                try:
                    _col.insert_one(_tmp_dict)
                    # self.logger.info("good data, {0}, type date{1}".format(_tmp_dict, type(_tmp_dict['date'])))
                except Exception as e:
                    self.logger.error(
                        "trace {0}, symbol {1}, data{2}, type date {3}".format(
                            e, symbol, _tmp_dict, type(_tmp_dict["date"])
                        )
                    )
                    continue

            time.sleep(1.5)
            if stock_hk_a_daily_hfq_df.shape[0] > 0:
                self.logger.info(
                    "{} finished saving from {} to {} ... last day data is {}".format(
                        symbol,
                        stock_hk_a_daily_hfq_df.iloc[0, 0],  # start date
                        stock_hk_a_daily_hfq_df.iloc[
                            stock_hk_a_daily_hfq_df.shape[0] - 1, 0
                        ],  # end date
                        stock_hk_a_daily_hfq_df[stock_hk_a_daily_hfq_df.shape[0] - 1 :],
                    )
                )
            else:
                self.logger.warning("no new data {}".format(symbol))
        return True

    # 获取HK股票信息数据
    def get_all_stock_code_info_of_hk(self):
        current_data_df = ak.stock_hk_spot()
        print(current_data_df.shape)
        print(current_data_df[:10])
        for index, row in current_data_df.iterrows():
            str_md5 = hashlib.md5(
                ("{0} {1}".format(row["name"], row["symbol"])).encode(encoding="utf-8")
            ).hexdigest()

            if self.col_basic_info_hk.find_one({"_id": str_md5}) is not None:
                self.logger.info(
                    "id already exist {0} {1} {2}".format(
                        str_md5, row["name"], row["symbol"]
                    )
                )
                continue

            _data = {
                "_id": str_md5,
                "symbol": row["symbol"],
                "name": row["name"],
                "tradetype": row["tradetype"],
                "engname": row["engname"],
            }

            self.col_basic_info_hk.insert_one(_data)
        return

    # 获取US股票信息数据
    # 新浪财经-美股
    # "get_us_stock_name"  # 获得美股的所有股票代码
    # "stock_us_spot"  # 获取美股行情报价
    # "stock_us_daily"  # 获取美股的历史数据(包括前复权因子)
    # "stock_us_fundamental"  # 获取美股的基本面数据
    # name cname symbol
    def get_all_stock_code_info_of_us(self):
        us_data = ak.get_us_stock_name()
        logging.info("shape is {}".format(us_data.shape))
        print(us_data[us_data.shape[0] - 100 :])
        # bao_jia = ak.stock_us_spot()
        # print(bao_jia.shape)
        # print(bao_jia[bao_jia.shape[0] - 100:])
        # print(current_data_df[:10])
        for index, row in us_data.iterrows():
            str_md5 = hashlib.md5(
                ("{0} {1}".format(row["name"], row["symbol"])).encode(encoding="utf-8")
            ).hexdigest()

            if self.col_basic_info_us.find_one({"_id": str_md5}) is not None:
                self.logger.info(
                    "id {0} already exist is us code info, {1} {2}".format(
                        str_md5, row["name"], row["symbol"]
                    )
                )
                continue
            else:
                _data = {
                    "_id": str_md5,
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "cname": row["cname"],
                }
                self.col_basic_info_us.insert_one(_data)
        logging.info("us market symbol get info complete!!!")
        return True

    # 美股-中国概念股行情和历史数据
    # "stock_us_zh_spot"  # 中国概念股行情
    # "stock_us_zh_daily"  # 中国概念股历史数据
    def get_all_stock_code_info_of_us_zh(self):
        us_zh_data = ak.stock_us_zh_spot()
        logging.info("shape is {}".format(us_zh_data.shape))
        print(us_zh_data[us_zh_data.shape[0] - 100 :])
        for index, row in us_zh_data.iterrows():
            str_md5 = hashlib.md5(
                ("{0} {1}".format(row["代码"], row["名称"])).encode(encoding="utf-8")
            ).hexdigest()

            if self.col_basic_info_us_zh.find_one({"_id": str_md5}) is not None:
                self.logger.info(
                    "id {0} already exist is us zh code info, {1} {2}".format(
                        str_md5, row["代码"], row["名称"]
                    )
                )
                continue
            else:
                _data = {
                    "_id": str_md5,
                    "symbol": row["代码"],
                    "name": row["名称"],
                    # "cname": row["cname"],
                }
                self.col_basic_info_us_zh.insert_one(_data)
        logging.info("us zh market 中国概念股 symbol get info complete!!!")
        return True

    # 获取CN股票信息数据
    # if database is empty, then get all code info first through ak share
    def get_all_stock_code_info_of_cn(self):
        data = StockInfoUtils.get_all_stock_code_info_of_cn()
        for index, row in data.iterrows():
            if self.col_basic_info_cn.find_one({"_id": row["_id"]}) is not None:
                self.logger.info("id already exist {0} {1}".format(row["_id"], index))
                continue

            _data = {
                "_id": row["_id"],
                "symbol": row["joint_quant_code"],
                "name": row["名称"],
                "code": row["代码"],
                "start_date": "",
                "end_date": "",
                "name_suo_xie": row["名称"],
                "joint_quant_code": index,
            }

            self.col_basic_info_cn.insert_one(_data)
        return True

    # 获取A股历史行情
    # need to rewrite, get all data from ak share, 2023/02/26
    def get_historical_cn_stock_daily_price(
        self, start_date=None, end_date=None, freq="day"
    ):
        if end_date is None:
            end_date = datetime.datetime.now().strftime("%Y%m%d")
        stock_symbol_list = self.col_basic_info_cn.distinct("symbol")

        if len(stock_symbol_list) == 0:
            self.get_all_stock_code_info_of_cn()
        stock_symbol_list = self.col_basic_info_cn.distinct("symbol")
        print(stock_symbol_list)
        if freq == "day":
            for symbol in stock_symbol_list:
                time.sleep(1)
                _col = self.db_obj.get_collection(self.database_name_cn, symbol)
                if start_date is None:
                    # 首先查询DB里面最大的时间
                    max_date = _col.find_one(sort=[("date", pymongo.DESCENDING)]).get(
                        "date"
                    )
                    if max_date:
                        _start_date = max_date
                        self.logger.info(
                            "stock {} max date is {}".format(symbol, max_date)
                        )
                    # 如果该symbol有历史数据，如果有则从API获取从数据库中最近的时间开始直到现在的所有价格数据
                    # 如果该symbol无历史数据，则从API获取从2015年1月1日开始直到现在的所有价格数据
                    else:
                        _start_date = config.STOCK_PRICE_REQUEST_DEFAULT_DATE
                else:
                    _start_date = start_date
                try:
                    if end_date is None:
                        stock_zh_a_daily_hfq_df = ak.stock_zh_a_daily(
                            symbol=symbol,
                            start_date=_start_date,
                            # end_date=end_date,
                            adjust="qfq",
                        )
                    else:
                        stock_zh_a_daily_hfq_df = ak.stock_zh_a_daily(
                            symbol=symbol,
                            start_date=_start_date,
                            end_date=end_date,
                            adjust="qfq",
                        )
                except Exception as e:
                    self.logger.error("trace {0}, symbol {1}".format(e, symbol))
                    continue

                stock_zh_a_daily_hfq_df.index = range(len(stock_zh_a_daily_hfq_df))
                res, cnt = self.insert_data_to_col_from_dataframe(
                    _col, symbol, stock_zh_a_daily_hfq_df
                )

                self.logger.info(
                    "{} finished saving from {} to {} ... {}, insert cnt is {}".format(
                        symbol,
                        start_date,
                        end_date,
                        stock_zh_a_daily_hfq_df[stock_zh_a_daily_hfq_df.shape[0] - 1 :],
                        cnt,
                    )
                )
        else:
            self.logger.warning("undefined frequent {}".format(freq))
            pass

    def get_cn_today_price(self, freq="day"):
        if freq == "day":
            time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stock_zh_a_spot_df = ak.stock_zh_a_spot()  # 当天的日数据行情下载
            for _id, symbol in enumerate(stock_zh_a_spot_df["symbol"]):
                _col = self.db_obj.get_collection(self.database_name_cn, symbol)
                _tmp_dict = {}
                _tmp_dict.update(
                    {"date": Timestamp("{} 00:00:00".format(time_now.split(" ")[0]))}
                )
                id_md5 = hashlib.md5(
                    ("{0} {1}".format(symbol, _tmp_dict["date"])).encode(
                        encoding="utf-8"
                    )
                ).hexdigest()
                _tmp_dict["_id"] = id_md5
                _tmp_dict.update({"open": stock_zh_a_spot_df.iloc[_id].open})
                _tmp_dict.update({"high": stock_zh_a_spot_df.iloc[_id].high})
                _tmp_dict.update({"low": stock_zh_a_spot_df.iloc[_id].low})
                _tmp_dict.update({"close": stock_zh_a_spot_df.iloc[_id].trade})
                _tmp_dict.update({"volume": stock_zh_a_spot_df.iloc[_id].volume})
                _tmp_dict.update(
                    {
                        "outstanding_share": stock_zh_a_spot_df.iloc[
                            _id
                        ].outstanding_share
                    }
                )
                _tmp_dict.update({"turnover": stock_zh_a_spot_df.iloc[_id].turnover})
                if _col.find_one({"_id": id_md5}) is not None:
                    self.logger.info(
                        "id already exist {0} {1}".format(id_md5, _tmp_dict)
                    )
                    continue
                _col.insert_one(_tmp_dict)

                self.logger.info(
                    "finished updating {} price data of {} ... ".format(
                        symbol, time_now.split(" ")[0]
                    )
                )


if __name__ == "__main__":
    spider = StockInfoSpyder(joint_quant_on=False)
    # spider.update_stock_industry()
    res = spider.get_target_stock_info_by_code(stock_code="301419")
    print(res)

    pass

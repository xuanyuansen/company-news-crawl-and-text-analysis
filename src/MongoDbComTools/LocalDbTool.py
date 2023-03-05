from pandas import DataFrame

from Utils.database import Database
from Utils import config, utils
import datetime


class LocalDbTool(object):
    def __init__(self):
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
        # hk stock market
        self.database_name_hk = config.HK_STOCK_DATABASE_NAME
        self.collection_name_hk = config.COLLECTION_NAME_STOCK_BASIC_INFO_HK
        self.col_basic_info_hk = self.db_obj.get_collection(
            self.database_name_hk, self.collection_name_hk
        )
        self.col_basic_info_hk_df = self.db_obj.get_data(
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

    def get_target_stock_info_by_code_of_hk(self, stock_code):
        query_res = self.col_basic_info_hk_df[
            self.col_basic_info_hk_df["symbol"] == stock_code
        ]
        print(query_res)
        return query_res

    def get_week_data_stock(
        self,
        symbol,
        market_type: str,
        start_date: str = None,
        end_date=None,
        _keys: list = None,
    ):
        res, stock_data = self.get_daily_price_data_of_specific_stock(
            symbol, market_type, start_date, end_date, _keys
        )
        if not res:
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
            stock_data = self.db_obj.get_data(
                db_name, symbol, sort=True, sort_key=["date"]
            )
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
                db_name, symbol, query=_query, keys=_keys, sort=True, sort_key=["date"]
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


pass

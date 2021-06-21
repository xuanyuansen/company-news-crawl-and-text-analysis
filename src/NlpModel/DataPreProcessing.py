# -*- coding: UTF-8 -*-
# 用于数据预处理
import os

from Surpriver.feature_generator import TAEngine
from Utils import config
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
import pandas as pd
from datetime import datetime
from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject
from ChanUtils.ChanFeature import BasicFeatureGen, DeepFeatureGen

import pickle


class DataPreProcessing(object):
    def __init__(self, feature_size: int, history_day_ta_feature_to_use: int = 10):
        self.market_type = "cn"
        self.daily_stock_data_start_date = "2020-01-01"
        self.binary_mode = False
        self.price_spider = StockInfoSpyder()
        self.db = self.price_spider.db_obj
        self.bfg = BasicFeatureGen()
        self.deep_feature_gen = DeepFeatureGen()
        # history_to_use 决定了technical_feature的长度
        self.technical_feature_gen = TAEngine(
            history_to_use=history_day_ta_feature_to_use
        )
        self.feature_size = feature_size
        pd.set_option("mode.use_inf_as_na", True)
        pass

    def get_ta_feature(self, stock_price_data, upper_case: bool = True):
        features_dictionary = self.technical_feature_gen.get_technical_indicators(
            stock_price_data, upper_case
        )
        print("features_dictionary keys, {}".format(features_dictionary.keys()))
        feature_list = self.technical_feature_gen.get_features(features_dictionary)
        return feature_list

    def get_symbols(self, market_type):
        if "cn" == market_type:
            data = self.db.get_data(
                config.STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO,
                query={"end_date": {"$gt": datetime(2021, 1, 1, 0, 0, 0, 000000)}},
                keys=["symbol", "name", "end_date", "concept", "industry"],
            )
        elif "hk" == market_type:
            data = self.db.get_data(
                config.HK_STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO_HK,
                keys=["symbol", "name"],
            )
        elif "us" == market_type:
            data = self.db.get_data(
                config.US_STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO_US,
                keys=["symbol", "name"],
            )
        else:
            data = self.db.get_data(
                config.US_STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO_US_ZH,
                keys=["symbol", "name"],
            )
        return data

    def get_daily_data(self, _symbol, _market_type, _start_date, _end_date):
        res, stock_data = self.price_spider.get_daily_price_data_of_specific_stock(
            symbol=_symbol, market_type=_market_type, start_date=_start_date
        )
        if not res:
            return None

        stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")

        # 注意这里通过start_date获得最后一周的标签，
        # 那么用于计算特征的数据不能包含这周的数据
        stock_data = stock_data[stock_data["Date"] < _end_date]
        # print(stock_data[-40:])

        stock_data.set_index("Date", inplace=True)
        return stock_data

    # 加入end_date过滤数据，不能有未来数据！！！
    def from_symbol_to_feature(self, _symbol, stock_data, industry, concepts):
        k_line_data = KiLineObject.k_line_merge(_symbol, stock_data, merge_or_not=True)
        chan_data = ChanSourceDataObject("daily", k_line_data)
        chan_data.gen_data_frame()
        chan_data.get_plot_data_frame()

        self.deep_feature_gen.set_base_data(chan_data)
        # tuple, (bi_feature_list, industry, concepts)
        deep_feature = self.deep_feature_gen.get_deep_sequence_feature(
            industry, concepts
        )

        self.bfg.set_base_data(chan_data)
        # feature list, size 40
        xgb_feature = self.bfg.get_feature()
        return {"deep_feature": deep_feature, "xgb_feature": xgb_feature}

    @staticmethod
    def direct_load_feature_file(file_data_name):
        if os.path.exists(file_data_name):
            with open(file_data_name, "rb") as _file:
                week_data = pickle.load(_file)
                label_cnt = week_data.groupby(["label"]).size()
                print(label_cnt)
                return week_data, label_cnt, week_data["feature_length"].max(), week_data[
                    "deep_feature_length"].max(), week_data["ta_features_length"].max()

    def get_label(
            self,
            symbols: pd.DataFrame,
            # market_type: str,
            week_data_start_date: str = None,
            week_data_end_date: str = None,
            cnt_limit_start: int = None,
            cnt_limit_end: int = None,
            # feature_type: str = "xgb",
            save_feature: bool = True,
            force_update_feature: bool = False,
    ):
        assert week_data_start_date is not None
        week_data = symbols[cnt_limit_start:cnt_limit_end]
        week_data["week"] = week_data.apply(
            lambda row: self.price_spider.get_week_data_stock(
                row["symbol"],
                market_type=self.market_type,
                start_date=week_data_start_date,
                end_date=week_data_end_date
            )[1],
            axis=1,
        )

        week_data["week_data_shape"] = week_data.apply(
            lambda row: row["week"].shape[0], axis=1
        )

        # 取最后一周的涨幅数据来作为标签，过滤没有标签的数据
        week_data = week_data[week_data["week_data_shape"] >= 1]
        week_data["week_data_start_date"] = week_data.apply(
            lambda row: row["week"].index[-1], axis=1
        )

        # print(week_data["week_data_start_date"])
        week_data_start_date_cnt = week_data.groupby(["week_data_start_date"]).size()
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Series.idxmax.html
        label_date = week_data_start_date_cnt.idxmax().strftime("%Y-%m-%d")
        # print(week_data_start_date_cnt.shape)
        # print(week_data_start_date_cnt.values)
        # print(week_data_start_date_cnt.index)
        # week_data_start_date_cnt.index is
        # DatetimeIndex(['2021-06-07'], dtype='datetime64[ns]', name='week_data_start_date', freq=None)

        file_path = os.getcwd()
        file_data_name = "{}/{}".format(
            file_path,
            "feature_file_{}_{}.dataframe".format(
                self.daily_stock_data_start_date, label_date
            ),
        )
        if not force_update_feature:
            self.direct_load_feature_file(file_data_name)

        week_data["ratio"] = week_data.apply(
            lambda row: 100
                        * (row["week"].iloc[-1, 1] - row["week"].iloc[-1, 0])
                        / row["week"].iloc[-1, 0],
            axis=1,
        )
        print("最大涨幅, {}".format(week_data["ratio"].max()))
        print("最大跌幅, {}".format(week_data["ratio"].min()))

        def _set_label(_value: float):
            if _value <= -10.0:
                return 0
            elif -10 < _value <= 0:
                return 1
            elif 0 < _value <= 10:
                return 2
            else:
                return 3

        def _set_binary_label(_value: float):
            if _value < 0.0:
                return 0
            else:
                return 1

        week_data["label"] = week_data.apply(
            lambda row: _set_binary_label(row["ratio"])
            if self.binary_mode
            else _set_label(row["ratio"]),
            axis=1,
        )
        week_data["sub_level_stock_data"] = week_data.apply(
            lambda row: self.get_daily_data(
                row["symbol"],
                _market_type=self.market_type,
                _start_date=self.daily_stock_data_start_date,
                _end_date=row["week_data_start_date"]
            ),
            axis=1,
        )

        # {'deep_feature': deep_feature, 'xgb_feature': xgb_feature}
        week_data["features"] = week_data.apply(
            lambda row: self.from_symbol_to_feature(
                row["symbol"],
                row["sub_level_stock_data"],
                row["industry"],
                row["concept"],  # feature_type
            ),
            axis=1,
        )
        week_data["xgb_features"] = week_data.apply(
            lambda row: row["features"].get("xgb_feature"), axis=1
        )

        week_data["deep_features"] = week_data.apply(
            lambda row: row["features"].get("deep_feature"), axis=1
        )

        # 2021.06.18 增加技术特征，这里的超参是使用数据的长度，最近的多少天，目前设置为10天，即两周。
        week_data["ta_features"] = week_data.apply(
            lambda row: self.get_ta_feature(
                stock_price_data=row["sub_level_stock_data"], upper_case=False
            ),
            axis=1,
        )
        week_data["ta_features_length"] = week_data.apply(
            lambda row: len(row["ta_features"]), axis=1
        )
        max_ta_length = week_data["ta_features_length"].max()
        week_data = week_data[week_data["ta_features_length"] == max_ta_length]

        for _index in range(0, max_ta_length):
            week_data["ta_feature_{}".format(_index)] = week_data.apply(
                lambda row: row["ta_features"][_index], axis=1
            )

        # xgb feature
        week_data["feature_length"] = week_data.apply(
            lambda row: len(row["xgb_features"]), axis=1
        )
        week_data = week_data[week_data["feature_length"] > 0]
        week_data.dropna(axis=0, how="any", inplace=True)
        # 10 + 10 + 13 + 2
        for _index in range(0, self.feature_size):
            week_data["feature_{}".format(_index)] = week_data.apply(
                lambda row: row["xgb_features"][_index], axis=1
            )

        week_data["deep_feature_length"] = week_data.apply(
            lambda row: len(row["deep_features"][0]), axis=1
        )
        # week_data.drop(['features'], axis=1, inplace=True)

        null_data = week_data[week_data.isnull().T.any()]
        print("null feature")
        print(null_data)
        print("null feature shape")
        print(week_data.shape)

        label_cnt = week_data.groupby(["label"]).size()
        print(label_cnt)

        if save_feature:
            with open(file_data_name, "wb") as _file:
                pickle.dump(week_data, _file)

        return (
            week_data,
            label_cnt,
            week_data["feature_length"].max(),
            week_data["deep_feature_length"].max(),
            max_ta_length,
        )

    pass
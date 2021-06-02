# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
https://www.akshare.xyz/zh_CN/latest/
"""
# import redis
import datetime
import time
from ComTools.JointQuantTool import JointQuantTool
from jqdatasdk import get_price
from MarketNewsSpider.BasicSpyder import Spyder
from pandas._libs.tslibs.timestamps import Timestamp
from Utils import config, utils
from Utils.database import Database
import hashlib
import akshare as ak


class StockInfoSpyder(Spyder):
    def __init__(self, database_name, collection_name):
        super().__init__()
        self.db_obj = Database()
        self.database_name = database_name
        self.collection_name = collection_name
        self.col_basic_info = self.db_obj.get_collection(database_name, collection_name)
        self.database_name_hk = config.HK_STOCK_DATABASE_NAME
        self.collection_name_hk = config.COLLECTION_NAME_STOCK_BASIC_INFO_HK
        self.col_basic_info_hk = self.db_obj.get_collection(self.database_name_hk, self.collection_name_hk)
        self.joint_quant_tool = JointQuantTool()

    def get_cn_stock_week_data_from_joint_quant(self):
        jq_stock_symbol_list = self.col_basic_info.distinct("joint_quant_code")
        for symbol in jq_stock_symbol_list:
            data = self.__get_week_data_from_joint_quant_of_one_cn_stock(symbol)
            _col = self.db_obj.get_collection(self.database_name, '{}_week'.format(symbol))
            self.insert_data_to_col_from_dataframe(_col, symbol, data)
            self.logger.info(
                "{} finished saving from {} to {} ... last day data is {}".format(
                    symbol,
                    data.iloc[0, 6],  # start date
                    data.iloc[data.shape[0] - 1, 6],  # end date
                    data[data.shape[0] - 1:],
                )
            )
        return True

    # https://www.joinquant.com/view/community/detail/738214d7db9b1c03de504177f4e94690
    def __get_week_data_from_joint_quant_of_one_cn_stock(self, t_stock):
        try:
            stock_data = get_price(t_stock, start_date='2015-01-01', end_date=utils.today_date,
                                   frequency='1d', skip_paused=True, fq='pre')
            stock_data['date'] = stock_data.index
            # print(stock_data[:100])
            # 直接使用resample方法搞定, pandas niu!!!
            df2 = stock_data.resample('W').agg({'open': 'first',
                                                'close': 'last',
                                                'high': 'max',
                                                'low': 'min',
                                                'money': 'sum',
                                                'volume': 'sum',
                                                'date': 'first'})
            # 主要是让索引使用我们定义的每周第一个交易日，而不是星期日
            # 把索引的别名删了，保持数据视图一致性
            df2 = df2[df2['open'].notnull()]
            df2.reset_index(inplace=True)

            df2.set_index('date', inplace=True)
            del df2['index']
            df2['date'] = df2.index
            return df2
        # del df2.index.name
        # 打印信息
        # print(df2)
        except Exception as e:
            self.logger.error('error info is {}'.format(e))
            return None

    @staticmethod
    def __get_single_hk_stock_data(symbol, adjust='qfq'):
        data = ak.stock_hk_daily(symbol=symbol, adjust=adjust)
        return data

    def get_historical_hk_stock_daily_price(self, start_date=None,
                                            end_date=None,
                                            start_symbol: str = None,
                                            symbols: list = None):
        if symbols is None:
            stock_symbol_list = self.col_basic_info_hk.distinct("symbol")
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
            _col = self.db_obj.get_collection(self.database_name_hk, symbol)

            for _idx in range(stock_hk_a_daily_hfq_df.shape[0]):
                _tmp_dict = stock_hk_a_daily_hfq_df.iloc[_idx].to_dict()

                if isinstance(_tmp_dict['date'], datetime.date):
                    _tmp_dict['date'] = str(_tmp_dict['date'])

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
                    self.logger.error("trace {0}, symbol {1}, data{2}, type date {3}"
                                      .format(e, symbol, _tmp_dict, type(_tmp_dict['date'])))
                    continue

            time.sleep(1.5)
            self.logger.info(
                "{} finished saving from {} to {} ... last day data is {}".format(
                    symbol,
                    stock_hk_a_daily_hfq_df.iloc[0, 0],  # start date
                    stock_hk_a_daily_hfq_df.iloc[stock_hk_a_daily_hfq_df.shape[0] - 1, 0],  # end date
                    stock_hk_a_daily_hfq_df[stock_hk_a_daily_hfq_df.shape[0] - 1:],
                )
            )

        return True

    def get_all_stock_code_info_of_hk(self):
        current_data_df = ak.stock_hk_spot()
        print(current_data_df[:10])
        for index, row in current_data_df.iterrows():
            str_md5 = hashlib.md5(
                ("{0} {1}".format(row["name"], row["symbol"])).encode(encoding="utf-8")
            ).hexdigest()

            if self.col_basic_info_hk.find_one({"_id": str_md5}) is not None:
                self.logger.info("id already exist {0} {1} {2}".format(str_md5, row["name"], row["symbol"]))
                continue

            _data = {
                "_id": str_md5,
                "symbol": row['symbol'],
                "name": row["name"],
                "tradetype": row["tradetype"],
                "engname": row["engname"],
            }

            self.col_basic_info_hk.insert_one(_data)
        return

    def get_all_stock_code_info(self):
        data = self.joint_quant_tool.get_all_stock()

        for index, row in data.iterrows():
            str_md5 = hashlib.md5(
                ("{0} {1}".format(row["name"], index)).encode(encoding="utf-8")
            ).hexdigest()

            if self.col_basic_info.find_one({"_id": str_md5}) is not None:
                self.logger.info("id already exist {0} {1}".format(str_md5, index))
                continue

            stock_code = str(index).split(".")[0]
            symbol = (
                "sh{0}".format(stock_code)
                if int(stock_code) >= 600000
                else "sz{0}".format(stock_code)
            )
            _data = {
                "_id": str_md5,
                "symbol": symbol,
                "name": row["display_name"],
                "code": stock_code,
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "name_suo_xie": row["name"],
                "joint_quant_code": index,
            }

            self.col_basic_info.insert_one(_data)
        return True

    def get_historical_price(self, start_date=None, end_date=None, freq="day"):
        if end_date is None:
            end_date = datetime.datetime.now().strftime("%Y%m%d")
        stock_symbol_list = self.col_basic_info.distinct("symbol")
        if len(stock_symbol_list) == 0:
            self.get_all_stock_code_info()
            stock_symbol_list = self.col_basic_info.distinct("symbol")
        if freq == "day":
            for symbol in stock_symbol_list:
                time.sleep(2)
                if start_date is None:
                    # 如果该symbol有历史数据，如果有则从API获取从数据库中最近的时间开始直到现在的所有价格数据
                    # 如果该symbol无历史数据，则从API获取从2015年1月1日开始直到现在的所有价格数据
                    start_date = config.STOCK_PRICE_REQUEST_DEFAULT_DATE
                try:
                    if end_date is None:
                        stock_zh_a_daily_hfq_df = ak.stock_zh_a_daily(
                            symbol=symbol,
                            start_date=start_date,
                            # end_date=end_date,
                            adjust="qfq",
                        )
                    else:
                        stock_zh_a_daily_hfq_df = ak.stock_zh_a_daily(
                            symbol=symbol,
                            start_date=start_date,
                            end_date=end_date,
                            adjust="qfq",
                        )
                except Exception as e:
                    self.logger.error("trace {0}, symbol {1}".format(e, symbol))
                    continue

                # print(symbol)
                # print(stock_zh_a_daily_hfq_df)
                stock_zh_a_daily_hfq_df.index = range(len(stock_zh_a_daily_hfq_df))
                _col = self.db_obj.get_collection(self.database_name, symbol)
                for _idx in range(stock_zh_a_daily_hfq_df.shape[0]):
                    _tmp_dict = stock_zh_a_daily_hfq_df.iloc[_idx].to_dict()
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
                    _col.insert_one(_tmp_dict)

                self.logger.info(
                    "{} finished saving from {} to {} ... {}".format(
                        symbol,
                        start_date,
                        end_date,
                        stock_zh_a_daily_hfq_df[stock_zh_a_daily_hfq_df.shape[0] - 1 :],
                    )
                )

        elif freq == "week":
            pass
        elif freq == "month":
            pass
        elif freq == "5mins":
            pass
        elif freq == "15mins":
            pass
        elif freq == "30mins":
            pass
        elif freq == "60mins":
            pass

    def get_today_price(self, freq="day"):
        if freq == "day":
            time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stock_zh_a_spot_df = ak.stock_zh_a_spot()  # 当天的日数据行情下载
            for _id, symbol in enumerate(stock_zh_a_spot_df["symbol"]):
                _col = self.db_obj.get_collection(self.database_name, symbol)
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

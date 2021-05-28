# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
"""
https://www.akshare.xyz/zh_CN/latest/
"""
# import redis
import datetime
import time

from ComTools.JointQuantTool import JointQuantTool
from MarketNewsSpider.BasicSpyder import Spyder
from pandas._libs.tslibs.timestamps import Timestamp
from Utils import config
import akshare as ak
from Utils.database import Database
import hashlib


class StockInfoSpyder(Spyder):
    def __init__(self, database_name, collection_name):
        super().__init__()
        self.db_obj = Database()
        self.database_name = database_name
        self.collection_name = collection_name
        self.col_basic_info = self.db_obj.get_collection(database_name, collection_name)
        self.joint_quant_tool = JointQuantTool()

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
                _col.insert_one(_tmp_dict)

                self.logger.info(
                    "finished updating {} price data of {} ... ".format(
                        symbol, time_now.split(" ")[0]
                    )
                )

# -*- coding:utf-8 -*-
"""
author wangshuai
date 2021/06/03
"""
import datetime
import json
import sys
import pandas as pd

from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
from Utils.utils import set_display, today_date
from Utils import config
from Utils.database import Database
import warnings

warnings.filterwarnings("ignore")

if __name__ == "__main__":
    set_display()
    print(today_date)
    db = Database()
    stock_type = sys.argv[1]
    stock_info_spyder = StockInfoSpyder(
        config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO
    )

    data = db.get_data(
        config.STOCK_DATABASE_NAME,
        config.COLLECTION_NAME_STOCK_BASIC_INFO,
        keys=["symbol", "name", "end_date"],
    )
    with open("./info/week_buy_point_res.json", "w") as file:
        for _, row in data.iterrows():
            if stock_type not in row["symbol"]:
                print("市场不对 跳过{}".format(row["symbol"]))
                continue
            if row["end_date"] < datetime.datetime.now():
                print("退市了，不考虑{}".format(row["symbol"]))
                continue
            res, stock_data = stock_info_spyder.get_week_data_cn_stock(
                row["symbol"], market_type="cn"
            )
            if not res or stock_data.shape[0] < 33:
                print("not enough data")
                continue
            print("current stock is {}".format(row["symbol"]))
            stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")
            stock_data.set_index("Date", inplace=True)
            # 周线不合并K线
            merged_k_line_data = KiLineObject.k_line_merge(row["symbol"], stock_data, merge_or_not=False)
            chan_data = ChanSourceDataObject("week", merged_k_line_data)
            chan_data.gen_data_frame()
            try:
                (
                    valid,
                    last_cross,
                    valid_ding_date,
                    valid_di_date,
                    distance,
                ) = chan_data.is_valid_buy_sell_point_on_k_line(level='week')
            except Exception as e:
                print(row)
                print(e)
                break
            # daily data
            res, stock_data_daily = stock_info_spyder.get_daily_data_cn_stock(
                row["symbol"], market_type="cn", start_date='2019-01-01'
            )
            if not res or stock_data_daily.shape[0] < 33:
                print("not enough data")
                continue
            # print("current stock is {}".format(row["symbol"]))
            stock_data_daily["Date"] = pd.to_datetime(stock_data_daily["date"], format="%Y-%m-%d")
            stock_data_daily.set_index("Date", inplace=True)
            # 周线不合并K线
            merged_k_line_data_daily = KiLineObject.k_line_merge(row["symbol"], stock_data, merge_or_not=True)
            chan_data_daily = ChanSourceDataObject("daily", merged_k_line_data_daily)
            chan_data_daily.gen_data_frame()

            try:
                (
                    valid_daily,
                    last_cross_daily,
                    valid_ding_date_daily,
                    valid_di_date_daily,
                    distance_daily,
                ) = chan_data_daily.is_valid_buy_sell_point_on_k_line(level='daily')
            except Exception as e:
                print(row)
                print(e)
                break

            if valid and valid_daily:
                print(row)
                print(
                    "{} is buy point {},{},{},{}, {},{},{},{}".format(
                        row["symbol"], valid, valid_daily, last_cross, valid_ding_date, valid_di_date,
                        last_cross_daily, valid_ding_date_daily, valid_di_date_daily
                    )
                )
                file.writelines(
                    "{}\n".format(
                        json.dumps(
                            {
                                "symbol": row["symbol"],
                                "name": row["name"],
                                "last_cross": last_cross[0].strftime("%Y-%m-%d"),
                                "last_cross_daily": last_cross_daily[0].strftime("%Y-%m-%d"),
                                "last_valid_ding_date": valid_ding_date.strftime(
                                    "%Y-%m-%d"
                                )
                                if valid_ding_date is not None
                                else "",
                                "last_valid_di_date": valid_di_date.strftime("%Y-%m-%d")
                                if valid_di_date is not None
                                else "",
                                "distance": distance,
                                "distance_daily": distance_daily,
                            },
                            ensure_ascii=False,
                        )
                    )
                )
    pass

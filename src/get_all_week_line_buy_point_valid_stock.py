# -*- coding:utf-8 -*-
"""
author wangshuai
date 2021/06/03
"""
import datetime
import json
import logging

# import sys
import pandas as pd
import argparse
from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
from Utils.utils import set_display, today_date
from Utils import config
from Utils.database import Database

# import warnings
# warnings.filterwarnings("ignore")


def check_buy_point_data(market_type, stock_symbol, data_level):
    res, stock_data = (
        stock_info_spyder.get_week_data_stock(stock_symbol, market_type=market_type)
        if "week" == data_level
        else stock_info_spyder.get_daily_price_data_of_specific_stock(
            stock_symbol, market_type=market_type, start_date="2019-01-01"
        )
    )
    if not res or stock_data.shape[0] < 33:
        print("not enough data")
        return False, tuple()

    print("current stock is {}".format(stock_symbol))
    stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")
    stock_data.set_index("Date", inplace=True)
    # 周线不合并K线
    try:
        _merge = True if "daily" == data_level else False
        merged_k_line_data = KiLineObject.k_line_merge(
            row["symbol"], stock_data, merge_or_not=_merge
        )
        chan_data = ChanSourceDataObject(data_level, merged_k_line_data)
        chan_data.gen_data_frame()

        return True, chan_data.is_valid_buy_sell_point_on_k_line(level=data_level)
    except Exception as e:
        print("error".format(stock_symbol))
        print(e)
        return False, tuple()


if __name__ == "__main__":
    set_display()
    print(today_date)

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--market", help="market type, cn or hk")
    parser.add_argument("-c", "--city", help="cn, sh or sz")
    args = parser.parse_args()

    if args.market:
        logging.info("market type is {}".format(args.market))
        if "cn" == args.market:
            if not args.city:
                logging.error("cn market should specify city!")
                exit(-3)
            price_spider = StockInfoSpyder()
        elif "hk" == args.market:
            price_spider = StockInfoSpyder()
        else:
            price_spider = None
            logging.error("check args {}".format(args.market))
            exit(-1)
    else:
        price_spider = None
        logging.error("check args")
        exit(-2)

    db = Database()
    data = (
        db.get_data(
            config.HK_STOCK_DATABASE_NAME,
            config.COLLECTION_NAME_STOCK_BASIC_INFO_HK,
            keys=["symbol", "name"],
        )
        if "hk" == args.market
        else db.get_data(
            config.STOCK_DATABASE_NAME,
            config.COLLECTION_NAME_STOCK_BASIC_INFO,
            keys=["symbol", "name", "end_date"],
        )
    )

    stock_city = args.city if args.market == "cn" else ""
    stock_info_spyder = price_spider
    with open(
        "./info/week_buy_point_res_{}_{}.json".format(args.market, stock_city), "w"
    ) as file:
        for _, row in data.iterrows():
            # cn, needs more condition
            if "cn" == args.market:
                if stock_city not in row["symbol"]:
                    print("市场不对 跳过{}".format(row["symbol"]))
                    continue
                if row["end_date"] < datetime.datetime.now():
                    print("退市了，不考虑{}".format(row["symbol"]))
                    continue

            week_result = check_buy_point_data(
                args.market, row["symbol"], data_level="week"
            )
            if week_result[0]:
                logging.info('week: {}'.format(week_result))
                valid = week_result[1][0]
                last_cross = week_result[1][1]
                valid_ding_date = week_result[1][2]
                valid_di_date = week_result[1][3]
                distance = week_result[1][4]
                variance_week = week_result[1][5]
            else:
                continue

            daily_result = check_buy_point_data(
                args.market, row["symbol"], data_level="daily"
            )
            if daily_result[0]:
                logging.info('daily: {}'.format(daily_result))
                valid_daily = daily_result[1][0]
                last_cross_daily = daily_result[1][1]
                valid_ding_date_daily = daily_result[1][2]
                valid_di_date_daily = daily_result[1][3]
                distance_daily = daily_result[1][4]
                variance_daily = daily_result[1][5]
            else:
                continue

            if valid and valid_daily:
                print(row)
                print(
                    "{} is buy point {},{},{},{}, {},{},{},{}".format(
                        row["symbol"],
                        valid,
                        valid_daily,
                        last_cross,
                        valid_ding_date,
                        valid_di_date,
                        last_cross_daily,
                        valid_ding_date_daily,
                        valid_di_date_daily,
                    )
                )
                file.writelines(
                    "{}\n".format(
                        json.dumps(
                            {
                                "symbol": row["symbol"],
                                "name": row["name"],
                                "last_cross_week": last_cross[0].strftime("%Y-%m-%d"),
                                "last_cross_daily": last_cross_daily[0].strftime(
                                    "%Y-%m-%d"
                                ),
                                "last_valid_ding_date_week": valid_ding_date.strftime(
                                    "%Y-%m-%d"
                                )
                                if valid_ding_date is not None
                                else "",
                                "last_valid_di_date_week": valid_di_date.strftime(
                                    "%Y-%m-%d"
                                )
                                if valid_di_date is not None
                                else "",
                                "distance_week": distance,
                                "distance_daily": distance_daily,
                                "variance_week": variance_week,
                                "variance_daily": variance_daily,
                            },
                            ensure_ascii=False,
                        )
                    )
                )
    pass

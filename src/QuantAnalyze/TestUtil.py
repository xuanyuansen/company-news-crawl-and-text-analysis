# -*- coding:utf-8 -*-
from MongoDbComTools.LocalDbTool import LocalDbTool
import time

# 量化分析用到的一些辅助功能函数


def get_start_and_end_date(target_date: str, previous_date: int, post_date: int):
    time_struct = time.strptime(target_date, "%Y%m%d")
    time_stamp = int(time.mktime(time_struct))
    # print(time_stamp)
    start_day = time.strftime(
        "%Y-%m-%d", time.localtime(time_stamp - previous_date * 86400)
    )
    end_day = time.strftime("%Y-%m-%d", time.localtime(time_stamp + post_date * 86400))
    # print(strTime)
    return start_day, end_day


if __name__ == "__main__":
    whole_stock_price_info = LocalDbTool()

    day_period = get_start_and_end_date("20200331", 3, 30)
    print(day_period)

    a_stock_price = whole_stock_price_info.get_daily_price_data_of_specific_stock(
        symbol="sz000001",
        market_type="cn",
        start_date=day_period[0],
        end_date=day_period[1],
    )
    print("res info")
    res_list = list((a_stock_price[1]["close"]))

    print(res_list[0])
    print(res_list[-1])

    print(whole_stock_price_info.get_symbol_from_code("000001"))
    pass

# -*- coding:utf-8 -*-
# 通过交易量的变化，找到在底部长期盘整，然后突然放量突破的股票，例如万丰奥威或者中信海直这样的形态。
# MACD没有用是后置，主要是量价关系
# 例如邵阳液压、襄阳轴承、红宝丽
from MarketPriceSpiderWithScrapy.StockInfoUtils import get_all_stock_code_info_of_cn
from MongoDbComTools.LocalDbTool import LocalDbTool
import sys
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from Utils.utils import set_display
from tqdm import tqdm

tqdm.pandas(desc="progress status")

local_db = LocalDbTool()


# print(datetime.date(2024,2,1) > datetime.date(2024,1,1))
def get_specific_target_stock(t_stock, market, start):
    return local_db.get_daily_price_data_of_specific_stock(
        symbol=t_stock, market_type=market, start_date=start
    )


# 计算前30天的平均成交量
def average_volume_last_30_days(group):
    return group.tail(30)["volume"].mean()


# AveDate 多少天内的平均股价，Ratio放量倍数
def getVolumeBreakDateList(t_stock, market, start, AveDate: int, Ratio: float):
    res, data = get_specific_target_stock(t_stock, market, start)
    if res and data.shape[0] >= AveDate:
        data["AvgVolumeLast30Days"] = data["volume"].rolling(AveDate).mean()
        # 30 日价格方差，描述的是过去30日价格的波动范围，越小越好
        data["VarClosePriceLast30Days"] = data["close"].rolling(AveDate).var()
        # 30 均线价格
        data["ClosePriceLast30Days"] = data["close"].rolling(AveDate).mean()
        data["TodayVsLast30Days"] = data.progress_apply(
            lambda row: row["close"] - row["ClosePriceLast30Days"],
            axis=1,
        )

        LastTodayVsLast30Days = data["TodayVsLast30Days"].values.tolist()[-1]
        last_close_price = data["close"].values.tolist()[-1]
        data["TodayVolumeVs30"] = data["volume"] / data["AvgVolumeLast30Days"]

        sub_list = data[data["TodayVolumeVs30"] >= Ratio]
        if sub_list.shape[0] > 0:
            price_var_list = sub_list["VarClosePriceLast30Days"].values.tolist()

            firstStartDayClosePrice = sub_list["close"].values.tolist()[0]

            up_ratio = (last_close_price - firstStartDayClosePrice)/ firstStartDayClosePrice

            return (sub_list["date"].values.tolist(),
                    sum(price_var_list) / len(price_var_list),
                    LastTodayVsLast30Days, up_ratio)

        else:
            return [], -1, LastTodayVsLast30Days, 0
    else:
        return [], -1, -1, 0


set_display()

if __name__ == "__main__":
    # res, data = get_specific_target_stock(sys.argv[1], sys.argv[2], sys.argv[3])
    getVolumeBreakDateList(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5]))
    # sys.exit(0)

    info = get_all_stock_code_info_of_cn()
    print(info.shape)
    info = info[~info['名称'].str.contains('ST')]
    print(info.shape)
    # info = info[:100]
    info["BreakDateAndVar"] = info.progress_apply(
        lambda row: getVolumeBreakDateList(
            row["joint_quant_code"], sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5])
        ),
        axis=1,
    )
    print(info)
    info["BreakDate"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][0],
        axis=1,
    )
    info["BreakDateCnt"] = info.progress_apply(
        lambda row: len(row["BreakDate"]),
        axis=1,
    )

    info["LatestBreakDate"] = info.progress_apply(
        lambda row: row["BreakDate"][-1] if len(row["BreakDate"]) > 0 else -1,
        axis=1,
    )

    info["PriceVar"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][1],
        axis=1,
    )

    info["LastTodayVsLast30Days"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][2],
        axis=1,
    )

    info["UpRatioVsFirstVolumeUp"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][3],
        axis=1,
    )

    info["name"] = info["名称"]

    info.to_csv("break_{}_{}_{}_{}.csv".format(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]))

    # We plot the Google stock data
    # plt.plot(data['volume'])
    # We plot the rolling mean ontop of our Google stock data
    # plt.plot(data['AvgVolumeLast30Days'])
    # plt.plot(data['TodayVolumeVs30'])
    # plt.legend(['volume', 'AvgVolumeLast30Days', 'TodayVolumeVs30'])
    # plt.legend(['TodayVolumeVs30'])
    # plt.show()
    pass

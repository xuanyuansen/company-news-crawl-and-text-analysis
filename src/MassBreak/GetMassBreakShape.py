# -*- coding:utf-8 -*-
# 通过交易量的变化，找到在底部长期盘整，然后突然放量突破的股票，例如万丰奥威或者中信海直这样的形态。
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
        data["exp12"] = data["close"].ewm(span=12, adjust=False).mean()
        data["exp26"] = data["close"].ewm(span=26, adjust=False).mean()
        # print(data)
        data["macd"] = data.progress_apply(
            lambda row: row["exp12"] - row["exp26"],
            axis=1,
        )

        data["AvgVolumeLast30Days"] = data["volume"].rolling(AveDate).mean()
        data["VarClosePriceLast30Days"] = data["close"].rolling(AveDate).var()
        # 30 均线价格
        data["ClosePriceLast30Days"] = data["close"].rolling(AveDate).mean()
        data["TodayVsLast30Days"] = data.progress_apply(
            lambda row: row["close"] - row["ClosePriceLast30Days"],
            axis=1,
        )

        LastTodayVsLast30Days = data["TodayVsLast30Days"].values.tolist()[-1]

        data["MACDSumLast30Days"] = data["macd"].rolling(AveDate).sum()
        data["TodayVolumeVs30"] = data["volume"] / data["AvgVolumeLast30Days"]
        sub_list = data[data["TodayVolumeVs30"] >= Ratio]
        if sub_list.shape[0] > 0:
            price_var_list = sub_list["VarClosePriceLast30Days"].values.tolist()
            macd_list = sub_list["MACDSumLast30Days"].values.tolist()
            macd_averge = sum(macd_list)/ len(macd_list)
            return sub_list["date"].values.tolist(), sum(price_var_list) / len(
                price_var_list
            ), macd_list, macd_averge, LastTodayVsLast30Days
        else:
            return [], -1, [0], 0, LastTodayVsLast30Days
    else:
        return [], -1, [0], 0, -1


set_display()

if __name__ == "__main__":
    # res, data = get_specific_target_stock(sys.argv[1], sys.argv[2], sys.argv[3])
    getVolumeBreakDateList(sys.argv[1], sys.argv[2], sys.argv[3], 30, 2)
    # sys.exit(0)

    info = get_all_stock_code_info_of_cn()
    print(info.shape)
    info = info[~info['名称'].str.contains('ST')]
    print(info.shape)
    # info = info[:100]
    info["BreakDateAndVar"] = info.progress_apply(
        lambda row: getVolumeBreakDateList(
            row["joint_quant_code"], sys.argv[2], sys.argv[3], 30, 2
        ),
        axis=1,
    )
    print(info)
    info["BreakDate"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][0],
        axis=1,
    )

    info["PriceVar"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][1],
        axis=1,
    )

    info["BreakDateCnt"] = info.progress_apply(
        lambda row: len(row["BreakDate"]),
        axis=1,
    )
    info["MACDList"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][2],
        axis=1,
    )
    info["MACDAverage"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][3],
        axis=1,
    )
    info["LastTodayVsLast30Days"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][4],
        axis=1,
    )
    info["name"] = info["名称"]

    info.to_csv("break_{}.csv".format(sys.argv[3]))

    # We plot the Google stock data
    # plt.plot(data['volume'])
    # We plot the rolling mean ontop of our Google stock data
    # plt.plot(data['AvgVolumeLast30Days'])
    # plt.plot(data['TodayVolumeVs30'])
    # plt.legend(['volume', 'AvgVolumeLast30Days', 'TodayVolumeVs30'])
    # plt.legend(['TodayVolumeVs30'])
    # plt.show()
    pass

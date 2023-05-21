# -*- coding:utf-8 -*-
# 基础的价值投资模型，利用基本面来打分
import sys

sys.path.append("../")
import akshare as ak
from FinancialAffairs import get_basic_stock
from MongoDbComTools import JointQuantTool
from Utils.utils import set_display, today_date


if __name__ == "__main__":
    # tool = JointQuantTool.JointQuantTool()
    set_display()

    stat_q = sys.argv[1]
    # df = get_basic_stock(stat_q, today_date)
    # https://www.akshare.xyz/data/stock/stock.html#id103
    df = ak.stock_yjbb_em(date=stat_q)
    print(df)
    # 这里面选出股票池，然后再分类研究，电子类，医疗类，小盘次新成长股是牛股的摇篮。再算一下自由现金流估值。
    df.to_csv("价值选股_{0}_{1}.csv".format(stat_q, today_date))
pass

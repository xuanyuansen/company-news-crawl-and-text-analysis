# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# import sys
import sys
from ChanUtils import PlotUtil

# https://www.zhiu.cn/46287.html
import pandas as pd
from MongoDbComTools.LocalDbTool import LocalDbTool
from Utils.utils import set_display, today_date
from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject, plot_with_mlf_v2
import argparse
import logging
import matplotlib

matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Micro Hei"]
matplotlib.rcParams["axes.unicode_minus"] = False
print(matplotlib.matplotlib_fname())


if __name__ == "__main__":
    set_display()
    print(today_date)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--market",
        help="which market",
        required=True,
        default="cn",
        choices=["cn", "hk", "us", "uszh"],
    )

    parser.add_argument(
        "-s",
        "--symbol",
        help="stock code with market type, like sz301419",
    )

    parser.add_argument(
        "-c",
        "--code",
        help="only stock code",
    )

    parser.add_argument(
        "-d",
        "--start",
        help="start date",
    )

    parser.add_argument(
        "-l",
        "--level",
        help="k line level",
        default="week",
        choices=["daily", "week"],
    )

    args = parser.parse_args()
    if args.market:
        logging.info("market type is {}".format(args.market))
        market_type = args.market
    else:
        logging.error("market type unknown!")
        raise Exception("market type unknown!")

    if args.level:
        k_level = args.level
    else:
        k_level = "week"

    t_stock = None

    local_db = LocalDbTool()

    if args.code:
        print("code is {}".format(args.code))
        _stock_code = args.code
    elif args.symbol:
        t_stock = args.symbol
        _stock_code = t_stock[-5]
        print("symbol is {}, code is {}".format(args.symbol, _stock_code))
    else:
        print("should input code or symbol(code with markey type)!!!")
        sys.exit(-2)

    if "cn" == args.market:
        info_frame = local_db.get_target_stock_info_by_code(stock_code=_stock_code)

        print(info_frame)

        name = str(info_frame["name"].values[0])
        t_stock = str(info_frame["symbol"].values[0])
        print("name is {}, symbol is {}".format(name, t_stock))
    elif "hk" == args.market:
        if args.code:
            t_stock = args.code
        else:
            t_stock = args.symbol
        info_frame = local_db.get_target_stock_info_by_code_of_hk(t_stock)
        name = str(info_frame["name"].values[0])
    else:
        sys.exit(0)
        pass

    data_res, df = (
        local_db.get_week_data_stock(symbol=t_stock, market_type=args.market)
        if "week" == k_level
        else local_db.get_daily_price_data_of_specific_stock(
            symbol=t_stock, market_type=args.market, start_date=args.start
        )
    )
    if not data_res:
        sys.exit(-1)

    print(df.shape)
    # db = Database()
    # df = db.get_data(database_name='stock', collection_name='000001.XSHE_week')
    # print(df[:100])
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.to_datetime.html
    # https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
    df["Date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df.set_index("Date", inplace=True)
    # print(df[:100])
    # run_type = str(sys.argv[4])

    stock_data = df

    merged_k_line_data = KiLineObject.k_line_merge(t_stock, stock_data)
    chan_data = ChanSourceDataObject(k_level, merged_k_line_data)
    chan_data.gen_data_frame()

    cross_list = chan_data.get_cross_list()
    print(cross_list)
    ding_di_data = chan_data.get_ding_di()
    print(ding_di_data)

    (
        res,
        cross,
        ding,
        di,
        distance,
        variance,
    ) = chan_data.is_valid_buy_sell_point_on_k_line()
    print(
        "is buy point {} {} {} {} {} {}".format(
            res, cross, ding, di, distance, variance
        )
    )

    plot_with_mlf_v2(
        chan_data, "{0},{1},{2}".format(t_stock, name, k_level), today_date
    )

    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    df.set_index("date", inplace=True)
    # print(df[:100])
    _plot = PlotUtil.PlotUtil(df)
    _plot.plot(t_stock, name)

    pass

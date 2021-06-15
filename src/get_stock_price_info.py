# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import logging
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
from Utils import utils
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--market",
        help="which market",
        required=True,
        choices=["cn", "hk", "us", "uszh"],
    )
    parser.add_argument("-s", "--start_date", help="set start date")
    parser.add_argument(
        "-j", "--joint_quant", help="weather to init quant", default=False
    )
    parser.add_argument("-c", "--start_code", help="start code")
    args = parser.parse_args()

    if args.market:
        logging.info("market type is {}".format(args.market))
        market_type = args.market
    else:
        logging.error("market type unknown!")
        raise Exception("market type unknown!")
    if args.start_date:
        _start_date = args.start_date
    else:
        _start_date = None
    if args.start_code:
        _start_symbol = args.start_code
    else:
        _start_symbol = None

    utils.set_display()

    # cn_stock_info_spyder = StockInfoSpyder(joint_quant_on=False)
    stock_info_spyder = StockInfoSpyder(joint_quant_on=args.joint_quant)

    if "cn" == market_type:
        stock_info_spyder.get_historical_cn_stock_daily_price(start_date=_start_date)
    elif "hk" == market_type:
        stock_info_spyder.get_historical_hk_stock_daily_price(
            start_date=_start_date, start_symbol=_start_symbol
        )
    elif "us" == market_type:
        # stock_info_spyder.get_historical_us_zh_stock_daily_price()
        stock_info_spyder.get_historical_us_stock_daily_price(start_date=_start_date)
    else:
        stock_info_spyder.get_historical_us_zh_stock_daily_price()
    pass

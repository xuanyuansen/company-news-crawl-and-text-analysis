# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
# import sys
import pandas as pd

from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
from Utils import config
from Utils.database import Database
from Utils.utils import set_display, today_date
from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject, plot_with_mlf_v2


if __name__ == '__main__':
    set_display()
    print(today_date)

    stock_info_spyder = StockInfoSpyder(
        config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO
    )

    t_stock = 'sh600000'
    k_level = 'week'
    name = '浦发银行'
    df = stock_info_spyder.get_week_data_cn_stock(symbol='sh600000', market_type='cn')

    # db = Database()
    # df = db.get_data(database_name='stock', collection_name='000001.XSHE_week')
    print(df[:100])
    # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.to_datetime.html
    # https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
    df['Date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')
    df.set_index("Date", inplace=True)
    print(df[:100])
    # run_type = str(sys.argv[4])

    stock_data = df

    merged_k_line_data = KiLineObject.k_line_merge(t_stock, stock_data)
    chan_data = ChanSourceDataObject(k_level, merged_k_line_data)
    chan_data.gen_data_frame()

    cross_list = chan_data.get_cross_list()
    print(cross_list)
    ding_di_data = chan_data.get_ding_di()
    print(ding_di_data)

    res = chan_data.is_valid_buy_sell_point_on_week_line()
    print('is buy point {}'.format(res))

    plot_with_mlf_v2(chan_data, '{0},{1},{2}'.format(t_stock, name, k_level), today_date)

    pass

# -*- coding:utf-8 -*-
"""
author wangshuai
date 2021/06/03
"""
import datetime
import json

import pandas as pd

from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
from Utils.utils import set_display, today_date
from Utils import config
from Utils.database import Database
import warnings

warnings.filterwarnings("ignore")

if __name__ == '__main__':
    set_display()
    print(today_date)
    db = Database()

    stock_info_spyder = StockInfoSpyder(
        config.STOCK_DATABASE_NAME, config.COLLECTION_NAME_STOCK_BASIC_INFO
    )

    data = db.get_data(config.STOCK_DATABASE_NAME,
                       config.COLLECTION_NAME_STOCK_BASIC_INFO,
                       keys=["symbol", "name", "end_date"])
    with open('./info/week_buy_point_res.json', 'w') as file:
        for _, row in data.iterrows():
            if row['end_date'] < datetime.datetime.now():
                continue
            stock_data = stock_info_spyder.get_week_data_cn_stock(row['symbol'], market_type='cn')
            stock_data['Date'] = pd.to_datetime(stock_data['date'], format='%Y-%m-%d')
            stock_data.set_index("Date", inplace=True)
            merged_k_line_data = KiLineObject.k_line_merge(row['symbol'], stock_data)
            chan_data = ChanSourceDataObject('week', merged_k_line_data)
            chan_data.gen_data_frame()

            valid, last_cross, valid_ding_date, valid_di_date = chan_data.is_valid_buy_sell_point_on_week_line()
            if valid:
                print(row)
                print('is buy point {},{},{},{}'.format(valid, last_cross, valid_ding_date, valid_di_date))
                file.writelines('{}\n'.format(json.dumps({'symbol': row['symbol'],
                                                          'name': row['name'],
                                                          'last_cross': last_cross[0].strftime('%Y-%m-%d'),
                                                          'last_valid_ding_date': valid_ding_date.strftime('%Y-%m-%d'),
                                                          'last_valid_di_date': valid_di_date.strftime('%Y-%m-%d')})))

    pass

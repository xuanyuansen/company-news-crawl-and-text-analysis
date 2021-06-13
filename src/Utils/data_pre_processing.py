# 用于数据预处理
import config
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
import pandas as pd
from datetime import datetime
from utils import set_display


class DataPreProcessing(object):
    def __init__(self):
        self.price_spider = StockInfoSpyder()
        self.db = self.price_spider.db_obj
        pass

    def get_symbols(self, market_type):
        if 'cn' == market_type:
            data = self.db.get_data(
                config.STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO,
                query={"end_date": {"$gt": datetime(2021, 1, 1, 0, 0, 0, 000000)}},
                keys=["symbol", "name", "end_date"],
            )
        elif 'hk' == market_type:
            data = self.db.get_data(
                config.HK_STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO_HK,
                keys=["symbol", "name"],
            )
        elif 'us' == market_type:
            data = self.db.get_data(
                config.US_STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO_US,
                keys=["symbol", "name"],
            )
        else:
            data = self.db.get_data(
                config.US_STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO_US_ZH,
                keys=["symbol", "name"],
            )
        return data

    def get_label(self, symbols: pd.DataFrame,
                  market_type: str,
                  start_date: str = None,
                  cnt_limit: int = None):
        week_data = symbols[:cnt_limit]
        week_data['week'] = week_data.apply(
            lambda row:
            self.price_spider.get_week_data_stock(row['symbol'], market_type=market_type, start_date=start_date)[1],
            axis=1
        )

        # print(week_data)
        week_data['ratio'] = week_data.apply(
            lambda row: 100 * (row['week'].iloc[-1, 1] - row['week'].iloc[-1, 0]) / row['week'].iloc[-1, 0], axis=1)
        print(week_data['ratio'].max())
        print(week_data['ratio'].min())

        def _set_label(_value: float):
            if _value <= -30.0:
                return -2
            elif -30 < _value <= -5:
                return -1
            elif -5 < _value <= 5:
                return 0
            elif 5 < _value <= 30:
                return 1
            else:
                return 2

        week_data['label'] = week_data.apply(lambda row: _set_label(row['ratio']), axis=1)
        print(week_data[:10])

        label_cnt = week_data.groupby(['label']).size()
        print(label_cnt)

        return week_data
    pass


if __name__ == "__main__":
    set_display()
    dpp = DataPreProcessing()
    symbol_data = dpp.get_symbols('cn')
    dpp.get_label(symbols=symbol_data, market_type='cn', start_date='2021-06-01')

    pass

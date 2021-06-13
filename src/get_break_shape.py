# -*- coding:utf-8 -*-
# 获得在日线级别长期扰动，然后突然放量的股票，例如近期物产中大，佳沃股份等，看看他们的特征。
# 有一个很长的中枢，中枢对应的macd的variance很小。物产中大的特征。
# 后续可以有两种方式，一种是直接利用variance，长度，ratio来做排序和筛选，另外一种是做机器学习。
# 机器学习这么处理数据，先用形态学的顶底等等划分出
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
import sys
import pandas as pd
from Utils.utils import set_display, today_date
from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject, plot_with_mlf_v2
from Surpriver import feature_generator


if __name__ == "__main__":
    set_display()
    print(today_date)
    price_spider = StockInfoSpyder()
    fEngine = feature_generator.TAEngine(history_to_use=0)
    res, stock_data = price_spider.get_daily_price_data_of_specific_stock(symbol=sys.argv[1],
                                                                          market_type='cn',
                                                                          start_date="2020-01-01")
    print(stock_data[:10])
    stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")
    stock_data.set_index("Date", inplace=True)

    k_line_data = KiLineObject.k_line_merge(
        sys.argv[1], stock_data, merge_or_not=False
    )
    chan_data = ChanSourceDataObject("daily", k_line_data)
    chan_data.gen_data_frame()
    _stock_data = chan_data.get_plot_data_frame()
    print(_stock_data[:10])
    feature_dict = fEngine.get_technical_indicators(_stock_data)
    _sub_feature_list = fEngine.get_features(feature_dict)
    print(_sub_feature_list)

    dynamic = chan_data.histogram

    zhong_shu_list = chan_data.get_zhong_shu_list()

    if len(zhong_shu_list) > 0:
        zhong_shu = zhong_shu_list[0]
        print('start idx {} end idx {}'.format(zhong_shu.start_index, zhong_shu.end_index))
        print('ratio {}, last day {}'.format(zhong_shu.zhong_shu_strength_ratio,
                                             zhong_shu.zhong_shu_time_strength_length))

        sub_dynamic = dynamic[zhong_shu.start_index: zhong_shu.end_index]
        sub_macd = chan_data.macd[zhong_shu.start_index: zhong_shu.end_index]
        print('zhong shu length is {}, variance is {}, macd var is {}'.format(sub_dynamic.shape[0],
                                                                              sub_dynamic.var(),
                                                                              sub_macd.var()))
    else:
        xian_duan_list = chan_data.merged_chan_line_list if len(chan_data.merged_chan_line_list) > 0 \
            else chan_data.origin_chan_line_list
        start_index = xian_duan_list[0].get_start_index()
        end_index = xian_duan_list[-1].get_end_index()
        sub_dynamic = dynamic[start_index: end_index]
        sub_macd = chan_data.macd[start_index: end_index]
        print('xian duan length is {}, variance is {}, macd var is {}'.format(sub_dynamic.shape[0],
                                                                              sub_dynamic.var(),
                                                                              sub_macd.var()))

    plot_with_mlf_v2(
        chan_data, "{0},{1},{2}".format(sys.argv[1], sys.argv[1], "daily"), today_date
    )
    pass

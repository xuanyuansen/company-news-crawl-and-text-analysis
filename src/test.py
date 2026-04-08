# from sklearn import model_selection
# from xgboost import XGBClassifier

# from ChanUtils.BasicUtil import KiLineObject
# from ChanUtils.ChanFeature import DeepFeatureGen
# from ChanUtils.ShapeUtil import ChanSourceDataObject
# from MarketPriceSpiderWithScrapy.StockInfoSpyder import StockInfoSpyder

# # import xgboost as xgb
# import sys
# import pandas as pd

# from NlpModel.ChanBasedCnn import CustomChanDataset, TextCNN
# from Utils.utils import set_display
# from NlpModel.DataPreProcessing import DataPreProcessing

# set_display()

# param = {
#     "max_depth": 5,
#     "eta": 1,
#     "num_class": 4,
#     "tree_method": "gpu_hist",
# }

# model = XGBClassifier(param, objective="multi:softmax")

# price_spider = StockInfoSpyder()
# res, df = price_spider.get_week_data_stock(
#     symbol="sz000001", market_type="cn", start_date="2021-06-04", end_date="2021-06-20"
# )
# if res:
#     print(df)
# exit(0)

# data_processor = DataPreProcessing(feature_size=40, history_day_ta_feature_to_use=10)
# # data_processor.get_ta_feature()

# _res, stock_data = price_spider.get_daily_price_data_of_specific_stock(
#     symbol="sz000001", market_type="cn", start_date="2020-06-01"
# )
# print(stock_data[:10])
# print("stock shape is {}".format(stock_data.shape))
# feature_list = data_processor.get_ta_feature(stock_data, upper_case=False)
# print("feature list size {}".format(len(feature_list)))
# print("feature list {}".format(feature_list))


# stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")
# stock_data.set_index("Date", inplace=True)

# k_line_data = KiLineObject.k_line_merge("sz000930", stock_data, merge_or_not=True)
# chan_data = ChanSourceDataObject("daily", k_line_data)
# chan_data.gen_data_frame()
# chan_data.get_plot_data_frame()

# data = price_spider.col_basic_info_cn.find_one({"symbol": "sz000930"})
# print(data["concept"])
# print(data["industry"])
# deep_fea_gen = DeepFeatureGen(chan_data)
# res = deep_fea_gen.get_deep_sequence_feature(data["industry"], data["concept"])
# print(res)
# print("bi feature length {}".format(len(res)))
# print(deep_fea_gen.concept_list)
# print(deep_fea_gen.industry_list)
# print(deep_fea_gen.industry_to_index)
# print(deep_fea_gen.concept_to_index)
# print(deep_fea_gen.from_industry_to_feature(data["industry"]))
# print(deep_fea_gen.from_concept_to_feature(data["concept"]))
# print(sum(deep_fea_gen.from_concept_to_feature(data["concept"])))

# from MassBreak.BacktestFramework import BacktestFramework, strategy_adapter_alphago, strategy_adapter_shape
# from Utils.utils import set_display

# set_display()


# if __name__ == "__main__":
#     import sys
    
#     # 示例用法
#     if len(sys.argv) < 6:
#         print("用法: python BacktestFramework.py <策略类型> <市场类型> <开始日期> <平均天数> <放量倍数> [持有天数] [止损] [止盈]")
#         print("策略类型: alphago 或 shape")
#         print("示例: python BacktestFramework.py alphago cn 2026-01-01 30 1.2 30 0.1 0.2")
#         sys.exit(1)
    
#     strategy_type = sys.argv[1]  # "alphago" 或 "shape"
#     market_type = sys.argv[2]
#     start_date = sys.argv[3]
#     ave_date = int(sys.argv[4])
#     ratio = float(sys.argv[5])
#     hold_days = int(sys.argv[6]) if len(sys.argv) > 6 else 30
#     stop_loss = float(sys.argv[7]) if len(sys.argv) > 7 else None
#     take_profit = float(sys.argv[8]) if len(sys.argv) > 8 else None
    
#     # 选择策略
#     if strategy_type == "alphago":
#         strategy_func = strategy_adapter_alphago
#     elif strategy_type == "shape":
#         strategy_func = strategy_adapter_shape
#     else:
#         print(f"未知策略类型: {strategy_type}")
#         sys.exit(1)
    
#     # 创建回测框架
#     backtest = BacktestFramework(
#         strategy_func=strategy_func,
#         market_type=market_type,
#         start_date=start_date,
#         hold_days=hold_days,
#         stop_loss=stop_loss,
#         take_profit=take_profit
#     )
    
#     # 运行回测
#     results = backtest.run_backtest(ave_date=ave_date, ratio=ratio, stock_list=["sh600938"])#, "sh600938", "sz000547"])
    
#     # 生成报告
#     output_file = f"backtest_{strategy_type}_{market_type}_{start_date}_{ave_date}_{ratio}.csv"
#     backtest.generate_report(output_file=output_file)
    
#     # 绘制图表
#     plot_file = f"backtest_{strategy_type}_{market_type}_{start_date}_{ave_date}_{ratio}.png"
#     backtest.plot_results(save_path=plot_file)

# from MassBreak.StockFundamentalIndicators import get_fundamental_indicators, print_fundamental_indicators
# # 获取指标字典
# indicators = get_fundamental_indicators("600938")
# print(indicators["pe_ttm"], indicators["ps"], indicators["revenue_yoy"], indicators["profit_yoy"])
# # 打印
# print_fundamental_indicators("600938")


# from Utils import config
# from MarketNewsSpiderWithScrapy.BasePlayCrawler import PlaywrightCrawlerProcess
# from scrapy.utils.project import get_project_settings
# from MarketNewsSpiderWithScrapy.mei_tong_spider import MeiTongSpider

# settings = get_project_settings()
# _process_play = PlaywrightCrawlerProcess(settings)


# for spider_config in config.MEI_TONG_SHE_SPIDER_LIST:
#     _process_play.crawl(MeiTongSpider, **spider_config)

# _process_play.start()

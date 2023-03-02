from sklearn import model_selection
from xgboost import XGBClassifier

from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ChanFeature import DeepFeatureGen
from ChanUtils.ShapeUtil import ChanSourceDataObject
from MarketPriceSpiderWithScrapy.StockInfoSpyder import StockInfoSpyder

# import xgboost as xgb
import sys
import pandas as pd

from NlpModel.ChanBasedCnn import CustomChanDataset, TextCNN
from Utils.utils import set_display
from NlpModel.DataPreProcessing import DataPreProcessing

set_display()

param = {
    "max_depth": 5,
    "eta": 1,
    "num_class": 4,
    "tree_method": "gpu_hist",
}

model = XGBClassifier(param, objective="multi:softmax")

price_spider = StockInfoSpyder()
res, df = price_spider.get_week_data_stock(
    symbol="sz000001", market_type="cn", start_date="2021-06-04", end_date="2021-06-20"
)
if res:
    print(df)
exit(0)

data_processor = DataPreProcessing(feature_size=40, history_day_ta_feature_to_use=10)
# data_processor.get_ta_feature()

_res, stock_data = price_spider.get_daily_price_data_of_specific_stock(
    symbol="sz000001", market_type="cn", start_date="2020-06-01"
)
print(stock_data[:10])
print("stock shape is {}".format(stock_data.shape))
feature_list = data_processor.get_ta_feature(stock_data, upper_case=False)
print("feature list size {}".format(len(feature_list)))
print("feature list {}".format(feature_list))


stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")
stock_data.set_index("Date", inplace=True)

k_line_data = KiLineObject.k_line_merge("sz000930", stock_data, merge_or_not=True)
chan_data = ChanSourceDataObject("daily", k_line_data)
chan_data.gen_data_frame()
chan_data.get_plot_data_frame()

data = price_spider.col_basic_info_cn.find_one({"symbol": "sz000930"})
print(data["concept"])
print(data["industry"])
deep_fea_gen = DeepFeatureGen(chan_data)
res = deep_fea_gen.get_deep_sequence_feature(data["industry"], data["concept"])
print(res)
print("bi feature length {}".format(len(res)))
print(deep_fea_gen.concept_list)
print(deep_fea_gen.industry_list)
print(deep_fea_gen.industry_to_index)
print(deep_fea_gen.concept_to_index)
print(deep_fea_gen.from_industry_to_feature(data["industry"]))
print(deep_fea_gen.from_concept_to_feature(data["concept"]))
print(sum(deep_fea_gen.from_concept_to_feature(data["concept"])))

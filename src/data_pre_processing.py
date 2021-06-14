# 用于数据预处理
from Utils import config
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
import pandas as pd
from datetime import datetime
from Utils.utils import set_display
from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject
from ChanUtils.ChanFeature import BasicFeatureGen
import xgboost as xgb
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
from sklearn import model_selection, metrics


class DataPreProcessing(object):
    def __init__(self, feature_size:int):
        self.price_spider = StockInfoSpyder()
        self.db = self.price_spider.db_obj
        self.bfg = BasicFeatureGen()
        self.feature_size = feature_size
        pd.set_option("mode.use_inf_as_na", True)
        pass

    def get_symbols(self, market_type):
        if "cn" == market_type:
            data = self.db.get_data(
                config.STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO,
                query={"end_date": {"$gt": datetime(2021, 1, 1, 0, 0, 0, 000000)}},
                keys=["symbol", "name", "end_date"],
            )
        elif "hk" == market_type:
            data = self.db.get_data(
                config.HK_STOCK_DATABASE_NAME,
                config.COLLECTION_NAME_STOCK_BASIC_INFO_HK,
                keys=["symbol", "name"],
            )
        elif "us" == market_type:
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

    # 加入end_date过滤数据，不能有未来数据！！！
    def from_symbol_to_feature(self, _symbol, end_date):
        res, stock_data = self.price_spider.get_daily_price_data_of_specific_stock(
            symbol=_symbol, market_type="cn", start_date="2020-01-01"
        )
        if not res:
            return None

        stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")
        
        # 注意这里通过start_date获得最后一周的标签，
        # 那么用于计算特征的数据不能包含这周的数据
        stock_data = stock_data[stock_data["Date"] < end_date]
        # print(stock_data[-40:])

        stock_data.set_index("Date", inplace=True)

        k_line_data = KiLineObject.k_line_merge(_symbol, stock_data, merge_or_not=True)
        chan_data = ChanSourceDataObject("daily", k_line_data)
        chan_data.gen_data_frame()
        chan_data.get_plot_data_frame()

        self.bfg.set_base_data(chan_data)

        return self.bfg.get_feature()

   
    def get_label(
        self,
        symbols: pd.DataFrame,
        market_type: str,
        start_date: str = None,
        cnt_limit_start: int = None,
        cnt_limit_end: int = None,
    ):
        week_data = symbols[cnt_limit_start:cnt_limit_end]
        week_data["week"] = week_data.apply(
            lambda row: self.price_spider.get_week_data_stock(
                row["symbol"],
                market_type=market_type,
                start_date=start_date,
            )[1],
            axis=1,
        )

        week_data["week_data_shape"] = week_data.apply(
            lambda row: row["week"].shape[0], axis=1
        )

        # 过滤没有标签的数据
        week_data = week_data[week_data["week_data_shape"] >= 1]
        week_data['week_data_start_date'] = week_data.apply(lambda row:row['week'].index[-1], axis=1)
        # print(week_data)

        # week_data_start_date_cnt = week_data.groupby(['week_data_start_date']).size()
        # print(type(week_data_start_date_cnt))
        # print(week_data_start_date_cnt)
        # print(week_data_start_date_cnt.shape)
        # print(week_data_start_date_cnt.values)
        # print(week_data_start_date_cnt.index)
        # week_data_start_date_cnt.index is 
        # DatetimeIndex(['2021-06-07'], dtype='datetime64[ns]', name='week_data_start_date', freq=None)

        week_data["ratio"] = week_data.apply(
            lambda row: 100
            * (row["week"].iloc[-1, 1] - row["week"].iloc[-1, 0])
            / row["week"].iloc[-1, 0],
            axis=1,
        )
        print(week_data["ratio"].max())
        print(week_data["ratio"].min())

        def _set_label(_value: float):
            if _value <= -10.0:
                return 0
            elif -10 < _value <= 0:
                return 1
            elif 0 < _value <= 10:
                return 2
            else:
                return 3

        week_data["label"] = week_data.apply(
            lambda row: _set_label(row["ratio"]), axis=1
        )
        week_data["features"] = week_data.apply(
            lambda row: self.from_symbol_to_feature(row["symbol"], row['week_data_start_date']), axis=1
        )

        # week_data = week_data[week_data['features'] is not None]

        # 10 + 10 + 13
        #
        for idx in range(0, self.feature_size):
            week_data["feature_{}".format(idx)] = week_data.apply(
                lambda row: row["features"][idx], axis=1
            )

        # week_data.drop(['features'], axis=1, inplace=True)

        null_data = week_data[week_data.isnull().T.any()]
        print(null_data)
        print(week_data.shape)

        label_cnt = week_data.groupby(["label"]).size()
        print(label_cnt)

        return week_data, label_cnt

    pass


if __name__ == "__main__":
    set_display()
    dpp = DataPreProcessing(feature_size = 38)
    symbol_data = dpp.get_symbols("cn")

    data_set, label_sum = dpp.get_label(
        symbols=symbol_data, market_type="cn", start_date="2021-06-01", cnt_limit_start=0, cnt_limit_end=2500
    )
    label_set=data_set["label"]

    X_train, X_test, y_train, y_test = model_selection.train_test_split(data_set, label_set, test_size=0.33, random_state=42)

    f_names = []
    for idx in range(0, dpp.feature_size):
        f_names.append("feature_{}".format(idx))

    # https://xgboost.readthedocs.io/en/latest/python/python_intro.html#setting-parameters
    # data = pandas.DataFrame(np.arange(12).reshape((4,3)), columns=['a', 'b', 'c'])
    # label = pandas.DataFrame(np.random.randint(2, size=4))
    # dtrain = xgb.DMatrix(data, label=label)
    dtrain = xgb.DMatrix(X_train[f_names], label=y_train)
    dtest = xgb.DMatrix(X_test[f_names])
    param = {
        "max_depth": 5,
        "eta": 1,
        "objective": "multi:softmax",
        "num_class": 4,
        "tree_method": "gpu_hist",
    }
    num_round = 10
    evallist = [(dtest, 'eval'), (dtrain, 'train')]
    bst = xgb.train(param, dtrain, num_round, evallist)

    y_pred_train = bst.predict(dtrain)
    accuracy = accuracy_score(y_train, y_pred_train)
    # roc_auc = metrics.roc_auc_score(y_train, y_pred_train)
    print("train accuarcy: %.2f%%" % (accuracy * 100.0))
    # print(roc_auc)



    # 计算准确率
    y_pred = bst.predict(dtest)
    print(y_pred)
    accuracy = accuracy_score(y_test, y_pred)
    # roc_auc = metrics.roc_auc_score(y_test, y_pred)
    print("test accuarcy: %.2f%%" % (accuracy * 100.0))
    # print(roc_auc)

    print(bst.get_fscore())
    bst.save_model('0001.model')
    pass

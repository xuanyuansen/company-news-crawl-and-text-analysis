# -*- coding:utf-8 -*-
# from Utils.utils import set_display
import platform
import argparse
import sys

import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import (
    accuracy_score,
    mean_squared_error,
    confusion_matrix,
    precision_score,
)
from sklearn import model_selection

# from sklearn.ensemble import RandomForestClassifier
# from sklearn.model_selection import cross_val_score
from NlpModel.DataPreProcessing import DataPreProcessing
import pandas as pd

# 显示所有列
pd.set_option("display.max_columns", None)
# 显示所有行
pd.set_option("display.max_rows", None)
pd.set_option("max_colwidth", 500)


parser = argparse.ArgumentParser()
parser.add_argument("-c", "--classify_mode", default="binary", help="类别数", type=str)
parser.add_argument("-f", "--feature_file", help="指定特征文件", type=str)
parser.add_argument(
    "--week_data_start_date", default="2022-06-07", help="提取标签的开始周日期", type=str
)
parser.add_argument(
    "--week_data_end_date", default="2022-06-19", help="提取标签的开始周日期", type=str
)
parser.add_argument("-m", "--market_type", default="cn", type=str)
parser.add_argument("-g", "--gpu_mode", default=False, type=bool)


if __name__ == "__main__":
    _args = parser.parse_args()

    # set_display()
    dpp = DataPreProcessing(feature_size=40)
    symbol_data = dpp.get_symbols(_args.market_type)
    print("symbol_data is {}".format(symbol_data))
    if _args.feature_file:
        data_set, label_sum, _, _, _max_ta_length = dpp.direct_load_feature_file(
            _args.feature_file
        )
    else:
        data_set, label_sum, _, _, _max_ta_length = dpp.get_label(
            symbols=symbol_data,
            # market_type="cn",
            week_data_start_date=_args.week_data_start_date,
            week_data_end_date=_args.week_data_end_date,
            cnt_limit_start=0,
            cnt_limit_end=10,
        )
    if _args.classify_mode and _args.classify_mode == "binary":
        data_set["label"] = data_set.apply(
            lambda row: 0 if row["label"] <= 1 else 1, axis=1
        )
    print("data_set type is {}".format(data_set))
    print(data_set)
    sys.exit(0)

    label_set = data_set["label"]

    X_train, X_test, y_train, y_test = model_selection.train_test_split(
        data_set, label_set, test_size=0.3, random_state=2021
    )

    f_names = []
    for idx in range(0, dpp.feature_size):
        f_names.append("feature_{}".format(idx))

    for _idx in range(0, _max_ta_length):
        f_names.append("ta_feature_{}".format(_idx))

    # https://xgboost.readthedocs.io/en/latest/python/python_intro.html#setting-parameters
    # data = pandas.DataFrame(np.arange(12).reshape((4,3)), columns=['a', 'b', 'c'])
    # label = pandas.DataFrame(np.random.randint(2, size=4))
    # dtrain = xgb.DMatrix(data, label=label)
    dtrain = xgb.DMatrix(X_train[f_names], label=y_train)
    dtest = xgb.DMatrix(X_test[f_names])
    param = {
        "max_depth": 2,
        "eta": 1,
        "objective": "multi:softmax",
        "num_class": 2
        if _args.classify_mode and _args.classify_mode == "binary"
        else 4,
        "tree_method": "gpu_hist" if platform.system() == "Linux" else "hist",
    }
    num_round = 10

    bst = xgb.train(param, dtrain, num_round)

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
    bst.save_model("0001.model")

    # # data_set, label_set
    # rf = RandomForestClassifier(n_estimators=100)
    # score = cross_val_score(rf, data_set[f_names], label_set, cv=5, scoring="accuracy")
    # print(score)
    # print(score.mean())
    lgb_model = lgb.LGBMClassifier(
        num_leaves=512,
        n_estimators=100,
        # max_depth=15,
        subsample=0.85,
        colsample_bytree=0.85,
        learning_rate=0.02,
        # class_weight={0: 1, 1: 2},
        n_jobs=20,
        reg_alpha=0.1,
        reg_lambda=0.1,
        random_state=2021,
    )
    lgb_model.fit(X_train[f_names], y_train)
    y_prediction = lgb_model.predict(X_test[f_names])
    prob = lgb_model.predict_proba(X_test[f_names])
    print(prob.shape)
    red_prob = prob[:, 1]
    X_test["red"] = prob[:, 1]
    df1 = X_test.sort_values(by=["red"], ascending=False)
    df1 = df1[["symbol", "name", "ratio", "label", "red"]]
    df1 = df1[df1["red"] >= 0.8]
    df1_1 = df1[df1["label"] == 1].shape[0]
    df1_0 = df1[df1["label"] == 0].shape[0]
    print(df1)
    print("correct is {}".format(df1_1 / (df1_1 + df1_0)))
    # eval
    print("The rmse of prediction is:", mean_squared_error(y_test, y_prediction) ** 0.5)
    cm = confusion_matrix(y_test, y_prediction, labels=[0, 1, 2, 3])
    print(cm)
    accuracy_lgb = accuracy_score(y_test, y_prediction)
    precision_lgb = precision_score(y_test, y_prediction, average="micro")
    print("accuracy_lgb {}".format(accuracy_lgb))
    print("precision_lgb {}".format(precision_lgb))
    # feature importance
    print("Feature importance:", list(lgb_model.feature_importances_))
    pass

# -*- coding:utf-8 -*-
import sys

from sklearn import model_selection
from sklearn.metrics import confusion_matrix, accuracy_score
from DataPreProcessing import DataPreProcessing

# from Utils.utils import set_display
import lightgbm as lgb
import pandas as pd

# 显示所有列
pd.set_option("display.max_columns", None)
# 显示所有行
pd.set_option("display.max_rows", None)
pd.set_option("max_colwidth", 500)


if __name__ == "__main__":
    # set_display()
    dpp = DataPreProcessing(feature_size=40)
    data_set, label_sum, _, _, _max_ta_length = dpp.direct_load_feature_file(
        sys.argv[1]
    )

    data_set["label"] = data_set.apply(
        lambda row: 0 if row["label"] <= 1 else 1, axis=1
    )
    label_set = data_set["label"]

    f_names = []
    for idx in range(0, dpp.feature_size):
        f_names.append("feature_{}".format(idx))

    for _idx in range(0, _max_ta_length):
        f_names.append("ta_feature_{}".format(_idx))

    lgb_model = lgb.LGBMClassifier(
        num_leaves=512,
        n_estimators=200,
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

    X_train, X_test, y_train, y_test = model_selection.train_test_split(
        data_set, label_set, test_size=0.3, random_state=2021
    )

    lgb_model.fit(X_train[f_names], y_train)
    y_prediction = lgb_model.predict(X_test[f_names])
    cm = confusion_matrix(y_test, y_prediction, labels=[0, 1])
    print(cm)
    accuracy_lgb = accuracy_score(y_test, y_prediction)
    print("accuracy_lgb {}".format(accuracy_lgb))

    data_set_predict, label_sum, _, _, _max_ta_length = dpp.direct_load_feature_file(
        sys.argv[2]
    )

    prob = lgb_model.predict_proba(data_set_predict[f_names])
    print(prob.shape)
    red_prob = prob[:, 1]
    data_set_predict["red"] = prob[:, 1]
    df1 = data_set_predict.sort_values(by=["red"], ascending=False)
    df1 = df1[["symbol", "name", "ratio", "label", "red"]]
    df1 = df1[df1["red"] >= 0.8]
    df1_1 = df1[df1["label"] == 1].shape[0]
    df1_0 = df1[df1["label"] == 0].shape[0]
    print(df1)
    print("correct is {}".format(df1_1 / (df1_1 + df1_0)))
    pass

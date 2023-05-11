# -*- coding:utf-8 -*-
# date="20200331"; choice of {"XXXX0331", "XXXX0630", "XXXX0930", "XXXX1231"}
# 看财报出现前三日股价，与后15日平均股价，后30日平均股价之间的关系。
from sklearn import model_selection
from sklearn.metrics import accuracy_score
from sklearn.tree import DecisionTreeClassifier
from Utils.utils import set_display, today_date
import argparse
from MongoDbComTools.LocalDbTool import LocalDbTool
import akshare as ak
from tqdm import tqdm
import pandas as pd
from TestUtil import get_start_and_end_date
from sklearn import tree
from matplotlib import pyplot as plt
tqdm.pandas(desc="progress status")


if __name__ == "__main__":
    set_display()
    print(today_date)

    local_db_tool = LocalDbTool()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--season",
        help="which season",
        required=True,
        choices=["0331", "0630", "0930", "1231"],
    )
    parser.add_argument("-y", "--year", help="report of which year")

    args = parser.parse_args()

    target_date = "{0}{1}".format(args.year, args.season)
    print("target date is {}".format(target_date))

    stock_yjbb_em_df = ak.stock_yjbb_em(date=target_date)
    print(stock_yjbb_em_df[:5])
    # 每股收益, 营业收入-营业收入,营业收入-同比增长,营业收入-季度环比增长,净利润-净利润,净利润-同比增长,净利润-季度环比增长
    # 每股净资产, 净资产收益率, 每股经营现金流量, 销售毛利率

    stock_yjbb_em_df_feature = stock_yjbb_em_df[
        [
            "股票代码",
            "股票简称",
            "每股收益",
            "营业收入-营业收入",
            "营业收入-同比增长",
            "净利润-季度环比增长",
            "净利润-净利润",
            "每股净资产",
            "净资产收益率",
            "每股经营现金流量",
            "销售毛利率",
        ]
    ]
    # 获取特征
    print(stock_yjbb_em_df_feature[:5])
    print("stock_yjbb_em_df_feature shape is {}".format(stock_yjbb_em_df_feature.shape))

    stock_lrb_em_df = ak.stock_lrb_em(date="20220331")
    # 净利润, 净利润同比, 营业总收入, 营业总收入同比, 营业总支出-营业支出	, 营业总支出-销售费用,
    # 营业总支出-管理费用, 营业总支出-财务费用, 营业总支出-营业总支出, 营业利润, 利润总额
    print(stock_lrb_em_df[:5])
    stock_lrb_em_df_feature = stock_lrb_em_df[
        [
            "股票代码",
            "营业总支出-营业支出",
            "营业总支出-销售费用",
            "营业总支出-管理费用",
            "营业总支出-财务费用",
            "营业总支出-营业总支出",
            "营业利润",
            "利润总额",
        ]
    ]
    print(stock_lrb_em_df_feature[:5])
    print("stock_lrb_em_df_feature shape is {}".format(stock_lrb_em_df_feature.shape))
    feature_data_merge = pd.merge(
        stock_yjbb_em_df_feature, stock_lrb_em_df_feature, how="left", on="股票代码"
    )

    start_day, end_day = get_start_and_end_date(target_date, 7, 21)

    # 过滤掉新股
    shape_of_all_code = feature_data_merge.shape[0]

    feature_data_merge["symbol"] = feature_data_merge.progress_apply(
        lambda row: local_db_tool.get_symbol_from_code(row["股票代码"]), axis=1
    )

    feature_data_merge = feature_data_merge[feature_data_merge["symbol"] != 0]
    shape_of_remove_new_stock = feature_data_merge.shape[0]

    print(
        "shape_of_all_code {0}, shape_of_remove_new_stock {1}".format(
            shape_of_all_code, shape_of_remove_new_stock
        )
    )

    feature_data_merge["price_list"] = feature_data_merge.progress_apply(
        lambda row: local_db_tool.get_price_list_by_range(
            symbol=row["symbol"], m_type="cn", start=start_day, end=end_day
        ),
        axis=1,
    )
    feature_data_merge = feature_data_merge[feature_data_merge["price_list"] != 0]
    print(
        "before get price shape {}, after get price shape {}".format(
            shape_of_remove_new_stock, feature_data_merge.shape
        )
    )
    print(feature_data_merge[:5])
    feature_data_merge.reset_index(inplace=True)

    # 增加净利润率
    feature_data_merge["PE"] = feature_data_merge.progress_apply(
        lambda row: row["price_list"][0]/row["每股收益"] if row["每股收益"]>0 else -1,
        axis=1,
    )

    feature_data_merge["净利润率"] = feature_data_merge.progress_apply(
        lambda row: (100 * row["净利润-净利润"]) / row["营业收入-营业收入"]
        if row["营业收入-营业收入"] > 0
        else 0.0,
        axis=1,
    )

    feature_data_merge["PEG"] = feature_data_merge.progress_apply(
        lambda row: row["PE"] / (100*row["营业收入-同比增长"]) if row["PE"] > 0 else -1,
        axis=1,
    )

    feature_data_merge["label"] = feature_data_merge.progress_apply(
        lambda row: 1 if row["price_list"][-1] / row["price_list"][0] > 1 else 0, axis=1
    )

    feature_df = feature_data_merge[
        [
            "每股收益",
            "营业收入-营业收入",
            "营业收入-同比增长",
            "净利润-季度环比增长",
            "净利润-净利润",
            "每股净资产",
            "净资产收益率",
            "每股经营现金流量",
            "销售毛利率",
            "营业总支出-营业支出",
            "营业总支出-销售费用",
            "营业总支出-管理费用",
            "营业总支出-财务费用",
            "营业总支出-营业总支出",
            "营业利润",
            "净利润率",
            "PE",
            "PEG",
        ]
    ]

    print(feature_data_merge[:5])

    label_set = feature_data_merge["label"]
    print("label_set size is {}".format(label_set.shape))

    print(feature_df.info())
    feature_df.fillna(value=0, inplace=True)

    X_train, X_test, y_train, y_test = model_selection.train_test_split(
        feature_df, label_set, test_size=0.3, random_state=2022
    )
    print("train data shape is {}, test data shape is {}".format(X_train.shape, X_test.shape))

    clf = DecisionTreeClassifier(max_leaf_nodes=5, random_state=0)
    clf.fit(X_train, y_train)

    y_pred_train = clf.predict(X_train)
    accuracy = accuracy_score(y_train, y_pred_train)
    print("train accuarcy: %.2f%%" % (accuracy * 100.0))

    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print("test accuarcy: %.2f%%" % (accuracy * 100.0))

    tree.plot_tree(clf)
    plt.show()
    pass

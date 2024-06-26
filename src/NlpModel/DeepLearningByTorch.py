# -*- coding:utf-8 -*-
"""
author wangshuai
date 2021/06/16
"""
import argparse

# import sys
from sklearn import model_selection
from ChanBasedCnn import TextCNN, CustomChanDataset, train

# from Utils.utils import set_display
from DataPreProcessing import DataPreProcessing
import pandas as pd

# 显示所有列
pd.set_option("display.max_columns", None)
# 显示所有行
pd.set_option("display.max_rows", None)
pd.set_option("max_colwidth", 500)


# args.lr
# args.epochs
# args.log_interval
# args.dev_interval
# args.save_best
# args.save_dir
# args.save_interval
def gen_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--embed_dim", default=200, help="每个词向量长度", type=int)
    parser.add_argument("-c", "--class_num", default=2, help="类别数", type=int)
    parser.add_argument("-k", "--kernel_num", default=2, help="每种卷积核的数量", type=int)
    parser.add_argument(
        "-s", "--kernel_sizes", default=[3, 4], help="卷积核list，形如[2,3,4]"
    )
    parser.add_argument("-r", "--lr", default=0.001, help="learning rate")
    parser.add_argument("-p", "--epochs", default=500, help="epochs", type=int)
    parser.add_argument(
        "-l", "--log_interval", default=100, help="log_interval", type=int
    )
    parser.add_argument(
        "-a", "--save_interval", default=500, help="save_interval", type=int
    )
    parser.add_argument("--dev_interval", default=500, help="evaluation", type=int)
    parser.add_argument("--save_dir", default="./", help="save_dir", type=str)
    parser.add_argument("--save_best", default=True, help="save_best")
    parser.add_argument("--dropout", default=0.5, help="dropout", type=float)
    parser.add_argument("--early_stop", default=10000, help="early_stop", type=int)
    parser.add_argument("--batch_size", default=64, help="batch_size", type=int)
    parser.add_argument("--cnt_limit_start", default=0, help="cnt_limit_start")
    parser.add_argument("--cnt_limit_end", default=None, help="cnt_limit_end", type=int)
    parser.add_argument(
        "--force_update_feature", default=False, help="force_update_feature"
    )
    parser.add_argument("--start_date", required=True, help="data_start_date", type=str)
    parser.add_argument("--end_date", default=None, help="data_end_date", type=str)
    parser.add_argument(
        "--direct_load_train_file",
        default=False,
        help="irect_load_train_file",
        type=bool,
    )
    _args = parser.parse_args()
    return _args


if __name__ == "__main__":
    args = gen_parser()
    # set_display()

    dpp = DataPreProcessing(feature_size=40)
    symbol_data = dpp.get_symbols("cn")

    data_set, label_sum, _, max_feature_length, ta_feature_length = dpp.get_label(
        symbols=symbol_data,
        # market_type="cn",
        week_data_start_date=args.start_date,
        week_data_end_date=args.end_date,
        cnt_limit_start=args.cnt_limit_start,
        cnt_limit_end=args.cnt_limit_end,
        # feature_type="deep",
        force_update_feature=args.force_update_feature,
        direct_load_file=args.direct_load_train_file,
    )
    data_set["label"] = data_set.apply(
        lambda row: 0 if row["label"] <= 1 else 1, axis=1
    )

    label_set = data_set["label"]
    print("max_feature_length {}".format(max_feature_length))
    X_train, X_test, y_train, y_test = model_selection.train_test_split(
        data_set, label_set, test_size=0.33, random_state=42
    )

    train_data_set = CustomChanDataset(
        X_train, y_train, max_feature_length, int(ta_feature_length)
    )
    test_data_set = CustomChanDataset(
        X_test, y_test, max_feature_length, int(ta_feature_length)
    )

    text_cnn = TextCNN(
        args=args,
        max_feature_length=max_feature_length,
        ta_dim=int(ta_feature_length),
        vocab_industry=dpp.deep_feature_gen.industry_vocab_dim,
        vocab_concept=dpp.deep_feature_gen.concept_vocab_dim,
    )
    train(
        train_data_set,
        test_data_set,
        batch_size=args.batch_size,
        model=text_cnn,
        args=args,
    )
    pass

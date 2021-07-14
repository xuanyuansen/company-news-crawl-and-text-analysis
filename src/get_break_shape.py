# -*- coding:utf-8 -*-
# 获得在日线级别长期扰动，然后突然放量的股票，例如近期物产中大，佳沃股份等，看看他们的特征。
# 有一个很长的中枢，中枢对应的macd的variance很小。物产中大的特征。
# 后续可以有两种方式，一种是直接利用variance，长度，ratio来做排序和筛选，另外一种是做机器学习。
# 机器学习这么处理数据，先用形态学的顶底等等划分出.
# to do利用深度学习，笔，线段，中枢，对应了三种表达，三个通道的输入，然后股票的行业，概念作为embedding的词加进去，维度。
# 先用传统的机器学习模型。后续用深度学习，因为是有序列的关系。
# 传统的机器学习模型。特征两部分，第一部分，笔，段，中枢；第二部分，特征提取器。
# 特征，笔的长度，variance。
# 我的label是什么呢？近一周内的涨幅，五个等级，涨跌幅取LOG看一下分布。每周训练一次模型，预测下周的结果。
from ChanUtils.ChanFeature import BasicFeatureGen, DeepFeatureGen
from MarketPriceSpider.StockInfoSpyder import StockInfoSpyder
import sys
import pandas as pd
from Utils.utils import set_display, today_date
from ChanUtils.BasicUtil import KiLineObject
from ChanUtils.ShapeUtil import ChanSourceDataObject, plot_with_mlf_v2
from Surpriver import feature_generator
import torch
import numpy as np
from NlpModel.ChanBasedCnn import (
    RNN,
    train_rnn,
    random_training_example,
    category_from_output,
)
import time
import math
import random
from NlpModel.DataPreProcessing import DataPreProcessing
import logging


if __name__ == "__main__":
    set_display()
    logging.info(today_date)
    price_spider = StockInfoSpyder()

    _res, stock_data = price_spider.get_daily_price_data_of_specific_stock(
        symbol=sys.argv[1], market_type="cn", start_date=sys.argv[2]
    )
    # print(stock_data[:10])
    stock_data["Date"] = pd.to_datetime(stock_data["date"], format="%Y-%m-%d")
    stock_data.set_index("Date", inplace=True)

    k_line_data = KiLineObject.k_line_merge(sys.argv[1], stock_data, merge_or_not=True)
    chan_data = ChanSourceDataObject("daily", k_line_data)
    chan_data.gen_data_frame()
    _stock_data = chan_data.get_plot_data_frame()

    plot_with_mlf_v2(
        chan_data, "{0},{1},{2}".format(sys.argv[1], sys.argv[1], "daily"), today_date
    )
    # print(_stock_data[:10])
    # fEngine = feature_generator.TAEngine(history_to_use=0)
    # feature_dict = fEngine.get_technical_indicators(_stock_data)
    # _sub_feature_list = fEngine.get_features(feature_dict)
    # print('len of _sub_feature_list {}'.format(len(_sub_feature_list)))

    bfg = BasicFeatureGen(chan_data)
    print(bfg.get_feature())

    dedp_fea_gen = DeepFeatureGen(chan_data)
    res = dedp_fea_gen.get_sequence_feature()
    logging.info("bi feature length {}".format(len(res[0])))
    print(res[0])
    print("xian duan feature length {}".format(len(res[1])))
    print(res[1])
    print("zhong shu feature")
    print(dedp_fea_gen.get_zhong_shu_feature_sequence())

    ##################
    set_display()
    data_prepare = DataPreProcessing(feature_size=38)
    symbol_data = data_prepare.get_symbols("cn")

    data_set, label_sum, _ = data_prepare.get_label(
        symbols=symbol_data,
        market_type="cn",
        start_date="2021-06-01",
        # cnt_limit_start=4100,
        # cnt_limit_end=10,
        feature_type="deep",
    )
    label_set = data_set["label"]

    data_cnt = data_set.shape[0]

    n_hidden = 128
    n_categories = 4
    bi_feature_list = res[0]
    rnn = RNN(len(bi_feature_list[0]), n_hidden, n_categories)

    _tensor = torch.zeros(1, len(bi_feature_list[0]))
    _tensor[0] = torch.from_numpy(np.array(bi_feature_list[0]))
    _input = _tensor
    print(_input)
    hidden = torch.zeros(1, n_hidden)

    output, next_hidden = rnn(_input, hidden)
    print("output", output)
    print("next_hidden", next_hidden)

    n_iters = 100000
    print_every = 100
    plot_every = 2000

    # Keep track of losses for plotting
    current_loss = 0
    all_losses = []
    print(data_set)

    def timeSince(since):
        now = time.time()
        s = now - since
        m = math.floor(s / 60)
        s -= m * 60
        return "%dm %ds" % (m, s)

    _data_index = data_set.index
    _data_index_min = _data_index.min()
    _data_index_max = _data_index.max()
    start = time.time()
    for iter in range(1, n_iters + 1):
        data_idx = random.randint(_data_index_min, _data_index_max)
        try:
            _data = data_set.loc[data_idx, ["features"]].values.tolist()[0]
        except:
            continue
        # print(type(_data), _data)
        _label = data_set.loc[data_idx, ["label"]].values.tolist()[0]

        category, category_tensor, line_tensor = random_training_example(_data, _label)

        # print(line_tensor.size())
        # print("category_tensor size {} ".format(category_tensor.size()))

        output, loss = train_rnn(rnn, category_tensor, line_tensor)
        current_loss += loss

        # Print iter number, loss, name and guess
        if iter % print_every == 0:
            print("output", output)
            print("loss", loss)
            # print("line_tensor", line_tensor)
            print("label", type(_label), _label)
            print("category_tensor", type(category_tensor), category_tensor)
            guess, guess_i = category_from_output(output)
            correct = "✓" if guess == category else "✗ (%s)" % category
            logging.info(
                "%d %d %% (%s) %.4f %s / %s %s"
                % (
                    iter,
                    iter / n_iters * 100,
                    timeSince(start),
                    loss,
                    guess_i,
                    guess,
                    correct,
                )
            )

        # Add current loss avg to list of losses
        if iter % plot_every == 0:
            all_losses.append(current_loss / plot_every)
            current_loss = 0

    print("print done!")
    pass

# -*- coding:utf-8 -*-
# bi xian duan zhong shu 有点像深度学习中不同层次网络的抽象
# 事实上我可以有大量的样本，例如过去三个月的数据，下一周的涨跌幅作为label，或者过去六个月的数据，下一周作为涨跌幅。
# 后续这个三个月，或者六个月也可以作为超参用机器学习来习得。
# 4000多只股票，3000训练，500validate，500测试。
import numpy

from ChanUtils.BasicUtil import ChanLine
from ChanUtils.ShapeUtil import ChanSourceDataObject
import numpy as np
from Utils import config


class BaseFeatureGen(object):
    def __init__(self, chan_data: ChanSourceDataObject = None):
        self.data: ChanSourceDataObject = chan_data
        self.base_length = 500  # 交易日的长度。后续这里要改为自动获取数据的最大长度。
        self.code = None if chan_data is None else chan_data.k_line_list[0].code
        self.concept_file = config.CN_STOCK_CONCEPT_DICT_FILE
        self.industry_file = config.CN_STOCK_INDUSTRY_DICT_FILE
        self.concept_list = self.__load_dict_file(self.concept_file)
        self.industry_list = self.__load_dict_file(self.industry_file)
        self.industry_to_index = {ch: i for i, ch in enumerate(self.industry_list)}
        self.index_to_industry = {i: ch for i, ch in enumerate(self.industry_list)}
        self.concept_to_index = {ch: i for i, ch in enumerate(self.concept_list)}
        self.index_to_concept = {i: ch for i, ch in enumerate(self.concept_list)}
        self.concept_vocab_dim = len(self.concept_list)
        self.industry_vocab_dim = len(self.industry_list)

    def from_industry_to_feature(self, industry: str):
        a = [0 for _ in range(0, self.industry_vocab_dim)]
        if industry is None or "null" == industry:
            return a
        idx = self.industry_to_index[industry]
        a[idx] = 1
        return a

    def from_concept_to_feature(self, concepts: str):
        a = [0 for _ in range(0, self.concept_vocab_dim)]
        if concepts is None or "null" == concepts:
            return a
        try:
            for con in concepts.split(","):
                idx = self.concept_to_index[con]
                a[idx] = 1
        except Exception as e:
            print(concepts)
            return a
        return a

    def set_base_data(self, chan_data: ChanSourceDataObject):
        self.data = chan_data
        self.code = self.data.k_line_list[0].code  # 获得代码用于获得行业和概念的embedding

    @staticmethod
    def __load_dict_file(file_name):
        with open(file_name) as _file:
            return [ele.strip() for ele in list(iter(_file.readlines()))]

    pass


# 生成序列特征
class DeepFeatureGen(BaseFeatureGen):
    def __init__(self, chan_data: ChanSourceDataObject = None):
        super().__init__(chan_data=chan_data)

    # 笔 线段 前三个序列，顶底序列（0，1序列），长度序列，角度序列
    # 后三个序列， volume ， hist， macd
    def __get_feature(self, _data: list[ChanLine]):
        if len(_data) <= 1:
            return list()
        ding_di_sequence = [
            1.0 if "up" == element.direction else 0.0 for element in _data
        ]

        length_sequence = [
            float(element.end_index - element.start_index) for element in _data
        ]
        # length_sequence_sum = sum(length_sequence)
        # 不能这么归一化，要看笔的强度，所以要在整个数据的区间上归一化
        length_sequence = [element / self.base_length for element in length_sequence]

        volume = [element.whole_volume for element in _data]
        volume_sum = sum(volume)
        volume_sequence = [element / volume_sum for element in volume]

        angle_sequence = [
            (
                (1.0 if "up" == element.direction else -1.0)
                * (
                    np.arctan(element.get_max() - element.get_min())
                    / (element.end_index - element.start_index)
                )
                + 1.5
            )
            / 3.0
            for element in _data
        ]

        sub_his = [
            sum(self.data.histogram[element.start_index : element.end_index])
            for element in _data
        ]
        sub_macd = [
            sum(self.data.macd[element.start_index : element.end_index])
            for element in _data
        ]

        max_sub_his = max(sub_his)
        min_sub_his = min(sub_his)

        max_sub_macd = max(sub_macd)
        min_sub_macd = min(sub_macd)

        sub_his_sequence = [
            element / (max_sub_his - min_sub_his)
            - min_sub_his / (max_sub_his - min_sub_his)
            if max_sub_his != min_sub_his
            else 1.0
            for element in sub_his
        ]
        sub_macd_sequence = [
            element / (max_sub_macd - min_sub_macd)
            - min_sub_macd / (max_sub_macd - min_sub_macd)
            if max_sub_macd != min_sub_macd
            else 1.0
            for element in sub_macd
        ]

        # print('sub_his_sequence', sub_his_sequence)
        # print('sub_macd_sequence', sub_macd_sequence)

        feature = list(
            zip(
                ding_di_sequence,
                length_sequence,
                angle_sequence,
                volume_sequence,
                sub_his_sequence,
                sub_macd_sequence,
            )
        )
        return [list(ele) for ele in feature]

    def get_sequence_feature(self):
        return self.__get_feature(self.data.get_bi_list()), self.__get_feature(
            self.data.merged_chan_line_list
        )

    def get_deep_sequence_feature(self, industry, concepts):
        return (
            self.__get_feature(self.data.get_bi_list()),
            self.from_industry_to_feature(industry),
            self.from_concept_to_feature(concepts),
        )

    def get_zhong_shu_feature_sequence(self):
        if len(self.data.zhong_shu_list) < 0:
            return [(0.0, 0.0, 0.0)]
        else:
            # self.max_low_value = max_low_value  # low point
            # self.min_max_value = min_max_value  # high point
            max_min_sequence = [
                (zs.min_max_value - zs.max_low_value) / zs.min_max_value
                for zs in self.data.zhong_shu_list
            ]

            length_sequence = [
                len(zs.list_of_duan) / len(self.data.merged_chan_line_list)
                for zs in self.data.zhong_shu_list
            ]

            zhong_shu_strength_length_sequence = [
                zs.zhong_shu_time_strength_length / self.base_length
                for zs in self.data.zhong_shu_list
            ]

        return list(
            zip(max_min_sequence, length_sequence, zhong_shu_strength_length_sequence)
        )

    pass


# 特征工程，然后用XGBOOST
class BasicFeatureGen(BaseFeatureGen):
    def __init__(self, chan_data: ChanSourceDataObject = None):
        super().__init__(chan_data=chan_data)

    # 10
    @staticmethod
    def __gen_feature(_data: list[ChanLine]):
        # 笔的个数
        # 笔的顶底值 均值 方差 标准差
        # 笔长度的 均值 方差 标准差
        # volume 均值 方差 标准差
        bi_s = _data
        f1 = float(len(bi_s))
        if f1 == 0.0:
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        value_list = [bi_s[0].high, bi_s[0].low]
        length_list = [bi_s[0].end_index - bi_s[0].start_index]
        volume_list = [
            np.log(bi_s[0].whole_volume) if bi_s[0].whole_volume != 0.0 else 0.0
        ]
        for idx in range(1, len(bi_s)):
            if bi_s[idx].high not in value_list[-2:]:
                value_list.append(bi_s[idx].high)
            if bi_s[idx].low not in value_list[-2:]:
                value_list.append(bi_s[idx].low)
            length_list.append(bi_s[idx].end_index - bi_s[idx].start_index)
            volume_list.append(
                np.log(bi_s[idx].whole_volume) if bi_s[idx].whole_volume != 0.0 else 0.0
            )

        _feature = [
            f1,
            np.average(value_list),
            np.var(value_list),
            np.std(value_list),
            np.average(length_list),
            np.var(length_list),
            np.std(length_list),
            float(np.average(volume_list)),
            float(np.var(volume_list)),
            float(np.std(volume_list)),
        ]
        for i, _word in enumerate(_feature):
            if np.isnan(_word):
                _feature[i] = 0.0
        return _feature

    # 10 + 10 + 13 + 5 + 2
    def get_feature(self):
        bi_feature = self.__gen_feature(self.data.get_bi_list())
        if len(self.data.merged_chan_line_list) > 0:
            xian_duan_feature = self.__gen_feature(self.data.merged_chan_line_list)
        else:
            xian_duan_feature = self.__gen_feature(self.data.origin_chan_line_list)

        # 最后一笔和最后一个线段的方向
        def direction_feature(data: list[ChanLine]):
            if len(data) > 0:
                if data[-1].direction == "up":
                    return 1
                else:
                    return -1
            else:
                return 0

        # print('macd feature is {}'.format(self.__get_macd_feature()))

        return (
            bi_feature
            + xian_duan_feature
            + self.__gen_zhong_shu_feature()
            + self.__get_macd_feature()
            + [
                direction_feature(self.data.get_bi_list()),
                direction_feature(self.data.merged_chan_line_list),
            ]
        )

    # 13维
    @staticmethod
    def __gen_average_variance_std(_data: list[float]):
        return [np.average(_data), np.var(_data), np.std(_data)]

    # 13
    # count
    # 中枢的长度 均值 方差 标准差
    # 中枢的max 均值 方差 标准差
    # 中枢的min 均值 方差 标准差
    # 中枢ratio 均值 方差 标准差
    def __gen_zhong_shu_feature(self):
        zhong_shu_list = self.data.zhong_shu_list
        if len(zhong_shu_list) > 0:
            length_list = [zs.zhong_shu_time_strength_length for zs in zhong_shu_list]
            max_list = [zs.max_low_value for zs in zhong_shu_list]
            min_list = [zs.min_max_value for zs in zhong_shu_list]
            ratio_list = [zs.zhong_shu_strength_ratio for zs in zhong_shu_list]

            return (
                [float(len(zhong_shu_list))]
                + self.__gen_average_variance_std(length_list)
                + self.__gen_average_variance_std(max_list)
                + self.__gen_average_variance_std(min_list)
                + self.__gen_average_variance_std(ratio_list)
            )
        else:
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def __get_macd_feature(self):
        zhong_shu_list = self.data.zhong_shu_list
        if len(zhong_shu_list) > 0:
            start_index = zhong_shu_list[0].start_index
            end_index = zhong_shu_list[-1].end_index
        else:
            xian_duan_list = (
                self.data.merged_chan_line_list
                if len(self.data.merged_chan_line_list) > 0
                else self.data.origin_chan_line_list
            )
            if len(xian_duan_list) > 0:
                start_index = xian_duan_list[0].get_start_index()
                end_index = xian_duan_list[-1].get_end_index()
            else:
                start_index = 0
                end_index = 0
        if 0 == start_index and 0 == end_index:
            return [0.0, 0.0, 0.0, 0.0, 0.0]
        else:
            sub_his = self.data.histogram[start_index:end_index]
            sub_macd = self.data.macd[start_index:end_index]
            return [
                float(end_index - start_index),
                sub_his.var(),
                sub_his.std(),
                sub_macd.var(),
                sub_macd.std(),
            ]

    pass

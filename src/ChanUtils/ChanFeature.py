# -*- coding:utf-8 -*-
# bi xian duan zhong shu 有点像深度学习中不同层次网络的抽象
# 事实上我可以有大量的样本，例如过去三个月的数据，下一周的涨跌幅作为label，或者过去六个月的数据，下一周作为涨跌幅。
# 后续这个三个月，或者六个月也可以作为超参用机器学习来习得。
# 4000多只股票，3000训练，500validate，500测试。
import numpy

from ChanUtils.BasicUtil import ChanLine
from ChanUtils.ShapeUtil import ChanSourceDataObject
import numpy as np


# 特征工程，然后用XGBOOST
class BasicFeatureGen(object):
    def __init__(self, chan_data: ChanSourceDataObject):
        self.data: ChanSourceDataObject = chan_data

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
        volume_list = [bi_s[0].whole_volume]
        for idx in range(1, len(bi_s)):
            if bi_s[idx].high not in value_list[-2:]:
                value_list.append(bi_s[idx].high)
            if bi_s[idx].low not in value_list[-2:]:
                value_list.append(bi_s[idx].low)
            length_list.append(bi_s[idx].end_index - bi_s[idx].start_index)
            volume_list.append(np.log(bi_s[idx].whole_volume))

        return [
            f1,
            np.average(value_list),
            np.var(value_list),
            np.std(value_list),
            np.average(length_list),
            np.var(length_list),
            np.std(length_list),
            np.average(volume_list),
            np.var(volume_list),
            np.std(volume_list),
        ]

    # 10 + 10 + 13
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

        return (
            bi_feature
            + xian_duan_feature
            + self.__gen_zhong_shu_feature()
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

    pass

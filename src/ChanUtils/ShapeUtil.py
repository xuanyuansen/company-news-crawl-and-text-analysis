# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
from .BasicUtil import KiLineObject, ChanBi, ChanLine, ZhongShu, is_contain, bi_inner_merge
from .DynamicUtil import inner_get_average_volume, from_xian_duan_to_zhong_shu
import warnings
import numpy as np
import pandas as pd
import ta
import mplfinance as mpf


# 2020.10.26 将原始数据和画图的数据剥离开来
# 进行技术分析的原始数据
# 这里比较复杂如何，把画图的逻辑单独抽象出来，需要好好的思考。
class ChanSourceDataObject(object):
    # level操作的级别
    def __init__(self, level: str, data: list):
        # K线的级别，操作的级别，非常重要
        self.k_line_level = level
        self.k_line_list = data
        # 生成所有的顶或者底，merge。
        ChanSourceDataObject.is_ding_di_shape(self.k_line_list, 3, False)
        # merge后的顶底分型，去除中间的顶底分型list
        self.ding_di_to_bi = []
        # 笔
        self.bi_list = []
        # 线段
        self.origin_chan_line_list = []
        self.merged_chan_line_list = []
        # 中枢
        self.zhong_shu_list = []

        self.data_to_plot_frame = None

        # MACD形态学
        self.histogram = None
        self.histogram_positive = None
        self.histogram_negative = None
        self.macd = None
        self.exp12 = None
        self.exp26 = None
        self.signal = None
        self.boll = None
        self.cross_list = list()

        if len(data) > 0:
            if not isinstance(data[0], KiLineObject):
                raise Exception("data type not right, type is {0}".format(type(data[0])))
            # 取中间的date index
            [element.set_date_2_plot(self.k_line_level) for element in data]
            # 这里是所有的顶底
            self.ding_to_plot = []
            self.di_to_plot = []
            # 只画出有效的顶和底，而非原始的顶底
            self.valid_ding_shape_to_plot = []
            self.valid_di_shape_to_plot = []

            self.shape_2_bi_value_to_plot = []
            self.ding_di_to_bi = []  # 记录所有的笔的开始结束信号,-1 1 0
            self.chan_line_to_plot = []

            self.zhong_shu_upper_line_to_plot = []
            self.zhong_shu_bottom_line_to_plot = []

            # 处理占位符号以及准备数据
            for element in data:
                self.ding_di_to_bi.append(element.ding_di_to_bi)

                # zhong shu line, 2020.10.11
                # 占位，对其数据
                self.chan_line_to_plot.append(np.nan)
                self.zhong_shu_upper_line_to_plot.append(np.nan)
                self.zhong_shu_bottom_line_to_plot.append(np.nan)

                # shape 处理顶或者底分型
                if element.ding_di_shape == 1:
                    self.ding_to_plot.append(element.high + 0.5)
                    self.di_to_plot.append(np.nan)
                elif element.ding_di_shape == -1:
                    self.di_to_plot.append(element.low - 0.5)
                    self.ding_to_plot.append(np.nan)
                else:
                    self.ding_to_plot.append(np.nan)  # 这里添加nan的目的是，对齐主图的k线数量
                    self.di_to_plot.append(np.nan)  # 这里添加nan的目的是，对齐主图的k线数量

                # bi 处理笔
                if element.ding_di_to_bi == 1:
                    self.shape_2_bi_value_to_plot.append(element.high)

                    # valid ding di shape
                    self.valid_ding_shape_to_plot.append(element.high + 0.5)
                    self.valid_di_shape_to_plot.append(np.nan)
                elif -1 == element.ding_di_to_bi:
                    self.shape_2_bi_value_to_plot.append(element.low)

                    # valid ding di shape
                    self.valid_ding_shape_to_plot.append(np.nan)
                    self.valid_di_shape_to_plot.append(element.low - 0.5)
                else:
                    self.shape_2_bi_value_to_plot.append(np.nan)

                    # valid ding di shape
                    self.valid_ding_shape_to_plot.append(np.nan)
                    self.valid_di_shape_to_plot.append(np.nan)
                    pass

            # 这里将笔画出，需要回归出顶和底之间的点。
            # ding_di_to_bi, index
            # shape_2_bi_value_to_plot, value
            bi_res = from_point_to_bi(self.ding_di_to_bi, self.shape_2_bi_value_to_plot)

            # chan_line = []
            if bi_res[0]:
                self.bi_list = bi_res[1]
                self.origin_chan_line_list = from_bi_list_to_line(self.bi_list)
                self.merged_chan_line_list = ChanLine.merge(self.origin_chan_line_list)

                # chan_line_merged, 修正后的线段列表
                self.zhong_shu_list = from_xian_duan_to_zhong_shu(self.merged_chan_line_list)
                # print('zhong shu list')
                for zs_element in self.zhong_shu_list:
                    # print(zs_element)
                    # draw zhong shu
                    # -1 避免连接
                    for idx in range(zs_element.start_index, zs_element.end_index - 1):
                        self.zhong_shu_upper_line_to_plot[idx] = zs_element.min_max_value
                        self.zhong_shu_bottom_line_to_plot[idx] = zs_element.max_low_value

                for line_ele in self.merged_chan_line_list:
                    for value_of_line in line_ele.value_list_with_index:
                        self.chan_line_to_plot[value_of_line[0]] = value_of_line[1]
        else:
            raise Exception('empty data list')
        pass

    def gen_data_frame(self):
        date_middle_convert = dict(
            {
                'Open': [element.open for element in self.k_line_list],
                'Close': [element.close for element in self.k_line_list],
                'High': [element.high for element in self.k_line_list],
                'Low': [element.low for element in self.k_line_list],
                'Volume': [element.volume for element in self.k_line_list],
                'Money': [element.money for element in self.k_line_list],
                'Shape': [element.ding_di_shape for element in self.k_line_list],
                'Ding_to_draw': self.ding_to_plot,
                'Di_to_draw': self.di_to_plot,
                # valid ding di shape
                'Valid_ding_to_draw': self.valid_ding_shape_to_plot,
                'Valid_di_to_draw': self.valid_di_shape_to_plot,
                'Bi': [element.ding_di_to_bi for element in self.k_line_list],
                'Bi_to_draw': self.shape_2_bi_value_to_plot,
                'Line_to_draw': self.chan_line_to_plot,
                'Zhong_shu_up_to_draw': self.zhong_shu_upper_line_to_plot,
                'Zhong_shu_down_to_draw': self.zhong_shu_bottom_line_to_plot,

            }
        )
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.html
        # https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Index.html
        date_middle_convert_index = pd.DatetimeIndex([element.date[0] for element in self.k_line_list], name='Date')

        self.data_to_plot_frame = pd.DataFrame(data=date_middle_convert, index=date_middle_convert_index)
        # get_volume_break_point
        # 这里新加了几个维度的数据，'average_volume'，'idx'，'break_point_of_buy'，'break_point_of_sell'
        # 这里的 'idx' 可以和中枢类里面的index对应
        get_res_success = inner_get_average_volume(self.data_to_plot_frame, level=self.k_line_level)
        if not get_res_success:
            warnings.warn("get break point of volume failed!")

        # 背离（背驰），意味着趋势的反转，反转时DIF与DEA之间的距离会越来越小，
        # 对应的股价可体现为第二轮上涨或者下跌虽然超过了第一轮股价的高点或者低点，
        # 但是第二轮运动（趋势）的动能比第一轮降低了，预示着趋势已经是强弩之末了。
        # 这里就是缠论说的趋势的背驰，用于辅助判断第一类买点（一般伴随着成交量放大）。
        # 计算macd的数据。Moving Average Convergence and Divergence，12，26，9。
        # 计算macd数据可以使用第三方模块talib（常用的金融指标kdj、macd、boll等等都有，这里不展开了），
        # 如果在金融数据分析和量化交易上深耕的朋友相信对这些指标的计算原理已经了如指掌，
        # 直接通过原始数据计算即可，以macd的计算为例如下：
        # 通过快速线与慢速线来挖掘买卖点
        # dif, dea, hist
        self.exp12 = self.data_to_plot_frame['Close'].ewm(span=12, adjust=False).mean()
        self.exp26 = self.data_to_plot_frame['Close'].ewm(span=26, adjust=False).mean()
        self.macd = self.exp12 - self.exp26
        # 这里计算的hist就是dif-dea,而很多证券商计算的MACD=hist*2=(dif-dea)*2
        self.signal = self.macd.ewm(span=9, adjust=False).mean()

        # 添加MACD子图，拆分成红绿柱子
        self.histogram = self.macd - self.signal
        temp_hist_p = self.macd - self.signal
        temp_hist_p[temp_hist_p < 0] = None
        self.histogram_positive = temp_hist_p
        temp_hist_n = self.macd - self.signal
        temp_hist_n[temp_hist_n >= 0] = None
        self.histogram_negative = temp_hist_n

        # 寻找MACD金叉和死叉

        for i in range(self.exp12.shape[0] - 1):
            if (self.exp12.iloc[i] <= self.exp26[i]) & (self.exp12[i + 1] >= self.exp26[i + 1]):
                self.cross_list.append((self.exp12.index[i + 1], 1))
                # print("MACD金叉的日期：{}".format(self.exp12.index[i + 1]))
            if (self.exp12.iloc[i] >= self.exp26[i]) & (self.exp12[i + 1] <= self.exp26[i + 1]):
                self.cross_list.append((self.exp12.index[i + 1], -1))
                # print("MACD死叉的日期：{}".format(self.exp12.index[i + 1]))

        # BOLL线
        # 一般在软件上都用BOLL表示。该指标一般都三条线，上、中、下三个轨道。
        # 一般性地，在上轨以上和下轨以下运行是超强状态，一般中枢移动时肯定会出现，唯一区别是前者是上涨超强，后者是下跌超强。
        #
        # 注意，用这个指标有一个很好的辅助判断第二类买卖点，有时候也可以用来判断第一类买卖点。
        # 一般来说，从上轨上跌回其下或从下轨下涨回其上，都是从超强区域转向一般性区域，
        # 这时候，如果再次的上涨或回跌创出新高或新低但不能重新有效回到超强区域，那么就意味着进入中阴状态了，也就是第一类买卖点出现了。
        #
        # 但更有效的是对第二买卖点的辅助判断，
        # 一般来说，在进入中阴状态，上轨和下轨都会滞后反应，也就是等第一次回跌或回升后再次向上或下跌时，上轨和下轨才会转向，
        # 而这时候转向的上轨和下轨，往往成为最大的阻力和支持，使得第二类买卖点在其下或其上被构造出来。
        # self.data_to_plot_frame['upper'], \
        #     self.data_to_plot_frame['middle'], self.data_to_plot_frame['lower'] = ta.BBANDS(
        #     self.data_to_plot_frame.Close.values,
        #     timeperiod=20,
        #     # number of non-biased standard deviations from the mean
        #     nbdevup=2,
        #     nbdevdn=2,
        #     # Moving average type: simple moving average here
        #     matype=0)
        self.boll = ta.volatility.BollingerBands(
            self.data_to_plot_frame['Close'],
            window=20,
            # number of non-biased standard deviations from the mean
            window_dev=2,
            # Moving average type: simple moving average here
            fillna=False)
        # print(self.boll)
        self.data_to_plot_frame['upper'] = self.boll.bollinger_hband()
        self.data_to_plot_frame['lower'] = self.boll.bollinger_lband()
        self.data_to_plot_frame['middle'] = self.boll.bollinger_mavg()
        pass

    def get_ding_di(self):
        return self.data_to_plot_frame[['Ding_to_draw', 'Di_to_draw']]

    def get_cross_list(self):
        return self.cross_list

    def get_macd_bar(self):
        return self.histogram

    def get_plot_data_frame(self):
        return self.data_to_plot_frame

    def get_zhong_shu_list(self):
        return self.zhong_shu_list

    # 周线级别上最近有金叉，而且最近一个顶底分型是底分型
    def is_valid_buy_sell_point_on_week_line(self):
        last_cross = self.cross_list[-1]
        valid_ding = self.data_to_plot_frame.loc[self.data_to_plot_frame.Ding_to_draw.notnull(), :]
        valid_di = self.data_to_plot_frame.loc[self.data_to_plot_frame.Di_to_draw.notnull(), :]
        valid_ding_date = valid_ding.iloc[-1].name
        valid_di_date = valid_di.iloc[-1].name
        # print('valid_ding_date {}'.format(valid_ding_date))
        # print('valid_di_date {}'.format(valid_di_date))
        return last_cross[1] == 1 and valid_di_date > valid_ding_date, last_cross, valid_ding_date, valid_di_date

    # 像图1这种，第二K线高点是相邻三K线高点中最高的，而低点也是相邻三K线低点中最高的，本ID给一个定义叫顶分型；
    # 图2这种叫底分型，第二K线低点是相邻三K线低点中最低的，而高点也是相邻三K线高点中最低的。
    # 输入merge完的K list(包含顶底分型)，返回顶底，这里的超参数是顶底分型之间是否需要至少一根K线，可以带来不同结果
    # 核心函数！！！！
    # 这里将所有的顶和底生成好。
    # 默认取k_param=3，实际是采用了新笔的定义，即两个分型之间可以没有独立的K线，自己的理解是如果经过包含处理的标准k线序列这么做没问题。
    # 忽闻台风可休市里面提到了新笔的定义。
    @staticmethod
    def is_ding_di_shape(k_line_merged: list, k_param: int = 3, debug_flag: bool = False):
        # 第一遍初始标记
        idx = 1
        while idx < (len(k_line_merged) - 1):
            # print("idx is {0}".format(idx))
            if max(k_line_merged[idx - 1].high, k_line_merged[idx].high,
                   k_line_merged[idx + 1].high) == k_line_merged[idx].high \
                    and max(k_line_merged[idx - 1].low, k_line_merged[idx].low,
                            k_line_merged[idx + 1].low) == k_line_merged[idx].low:
                k_line_merged[idx].ding_di_shape = 1
                k_line_merged[idx].ding_di_to_bi = 1
                # 分型的K线只能属于一个分型，且顶底分型之间可以不包含一个K线
                idx = idx + k_param
            elif min(k_line_merged[idx - 1].high, k_line_merged[idx].high,
                     k_line_merged[idx + 1].high) == k_line_merged[idx].high \
                    and min(k_line_merged[idx - 1].low, k_line_merged[idx].low,
                            k_line_merged[idx + 1].low) == k_line_merged[idx].low:
                k_line_merged[idx].ding_di_shape = -1
                k_line_merged[idx].ding_di_to_bi = -1
                # 分型的K线只能属于一个分型，且顶底分型之间可以不包含一个K线
                idx = idx + k_param
            else:
                idx += 1
        if debug_flag:
            print([ele.ding_di_shape for ele in k_line_merged])

        # 第二遍合并有问题，要看后面的走势再回溯的。
        # 出现不一致的情况，把前面的顶或者底改掉。
        current_ding_di = 0
        # 相邻顶或者底的index
        idx_revisit = 0

        # print("{0} {1}".format(idx_revisit, current_ding_di))
        for idx in range(idx_revisit + 1, len(k_line_merged) - 1):
            if k_line_merged[idx].ding_di_to_bi == 1 or k_line_merged[idx].ding_di_to_bi == -1:
                if k_line_merged[idx].ding_di_to_bi == current_ding_di:
                    # 这里需要增加一个条件限制，即相邻两个顶或者底取二者最高或者最低的，2020.9.28
                    if (k_line_merged[idx].ding_di_to_bi == 1 and
                        k_line_merged[idx].high >= k_line_merged[idx_revisit].high) or \
                            (k_line_merged[idx].ding_di_to_bi == -1 and
                             k_line_merged[idx].low <= k_line_merged[idx_revisit].low):
                        k_line_merged[idx_revisit].ding_di_to_bi = 0
                        current_ding_di = k_line_merged[idx].ding_di_to_bi
                        idx_revisit = idx
                    else:
                        k_line_merged[idx].ding_di_to_bi = 0
                        current_ding_di = k_line_merged[idx_revisit].ding_di_to_bi
                        # 不变
                        idx_revisit = idx_revisit
                else:
                    current_ding_di = k_line_merged[idx].ding_di_to_bi
                    idx_revisit = idx

        # 第三遍处理，如果向上笔开始，后面底高于前面顶，那么这个底和顶去掉，反之亦然
        # 如此处理的原因是，禅师笔的构成需要有条件三，即在同一笔中，
        # 顶分型中最高那根k线的区间至少要有一部分高于底分型中最低那根k线的区间。
        start_idx = 0
        up_or_down = 0
        while start_idx < len(k_line_merged) - 1:
            if k_line_merged[start_idx].ding_di_to_bi == 1 or k_line_merged[start_idx].ding_di_to_bi == -1:
                up_or_down = k_line_merged[start_idx].ding_di_to_bi
                break
            start_idx += 1

        idx_revisit = start_idx
        idx = start_idx + 1
        if up_or_down == -1:
            while idx < len(k_line_merged) - 1:
                if k_line_merged[idx].ding_di_to_bi == 1:
                    idx_revisit = idx
                if k_line_merged[idx].ding_di_to_bi == -1:
                    if k_line_merged[idx].low >= k_line_merged[idx_revisit].high:
                        k_line_merged[idx].ding_di_to_bi = 0
                        k_line_merged[idx_revisit].ding_di_to_bi = 0
                idx += 1

            idx = start_idx + 1
            idx_revisit = start_idx
            while idx < len(k_line_merged) - 1:
                if k_line_merged[idx].ding_di_to_bi == 1:
                    if k_line_merged[idx].high <= k_line_merged[idx_revisit].low:
                        k_line_merged[idx].ding_di_to_bi = 0
                        k_line_merged[idx_revisit].ding_di_to_bi = 0

                if k_line_merged[idx].ding_di_to_bi == -1:
                    idx_revisit = idx
                idx += 1

        if up_or_down == 1:
            while idx < len(k_line_merged) - 1:
                if k_line_merged[idx].ding_di_to_bi == -1:
                    idx_revisit = idx
                if k_line_merged[idx].ding_di_to_bi == 1:
                    if k_line_merged[idx].high <= k_line_merged[idx_revisit].low:
                        k_line_merged[idx].ding_di_to_bi = 0
                        k_line_merged[idx_revisit].ding_di_to_bi = 0
                idx += 1

            # 再排除另外一种情况下的顶底不符合情况
            idx = start_idx + 1
            idx_revisit = start_idx
            while idx < len(k_line_merged) - 1:
                if k_line_merged[idx].ding_di_to_bi == -1:
                    if k_line_merged[idx].low >= k_line_merged[idx_revisit].high:
                        k_line_merged[idx].ding_di_to_bi = 0
                        k_line_merged[idx_revisit].ding_di_to_bi = 0
                if k_line_merged[idx].ding_di_to_bi == 1:
                    idx_revisit = idx

                idx += 1

        if debug_flag:
            print([ele.ding_di_to_bi for ele in k_line_merged])
        return None
    pass
# 类定义结束


# 处理特征序列的包含关系
def feature_bao_han(k_line_list: list, direction: str):
    # print("len of k_line_list {0}".format(len(k_line_list)))
    k_line_list_out = []
    for idx in range(0, len(k_line_list) - 1):
        m_res = is_contain(k_line_list[idx], k_line_list[idx + 1], direction)
        if m_res[0]:
            new_line = m_res[1]
            # 如果是包含， 将该K线填回去到原K线的下一个继续比较
            k_line_list[idx + 1] = new_line
            if idx + 1 == len(k_line_list) - 1:
                k_line_list_out.append(new_line)
        else:
            k_line_list_out.append(k_line_list[idx])

    # print("len of k_line_list_out {0}".format(len(k_line_list_out)))
    return k_line_list_out


# 准备画线段的数据， data 标识，value_data，值
# 核心函数
# 需要笔的两个端点之间的点回归出来，同时返回所有笔的list，用于生成线段
def from_point_to_bi(data: list, value_data: list):
    # new_line = []
    # sub_data = [element for element in data if element != 0]

    idx_start = 0
    bi_list = []
    while idx_start < len(data) - 1:
        # up bi
        if data[idx_start] == -1:
            idx_end_j = idx_start+1
            while idx_end_j < len(data) - 1:
                if 1 == data[idx_end_j]:
                    break
                idx_end_j += 1
            if idx_end_j < len(data) - 1:
                # up bi done
                bi_list.append(ChanBi('up', idx_start, idx_end_j, value_data[idx_start], value_data[idx_end_j]))
                idx_start = idx_end_j
            else:
                idx_start += 1
        elif data[idx_start] == 1:
            idx_end_j = idx_start + 1
            while idx_end_j < len(data) - 1:
                if -1 == data[idx_end_j]:
                    break
                idx_end_j += 1
            if idx_end_j < len(data) - 1:
                # down bi done
                try:
                    bi_list.append(ChanBi('down', idx_start, idx_end_j, value_data[idx_start], value_data[idx_end_j]))
                except Exception as e:
                    print('data, idx_start', idx_start, data[idx_start])
                    print('value_data, idx_start', idx_start, value_data[idx_start])
                    print('data, idx_end_j', idx_end_j, data[idx_end_j])
                    print('value_data, idx_end_j', idx_end_j, value_data[idx_end_j])
                    raise Exception(e)

                idx_start = idx_end_j
            else:
                idx_start += 1
        else:
            idx_start += 1
            pass

    print('all has {0}  bi '.format(len(bi_list)))
    for bi_element in bi_list:
        for bi_padding in bi_element.value_list_with_index:
            value_data[bi_padding[0]] = bi_padding[1]
    # 这里的笔是一笔接着一笔的
    return True, bi_list


def debug(sub_origin_down_bi_list, standard_feature_line):
    print('==================================================================================')
    print('origin down bi list is :\n{0}'.format(
        (',  \n'.join(['index is: {0}, value is:{1}'.format(ele[1], ele[0]) for ele in sub_origin_down_bi_list]))))
    print('--------------------------------------------')
    print('standard_feature_line list is:\n {0}'
          .format((',  \n'.join(['index is: {0}, value is:{1}'
                                .format(ele[1], ele[0]) for ele in zip(standard_feature_line,
                                                                       range(0, len(standard_feature_line)))]))))
    print('==============================================================================')


# 判断特征序列出现分型，分型第一和第二元素直接存在缺口的情况下，后续新方向的原始特征序列是否出现顶或者底的分型
# 笔构成分型的判断标准要松一些，这里特别注意只判断high或者low即可。
def gap_between_first_second_element_then_shape_or_not(standard_feature_line: list, direction: str):
    print("======gap found, check!======")

    has_shape = False
    idx_feature_line = 1
    while idx_feature_line < len(standard_feature_line) - 1:
        # 向上时候看后续是否有底分型
        # 这个时候新序列的方向变了
        if 'up' == direction:
            if standard_feature_line[idx_feature_line].low == min(
                                                                standard_feature_line[idx_feature_line - 1].low,
                                                                standard_feature_line[idx_feature_line].low,
                                                                standard_feature_line[idx_feature_line + 1].low):
                has_shape = True
                break
        # 向xia时候看后续是否有ding分型
        # 这个时候序列的方向变了
        elif 'down' == direction:
            if standard_feature_line[idx_feature_line].high == max(standard_feature_line[idx_feature_line - 1].high,
                                                                   standard_feature_line[idx_feature_line].high,
                                                                   standard_feature_line[idx_feature_line + 1].high):
                has_shape = True
                break
        idx_feature_line += 1
        print("gap found, check! {0}".format(idx_feature_line))
    print("======gap  check done!======")
    return has_shape


# 获取新方向上面的原始特征序列，因为只是判断，所以不做特征序列的包含处理来获得标准特征序列
# 特征序列的意义在于判断在一个方向上面的力量处于主导时，反转的力量强与弱，以及是否能够成功。
def get_new_feature_line(sub_origin_down_bi_list, bi_list, new_start_idx):
    new_other_direction_feature_line = []

    tt_idx = 0
    while tt_idx < len(sub_origin_down_bi_list):
        if sub_origin_down_bi_list[tt_idx][0].start_index == new_start_idx:
            new_start_idx = sub_origin_down_bi_list[tt_idx][1]
            break
        tt_idx += 1

    new_start_idx += 1
    while new_start_idx < len(bi_list):
        new_other_direction_feature_line.append(bi_list[new_start_idx])
        new_start_idx += 2
    return new_other_direction_feature_line


# 输入的是从idx开始的部分笔的序列
# 核心函数
def check_current_direction_line_with_other_direction_bi(sub_start_idx, bi_list, stop_idx,
                                                         feature_line_direction: str,
                                                         check_ding_di_shape_gap: bool = True,
                                                         debug_f: bool = False):
    if debug_f:
        print('===============start check_current_direction_line_with_other_direction_bi=======================')
        print('start')
    # 第一个向下笔, 这里多加了1。
    start_idx = 1
    sub_origin_down_bi_list = []
    while start_idx < len(bi_list):
        sub_origin_down_bi_list.append((bi_list[start_idx], start_idx))
        start_idx += 2

    # for element in sub_origin_down_bi_list:
        # print(element[0])

    # 向下特征序列起始方向是向上的，处理成标准特征序列
    # 向下线段的特征序列由向上笔构成，这些笔的方向连起来看是向下的
    if len(sub_origin_down_bi_list) <= 1:
        return 0
    if debug_f:
        print('origin length of feature line is {0}'.format(len(sub_origin_down_bi_list)))

    if 'up' == feature_line_direction:
        standard_feature_line = bi_inner_merge([ele[0] for ele in sub_origin_down_bi_list], feature_line_direction)
    elif 'down' == feature_line_direction:
        standard_feature_line = bi_inner_merge([ele[0] for ele in sub_origin_down_bi_list], feature_line_direction)
    else:
        raise Exception('wrong direction {0}'.format(feature_line_direction))

    if debug_f:
        print('standard length of feature line is {0}'.format(len(standard_feature_line)))

    if debug_f:
        debug(sub_origin_down_bi_list, standard_feature_line)
    # 检查是否出现顶分型
    idx_feature_line = 1
    # 这里是在特征序列中的index，实际上的其实index要+idx
    new_stop_idx = 0
    while idx_feature_line < len(standard_feature_line)-1:
        # 向上的情况看顶分型
        if 'up' == feature_line_direction:
            if standard_feature_line[idx_feature_line].high == max(standard_feature_line[idx_feature_line-1].high,
                                                                   standard_feature_line[idx_feature_line].high,
                                                                   standard_feature_line[idx_feature_line+1].high
                                                                   ):
                # 顶或者底分型前两个元素出现缺口时划分
                if check_ding_di_shape_gap:
                    if standard_feature_line[idx_feature_line-1].high < standard_feature_line[idx_feature_line].low:
                        new_start_idx = standard_feature_line[idx_feature_line].start_index

                        new_other_direction_feature_line = \
                            get_new_feature_line(sub_origin_down_bi_list, bi_list, new_start_idx)

                        has_other_shape = gap_between_first_second_element_then_shape_or_not(
                            new_other_direction_feature_line,
                            feature_line_direction)
                        if has_other_shape:
                            new_stop_idx = idx_feature_line
                            break
                        else:
                            idx_feature_line += 1
                            continue

                new_stop_idx = idx_feature_line
                break
        elif 'down' == feature_line_direction:
            # 向下方向的情况看底分型
            if standard_feature_line[idx_feature_line].low == min(
                                                    standard_feature_line[idx_feature_line - 1].low,
                                                    standard_feature_line[idx_feature_line].low,
                                                    standard_feature_line[idx_feature_line + 1].low):
                # 顶或者底分型前两个元素出现缺口时划分
                if check_ding_di_shape_gap:
                    if standard_feature_line[idx_feature_line - 1].low > standard_feature_line[idx_feature_line].high:
                        new_start_idx = standard_feature_line[idx_feature_line].start_index

                        new_other_direction_feature_line = \
                            get_new_feature_line(sub_origin_down_bi_list, bi_list, new_start_idx)

                        has_other_shape = gap_between_first_second_element_then_shape_or_not(
                            new_other_direction_feature_line,
                            feature_line_direction)
                        if has_other_shape:
                            new_stop_idx = idx_feature_line
                            break
                        else:
                            idx_feature_line += 1
                            continue

                new_stop_idx = idx_feature_line
                break
        else:
            raise Exception('wrong direction {0}'.format(feature_line_direction))
        idx_feature_line += 1

    if 0 == new_stop_idx:
        if debug_f:
            debug(sub_origin_down_bi_list, standard_feature_line)
            print("do not have ding shape in standard feature bi list")
        return 0

    # start_idx = idx + 1，这里要加回来才是最开始序列的位置，这里是合并后的所以不准确，从特征序列找, sub_origin_down_bi_list
    new_stop_idx_in_origin_list = 0
    while new_stop_idx_in_origin_list < len(sub_origin_down_bi_list)-1:
        if sub_origin_down_bi_list[new_stop_idx_in_origin_list][0].start_index \
                == standard_feature_line[new_stop_idx].start_index:
            new_stop_idx_in_origin_list = sub_origin_down_bi_list[new_stop_idx_in_origin_list][1]
            break
        new_stop_idx_in_origin_list += 1

    # 缺的加回来
    new_stop_idx_in_origin_list += sub_start_idx

    if debug_f:
        print("direct check new stop point is {0}".format(new_stop_idx_in_origin_list))
        print('VIP target bi is {0}'.format(standard_feature_line[new_stop_idx]))
    # 通过start index去校验原始位置
    idx_double_check = 0

    # 从原始序列找。
    new_stop_idx_in_origin_list_double_check = 0
    while idx_double_check < len(bi_list)-1:
        if bi_list[idx_double_check].start_index == standard_feature_line[new_stop_idx].start_index:
            new_stop_idx_in_origin_list_double_check = idx_double_check + sub_start_idx
            break
        idx_double_check += 1

    if debug_f:
        print("double check new stop point is {0}".format(new_stop_idx_in_origin_list_double_check))
    if new_stop_idx_in_origin_list != new_stop_idx_in_origin_list_double_check:
        print('==============debug start===================')
        debug(sub_origin_down_bi_list, standard_feature_line)
        print('feature line ding shape index is {0}'.format(new_stop_idx))
        print('--------------------------------------------')
        print('feature line ding shape index is {0} in origin bi list'.format(new_stop_idx_in_origin_list))
        print('--------------------------------------------')
        print('new_stop_idx_in_origin_list_double_check index is {0} in origin bi list'
              .format(new_stop_idx_in_origin_list_double_check))

        print('==============debug done===================')
        raise Exception("not equal")
    if debug_f:
        print('origin stop idx is {0}, new stop idx is {1}'.format(stop_idx, new_stop_idx_in_origin_list))
        print('find done!-------------------------------------------------------------------------------\n\n\n')
    return new_stop_idx_in_origin_list


# start idx, list of bi
# list of xian duan, store result
# core function
def bi_to_line_inner_check(start_idx: int,
                           bi_list: list,
                           chan_line_list: list,
                           direction: str, is_debug: bool = False):
    if 'up' == bi_list[start_idx].direction:
        # 如果第二个向上笔出问题，那么换方向
        if bi_list[start_idx].low >= bi_list[start_idx + 1].low:
            return start_idx + 1
    elif 'down' == bi_list[start_idx].direction:
        # 如果第二个向xia笔出问题，那么换方向
        if bi_list[start_idx].high <= bi_list[start_idx + 1].high:
            return start_idx + 1
    else:
        raise Exception('no direction')

    # 记录开始计算的start idx
    idx = start_idx

    stop_idx = 0
    low_idx_j = idx + 4
    if is_debug:
        print("direction {0} start, idx {0}".format(direction, idx))

    actual_stop_index = 0

    while low_idx_j < len(bi_list) - 1:
        high_idx_i = idx
        while high_idx_i <= low_idx_j - 4:  # 同方向上至少3笔才形成线段。
            if 'up' == direction:
                if bi_list[low_idx_j].low <= bi_list[high_idx_i].high:
                    stop_idx = low_idx_j - 2
                    # 这里出现了笔破坏，然后基于特征序列进行判断
                    break
            else:
                # bi_list[high_idx_j].high >= bi_list[low_idx_i].low:
                if bi_list[low_idx_j].high >= bi_list[high_idx_i].low:
                    stop_idx = low_idx_j - 2
                    # 这里出现了笔破坏，然后基于特征序列进行判断
                    break
            high_idx_i += 2

        if stop_idx != 0:
            if is_debug:
                print("direction {0} stop, idx {0}, stop idx is {1}".format(direction, idx, stop_idx))
            # 转换成原始坐标，意味着出现了向下的笔破坏，这个时候考察特征序列
            actual_stop_index = check_current_direction_line_with_other_direction_bi(idx,
                                                                                     bi_list[idx:],
                                                                                     stop_idx,
                                                                                     direction)
            if actual_stop_index != 0:
                stop_idx = actual_stop_index
                if 'up' == direction and bi_list[idx].low <= bi_list[stop_idx].high:
                    chan_line_list.append(ChanLine(direction,
                                                   bi_list[idx].start_index,
                                                   bi_list[stop_idx].start_index,
                                                   bi_list[idx].low, bi_list[stop_idx].high,
                                                   bi_list[idx: stop_idx]))
                elif 'down' == direction and bi_list[idx].high > bi_list[stop_idx].low:
                    chan_line_list.append(ChanLine(direction, bi_list[idx].start_index,
                                                   bi_list[stop_idx].start_index,
                                                   bi_list[idx].high, bi_list[stop_idx].low,
                                                   bi_list[idx: stop_idx]))
                else:
                    if is_debug:
                        print('direction {0} line not right'.format(direction))
            # 还是按照笔破坏处理
            else:
                o_message = 'direction {0}!!!笔破坏, start idx {0}, bi stop index{1}'.format(
                    direction, start_idx, stop_idx)
                warnings.warn(o_message)
                # print(o_message)

                if 'up' == direction and bi_list[idx].low <= bi_list[stop_idx].high:
                    chan_line_list.append(
                        ChanLine(direction, bi_list[idx].start_index,
                                 bi_list[stop_idx].end_index,
                                 bi_list[idx].low, bi_list[stop_idx].high,
                                 bi_list[idx: stop_idx + 1]))
                elif 'down' == direction and bi_list[idx].high > bi_list[stop_idx].low:
                    chan_line_list.append(ChanLine(direction, bi_list[idx].start_index,
                                                   bi_list[stop_idx].end_index,
                                                   bi_list[idx].high, bi_list[stop_idx].low,
                                                   bi_list[idx: stop_idx + 1]))
                else:
                    o_message = 'current line not right, direction is {0}, idx is {1}'\
                        .format(direction, start_idx)
                    warnings.warn(o_message)
                    # print(o_message)

            idx = stop_idx
            break
        low_idx_j += 2

    if 0 == actual_stop_index:
        # 这里说明出现了笔破坏，但是没有出现线段破坏，所以这个时候该线段延续，并不转换方向
        # 禅的理论
        # 继续向上的线段直到出现线段被线段破坏
        if stop_idx != 0:
            idx = stop_idx+2
        else:
            idx += 2

    return idx


# with data struct
# 核心函数！！！！！！！
# 用笔来形成线段！！！！
# 输入包含所有笔的序列
def from_bi_list_to_line(bi_list: list, is_debug: bool = False):
    bi_idx = 0
    while bi_idx < len(bi_list)-1:
        if is_debug:
            print('index is {0}, bi element is {1}'.format(bi_idx, bi_list[bi_idx]))
        bi_idx += 1

    chan_line_list = []
    idx = 0
    while idx < len(bi_list) - 1:
        if is_debug:
            print('===============outer start check, index is {0}, bi is {1}.==================='.format(idx, bi_list[idx]))
            print('===============outer check end.========================================\n\n\n')
        out_idx = bi_to_line_inner_check(idx, bi_list, chan_line_list, direction=bi_list[idx].direction)
        idx = out_idx

        # if 'up' == bi_list[idx].direction:
        #     # 如果第二个向上笔出问题，那么换方向
        #     if bi_list[idx].low >= bi_list[idx+1].low:
        #         idx += 1
        #         continue
        #     out_idx = bi_to_line_inner_check(idx, bi_list, chan_line_list, direction='up')
        #     idx = out_idx
        # elif 'down' == bi_list[idx].direction:
        #     # 如果第二个向xia笔出问题，那么换方向
        #     if bi_list[idx].high <= bi_list[idx + 1].high:
        #         idx += 1
        #         continue
        #     out_idx = bi_to_line_inner_check(idx, bi_list, chan_line_list, direction='down')
        #     idx = out_idx
        # else:
        #     raise Exception('no direction')

    print('len of chan line {0}'.format(len(chan_line_list)))
    if is_debug:
        for element in chan_line_list:
            print(element)
    return chan_line_list


# 计算MACD序列的面积变化，挖掘第一第二类买点
# 激动人心的part来了！！！
# 2020.10.27
# 利用中枢震荡可以做差价，绝对做差价的关键就在于识别中枢，目前程序以及可做到
# 缠中说禅中枢形成走势，走势的转折形成买点和卖点
# macd绿柱子面积变小，一般在一个中枢内，形成背驰，然后快速线和慢速线形成金叉，可以作为第一类买点，意味着转折明朗！
# macd在0轴上下，多头，空头主导的分界！
# 然而在0轴上，趋势转弱即空头在扭转，在0轴下，向上即为多头在抗争，也是缠！！！
# 买点、卖点、背驰与否，一个中枢之中盘整背驰，可能意味着反转，中枢震荡之中做差价。
# 首先根据macd在0轴上下做区分，在0轴下，空军主导，找背驰确认买点；
# 在0轴上，多军主导，找背驰确认卖点。如果新的红柱子面积越来越大则没有卖点，红柱子面积缩小，找死叉，macd交叉的地方，卖。
# 在0轴下，空军主导，找背驰，直到回到0轴上方再买入，保证安全。
# 缠技术，50课，先根据中枢与走势类型进行分析，然后选出需要比较力度的走势段，最后才用MACD辅助判断的顺序。
# 49课，利润最大的操作模式
# 分为两种情况处理，只是别出一个中枢，在中枢价格内那么选择震荡差价模式。在中枢外，那么考虑上还是下，也就是三类买卖点的问题。
# 如果至少两个中枢，那么根据中枢的趋势再来判断。找买点还是卖点。如果最近是卖点那么等买点。如果最近是买点，那么找卖点。
# 推荐采用30m级别线分析，因为是日级别操作者。
# 利润最大的操作模式，缠中说禅操作模式利润最大，首先确定操作级别，日级别，所以在60m或者30m级别的K线开始识别中枢。
# 中枢震荡的操作，一定是向上力度盘整背驰时抛出，向下力度盘整背驰时补回，而不是追涨杀跌。懂了中枢才懂操作。
# 事后技术分析，决定当下的操作方法和模式。
def from_macd_seq_with_zhong_shu_2_buy_sell_point_list_afterwords(chan_data: ChanSourceDataObject):
    zhong_shu_list = chan_data.get_zhong_shu_list()
    bi_all = chan_data.bi_list
    plot_data = chan_data.get_plot_data_frame()
    plot_data_shape = plot_data.shape
    print('data shape is {0}'.format(plot_data_shape))
    last_data = plot_data.iloc[plot_data_shape[0] - 1, :]
    last_close_price = last_data['Close']
    print(last_data)
    print('last close price is {0}'.format(last_close_price))

    if len(zhong_shu_list) == 0:
        print('没有中枢，一般不太会出现这种情况，只能说明选择的区间太短')
        ret_current_type = '走势不清楚'
        current_action = '持币观望'
        sub_action = ''
        vol_b = 0
    elif 1 == len(zhong_shu_list):
        print('中枢有 {0} 个'.format(len(zhong_shu_list)))
        # ret_current_type = None

        # 看中枢后的成交量情况
        volume_break = plot_data[plot_data['idx'] > zhong_shu_list[-1].end_index]
        # volume_up = volume_break['break_point_of_buy']
        volume_up = volume_break[1.0 == volume_break['break_point_of_buy']]
        # volume_down = volume_break['break_point_of_sell']
        volume_down = volume_break[1.0 == volume_break['break_point_of_sell']]

        vol_b = {'up_cnt': volume_up.shape[0],
                 'up_detail': volume_up['break_point_of_buy'].index,
                 'down_cnt': volume_down.shape[0], 'down_detail': volume_down['break_point_of_sell'].index}
        print(vol_b)

        ret_current_type = '盘整'
        current_action = '判断是否盘整背驰'
        sub_action = last_zhong_shu_and_price(zhong_shu_list[-1], last_close_price, bi_all)

    else:
        zhong_shu_cnt = len(zhong_shu_list)
        last_zhong_shu = zhong_shu_list[zhong_shu_cnt-1]
        l_z_s_price = last_zhong_shu.zhong_shu_middle_price
        second_last_zhong_shu = zhong_shu_list[zhong_shu_cnt - 2]
        s_l_z_s_price = second_last_zhong_shu.zhong_shu_middle_price
        print('最后两个中枢的price为{0} {1}'.format(s_l_z_s_price, l_z_s_price))

        # 获取macd数据
        duo_kong_rate_last = get_macd_info(chan_data, last_zhong_shu)
        duo_kong_rate_second = get_macd_info(chan_data, second_last_zhong_shu)

        # vol_b代表什么呢？
        vol_b = 0
        if s_l_z_s_price - l_z_s_price >= 0:
            ret_current_type = '下跌'
            print('下跌趋势，不建议操作，等待机会，需要等待第一类买点')
            print('先判断这两个中枢是否出现背驰，即趋势的力度')
            if 1.0/duo_kong_rate_last < 1.0/duo_kong_rate_second:
                current_action = '背驰，空的力量变小，等第一类买点，重要的是耐心，至少日级别MACD回零轴'
                sub_action = last_zhong_shu_and_price(zhong_shu_list[-1], last_close_price, bi_all)
                print(current_action)
            else:
                current_action = '没有背驰，下跌趋势依旧，不操作'
                print(current_action)
                sub_action = '', 0.0, 0.0
        else:
            ret_current_type = '上涨'
            print('上涨趋势，判断是否要考虑第一类卖点，或者二三类买点，这要根据动力学判断')
            print('先判断这两个中枢是否出现背驰，即趋势的力度，如果上涨的趋势力度变小，则出现衰竭，考虑卖哦！')
            if duo_kong_rate_last > duo_kong_rate_second:
                current_action = '没有背驰，继续持有，稳定持有，不操做'
                sub_action = '', 0.0, 0.0
                print(current_action)
            else:
                current_action = '背驰，有卖点卖出后观望，没有卖点等卖点马上卖，特别要会卖'
                print(current_action)
                sub_action = last_zhong_shu_and_price(zhong_shu_list[-1], last_close_price, bi_all)
        pass

    return last_close_price, ret_current_type, current_action, sub_action, vol_b


def last_zhong_shu_and_price(last_zhong_shu: ZhongShu, last_close_price, bi_all):
    last_zhong_shu_middle_price = last_zhong_shu.zhong_shu_middle_price
    last_zhong_shu_middle_upper_price = last_zhong_shu.min_max_value
    last_zhong_shu_middle_bottom_price = last_zhong_shu.max_low_value

    break_ratio = (last_close_price - last_zhong_shu_middle_price) / last_zhong_shu_middle_price
    # 当前位置距离中枢的距离
    current_distance = bi_all[-1].end_index - last_zhong_shu.end_index

    if last_close_price > last_zhong_shu_middle_upper_price:
        print('在中枢之上，需要判断三类买卖点是否已成，如果距离中枢不远，例如10%以内，可以操作买入')
        print('判断回调是否破中枢')
        sub_xian_duan_min_vs = [ele.get_min() for ele in bi_all if ele.start_index >= last_zhong_shu.end_index]
        xian_duan_min_value = min(sub_xian_duan_min_vs)

        if xian_duan_min_value > last_zhong_shu_middle_bottom_price:
            current_action = '不破中枢，距离中枢{0},多空分出胜负，脱离中枢价格{1}，可以选择涨幅小的买入'\
                .format(current_distance, break_ratio)
            # print(current_action)
        else:
            current_action = '回调破中枢，可以耐心等待操作机会'
            # print(current_action)
    elif last_zhong_shu_middle_bottom_price <= last_close_price <= last_zhong_shu_middle_upper_price:
        print('在中枢之中，可以按照震荡差价的方式进行操作，或者不操做')
        if last_close_price >= last_zhong_shu_middle_price:
            current_action = '在中枢中线上方，可以找机会卖出'
            # print()
        else:
            print('震荡差价买入')
            current_action = '在中枢中线下方，可以找机会买入，震荡差价，快进快出'
    else:
        current_action = '在中枢之下，需要判断三类买卖点是否已成，建议等待买点，不应该持有该股票'
    return current_action, break_ratio, current_distance


def get_macd_info(chan_data: ChanSourceDataObject, t_zhong_shu: ZhongShu):
    zhong_shu_start_index = t_zhong_shu.start_index
    zhong_shu_end_index = t_zhong_shu.end_index
    red_line = chan_data.histogram_positive.iloc[zhong_shu_start_index: zhong_shu_end_index]
    red_line = red_line[red_line > 0]
    red_line_cnt = red_line.shape[0]
    red_line_sum = red_line.sum()
    print('red_line_cnt', red_line_cnt)
    print('red_line_sum', red_line_sum)
    print('average_red_strength', red_line_sum/red_line_cnt)

    green_line = chan_data.histogram_negative.iloc[zhong_shu_start_index: zhong_shu_end_index]
    green_line = green_line[green_line < 0]
    green_line_cnt = green_line.shape[0]
    green_line_sum = green_line.sum()
    print('green_line_cnt', green_line_cnt)
    print('green_line_sum', green_line_sum)
    print('average_green_strength', green_line_sum/green_line_cnt)

    print('中枢内多空力量比，{0}'.format(red_line_sum/(-1.0*green_line_sum)))
    return red_line_sum/(-1.0*green_line_sum)


# 注意该方法要在事中进行分析，不能使用未来的数据。
# 在每时每刻计算当下的中枢分型进行分析。
# 这里应划分到回测范围，后续实现
def from_macd_seq_with_zhong_shu_2_buy_sell_point_in_time(chan_data: ChanSourceDataObject):
    # zhong_shu_list = chan_data.get_zhong_shu_list()
    plot_data = chan_data.get_plot_data_frame()
    histogram = chan_data.get_macd_bar()
    # print("histogram")
    # print(histogram)

    t_time = list(histogram.index)
    close_price = list(plot_data['Close'])
    print("close_price {0}".format(close_price))

    h_len = histogram.shape[0]
    buy_flag = False
    for idx in range(1, h_len):
        current_macd = histogram.iloc[idx-1]
        next_macd = histogram.iloc[idx]
        if next_macd < 0:
            print("hold money")
            # if next_macd > current_macd > -0.01:
            #     if not buy_flag:
            #         print("buy {0}, current_macd {1}".format(t_time[idx], current_macd))
            #         buy_price = close_price[idx]
            #         buy_flag = True
            #     else:
            #         print("hold stock")
            # else:
            #     print("hold money")
        else:
            if current_macd < next_macd:
                if not buy_flag:
                    print("buy {0}, current_macd {1}".format(t_time[idx], current_macd))
                    buy_price = close_price[idx]
                    buy_flag = True
                else:
                    print("hold stock")
            else:
                if buy_flag:
                    print("sell {0}, current_macd {1}".format(t_time[idx], current_macd))
                    buy_flag = False
                    sell_price = close_price[idx]
                    print("profit is {0}".format(sell_price - buy_price))
                else:
                    print("hold money")

    return None


def plot_with_mlf_v2(chan_data_object: ChanSourceDataObject, stock_name: str, pic_date: str):
    data = chan_data_object.get_plot_data_frame()
    max_boll = data['upper'].max()
    print("max of boll is {0}".format(max_boll))

    add_plot = [
        # 原图上面的MACD线
        # mpf.make_addplot(exp12, type='line', color='y'),
        # mpf.make_addplot(exp26, type='line', color='r'),
        # MACD图上面的面积柱子，红柱子，绿柱子
        mpf.make_addplot(chan_data_object.histogram_positive, type='bar', width=0.7, panel=2, color='red'),
        mpf.make_addplot(chan_data_object.histogram_negative, type='bar', width=0.7, panel=2, color='green'),
        mpf.make_addplot(chan_data_object.macd, panel=2, color='fuchsia', secondary_y=True),
        mpf.make_addplot(chan_data_object.signal, panel=2, color='b', secondary_y=True),

        # 成交量放大的点可以加到成交量的图上面去。
        mpf.make_addplot(data['break_point_of_buy']*max_boll,
                         scatter=True, markersize=10, marker='^',
                         color='r', panel=1, secondary_y='auto'),
        mpf.make_addplot(data['break_point_of_sell']*max_boll,
                         scatter=True, markersize=10, marker='v',
                         color='blue', panel=1, secondary_y='auto'),

        # BOLL线
        mpf.make_addplot(data['upper'], type='line', color='r', panel=1),
        mpf.make_addplot(data['lower'], type='line', color='g', panel=1),
        mpf.make_addplot(data['middle'], type='line', color='b', panel=1),

        # 顶底分型
        # ding red and di  green
        mpf.make_addplot(data['Valid_ding_to_draw'], scatter=True, markersize=15, marker='^', color='r'),
        mpf.make_addplot(data['Valid_di_to_draw'], scatter=True, markersize=15, marker='v', color='g'),

        # 笔
        # chan bi
        mpf.make_addplot(data['Bi_to_draw'], scatter=False, type='line',
                         color='black', linestyle='--', width=0.8),

        # 线段
        # chan line
        mpf.make_addplot(data['Line_to_draw'], scatter=False, type='line',
                         color='blue', linestyle='--', width=1.2),


    ]
    # zhong shu
    if len(chan_data_object.zhong_shu_list) > 0:
        add_plot.append(mpf.make_addplot(data['Zhong_shu_up_to_draw'], scatter=False, type='line',
                                         color='red', linestyle='-', width=0.5),)
        add_plot.append(mpf.make_addplot(data['Zhong_shu_down_to_draw'], scatter=False, type='line',
                                         color='black', linestyle='-', width=0.5),)

    my_color = mpf.make_marketcolors(up='red', down='cyan', edge='inherit', wick='black',
                                     volume={'up': 'red', 'down': 'green'})
    my_style = mpf.make_mpf_style(marketcolors=my_color, gridaxis='both', gridstyle='-.', y_on_right=False)

    print("shape of data is {0}".format(data.shape))
    # print("############")
    # print(add_plot)
    # print(data)
    # print("############")
    mpf.plot(data, type='candle', addplot=add_plot, mav=(5, 10, 30), volume=True, figscale=1.4,
             style=my_style, title='{0}: {1}'.format(stock_name, pic_date),
             ylabel='Price', ylabel_lower='Volume', xrotation=10)


pass

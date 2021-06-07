# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import logging
import math
import datetime
import copy
from deprecated.sphinx import deprecated


# 定义K线的类
class KiLineObject(object):
    def __init__(self):
        self.code = ""
        self.date = []
        self.open = 0.0
        self.close = 0.0
        self.high = 0.0
        self.low = 0.0
        self.volume = 0.0
        self.money = 0.0
        # 0 means not ding not di
        # 这里是原始的顶分型或者底分型
        self.ding_di_shape: int = 0
        # 这里是笔的开始和结束标记
        self.ding_di_to_bi: int = 0
        self.bi_to_line: int = 0

    def __init__(
        self,
        code: str,
        date: list,
        open_price: float,
        close: float,
        high: float,
        low: float,
        volume: float,
        money: float,
    ):
        self.code = code
        self.date = date
        self.open = open_price
        self.close = close
        self.high = high
        self.low = low
        self.volume = volume
        self.money = money
        self.ding_di_shape: int = 0
        self.ding_di_to_bi: int = 0
        self.bi_to_line: int = 0

    def __str__(self):
        return "{0}, {1}, {2}, {3}, {4}, {5}, {6}".format(
            self.code,
            ",".join([ele.strftime("%Y-%m-%d") for ele in self.date]),
            self.open,
            self.close,
            self.high,
            self.low,
            self.volume,
        )

    def set_date_2_plot(self, k_line_level):
        if k_line_level in ["30m", "60m", "15m", "120m"]:
            date_time = datetime.datetime.strptime(
                self.date[int(math.floor(len(self.date) / 2))].strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "%Y-%m-%d %H:%M:%S",
            )
        else:
            date_time = datetime.datetime.strptime(
                self.date[int(math.floor(len(self.date) / 2))].strftime("%Y-%m-%d"),
                "%Y-%m-%d",
            )
        self.date = [date_time]

    # 处理，先找到不包含的K线，然后开始处理。
    @staticmethod
    def k_line_merge(stock_code, stock_data, merge_or_not: bool = True):
        k_line_list = []
        for idx in range(0, stock_data.shape[0]):
            k_line_ele = KiLineObject(
                stock_code,
                [stock_data.iloc[idx].name],
                stock_data.iloc[idx]["open"],
                stock_data.iloc[idx]["close"],
                stock_data.iloc[idx]["high"],
                stock_data.iloc[idx]["low"],
                stock_data.iloc[idx]["volume"],
                stock_data.iloc[idx]["money"],
            )
            k_line_list.append(k_line_ele)
        if merge_or_not:
            return inner_merge(k_line_list)
        else:
            return k_line_list

    pass


class ChanBi(KiLineObject):
    # def __init__(self):
    #     self.direction = ''
    #     self.start_index = 0
    #     self.end_index = 0
    #     self.start_value = 0.0
    #     self.end_value = 0.0
    #     self.value_list_with_index = []
    #     self.high = 0.0
    #     self.low = 0.0
    #     self.asKLine = None

    def __init__(self, direction, start_index, end_index, start_value, end_value):
        self.direction = direction
        self.start_index = start_index
        self.end_index = end_index
        self.start_value = start_value
        self.end_value = end_value
        self.value_list_with_index = []

        super(ChanBi, self).__init__(
            direction, [start_index], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        )

        if start_index >= end_index:
            raise Exception("index error")

        if direction == "up":
            self.low = start_value
            self.high = end_value
            if start_value >= end_value:
                raise Exception("value error")
        if direction == "down":
            self.low = end_value
            self.high = start_value
            if start_value <= end_value:
                raise Exception(
                    "value error date: {0}, direction: {1},"
                    " start_value: {2}, end_value: {3}, "
                    "start_index: {4}, end_index: {5}".format(
                        self.date,
                        self.direction,
                        self.start_value,
                        self.end_value,
                        self.start_index,
                        self.end_index,
                    )
                )
        gap = (end_value - start_value) / (end_index - start_index)
        idx = start_index + 1
        while idx < end_index:
            self.value_list_with_index.append(
                (idx, start_value + (idx - start_index) * gap)
            )
            idx += 1
        # self.asKLine = KiLineObject('', [start_index], 0.0, 0.0, self.high, self.low, 0.0, 0.0)

    def get_min(self):
        return min(self.start_value, self.end_value)

    # 这里还有问题，合并的时候并没有解决性质问题
    # 目前解决了
    def __add__(self, other):
        if self.direction != other.direction:
            raise Exception("{0}, {1}".format(self.direction, other.direction))

        # 在向上时，把两根K线的 最高点 当高点，而两根K线低点中的 较高者 当成低点，这样就把两根K线合并成一根新的K线
        # 反之，当向下时，把两根K线的 最低点 当最低点，而把两根K线高点中的 较低者 当成最高点，这样就把两根K线合并成一根新的K线
        # k1 k2 判断两个K线元素在某个方向上是否存在包含关系

        # 向上笔构成特征序列在merge的时候方向是向下的
        if other.direction == "up":
            low = min(self.low, other.low)
            start_value = low
            high = max(self.high, other.high)
            end_value = high
        # 向xia笔构成特征序列在merge的时候方向是向上的
        else:
            high = max(self.high, other.high)
            start_value = high

            low = min(self.low, other.low)
            end_value = low

        t = ChanBi(
            other.direction,
            min(self.start_index, other.start_index),
            max(self.end_index, other.end_index),
            start_value,
            end_value,
        )
        t.date = [self.start_index, other.start_index]

        # 这里改好了之后还有问题，即顶或者底分型前两个元素出现缺口时划分是不对的。所以需要增加逻辑来解决。
        # 这里复杂的是当结束条件是合并后的笔，那么结束点取哪一个，答案是取主导作用笔的index!
        if self.low <= other.low and self.high >= other.high:
            # K1包含K2
            t.start_index = t.date[0]
            # t.end_index =
        else:
            t.start_index = t.date[1]
            # t.end_index =
        return t

    def __str__(self):
        return "date index is: {0}, direction: {1}, start idx: {2}, end idx: {3}, start value is: {4}," " end value is: {5}, high: {6}, low: {7}".format(
            ",".join([str(ele) for ele in self.date]),
            self.direction,
            self.start_index,
            self.end_index,
            self.start_value,
            self.end_value,
            self.high,
            self.low,
        )

    pass


@deprecated(version="0.1", reason="This function will be removed soon, no use")
def merge(k1: ChanBi, k2: ChanBi, merge_direction: str, domain_ele: str):
    if k1.direction != k2.direction:
        raise Exception("{0}, {1}".format(k1.direction, k2.direction))

    if merge_direction == "up":
        low = max(k1.low, k2.low)
        high = max(k1.high, k2.high)
        # 向xia笔构成特征序列在merge的时候方向是向上的
    else:
        low = min(k1.low, k2.low)
        high = min(k1.high, k2.high)

    if "k1" == domain_ele:

        new_bi = ChanBi(
            k1.direction, k1.start_index, k2.end_index, k1.start_value, k1.end_value
        )

        new_bi.start_index = k1.start_index
    else:
        new_bi = ChanBi(
            k1.direction, k1.start_index, k2.end_index, k2.start_value, k2.end_value
        )

        new_bi.start_index = k2.start_index

    new_bi.high = high
    new_bi.low = low
    new_bi.date = [k1.start_index, k2.start_index]

    return new_bi


class ChanLine(ChanBi):
    def __init__(
        self,
        direction,
        start_index,
        end_index,
        start_value,
        end_value,
        list_of_bi: list,
    ):
        super(ChanLine, self).__init__(
            direction, start_index, end_index, start_value, end_value
        )
        self.list_of_bi = list_of_bi

    def get_start_index(self):
        return self.start_index

    def get_end_index(self):
        return self.end_index

    def print(self):
        print(self.start_index)

    def get_max(self):
        if self.direction == "up":
            return self.end_value
        else:
            return self.start_value

    def get_min(self):
        if self.direction == "down":
            return self.end_value
        else:
            return self.start_value

    def __str__(self):

        return "direction {0}, start_index {1}, end_index {2}, start_value {3}, end_value {4}, values: {5}".format(
            self.direction,
            self.start_index,
            self.end_index,
            self.start_value,
            self.end_value,
            ",".join(
                [
                    "id {0}: {1}".format(element[0], element[1])
                    for element in self.value_list_with_index
                ]
            ),
        )

    def __add__(self, other):
        if self.direction != other.direction:
            raise Exception("{0}, {1}".format(self.direction, other.direction))

        return ChanLine(
            self.direction,
            min(self.start_index, other.start_index),
            max(self.end_index, other.end_index),
            self.start_value,
            other.end_value,
            self.list_of_bi + other.list_of_bi,
        )

    # 20201004发现问题，少了最后一笔
    @staticmethod
    def merge(in_line_list: list):
        out_line_list = []
        idx = 0
        while idx < len(in_line_list) - 1:
            if in_line_list[idx].direction == in_line_list[idx + 1].direction:
                # 2020.10.31如果不能合并，说明中间少了，这时候要把这一中间笔加上去
                try:
                    new_line_element = in_line_list[idx] + in_line_list[idx + 1]
                    # 如果是包含， 将该K线填回去到原K线的下一个继续比较
                    in_line_list[idx + 1] = new_line_element
                except Exception as e:
                    print(e)
                    # 在二者之间增加一个段，注意此段是虚拟的，所以bi list是空
                    if in_line_list[idx].direction == "up":
                        new_line_element = ChanLine(
                            "down",
                            in_line_list[idx].end_index,
                            in_line_list[idx + 1].start_index,
                            in_line_list[idx].end_value,
                            in_line_list[idx + 1].start_value,
                            [],
                        )
                    else:
                        new_line_element = ChanLine(
                            "up",
                            in_line_list[idx].end_index,
                            in_line_list[idx + 1].start_index,
                            in_line_list[idx].end_value,
                            in_line_list[idx + 1].start_value,
                            [],
                        )
                    out_line_list.append(in_line_list[idx])
                    out_line_list.append(new_line_element)
            else:
                out_line_list.append(in_line_list[idx])
            # 2020.9.29 这里漏了一种情况，如果是最后两根K线出现包含关系，那么要放进去
            if idx + 1 == len(in_line_list) - 1:
                out_line_list.append(in_line_list[idx + 1])
                break
            idx += 1
        return out_line_list

    pass


# 定义中枢构件
class ZhongShu(object):
    def __init__(
        self,
        start_index: int,
        end_index: int,
        max_low_value: float,
        min_max_value: float,
        list_of_duan: list,
    ):
        self.start_index = start_index
        self.end_index = end_index
        self.max_low_value = max_low_value  # low point
        self.min_max_value = min_max_value  # high point
        self.list_of_duan = list_of_duan
        self.zhong_shu_middle_price = 0.5 * (self.max_low_value + self.min_max_value)
        # 描述中枢的震荡力度
        self.zhong_shu_strength_ratio = (
            self.min_max_value - self.max_low_value
        ) / self.zhong_shu_middle_price
        self.zhong_shu_time_strength_length = end_index - start_index

    def is_contain_duan(self, next_line: ChanLine):
        # 范围之外
        if self.end_index != next_line.get_start_index():
            return False
        else:
            if (
                self.min_max_value < next_line.get_min()
                or self.max_low_value > next_line.get_max()
            ):
                return False
            else:
                return True

    def merge_duan(self, next_line: ChanLine):
        if self.end_index != next_line.start_index:
            raise Exception(
                "index not right, {0} , {1}".format(
                    self.end_index, next_line.start_index
                )
            )

        self.max_low_value = max(self.max_low_value, next_line.low)
        logging.info("merge {} {}".format(type(self.max_low_value), self.max_low_value))
        self.min_max_value = min(self.min_max_value, next_line.high)
        logging.info("merge {} {}".format(type(self.min_max_value), self.min_max_value))
        self.end_index = next_line.end_index
        self.list_of_duan.append(next_line)  # 2020.10.21 fix bug
        self.zhong_shu_middle_price = 0.5 * (self.max_low_value + self.min_max_value)
        # 描述中枢的震荡力度
        self.zhong_shu_strength_ratio = (
            self.min_max_value - self.max_low_value
        ) / self.zhong_shu_middle_price

    def __str__(self):
        print(
            "types {0}, {1}, {2}, {3}".format(
                type(self.start_index),
                type(self.end_index),
                type(self.max_low_value),
                type(self.min_max_value),
            )
        )
        return (
            "start_index: {0}, "
            "end index: {1}, "
            "low value {2}, max value {3}, "
            "zhong_shu_middle_price {4}, "
            "zhong_shu_strength_ratio {5}".format(
                self.start_index,
                self.end_index,
                self.max_low_value,
                self.min_max_value,
                self.zhong_shu_middle_price,
                self.zhong_shu_strength_ratio,
            )
        )

    @staticmethod
    def from_duan_2_zhong_shu(line1: ChanLine, line2: ChanLine, line3: ChanLine):
        high_1 = line1.get_max()
        high_2 = line2.get_max()
        high_3 = line3.get_max()
        min_high = min(high_1, high_2, high_3)
        print(type(min_high), min_high)

        low_1 = line1.get_min()
        low_2 = line2.get_min()
        low_3 = line3.get_min()

        low_max = max(low_1, low_2, low_3)
        print(type(low_max), low_max)

        if min_high >= low_max:
            line_list = [line1, line2, line3]
            print("zhong shu birth")
            # print('line1.get_start_index()', type(line1.get_start_index()), line1.get_start_index())
            current_element = ZhongShu(
                line1.get_start_index(),
                line3.get_end_index(),
                low_max,
                min_high,
                line_list,
            )
            # print('current zhong shu element', current_element)
            return True, current_element
        else:
            return False, None

    pass


# 在向上时，把两根K线的最高点当高点，而两根K线低点中的较高者当成低点，
# 这样就把两根K线合并成一根新的K线，反之，当向下时，把两根K线的最低点当最低点，
# 而把两根K线高点中的较低者当成最高点，这样就把两根K线合并成一根新的K线
# k1 k2 判断两个K线元素在某个方向上是否存在包含关系
def is_contain(k1, k2, merge_direction: str, check_code: bool = False):
    # print(isinstance(k1, KiLineObject))
    # print(isinstance(k1, ChanBi))
    if check_code and k1.code != k2.code:
        raise Exception("not same stock")

    if k1.low <= k2.low and k1.high >= k2.high:
        # K1包含K2
        if "up" == merge_direction:
            m_low = k2.low
            m_high = k1.high
        elif "down" == merge_direction:
            m_low = k1.low
            m_high = k2.high
        # return judge
        else:
            return False, "up" if k1.high <= k2.high else "down"
        if isinstance(k1, ChanBi):
            return True, k1 + k2

        elif isinstance(k1, KiLineObject):
            return True, KiLineObject(
                k1.code,
                k1.date + k2.date,
                k1.open,
                k2.close,
                m_high,
                m_low,
                k1.volume + k2.volume,
                k1.money + k2.money,
            )

        else:
            raise Exception("unknown type")

    elif k1.low >= k2.low and k1.high <= k2.high:
        # K2包含K1
        if "up" == merge_direction:
            m_low = k1.low
            m_high = k2.high
        elif "down" == merge_direction:
            m_low = k2.low
            m_high = k1.high
        # return judge
        else:
            return False, "up" if k1.high <= k2.high else "down"

        if isinstance(k1, ChanBi):
            return True, k1 + k2
            # return True, k1+k2
            # return True, k1
        elif isinstance(k1, KiLineObject):
            return True, KiLineObject(
                k1.code,
                k1.date + k2.date,
                k1.open,
                k2.close,
                m_high,
                m_low,
                k1.volume + k2.volume,
                k1.money + k2.money,
            )
        else:
            raise Exception("unknown type")

    else:
        return False, "up" if k1.high <= k2.high else "down"


# 用于合并K线，K线的合并处理
def inner_merge(k_line_list, merge_direction: str = "unknown"):
    # print(len(k_line_list))

    start_merge = False
    k_line_list_out = []
    idx = 0
    direction = merge_direction
    while idx < len(k_line_list) - 1:
        if not start_merge:
            k_line_list_out.append(k_line_list[idx])
            # 判断是否非包含
            c_res = is_contain(k_line_list[idx], k_line_list[idx + 1], direction)
            if not c_res[0]:
                start_merge = True
                direction = c_res[1]
            else:
                idx += 1
                continue
        else:
            m_res = is_contain(k_line_list[idx], k_line_list[idx + 1], direction)
            if m_res[0]:
                new_line = m_res[1]
                # 如果是包含， 将该K线填回去到原K线的下一个继续比较
                k_line_list[idx + 1] = new_line
            else:
                # 非包含了，才把该K线放到新K线里面去，同时更新方向
                direction = m_res[1]
                k_line_list_out.append(k_line_list[idx])
            # 2020.9.29 这里漏了一种情况，如果是最后两根K线出现包含关系，那么要放进去
            if idx + 1 == len(k_line_list) - 1:
                k_line_list_out.append(k_line_list[idx + 1])
                break
        idx += 1

    # print("k_line_list_out")
    # print(len(k_line_list_out))
    return k_line_list_out


# 用于笔的合并，与K线不完全一样
def bi_inner_merge(
    input_line_list, merge_direction: str = "unknown", is_debug: bool = False
):
    bi_line_list = copy.deepcopy(input_line_list)
    if is_debug:
        print("merge_direction is {0}".format(merge_direction))
        print("len line list")
        print(len(bi_line_list))

    k_line_list_out = list()
    k_line_list_out.append(input_line_list[0])
    # 避免第一个分型失效
    # 这个点太关键了！！！！
    idx = 1

    while idx < len(bi_line_list) - 1:
        m_res = is_contain(bi_line_list[idx], bi_line_list[idx + 1], merge_direction)
        if m_res[0]:
            new_line = m_res[1]
            # 如果是包含， 将该K线填回去到原K线的下一个继续比较
            bi_line_list[idx + 1] = new_line
        else:
            k_line_list_out.append(bi_line_list[idx])
        # 2020.9.29 这里漏了一种情况，如果是最后两根K线出现包含关系，那么要放进去
        if idx + 1 == len(bi_line_list) - 1:
            k_line_list_out.append(bi_line_list[idx + 1])
            break
        idx += 1
    if is_debug:
        print("k_line_list_out")
        print(len(k_line_list_out))
    return k_line_list_out


pass

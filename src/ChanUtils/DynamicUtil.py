# -*- coding:utf-8 -*-
# remind install clang on mac with cmd, xcode-select --install
import numpy
from .BasicUtil import ZhongShu


# input data frame of day data
def inner_get_average_volume(t_price,
                             level: str = 'daily',
                             volume_col_name: str = 'Volume',
                             open_col_name: str = 'Open',
                             close_col_name: str = 'Close',
                             v_ratio: float = 3.0):
    if 'daily' == level:
        range_of_days = 7
    elif '30m' == level:
        range_of_days = 7 * 8
    elif '60m' == level:
        range_of_days = 7 * 4
    elif '120m' == level:
        range_of_days = 7 * 2
    elif '15m' == level:
        range_of_days = 7 * 16
    elif 'week' == level:
        range_of_days = 1
    else:
        raise Exception

    t_price['average_volume'] = t_price[volume_col_name]*0.0

    # print("t_price.index")
    # print(t_price.index)
    # 把日期编号，从0到最后一天，然后好根据编号获得天数。t_price.index 代表每一个交易日
    date_idx = range(0, len(t_price.index))
    map_idx_date = dict(zip(date_idx, t_price.index))
    # print(type(map_idx_date))
    # print(map_idx_date)

    t_price['idx'] = date_idx

    # 计算7日内平均交易量，仅从大于7日的天数开始计算，否则设置为0。这里的7日是超参数
    for index in t_price.index:
        # 获得当前日期向前推7天的日期
        first_date = map_idx_date.get(0 if (int(t_price.loc[index]['idx']) - range_of_days) < 0 else int(
            t_price.loc[index]['idx'] - range_of_days))
        # print(lst_date)
        # print(type(lst_date))
        # 左闭右开，所以正好是前7天的交易量
        volume_num = t_price.loc[(t_price.index >= first_date) & (t_price.index < index)][volume_col_name]
        # print(num)
        volume_sum = volume_num.sum()
        # print(num_s)
        # print(t_price.loc[index]['average_volume'])
        t_price.loc[index, 'average_volume'] = volume_sum / float(range_of_days)

    # print(t_price)
    # 放量买点，价格向上且成交量放大1.5倍以上
    t_price['break_point_of_buy'] = t_price.apply(lambda row:
                                                  1.0 if (row[volume_col_name] > v_ratio * row['average_volume']) &
                                                         ((row[close_col_name] - row[open_col_name]) >= 0) &
                                                         (row['idx'] > range_of_days) else numpy.nan, axis=1)

    t_price['break_point_of_sell'] = t_price.apply(lambda row:
                                                   1.0 if (row[volume_col_name] > v_ratio * row['average_volume']) &
                                                          ((row[close_col_name] - row[open_col_name]) < 0) &
                                                          (row['idx'] > range_of_days) else numpy.nan, axis=1)

    return True


# 股票买入后就要考虑卖点，当然卖点是有不同级别的。
# 进入市场的目的是为了赢钱，不是筹码，筹码早晚是要换钱的。
# 市场哲学的数学原理！！！！
def from_xian_duan_to_zhong_shu(input_lines: list):
    line_cnt = len(input_lines)
    if line_cnt < 3:
        print('没有足够线段')
        return []
    idx_duan = 0
    zhong_shu_list = []
    while idx_duan < line_cnt:
        if len(zhong_shu_list) == 0 and idx_duan+2 < line_cnt:
            res = ZhongShu.from_duan_2_zhong_shu(input_lines[idx_duan],
                                                 input_lines[idx_duan+1],
                                                 input_lines[idx_duan+2])
            if res[0]:
                zhong_shu_list.append(res[1])
                idx_duan = idx_duan+3
            else:
                print('not zhong shu, continue')
                idx_duan += 1
        else:
            print('看是否包含，如果不包含尝试新的中枢')
            last_zhong_shu = zhong_shu_list[-1]
            contain_flag = last_zhong_shu.is_contain_duan(input_lines[idx_duan])
            if contain_flag:
                print('包含，合并')
                zhong_shu_list[-1].merge_duan(input_lines[idx_duan])
                idx_duan += 1
            elif idx_duan+2 < line_cnt:
                res = ZhongShu.from_duan_2_zhong_shu(input_lines[idx_duan],
                                                     input_lines[idx_duan + 1],
                                                     input_lines[idx_duan + 2])
                if res[0]:
                    zhong_shu_list.append(res[1])
                    idx_duan = idx_duan + 3
                else:
                    print('not zhong shu, continue')
                    idx_duan += 1
            else:
                print('没有足够线段形成中枢，结束')
                idx_duan += 1
    return zhong_shu_list


pass

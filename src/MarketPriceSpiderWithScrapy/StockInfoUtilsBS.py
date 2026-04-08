# -*- coding:utf-8 -*-
# get all stock codes info by baostock  akshare东财接口不可用使用baostock替代 只有沪指和深指
import hashlib
import warnings
import pandas as pd
from tqdm import tqdm
import baostock as bs
# from datetime import datetime as dt

tqdm.pandas(desc="progress status")
pd.set_option("display.max_columns", None)
# 显示所有行
pd.set_option("display.max_rows", None)
pd.set_option("max_colwidth", 500)

def get_last_trade_day():
    import datetime 
    bs.login()
    # 获取当前日期
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 查询当前日期之前的交易日列表
    # we use a buffer of 10 days to ensure we catch the previous one
    start_date = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
    
    rs = bs.query_trade_dates(start_date=start_date, end_date=today)
    date_list = []
    while (rs.error_code == '0') & rs.next():
        date_list.append(rs.get_row_data())
    
    bs.logout()
    
    # 筛选出所有交易日且小于今天的最后一个
    trade_days = [d[0] for d in date_list if d[1] == '1' and d[0] < today]
    return trade_days[-1] if trade_days else None

def get_all_stock_code_info_of_cn(date=None):
    # 代码 名称
    # stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
    # 沪 A 股 stock_sh_a_spot_em
    # 京 A 股 stock_bj_a_spot_em
    # 深 A 股 stock_sz_a_spot_em
    # 科创板 stock_kc_a_spot_em
    # 新股 stock_new_a_spot_em

    if not date:
        # date = dt.now() - pd.tseries.offsets.BusinessDay(n=1)
        # date = date.strftime('%Y-%m-%d')
        date = get_last_trade_day()
    
    lg = bs.login()
    rs = bs.query_all_stock(day="")
    stock_df = bs.query_all_stock(day=date).get_data()
    bs.logout()
    
    data_sh = stock_df[stock_df['code'].str.startswith('sh.')]
    data_sh["joint_quant_code"] = data_sh.progress_apply(
        lambda row: "sh{0}".format(row["code"].split(".")[1]),
        axis=1,
    )
    data_sh["market_type"] = data_sh.progress_apply(
        lambda row: "sh",
        axis=1,
    )

    data_sz = stock_df[stock_df['code'].str.startswith('sz.')]
    data_sz["joint_quant_code"] = data_sz.progress_apply(
        lambda row: "sz{0}".format(row["code"].split(".")[1]),
        axis=1,
    )
    data_sz["market_type"] = data_sz.progress_apply(
        lambda row: "sz",
        axis=1,
    )

    print("all {} length is {}, sample {}".format(type(stock_df), len(stock_df), stock_df[:10]))

    print(
        "sh {} length is {}, sample {}".format(
            type(data_sh), len(data_sh), data_sh[:10]
        )
    )
    print(
        "sz {} length is {}, sample {}".format(
            type(data_sz), len(data_sz), data_sz[:10]
        )
    )

    sub_data_cnt = data_sh.shape[0] + data_sz.shape[0]
    all_code_cnt = stock_df.shape[0]

    print("all_code_cnt {}, sub_data_cnt {}".format(all_code_cnt, sub_data_cnt))
    if sub_data_cnt != all_code_cnt:
        warnings.warn(
            "all_code_cnt not equal sub_data_cnt",
            category=None,
            stacklevel=1,
            source=None,
        )

    data_merge = pd.concat([data_sh, data_sz], ignore_index=True)

    data_merge["_id"] = data_merge.progress_apply(
        lambda row: hashlib.md5(
            ("{0}".format(row["code"])).encode(encoding="utf-8")
        ).hexdigest(),
        axis=1,
    )

    print("data_merge shape {}".format(data_merge.shape))

    return data_merge



if __name__ == "__main__":
    info = get_all_stock_code_info_of_cn()
    print("top")
    print(info[:10])

    print("end")
    print(info[-10:])
    pass

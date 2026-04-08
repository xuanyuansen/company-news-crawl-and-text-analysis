# -*- coding:utf-8 -*-
# get all stock codes info by akshare
import hashlib
import warnings
import pandas as pd
from tqdm import tqdm
import akshare as ak

tqdm.pandas(desc="progress status")
pd.set_option("display.max_columns", None)
# 显示所有行
pd.set_option("display.max_rows", None)
pd.set_option("max_colwidth", 500)


def get_all_stock_code_info_of_cn():
    # 代码 名称
    # stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
    # 沪 A 股 stock_sh_a_spot_em
    # 京 A 股 stock_bj_a_spot_em
    # 深 A 股 stock_sz_a_spot_em
    # 科创板 stock_kc_a_spot_em
    # 新股 stock_new_a_spot_em
    data = ak.stock_zh_a_spot_em()

    data_sh = ak.stock_sh_a_spot_em()
    data_sh["joint_quant_code"] = data_sh.progress_apply(
        lambda row: "sh{0}".format(row["代码"]),
        axis=1,
    )
    data_sh["market_type"] = data_sh.progress_apply(
        lambda row: "sh",
        axis=1,
    )

    data_sz = ak.stock_sz_a_spot_em()
    data_sz["joint_quant_code"] = data_sz.progress_apply(
        lambda row: "sz{0}".format(row["代码"]),
        axis=1,
    )
    data_sz["market_type"] = data_sz.progress_apply(
        lambda row: "sz",
        axis=1,
    )

    data_bj = ak.stock_bj_a_spot_em()
    data_bj["joint_quant_code"] = data_bj.progress_apply(
        lambda row: "bj{0}".format(row["代码"]),
        axis=1,
    )
    data_bj["market_type"] = data_bj.progress_apply(
        lambda row: "bj",
        axis=1,
    )

    data_kc = ak.stock_kc_a_spot_em()
    data_kc["joint_quant_code"] = data_kc.progress_apply(
        lambda row: "kc{0}".format(row["代码"]),
        axis=1,
    )
    data_kc["market_type"] = data_kc.progress_apply(
        lambda row: "kc",
        axis=1,
    )

    print("all {} length is {}, sample {}".format(type(data), len(data), data[:10]))

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
    print(
        "bj {} length is {}, sample {}".format(
            type(data_bj), len(data_bj), data_bj[:10]
        )
    )
    print(
        "kc {} length is {}, sample {}".format(
            type(data_kc), len(data_kc), data_kc[:10]
        )
    )

    sub_data_cnt = data_sh.shape[0] + data_sz.shape[0] + data_bj.shape[0]
    all_code_cnt = data.shape[0]

    print("all_code_cnt {}, sub_data_cnt {}".format(all_code_cnt, sub_data_cnt))
    if sub_data_cnt != all_code_cnt:
        warnings.warn(
            "all_code_cnt not equal sub_data_cnt",
            category=None,
            stacklevel=1,
            source=None,
        )

    data_merge = pd.concat([data_sh, data_sz, data_bj], ignore_index=True)

    data_merge["_id"] = data_merge.progress_apply(
        lambda row: hashlib.md5(
            ("{0}".format(row["代码"])).encode(encoding="utf-8")
        ).hexdigest(),
        axis=1,
    )

    print("data_merge shape {}".format(data_merge.shape))

    return data_merge


def get_all_stock_code_info_of_hk():
    stock_hk_spot_em_df = ak.stock_hk_spot_em()
    print(stock_hk_spot_em_df)
    return stock_hk_spot_em_df


if __name__ == "__main__":
    info = get_all_stock_code_info_of_cn()
    print("top")
    print(info[:10])

    print("end")
    print(info[-10:])
    pass

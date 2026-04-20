# -*- coding:utf-8 -*-
# 通过交易量变化，找到底部长期盘整后放量突破的股票（优化版）。
# 在 GetMassBreakAlphaGo.py 的结构上扩展：
# 1) 支持“维持放量 Ratio 连续 X 天”后再触发选股
# 2) 对“开盘涨停导致无放量”的场景做特殊处理

import argparse
import sys

from MarketPriceSpiderWithScrapy.StockInfoUtilsBS import get_all_stock_code_info_of_cn
from MongoDbComTools.LocalDbTool import LocalDbTool
import pandas as pd
from Utils.utils import set_display
from tqdm import tqdm

tqdm.pandas(desc="progress status")

local_db = LocalDbTool()

AVG_VOLUME_MIN_THRESHOLD = 10000
MIN_VOLUME_MIN_THRESHOLD = 1000


def get_specific_target_stock(t_stock, market, start, end_date: str = ""):
    return local_db.get_daily_price_data_of_specific_stock(
        symbol=t_stock, market_type=market, start_date=start, end_date=end_date or None
    )


# 保留原结构中的函数定义，便于兼容
def average_volume_last_30_days(group):
    return group.tail(30)["volume"].mean()


def _extract_code_prefix(t_stock: str) -> str:
    code = "".join(ch for ch in str(t_stock) if ch.isdigit())
    return code[:3] if len(code) >= 3 else code


def _get_limit_up_pct(t_stock: str) -> float:
    # 主板通常 10%，创业板/科创板通常 20%，北交所通常 30%
    prefix = _extract_code_prefix(t_stock)
    if prefix in {"300", "301", "688", "689"}:
        return 0.20
    if prefix.startswith("8") or prefix.startswith("4"):
        return 0.30
    return 0.10


def _market_has_limit_up(market: str) -> bool:
    # A 股有较明确涨跌停制度；美股/港股默认不启用该逻辑
    return str(market).lower() == "cn"


def _calc_consecutive_true_count(bool_series: pd.Series) -> pd.Series:
    group_id = (~bool_series).cumsum()
    return bool_series.groupby(group_id).cumsum().astype(int)


def _pick_code_column(df: pd.DataFrame) -> str:
    for col in ["joint_quant_code", "symbol", "code"]:
        if col in df.columns:
            return col
    return ""


def _pick_name_column(df: pd.DataFrame) -> str:
    for col in ["code_name", "name", "股票名称"]:
        if col in df.columns:
            return col
    return ""



def get_stock_pool_by_market(market: str) -> pd.DataFrame:
    market_l = str(market).lower()

    if market_l == "cn":
        return get_all_stock_code_info_of_cn()

    if market_l == "hk":
        df = local_db.col_basic_info_hk_df.copy()
    elif market_l == "us":
        df = local_db.db_obj.get_data(local_db.database_name_us, local_db.collection_name_us)
        if df is None or getattr(df, "empty", True):
            df = local_db.db_obj.get_data(local_db.database_name_us, local_db.collection_name_us_zh)
        if df is None:
            return pd.DataFrame()
    else:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    code_col = _pick_code_column(df)
    if code_col:
        df["joint_quant_code"] = df[code_col]

    name_col = _pick_name_column(df)
    if name_col and "code_name" not in df.columns:
        df["code_name"] = df[name_col]

    return df


# AveDate: 均线窗口; Ratio: 放量倍数; KeepDays: 持续放量天数
def getVolumeBreakDateList(
    t_stock,
    market,
    start,
    AveDate: int,
    Ratio: float,
    KeepDays: int = 1,
    EnableLimitUpSpecial: bool = None,
    PriceStableThreshold: float = 0.05,
    end_date: str = "",
):
    res, data = get_specific_target_stock(t_stock, market, start, end_date=end_date)
    min_days = max(AveDate, KeepDays + 1)
    if (not res) or data.shape[0] < min_days:
        return [], -1, -1, 0, 0, []

    data = data.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["open", "high", "low", "close", "volume"])
    if data.shape[0] < min_days:
        return [], -1, -1, 0, 0, []

    data["AvgVolumeLastNDays"] = data["volume"].rolling(AveDate).mean()
    data["MinVolumeLastNDays"] = data["volume"].rolling(AveDate).min()
    data["VarClosePriceLastNDays"] = data["close"].rolling(AveDate).var()
    data["ClosePriceLastNDays"] = data["close"].rolling(AveDate).mean()
    data["TodayVsLastNDays"] = data["close"] - data["ClosePriceLastNDays"]

    last_today_vs_last_n_days = data["TodayVsLastNDays"].iloc[-1]
    if pd.isna(last_today_vs_last_n_days):
        last_today_vs_last_n_days = -1

    data["TodayVolumeVsN"] = data["volume"] / data["AvgVolumeLastNDays"].replace(0, pd.NA)
    latest_today_volume_vs_n = data["TodayVolumeVsN"].iloc[-1]
    if pd.isna(latest_today_volume_vs_n):
        latest_today_volume_vs_n = 0

    # ===== 放量期间（KeepDays窗口）价格稳定性 =====
    # 使用 KeepDays 窗口的价格区间 / 均价衡量，越小越稳定。
    keep_window = max(1, int(KeepDays))
    data["KeepWindowCloseMax"] = data["close"].rolling(keep_window).max()
    data["KeepWindowCloseMin"] = data["close"].rolling(keep_window).min()
    data["KeepWindowCloseMean"] = data["close"].rolling(keep_window).mean()
    data["KeepWindowPriceRangeRatio"] = (
        (data["KeepWindowCloseMax"] - data["KeepWindowCloseMin"])
        / data["KeepWindowCloseMean"].replace(0, pd.NA)
    )
    data["IsPriceStableInKeepDays"] = (
        data["KeepWindowPriceRangeRatio"] <= PriceStableThreshold
    ).fillna(False)

    if EnableLimitUpSpecial is None:
        EnableLimitUpSpecial = _market_has_limit_up(market)

    # ===== 开盘涨停特殊处理（仅支持有涨停制度的市场）=====
    # 避免“开盘一字板导致成交量不明显放大”时被误过滤。
    if EnableLimitUpSpecial:
        data["PrevClose"] = data["close"].shift(1)
        data["OpenRiseVsPrevClose"] = data["open"] / data["PrevClose"] - 1

        limit_up_pct = _get_limit_up_pct(t_stock)
        limit_threshold = limit_up_pct * 0.98  # 留少量容忍度，减少数据精度导致的漏检
        data["IsOpenLimitUp"] = (data["PrevClose"] > 0) & (
            data["OpenRiseVsPrevClose"] >= limit_threshold
        )
    else:
        data["IsOpenLimitUp"] = False

    # 在保证放量条件的同时，放量期间 KeepDays 内价格应相对稳定
    # 同时要求 AveDate 滚动均量和窗口最小成交量满足最低门槛，避免低流动性标的误入选股。
    data["VolumeWithStable"] = (
        (data["TodayVolumeVsN"] >= Ratio)
        & data["IsPriceStableInKeepDays"]
        & (data["AvgVolumeLastNDays"] > AVG_VOLUME_MIN_THRESHOLD)
        & (data["MinVolumeLastNDays"] > MIN_VOLUME_MIN_THRESHOLD)
    )
    # 放量且稳定 OR 开盘涨停特例
    data["VolumeOrLimitUp"] = data["VolumeWithStable"]# | data["IsOpenLimitUp"]
    data["VolumeOrLimitUp"] = data["VolumeOrLimitUp"].fillna(False)

    # 连续天数统计，达到 KeepDays 后才触发信号
    data["KeepCount"] = _calc_consecutive_true_count(data["VolumeOrLimitUp"])
    data["IsSignalDay"] = (data["KeepCount"] >= KeepDays) & (
        data["KeepCount"].shift(1).fillna(0) < KeepDays
    )

    signal_df = data[data["IsSignalDay"]]
    if signal_df.shape[0] == 0:
        return [], -1, float(last_today_vs_last_n_days), float(latest_today_volume_vs_n), 0, []

    signal_dates = signal_df["date"].values.tolist()
    price_var_list = signal_df["VarClosePriceLastNDays"].dropna().values.tolist()
    avg_price_var = sum(price_var_list) / len(price_var_list) if price_var_list else -1

    avg_signal_volume_ratio = signal_df["TodayVolumeVsN"].dropna().mean()
    if pd.isna(avg_signal_volume_ratio):
        avg_signal_volume_ratio = 0

    open_limit_up_signal_dates = signal_df[signal_df["IsOpenLimitUp"]]["date"].values.tolist()

    return (
        signal_dates,
        float(avg_price_var),
        float(last_today_vs_last_n_days),
        float(latest_today_volume_vs_n),
        float(avg_signal_volume_ratio),
        open_limit_up_signal_dates,
    )


set_display()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stock_code")
    parser.add_argument("market")
    parser.add_argument("start_date")
    parser.add_argument("ave_date", type=int)
    parser.add_argument("ratio", type=float)
    parser.add_argument("--keep-days", type=int, default=2)
    parser.add_argument("--price-stable-threshold", type=float, default=0.12)
    parser.add_argument(
        "--end-date",
        default="",
        help="数据截止日期 YYYY-MM-DD；为空则使用最新可用数据",
    )
    args = parser.parse_args()

    res = getVolumeBreakDateList(
        args.stock_code,
        args.market,
        args.start_date,
        args.ave_date,
        args.ratio,
        args.keep_days,
        None,
        args.price_stable_threshold,
        args.end_date,
    )
    print(f"stock {args.stock_code} res is {res}")

    info = get_stock_pool_by_market(args.market)
    if info is None or info.empty:
        print("stock pool is empty for market={}, skip batch scan".format(args.market))
        sys.exit(0)

    if "joint_quant_code" not in info.columns:
        print("stock pool missing joint_quant_code, skip batch scan")
        sys.exit(0)

    print(info.shape)
    print(info.head(10))

    info["BreakDateAndVar"] = info.progress_apply(
        lambda row: getVolumeBreakDateList(
            row["joint_quant_code"],
            args.market,
            args.start_date,
            args.ave_date,
            args.ratio,
            args.keep_days,
            None,
            args.price_stable_threshold,
            args.end_date,
        ),
        axis=1,
    )

    info["BreakDate"] = info.progress_apply(lambda row: row["BreakDateAndVar"][0], axis=1)
    info["BreakDateCnt"] = info.progress_apply(lambda row: len(row["BreakDate"]), axis=1)
    info["LatestBreakDate"] = info.progress_apply(
        lambda row: row["BreakDate"][-1] if len(row["BreakDate"]) > 0 else -1,
        axis=1,
    )
    info["PriceVar"] = info.progress_apply(lambda row: row["BreakDateAndVar"][1], axis=1)
    info["LastTodayVsLastNDays"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][2], axis=1
    )
    info["TodayVolumeVsN"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][3], axis=1
    )
    info["AvgSignalVolumeRatio"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][4], axis=1
    )
    info["OpenLimitUpSignalDates"] = info.progress_apply(
        lambda row: row["BreakDateAndVar"][5], axis=1
    )
    info["OpenLimitUpSignalCnt"] = info.progress_apply(
        lambda row: len(row["OpenLimitUpSignalDates"]), axis=1
    )

    info["name"] = info["code_name"] if "code_name" in info.columns else info["code"]

    info.to_csv(
        "break_alphago_{}_{}_{}_{}_keep{}_stable{}.csv".format(
            args.market, args.start_date, args.ave_date, args.ratio, args.keep_days, args.price_stable_threshold
        ),
        index=False,
    )

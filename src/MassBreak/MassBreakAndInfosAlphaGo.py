# -*- coding:utf-8 -*-
"""
融合 MassBreakAlphaGo 量价信号与 run_scrapy_one_day 落库新闻数据，生成综合选股评分。
"""

import argparse
import datetime as dt
import os
import sys
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

# 兼容 `python MassBreak/xxx.py` 直接运行
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

try:
    from MassBreak.MassBreakAlphaGo import getVolumeBreakDateList, get_stock_pool_by_market
except ModuleNotFoundError:
    from MassBreakAlphaGo import getVolumeBreakDateList, get_stock_pool_by_market

from Utils import config
from Utils.database import Database

tqdm.pandas(desc="progress status")


def normalize_stock_code(raw_code) -> str:
    if pd.isna(raw_code):
        return ""
    code = str(raw_code).strip().upper()
    if not code:
        return ""

    if code.startswith("SH") or code.startswith("SZ"):
        body = code[2:]
        if body.isdigit():
            return body.zfill(6)

    if "." in code:
        left, right = code.split(".", 1)
        if right.isdigit():
            return right.zfill(6)
        if left.isdigit():
            return left.zfill(6)

    if len(code) > 3 and code[-3:] in {".SH", ".SZ"} and code[:-3].isdigit():
        return code[:-3].zfill(6)

    if code.isdigit():
        return code.zfill(6)

    return code


def to_symbol_for_stock_specific_news(code_norm: str) -> str:
    # 与 BuildStockNewsDb.__insert_data_to_db 的规则保持一致
    if code_norm.isdigit():
        return "sh{}".format(code_norm) if int(code_norm) >= 600000 else "sz{}".format(code_norm)
    return code_norm.lower()


def to_cn_news_date_start(date_str: str) -> str:
    d = dt.datetime.strptime(date_str, "%Y-%m-%d")
    return d.strftime("%Y年%m月%d日 00:00")


def load_massbreak_candidates(
    market: str,
    start_date: str,
    ave_date: int,
    ratio: float,
    keep_days: int,
    price_stable_threshold: float,
    min_break_count: int,
    enable_limit_up_special=None,
    max_stocks: int = 0,
) -> pd.DataFrame:
    stock_pool = get_stock_pool_by_market(market)
    if stock_pool is None or stock_pool.empty:
        raise ValueError("股票池为空，market={}".format(market))

    code_col = "joint_quant_code" if "joint_quant_code" in stock_pool.columns else None
    if not code_col:
        for c in ["symbol", "code"]:
            if c in stock_pool.columns:
                code_col = c
                break
    if not code_col:
        raise ValueError("股票池缺少代码列（joint_quant_code/symbol/code）")

    if "joint_quant_code" not in stock_pool.columns:
        stock_pool["joint_quant_code"] = stock_pool[code_col]

    market_l = str(market).lower()
    if market_l == "cn":
        # 过滤明显非个股标的，减少无行情数据造成的噪声
        stock_pool["joint_quant_code"] = stock_pool["joint_quant_code"].astype(str)
        stock_pool = stock_pool[
            stock_pool["joint_quant_code"].str.match(r"^(sh6|sz0|sz3|bj4|bj8)\d{5}$")
        ].copy()
        if "code_name" in stock_pool.columns:
            stock_pool = stock_pool[
                ~stock_pool["code_name"].astype(str).str.contains("指数", na=False)
            ].copy()

    if max_stocks and max_stocks > 0:
        stock_pool = stock_pool.head(max_stocks).copy()

    stock_pool["BreakDateAndVar"] = stock_pool.progress_apply(
        lambda row: getVolumeBreakDateList(
            row["joint_quant_code"],
            market,
            start_date,
            int(ave_date),
            float(ratio),
            int(keep_days),
            enable_limit_up_special,
            float(price_stable_threshold),
        ),
        axis=1,
    )

    stock_pool["BreakDate"] = stock_pool["BreakDateAndVar"].map(lambda x: x[0] if isinstance(x, tuple) else [])
    stock_pool["BreakDateCnt"] = stock_pool["BreakDate"].map(len)
    stock_pool["LatestBreakDate"] = stock_pool["BreakDate"].map(
        lambda x: x[-1] if isinstance(x, list) and len(x) > 0 else -1
    )
    stock_pool["PriceVar"] = stock_pool["BreakDateAndVar"].map(lambda x: x[1] if isinstance(x, tuple) else -1)
    stock_pool["LastTodayVsLastNDays"] = stock_pool["BreakDateAndVar"].map(
        lambda x: x[2] if isinstance(x, tuple) else -1 # 最新一天收盘价与 N 日均价的差值。
    )
    stock_pool["TodayVolumeVsN"] = stock_pool["BreakDateAndVar"].map(
        lambda x: x[3] if isinstance(x, tuple) else 0  # 最新一天成交量 / N日平均成交量。
    )
    stock_pool["AvgSignalVolumeRatio"] = stock_pool["BreakDateAndVar"].map(
        lambda x: x[4] if isinstance(x, tuple) else 0
    )
    stock_pool["OpenLimitUpSignalDates"] = stock_pool["BreakDateAndVar"].map(
        lambda x: x[5] if isinstance(x, tuple) else []
    )
    stock_pool["OpenLimitUpSignalCnt"] = stock_pool["OpenLimitUpSignalDates"].map(
        lambda x: len(x) if isinstance(x, list) else 0
    )

    stock_pool["stock_code_norm"] = stock_pool["joint_quant_code"].map(normalize_stock_code)
    stock_pool["name"] = stock_pool["code_name"] if "code_name" in stock_pool.columns else stock_pool["joint_quant_code"]

    return stock_pool[stock_pool["BreakDateCnt"] >= min_break_count].copy()


def load_news_good_or_bad(
    candidate_df: pd.DataFrame,
    label_field: str = "Label",
    news_start_date: str = "",
) -> pd.DataFrame:
    """
    从 stock_specific_news 按候选股票聚合新闻情绪。
    """
    empty_cols = [
        "stock_code_norm",
        "news_stock_name",
        "good_cnt",
        "bad_cnt",
        "total_mentions",
        "sentiment_balance",
    ]
    if candidate_df is None or candidate_df.empty:
        return pd.DataFrame(columns=empty_cols)

    db = Database()
    news_db = db.connect_database(config.ALL_NEWS_OF_SPECIFIC_STOCK_DATABASE)
    collection_names = set(news_db.list_collection_names())

    start_cn = ""
    if news_start_date:
        start_cn = to_cn_news_date_start(news_start_date)

    unique_codes = candidate_df["stock_code_norm"].dropna().astype(str).unique().tolist()
    rows = []

    for code_norm in tqdm(unique_codes, desc="news-match"):
        symbol = to_symbol_for_stock_specific_news(code_norm)
        if symbol not in collection_names:
            rows.append(
                {
                    "stock_code_norm": code_norm,
                    "news_stock_name": "",
                    "good_cnt": 0.0,
                    "bad_cnt": 0.0,
                    "total_mentions": 0.0,
                    "sentiment_balance": 0.0,
                }
            )
            continue

        col = news_db.get_collection(symbol)
        match_query = {label_field: {"$in": ["利好", "利空"]}}
        if start_cn:
            match_query["Date"] = {"$gte": start_cn}

        grouped = list(
            col.aggregate(
                [
                    {"$match": match_query},
                    {"$group": {"_id": "${}".format(label_field), "cnt": {"$sum": 1}}},
                ]
            )
        )

        good_cnt = 0.0
        bad_cnt = 0.0
        for g in grouped:
            if g.get("_id") == "利好":
                good_cnt = float(g.get("cnt", 0))
            elif g.get("_id") == "利空":
                bad_cnt = float(g.get("cnt", 0))

        name_doc = col.find_one(sort=[("Date", -1)])
        stock_name = name_doc.get("Name", "") if name_doc else ""

        total = good_cnt + bad_cnt
        sentiment_balance = (good_cnt - bad_cnt) / total if total > 0 else 0.0
        rows.append(
            {
                "stock_code_norm": code_norm,
                "news_stock_name": stock_name,
                "good_cnt": good_cnt,
                "bad_cnt": bad_cnt,
                "total_mentions": total,
                "sentiment_balance": sentiment_balance,
            }
        )

    if not rows:
        return pd.DataFrame(columns=empty_cols)
    return pd.DataFrame(rows, columns=empty_cols)


def classify_news_match(total_mentions: float, sentiment_balance: float) -> str:
    if total_mentions <= 0:
        return "no_match"
    if sentiment_balance > 0.2:
        return "matched_positive"
    if sentiment_balance < -0.2:
        return "matched_negative"
    return "matched_neutral"


def calc_break_days_ago(latest_break_date, as_of_date: dt.date) -> int:
    if latest_break_date in (-1, None, "", "nan"):
        return 9999
    try:
        d = dt.datetime.strptime(str(latest_break_date), "%Y-%m-%d").date()
        days = (as_of_date - d).days
        return max(0, int(days))
    except Exception:
        return 9999


def calc_recency_adjust(break_days_ago: int, max_score: float = 12.0, decay_days: int = 60) -> float:
    # 距今越近分越高：0天=满分，>=decay_days 约等于 0 分
    if break_days_ago >= 9999:
        return 0.0
    if break_days_ago <= 0:
        return max_score
    ratio = max(0.0, 1.0 - break_days_ago / float(decay_days))
    return max_score * ratio


def score_one_stock(
    today_volume_vs_n: float,
    total_mentions: float,
    sentiment_balance: float,
    recency_adjust: float,
) -> Tuple[float, Dict]:
    """
    评分策略（0-100）：
    - 基础分（按匹配结果分层）
      matched_positive: 72
      no_match: 52
      matched_negative: 28
      matched_neutral: 45
    - 新闻项：news_adjust = 15 * sentiment_balance * mention_strength
      mention_strength = min(1, total_mentions / 20)
    - 动量项：momentum_adjust = 6 * (clip(TodayVolumeVsN, 0, 5) - 1)
      TodayVolumeVsN=1 时动量项约为 0，放量越大动量项越高
    - 新鲜度项：recency_adjust，BreakDate 距今天越近分越高（0~12）
    """
    match_type = classify_news_match(total_mentions, sentiment_balance)
    base_score_map = {
        "matched_positive": 72.0,
        "no_match": 52.0,
        "matched_negative": 28.0,
        "matched_neutral": 45.0,
    }
    base_score = base_score_map[match_type]

    mention_strength = min(1.0, max(0.0, total_mentions) / 20.0)
    news_adjust = 15.0 * sentiment_balance * mention_strength if total_mentions > 0 else 0.0

    today_volume_vs_n = 0.0 if pd.isna(today_volume_vs_n) else float(today_volume_vs_n)
    volume_ratio_clip = min(5.0, max(0.0, today_volume_vs_n))
    momentum_adjust = 6.0 * (volume_ratio_clip - 1.0)

    final_score = float(np.clip(base_score + news_adjust + momentum_adjust + recency_adjust, 0.0, 100.0))
    explain = {
        "match_type": match_type,
        "base_score": base_score,
        "news_adjust": news_adjust,
        "momentum_adjust": momentum_adjust,
        "recency_adjust": recency_adjust,
        "mention_strength": mention_strength,
    }
    return final_score, explain


def merge_and_score(massbreak_df: pd.DataFrame, news_df: pd.DataFrame, as_of_date: str = "") -> pd.DataFrame:
    if massbreak_df is None or massbreak_df.empty:
        return pd.DataFrame()

    if news_df is None or news_df.empty:
        news_df = pd.DataFrame(
            columns=[
                "stock_code_norm",
                "news_stock_name",
                "good_cnt",
                "bad_cnt",
                "total_mentions",
                "sentiment_balance",
            ]
        )

    merged = massbreak_df.merge(news_df, how="left", on="stock_code_norm")
    merged["good_cnt"] = merged["good_cnt"].fillna(0.0)
    merged["bad_cnt"] = merged["bad_cnt"].fillna(0.0)
    merged["total_mentions"] = merged["total_mentions"].fillna(0.0)
    merged["sentiment_balance"] = merged["sentiment_balance"].fillna(0.0)
    merged["news_stock_name"] = merged["news_stock_name"].fillna("")
    ref_date = (
        dt.datetime.strptime(as_of_date, "%Y-%m-%d").date()
        if as_of_date
        else dt.date.today()
    )
    merged["break_days_ago"] = merged["LatestBreakDate"].map(lambda x: calc_break_days_ago(x, ref_date))
    merged["recency_adjust"] = merged["break_days_ago"].map(calc_recency_adjust)

    score_list = []
    explain_list = []
    for _, row in merged.iterrows():
        score, explain = score_one_stock(
            today_volume_vs_n=row.get("TodayVolumeVsN", row.get("AvgSignalVolumeRatio", 0.0)),
            total_mentions=row.get("total_mentions", 0.0),
            sentiment_balance=row.get("sentiment_balance", 0.0),
            recency_adjust=row.get("recency_adjust", 0.0),
        )
        score_list.append(score)
        explain_list.append(explain)

    merged["final_score"] = score_list
    merged["match_type"] = [x["match_type"] for x in explain_list]
    merged["base_score"] = [x["base_score"] for x in explain_list]
    merged["news_adjust"] = [x["news_adjust"] for x in explain_list]
    merged["momentum_adjust"] = [x["momentum_adjust"] for x in explain_list]
    merged["recency_adjust"] = [x["recency_adjust"] for x in explain_list]
    merged["mention_strength"] = [x["mention_strength"] for x in explain_list]

    merged = merged.sort_values(
        by=["final_score", "good_cnt", "TodayVolumeVsN"], ascending=False
    ).reset_index(drop=True)
    merged["rank"] = merged.index + 1
    return merged


def build_default_output_path() -> str:
    today = dt.datetime.now().strftime("%Y-%m-%d")
    return f"./mass_break_and_infos_score_{today}.csv"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default="cn", help="市场类型: cn/us/hk")
    parser.add_argument("--start-date", required=True, help="MassBreak 开始日期 YYYY-MM-DD")
    parser.add_argument("--ave-date", type=int, default=30, help="均量窗口天数")
    parser.add_argument("--ratio", type=float, default=2.0, help="放量倍数")
    parser.add_argument("--keep-days", type=int, default=2, help="连续放量天数")
    parser.add_argument(
        "--price-stable-threshold",
        type=float,
        default=0.12,
        help="放量期间 KeepDays 内价格稳定阈值，越小越严格",
    )
    parser.add_argument("--min-break-count", type=int, default=1, help="最小 BreakDateCnt")
    parser.add_argument("--news-start-date", default="", help="新闻统计起始日期 YYYY-MM-DD")
    parser.add_argument("--use-new-label", action="store_true", help="使用 NewLabel 代替 Label 聚合")
    parser.add_argument("--max-stocks", type=int, default=0, help="仅调试用，限制股票池数量")
    parser.add_argument("--output-file", default="", help="最终输出 CSV 路径")
    parser.add_argument("--top-n", type=int, default=50, help="打印前 N 名")
    parser.add_argument("--as-of-date", default="", help="评分参考日期 YYYY-MM-DD，默认当天")
    args = parser.parse_args()

    output_file = args.output_file or build_default_output_path()
    label_field = "NewLabel" if args.use_new_label else "Label"

    print(
        "massbreak params:",
        args.market,
        args.start_date,
        args.ave_date,
        args.ratio,
        args.keep_days,
        args.price_stable_threshold,
    )
    massbreak_candidates = load_massbreak_candidates(
        market=args.market,
        start_date=args.start_date,
        ave_date=args.ave_date,
        ratio=args.ratio,
        keep_days=args.keep_days,
        price_stable_threshold=args.price_stable_threshold,
        min_break_count=args.min_break_count,
        max_stocks=args.max_stocks,
    )
    print("massbreak candidates:", massbreak_candidates.shape)
    if massbreak_candidates.empty:
        print("no candidates found, write empty output and exit")
        massbreak_candidates.to_csv(output_file, index=False)
        sys.exit(0)

    news_df = load_news_good_or_bad(
        candidate_df=massbreak_candidates,
        label_field=label_field,
        news_start_date=args.news_start_date,
    )
    print("news stock records:", news_df.shape)

    final_df = merge_and_score(massbreak_candidates, news_df, as_of_date=args.as_of_date)
    csv_colums = ['code','tradeStatus','code_name','joint_quant_code','market_type','BreakDate','BreakDateCnt','LatestBreakDate',
                  'PriceVar','good_cnt','bad_cnt','mention_strength','final_score','match_type','rank']
    final_df[csv_colums].to_csv(output_file, index=False)

    print("output file:", output_file)
    print("top", args.top_n)
    show_cols = [
        "rank",
        "joint_quant_code" if "joint_quant_code" in final_df.columns else "stock_code_norm",
        "code_name" if "code_name" in final_df.columns else "name",
        "TodayVolumeVsN",
        "break_days_ago",
        "recency_adjust",
        "good_cnt",
        "bad_cnt",
        "match_type",
        "final_score",
    ]
    show_cols = [c for c in show_cols if c in final_df.columns]
    print(final_df[show_cols].head(args.top_n))

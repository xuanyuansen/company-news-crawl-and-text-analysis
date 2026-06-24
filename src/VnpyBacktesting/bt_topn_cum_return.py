from __future__ import annotations

import argparse
from collections import defaultdict
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import akshare as ak
import matplotlib
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from vnpy.trader.constant import Direction, Interval
from vnpy.trader.object import TradeData

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

try:
    import plotly.graph_objects as go
except ModuleNotFoundError:  # pragma: no cover
    go = None

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

try:
    from VnpyBacktesting.PortfolioDailyStockAllocateStrategy import (
        DailyStockAllocateStrategy,
        build_topn_selection_df,
        extract_candidate_symbols,
    )
    from VnpyBacktesting.prepare_data import prepare_symbols
except ModuleNotFoundError:
    from PortfolioDailyStockAllocateStrategy import (
        DailyStockAllocateStrategy,
        build_topn_selection_df,
        extract_candidate_symbols,
    )
    from prepare_data import prepare_symbols

try:
    from vnpy_portfoliostrategy import BacktestingEngine
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ModuleNotFoundError(
        "缺少 vnpy_portfoliostrategy 依赖，无法运行组合策略回测"
    ) from exc


STATS_NAME_MAP = {
    "total_return": "总收益率(%)",
    "annual_return": "年化收益率(%)",
    "max_ddpercent": "最大回撤率(%)",
    "sharpe_ratio": "夏普比率",
    "return_drawdown_ratio": "收益回撤比",
    "win_ratio": "胜率",
    "total_net_pnl": "总净盈亏",
    "end_balance": "期末资金",
}

BENCHMARK_SERIES_META = (
    ("shanghai_cum_return", "沪指收益", "#c55a11", "sh000001"),
    ("shenzhen_cum_return", "深指收益", "#2f8f4e", "sz399001"),
)


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def normalize_timestamp(value: Any) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        # 保留本地日历时间，只去掉时区信息，避免把 00:00+08 误转成前一天 UTC。
        return ts.tz_localize(None)
    return ts


def normalize_date_timestamp(value: Any) -> pd.Timestamp:
    return normalize_timestamp(value).normalize()


def normalize_datetime_index(index: pd.Index) -> pd.DatetimeIndex:
    normalized = pd.DatetimeIndex(pd.to_datetime(index))
    if normalized.tz is not None:
        normalized = normalized.tz_localize(None)
    return normalized


def date_range(start_date: str, end_date: str) -> list[str]:
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date)
    if start_dt > end_dt:
        raise ValueError("start-date 不能晚于 end-date")

    return [dt.strftime("%Y-%m-%d") for dt in pd.date_range(start_dt, end_dt, freq="D")]


def build_strategy_setting(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "selection_start_date": args.selection_start_date,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "market": args.market,
        "ave_date": args.ave_date,
        "ratio": args.ratio,
        "keep_days": args.keep_days,
        "price_stable_threshold": args.price_stable_threshold,
        "min_break_count": args.min_break_count,
        "news_start_date": args.news_start_date,
        "use_new_label": args.use_new_label,
        "max_stocks": args.max_stocks,
        "top_n": args.top_n,
        "min_final_score": args.min_final_score,
        "daily_selection_df": args.daily_selection_df,
        "daily_selection_map": args.daily_selection_map,
        "stop_loss_ratio": args.stop_loss_ratio,
        "take_profit_ratio": args.take_profit_ratio,
        "trailing_activate_ratio": args.trailing_activate_ratio,
        "trailing_stop_ratio": args.trailing_stop_ratio,
        "max_hold_bars": args.max_hold_bars,
        "initial_capital": args.capital,
        "max_per_stock_capital": args.max_per_stock_capital,
        "min_per_stock_capital": args.min_per_stock_capital,
        "rebalance_hour": args.rebalance_hour,
        "rebalance_minute": args.rebalance_minute,
        "price_add": args.price_add,
        "lot_size": args.lot_size,
    }


def build_selection_symbols_for_date(args: argparse.Namespace, signal_date: str) -> list[str]:
    selection_df = build_topn_selection_df(
        market=args.market,
        selection_start_date=args.selection_start_date,
        as_of_date=signal_date,
        ave_date=args.ave_date,
        ratio=args.ratio,
        keep_days=args.keep_days,
        price_stable_threshold=args.price_stable_threshold,
        min_break_count=args.min_break_count,
        news_start_date=args.news_start_date,
        use_new_label=args.use_new_label,
        max_stocks=args.max_stocks,
        top_n=args.top_n,
        min_final_score=args.min_final_score,
    )
    return extract_candidate_symbols(selection_df, market=args.market)


def build_daily_selection_plan(args: argparse.Namespace) -> tuple[dict[str, list[str]], list[str]]:
    daily_selection_map: dict[str, list[str]] = {}
    selected_symbols: list[str] = []
    seen: set[str] = set()

    for current_date in date_range(args.start_date, args.end_date):
        daily_symbols = build_selection_symbols_for_date(args, current_date)
        daily_selection_map[current_date] = daily_symbols
        for vt_symbol in daily_symbols:
            if vt_symbol in seen:
                continue
            seen.add(vt_symbol)
            selected_symbols.append(vt_symbol)

    return daily_selection_map, selected_symbols


def find_latest_nonempty_selection_before_start(args: argparse.Namespace) -> tuple[str, list[str]]:
    start_dt = parse_date(args.start_date)
    selection_start_dt = parse_date(args.selection_start_date)
    if selection_start_dt >= start_dt:
        return "", []

    search_dates = pd.date_range(selection_start_dt, start_dt - pd.Timedelta(days=1), freq="D")
    for signal_dt in reversed(search_dates):
        signal_date = signal_dt.strftime("%Y-%m-%d")
        symbols = build_selection_symbols_for_date(args, signal_date)
        if symbols:
            return signal_date, symbols

    return "", []


def build_daily_selection_df(
    daily_selection_map: dict[str, list[str]],
    trading_dates: list[str] | None = None,
) -> pd.DataFrame:
    columns = ["date", "actual_trade_date", "vt_symbol", "rank"]
    rows: list[dict[str, Any]] = []
    sorted_dates = sorted(daily_selection_map.keys())
    next_trade_date_map: dict[str, str] = {}
    if trading_dates:
        normalized_trade_dates = sorted({pd.Timestamp(date_str).normalize() for date_str in trading_dates})
        for date_str in sorted_dates:
            signal_ts = pd.Timestamp(date_str).normalize()
            next_trade_date = ""
            for trade_ts in normalized_trade_dates:
                if trade_ts > signal_ts:
                    next_trade_date = trade_ts.strftime("%Y-%m-%d")
                    break
            next_trade_date_map[date_str] = next_trade_date
    else:
        next_trade_date_map = {
            date_str: (sorted_dates[i + 1] if i + 1 < len(sorted_dates) else "")
            for i, date_str in enumerate(sorted_dates)
        }

    for date_str in sorted_dates:
        symbols = daily_selection_map.get(date_str, [])
        actual_trade_date = next_trade_date_map.get(date_str, "")
        for rank, vt_symbol in enumerate(symbols, start=1):
            rows.append(
                {
                    "date": date_str,
                    "actual_trade_date": actual_trade_date,
                    "vt_symbol": vt_symbol,
                    "rank": rank,
                }
            )
    return pd.DataFrame(rows, columns=columns)


def build_trade_ledger(trades: list[TradeData], sizes: dict[str, float], rate: float, slippage: float) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()

    trade_rows: list[dict[str, Any]] = []
    symbol_state: dict[str, dict[str, float]] = defaultdict(lambda: {"qty": 0.0, "cost": 0.0})

    sorted_trades = sorted(
        trades,
        key=lambda trade: (
            normalize_timestamp(trade.datetime),
            str(trade.tradeid),
        ),
    )

    for trade in sorted_trades:
        unit_size = float(sizes.get(trade.vt_symbol, 1) or 1)
        trade_qty = float(trade.volume) * unit_size
        turnover = trade_qty * float(trade.price)
        commission = turnover * float(rate)
        slippage_cost = trade_qty * float(slippage)
        side = "buy" if trade.direction == Direction.LONG else "sell"
        trade_date = normalize_date_timestamp(trade.datetime)
        state = symbol_state[trade.vt_symbol]

        realized_pnl = 0.0
        open_qty_before = float(state["qty"])
        cost_before = float(state["cost"])
        avg_cost = cost_before / open_qty_before if open_qty_before > 0 else 0.0

        if side == "buy":
            state["qty"] += trade_qty
            state["cost"] += turnover + commission + slippage_cost
        else:
            closed_qty = min(trade_qty, open_qty_before)
            realized_pnl = turnover - commission - slippage_cost - avg_cost * closed_qty
            state["qty"] = max(open_qty_before - closed_qty, 0.0)
            state["cost"] = max(cost_before - avg_cost * closed_qty, 0.0)

        position_qty_after = float(state["qty"])
        position_shares_after = position_qty_after
        if side == "buy":
            position_shares_after = position_qty_after

        trade_rows.append(
            {
                "trade_datetime": normalize_timestamp(trade.datetime),
                "trade_date": trade_date,
                "vt_symbol": trade.vt_symbol,
                "side": side,
                "direction": trade.direction.value if hasattr(trade.direction, "value") else str(trade.direction),
                "offset": trade.offset.value if hasattr(trade.offset, "value") else str(trade.offset),
                "price": float(trade.price),
                "volume": float(trade.volume),
                "unit_size": unit_size,
                "trade_shares": trade_qty,
                "turnover": turnover,
                "commission": commission,
                "slippage": slippage_cost,
                "realized_pnl": realized_pnl,
                "position_qty_after": position_qty_after,
                "position_shares_after": position_shares_after,
                "open_cost_after": float(state["cost"]),
            }
        )

    trade_df = pd.DataFrame(trade_rows)
    if not trade_df.empty:
        trade_df = trade_df.sort_values(by=["trade_datetime", "vt_symbol"]).reset_index(drop=True)
    return trade_df


def build_trade_equity_curve(
    trade_df: pd.DataFrame,
    close_df: pd.DataFrame,
    start_date: str,
    end_date: str,
    capital: float,
) -> pd.DataFrame:
    if trade_df.empty or close_df.empty:
        return pd.DataFrame()

    all_dates = pd.date_range(parse_date(start_date), parse_date(end_date), freq="D")
    end_ts = normalize_date_timestamp(end_date)
    price_df = close_df.copy()
    price_df.index = normalize_datetime_index(price_df.index).normalize()
    price_df = price_df.reindex(all_dates).ffill().bfill()

    sorted_trades = trade_df.sort_values(by=["trade_datetime", "vt_symbol"]).reset_index(drop=True)
    positions: dict[str, float] = defaultdict(float)
    cash: float = float(capital)
    trade_pos = 0
    daily_rows: list[dict[str, Any]] = []
    prev_equity = float(capital)

    for current_date in all_dates:
        current_ts = pd.Timestamp(current_date).normalize()
        while trade_pos < len(sorted_trades):
            row = sorted_trades.iloc[trade_pos]
            trade_date = normalize_date_timestamp(row["trade_date"])
            if trade_date != current_ts:
                break

            vt_symbol = str(row["vt_symbol"])
            trade_shares = float(row["trade_shares"])
            turnover = float(row["turnover"])
            commission = float(row["commission"])
            slippage_cost = float(row["slippage"])
            if row["side"] == "buy":
                cash -= turnover + commission + slippage_cost
                positions[vt_symbol] += trade_shares
            else:
                cash += turnover - commission - slippage_cost
                positions[vt_symbol] = max(positions[vt_symbol] - trade_shares, 0.0)
            trade_pos += 1

        if current_ts in price_df.index:
            price_row = price_df.loc[current_ts]
        else:
            price_row = pd.Series(dtype=float)

        holdings_value = 0.0
        for vt_symbol, qty in positions.items():
            if qty <= 0:
                continue
            if vt_symbol not in price_row.index or pd.isna(price_row.get(vt_symbol)):
                continue
            holdings_value += float(qty) * float(price_row.get(vt_symbol))

        equity = cash + holdings_value
        daily_rows.append(
            {
                "date": current_ts,
                "cash": cash,
                "holdings_value": holdings_value,
                "equity": equity,
                "daily_pnl": equity - prev_equity,
                "cum_return": equity / float(capital) - 1.0,
            }
        )
        prev_equity = equity

    daily_df = pd.DataFrame(daily_rows).set_index("date")
    return daily_df


def build_symbol_summary(trade_df: pd.DataFrame) -> pd.DataFrame:
    if trade_df.empty:
        return pd.DataFrame()

    summary_df = trade_df.groupby("vt_symbol").agg(
        trade_count=("vt_symbol", "size"),
        buy_count=("side", lambda s: int((s == "buy").sum())),
        sell_count=("side", lambda s: int((s == "sell").sum())),
        total_turnover=("turnover", "sum"),
        total_commission=("commission", "sum"),
        total_slippage=("slippage", "sum"),
        realized_pnl=("realized_pnl", "sum"),
    )
    summary_df["realized_return"] = np.where(
        summary_df["total_turnover"] > 0,
        summary_df["realized_pnl"] / summary_df["total_turnover"],
        0.0,
    )
    return summary_df


def build_return_comparison(active_result_df: pd.DataFrame, trade_equity_df: pd.DataFrame) -> pd.DataFrame:
    if active_result_df.empty or trade_equity_df.empty:
        return pd.DataFrame()

    strategy_df = active_result_df[["strategy_balance", "strategy_cum_return"]].copy()
    strategy_df.index = normalize_datetime_index(strategy_df.index).normalize()

    trade_df = trade_equity_df[["equity", "cum_return"]].copy()
    trade_df.index = normalize_datetime_index(trade_df.index).normalize()

    compare_df = strategy_df.join(
        trade_df.rename(
            columns={
                "equity": "trade_equity",
                "cum_return": "trade_cum_return",
            }
        ),
        how="inner",
    )
    if compare_df.empty:
        return compare_df

    compare_df["balance_gap"] = compare_df["strategy_balance"] - compare_df["trade_equity"]
    compare_df["return_gap"] = compare_df["strategy_cum_return"] - compare_df["trade_cum_return"]
    return compare_df


def build_contract_settings(vt_symbols: list[str], args: argparse.Namespace) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    rates = {vt_symbol: args.rate for vt_symbol in vt_symbols}
    slippages = {vt_symbol: args.slippage for vt_symbol in vt_symbols}
    sizes = {vt_symbol: args.size for vt_symbol in vt_symbols}
    priceticks = {vt_symbol: args.pricetick for vt_symbol in vt_symbols}
    return rates, slippages, sizes, priceticks


def prepare_vnpy_data(vt_symbols: list[str], args: argparse.Namespace) -> dict[str, int]:
    if not vt_symbols:
        return {}

    return prepare_symbols(
        symbols=vt_symbols,
        start=args.selection_start_date,
        end=args.end_date,
        adjust=args.adjust,
        market=args.market,
        clean_before_save=not args.no_clean,
    )


def build_close_panel(history_data: dict, vt_symbols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    symbol_set = set(vt_symbols)

    for (dt, vt_symbol), bar in history_data.items():
        if vt_symbol not in symbol_set:
            continue
        rows.append(
            {
                "datetime": normalize_date_timestamp(dt),
                "vt_symbol": vt_symbol,
                "close_price": float(bar.close_price),
            }
        )

    if not rows:
        return pd.DataFrame()

    close_df = pd.DataFrame(rows).pivot(
        index="datetime",
        columns="vt_symbol",
        values="close_price",
    )
    return close_df.sort_index()


def resolve_benchmark_start_date(selection_df: pd.DataFrame) -> str:
    if selection_df.empty or "actual_trade_date" not in selection_df.columns:
        raise ValueError("selection_df 为空，无法确定基准起始日期")

    actual_trade_dates = selection_df["actual_trade_date"].astype(str)
    actual_trade_dates = actual_trade_dates[(actual_trade_dates != "") & (actual_trade_dates != "nan")]
    if actual_trade_dates.empty:
        raise ValueError("selection_df 中没有可用的 actual_trade_date，无法确定基准起始日期")

    return pd.to_datetime(actual_trade_dates).min().strftime("%Y-%m-%d")


def build_index_benchmark_curve(start_date: str, end_date: str) -> pd.DataFrame:
    start_ts = normalize_timestamp(parse_date(start_date))
    end_ts = normalize_timestamp(parse_date(end_date))
    benchmark_frames: list[pd.DataFrame] = []

    for column_name, _label, _color, ak_symbol in BENCHMARK_SERIES_META:
        raw_df = ak.stock_zh_index_daily(symbol=ak_symbol)
        if raw_df is None or raw_df.empty:
            raise ValueError(f"{ak_symbol} 无可用指数日线数据")

        index_df = raw_df.copy()
        index_df["date"] = pd.to_datetime(index_df["date"]).dt.normalize()
        index_df = index_df.loc[(index_df["date"] >= start_ts) & (index_df["date"] <= end_ts)].copy()
        if index_df.empty:
            raise ValueError(f"{ak_symbol} 在 {start_date} ~ {end_date} 区间无可用指数数据")

        entry_open = float(index_df.iloc[0]["open"])
        if entry_open <= 0:
            raise ValueError(f"{ak_symbol} 起始开盘价异常: {entry_open}")

        index_df[column_name] = index_df["close"].astype(float) / entry_open - 1.0
        benchmark_frames.append(index_df.set_index("date")[[column_name]])

    benchmark_df = benchmark_frames[0]
    for frame in benchmark_frames[1:]:
        benchmark_df = benchmark_df.join(frame, how="outer")

    benchmark_df.index = normalize_datetime_index(benchmark_df.index)
    return benchmark_df.sort_index()


def extract_active_result(result_df: pd.DataFrame, start_date: str, end_date: str, capital: float) -> pd.DataFrame:
    if result_df.empty:
        return result_df

    active_df = result_df.copy()
    active_df.index = normalize_datetime_index(active_df.index)
    start_ts = normalize_timestamp(parse_date(start_date))
    end_ts = normalize_timestamp(parse_date(end_date))
    active_df = active_df.loc[(active_df.index >= start_ts) & (active_df.index <= end_ts)].copy()
    if active_df.empty:
        return active_df

    if "net_pnl" not in active_df.columns:
        raise KeyError("result_df 缺少 net_pnl 列，无法计算累计收益")

    active_df["strategy_balance"] = active_df["net_pnl"].astype(float).cumsum() + float(capital)

    blowup_mask = active_df["strategy_balance"] <= 0
    if blowup_mask.any():
        blowup_dt = active_df.index[blowup_mask.to_numpy().nonzero()[0][0]]
        print(f"警告: 策略净值在 {blowup_dt.strftime('%Y-%m-%d')} 首次小于等于 0，已截断该日期及之后的数据")
        active_df = active_df.loc[active_df["strategy_balance"] > 0].copy()

    if active_df.empty:
        return active_df

    active_df["strategy_cum_return"] = active_df["strategy_balance"] / float(capital) - 1.0
    return active_df


def calculate_safe_statistics(df: pd.DataFrame, capital: float, annual_days: int = 240, risk_free: float = 0.0) -> dict[str, Any]:
    if df.empty:
        return {}

    stats_df = df.copy()
    stats_df["balance"] = stats_df["net_pnl"].cumsum() + float(capital)
    return_ratio = stats_df["balance"] / stats_df["balance"].shift(1)
    stats_df["return"] = np.where(return_ratio > 0, np.log(return_ratio), 0.0)
    stats_df["highlevel"] = stats_df["balance"].rolling(min_periods=1, window=len(stats_df), center=False).max()
    stats_df["drawdown"] = stats_df["balance"] - stats_df["highlevel"]
    stats_df["ddpercent"] = stats_df["drawdown"] / stats_df["highlevel"] * 100

    start_date = stats_df.index[0]
    end_date = stats_df.index[-1]
    total_days = len(stats_df)
    profit_days = len(stats_df[stats_df["net_pnl"] > 0])
    loss_days = len(stats_df[stats_df["net_pnl"] < 0])

    end_balance = float(stats_df["balance"].iloc[-1])
    max_drawdown = float(stats_df["drawdown"].min())
    max_ddpercent = float(stats_df["ddpercent"].min())
    max_drawdown_end = stats_df["drawdown"].idxmin()

    if max_drawdown < 0 and isinstance(max_drawdown_end, pd.Timestamp):
        max_drawdown_start = stats_df["balance"][:max_drawdown_end].idxmax()
        max_drawdown_duration = (max_drawdown_end - max_drawdown_start).days
    else:
        max_drawdown_duration = 0

    total_net_pnl = float(stats_df["net_pnl"].sum())
    daily_net_pnl = total_net_pnl / total_days
    total_commission = float(stats_df["commission"].sum())
    daily_commission = total_commission / total_days
    total_slippage = float(stats_df["slippage"].sum())
    daily_slippage = total_slippage / total_days
    total_turnover = float(stats_df["turnover"].sum())
    daily_turnover = total_turnover / total_days
    total_trade_count = int(stats_df["trade_count"].sum())
    daily_trade_count = total_trade_count / total_days

    total_return = (end_balance / float(capital) - 1.0) * 100
    annual_return = total_return / total_days * annual_days
    daily_return = float(np.nanmean(stats_df["return"])) * 100
    return_std = float(pd.Series(stats_df["return"]).std()) * 100

    if np.isfinite(return_std) and return_std != 0:
        daily_risk_free = risk_free / (annual_days ** 0.5)
        sharpe_ratio = (daily_return - daily_risk_free) / return_std * (annual_days ** 0.5)
    else:
        sharpe_ratio = 0.0

    return_drawdown_ratio = 0.0 if max_drawdown == 0 else -total_net_pnl / max_drawdown

    statistics: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
        "total_days": total_days,
        "profit_days": profit_days,
        "loss_days": loss_days,
        "capital": float(capital),
        "end_balance": end_balance,
        "max_drawdown": max_drawdown,
        "max_ddpercent": max_ddpercent,
        "max_drawdown_duration": max_drawdown_duration,
        "total_net_pnl": total_net_pnl,
        "daily_net_pnl": daily_net_pnl,
        "total_commission": total_commission,
        "daily_commission": daily_commission,
        "total_slippage": total_slippage,
        "daily_slippage": daily_slippage,
        "total_turnover": total_turnover,
        "daily_turnover": daily_turnover,
        "total_trade_count": total_trade_count,
        "daily_trade_count": daily_trade_count,
        "total_return": total_return,
        "annual_return": annual_return,
        "daily_return": daily_return,
        "return_std": return_std,
        "sharpe_ratio": sharpe_ratio,
        "return_drawdown_ratio": return_drawdown_ratio,
    }

    numeric_keys = {
        "total_days",
        "profit_days",
        "loss_days",
        "capital",
        "end_balance",
        "max_drawdown",
        "max_ddpercent",
        "max_drawdown_duration",
        "total_net_pnl",
        "daily_net_pnl",
        "total_commission",
        "daily_commission",
        "total_slippage",
        "daily_slippage",
        "total_turnover",
        "daily_turnover",
        "total_trade_count",
        "daily_trade_count",
        "total_return",
        "annual_return",
        "daily_return",
        "return_std",
        "sharpe_ratio",
        "return_drawdown_ratio",
    }
    int_keys = {"total_days", "profit_days", "loss_days", "max_drawdown_duration", "total_trade_count"}
    for key in numeric_keys:
        value = statistics[key]
        if isinstance(value, (int, float)) and not np.isfinite(value):
            value = 0
        cleaned_value = np.nan_to_num(value)
        statistics[key] = int(cleaned_value) if key in int_keys else float(cleaned_value)

    return statistics


def save_cumulative_chart_png(curve_df: pd.DataFrame, chart_file: Path) -> None:
    chart_file.parent.mkdir(parents=True, exist_ok=True)
    if curve_df.empty:
        raise ValueError("curve_df 为空，无法绘图")

    fig, ax = plt.subplots(figsize=(16, 7))

    x = pd.to_datetime(curve_df.index)
    strategy = curve_df["strategy_cum_return"].astype(float)

    ax.plot(x, strategy, color="#4d76c9", linewidth=2.6, label="策略收益")
    ax.fill_between(x, strategy, 0, color="#4d76c9", alpha=0.16)

    for column_name, label, color, _ak_symbol in BENCHMARK_SERIES_META:
        if column_name not in curve_df.columns:
            continue
        series = curve_df[column_name].astype(float)
        ax.plot(x, series, color=color, linewidth=2.0, label=label)

    ax.axhline(0, color="#222222", linewidth=1.0)

    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.set_ylabel("累计收益", rotation=270, labelpad=18)
    ax.grid(alpha=0.28, linestyle="--")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc="upper left", frameon=False)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y-%m-%d"))
    fig.autofmt_xdate(rotation=0)

    last_dt = x[-1]
    last_strategy = float(strategy.iloc[-1])
    ax.scatter([last_dt], [last_strategy], color="#4d76c9", s=36, zorder=5)
    ax.annotate(
        f"策略收益: {last_strategy:.2%}",
        xy=(last_dt, last_strategy),
        xytext=(18, 18),
        textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#9bb0d1", alpha=0.95),
        fontsize=11,
    )

    fig.tight_layout()
    fig.savefig(chart_file, dpi=180, bbox_inches="tight")
    plt.close(fig)


def save_cumulative_chart_html(curve_df: pd.DataFrame, html_file: Path) -> None:
    if go is None:
        return

    html_file.parent.mkdir(parents=True, exist_ok=True)
    if curve_df.empty:
        raise ValueError("curve_df 为空，无法绘图")

    x = pd.to_datetime(curve_df.index)
    strategy = curve_df["strategy_cum_return"].astype(float)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=strategy,
            mode="lines",
            name="策略收益",
            line=dict(color="#4d76c9", width=3),
            fill="tozeroy",
            fillcolor="rgba(77, 118, 201, 0.16)",
            hovertemplate="%{x|%Y-%m-%d}<br>策略收益: %{y:.2%}<extra></extra>",
        )
    )

    for column_name, label, color, _ak_symbol in BENCHMARK_SERIES_META:
        if column_name not in curve_df.columns:
            continue
        series = curve_df[column_name].astype(float)
        fig.add_trace(
            go.Scatter(
                x=x,
                y=series,
                mode="lines",
                name=label,
                line=dict(color=color, width=2.5),
                hovertemplate=f"%{{x|%Y-%m-%d}}<br>{label}: %{{y:.2%}}<extra></extra>",
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=720,
        width=1400,
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01),
        yaxis=dict(
            title="累计收益",
            tickformat=".0%",
            side="right",
            showgrid=True,
            zeroline=True,
        ),
        xaxis=dict(
            rangeslider=dict(visible=True),
            showgrid=True,
        ),
    )
    fig.write_html(str(html_file), include_plotlyjs=True)


def run_portfolio_backtest(
    args: argparse.Namespace,
    vt_symbols: list[str],
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    engine = BacktestingEngine()
    rates, slippages, sizes, priceticks = build_contract_settings(vt_symbols, args)

    engine.set_parameters(
        vt_symbols=vt_symbols,
        interval=Interval.DAILY,
        start=parse_date(args.selection_start_date),
        end=parse_date(args.end_date),
        rates=rates,
        slippages=slippages,
        sizes=sizes,
        priceticks=priceticks,
        capital=float(args.capital),
    )

    strategy_setting = build_strategy_setting(args)
    engine.add_strategy(DailyStockAllocateStrategy, strategy_setting)
    engine.load_data()
    print(f"调试: engine.history_data 条数={len(engine.history_data)}")

    if not engine.history_data:
        engine.clear_data()
        empty_df = pd.DataFrame()
        return empty_df, {"错误信息": "no_history_data"}, empty_df, empty_df, empty_df, empty_df, []

    close_df = build_close_panel(engine.history_data, vt_symbols)
    trading_dates = [pd.Timestamp(dt).normalize().strftime("%Y-%m-%d") for dt in close_df.index]

    engine.run_backtesting()
    raw_result_df = engine.calculate_result()
    if raw_result_df is None or raw_result_df.empty:
        engine.clear_data()
        empty_df = pd.DataFrame()
        return empty_df, {"错误信息": "empty_result"}, empty_df, empty_df, empty_df, empty_df, trading_dates

    active_result_df = extract_active_result(
        raw_result_df,
        start_date=args.start_date,
        end_date=args.end_date,
        capital=float(args.capital),
    )
    print(f"调试: raw_result_df {raw_result_df}")
    print(f"调试: active_result_df {active_result_df}")
    print(
        f"调试: raw_result_df 条数={0 if raw_result_df is None else len(raw_result_df)}, "
        f"active_result_df 条数={len(active_result_df)}"
    )
    if active_result_df.empty:
        engine.clear_data()
        empty_df = pd.DataFrame()
        return empty_df, {"错误信息": "empty_active_result"}, empty_df, empty_df, empty_df, empty_df, trading_dates

    stats = calculate_safe_statistics(
        df=active_result_df.copy(),
        capital=float(args.capital),
    )
    trades = list(engine.get_all_trades())
    trade_df = build_trade_ledger(trades, sizes, args.rate, args.slippage)
    trade_equity_df = build_trade_equity_curve(
        trade_df=trade_df,
        close_df=close_df,
        start_date=args.start_date,
        end_date=args.end_date,
        capital=float(args.capital),
    )
    symbol_summary_df = build_symbol_summary(trade_df)
    comparison_df = build_return_comparison(active_result_df, trade_equity_df)
    engine.clear_data()
    return active_result_df, stats, trade_df, trade_equity_df, symbol_summary_df, comparison_df, trading_dates


def build_output_paths(output_path: Path, chart_file: str, html_file: str) -> dict[str, Path]:
    base_dir = output_path.parent
    stem = output_path.stem
    return {
        "selection_csv": base_dir / f"{stem}_selection_records.csv",
        "trade_ledger_csv": base_dir / f"{stem}_trade_ledger.csv",
        "symbol_summary_csv": base_dir / f"{stem}_symbol_summary.csv",
        "trade_equity_csv": base_dir / f"{stem}_trade_equity_curve.csv",
        "comparison_csv": base_dir / f"{stem}_return_comparison.csv",
        "chart_path": Path(chart_file) if chart_file else Path.cwd() / "charts" / f"bt_topn_cum_return_{stem}.png",
        "html_path": Path(html_file) if html_file else (Path(chart_file) if chart_file else Path.cwd() / "charts" / f"bt_topn_cum_return_{stem}.png").with_suffix(".html"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="vnpy 组合策略回测（TopN 累计收益）")

    parser.add_argument("--selection-start-date", default="2024-01-01", help="选股数据开始日期 YYYY-MM-DD")
    parser.add_argument(
        "--start-date",
        default="2024-01-01",
        help="组合开始买入日期 YYYY-MM-DD；当日按当日信号发单，下一根 bar 撮合成交",
    )
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"), help="收益统计截止日期 YYYY-MM-DD")

    parser.add_argument("--market", default="cn", help="市场类型: cn/us/hk")
    parser.add_argument("--ave-date", type=int, default=10, help="均量窗口天数")
    parser.add_argument("--ratio", type=float, default=1.5, help="放量倍数")
    parser.add_argument("--keep-days", type=int, default=3, help="连续放量天数")
    parser.add_argument("--price-stable-threshold", type=float, default=0.05, help="KeepDays 内价格稳定阈值")
    parser.add_argument("--min-break-count", type=int, default=1, help="最小 BreakDateCnt")
    parser.add_argument("--news-start-date", default="", help="新闻统计起始日期 YYYY-MM-DD")
    parser.add_argument("--use-new-label", action="store_true", help="使用 NewLabel 代替 Label 聚合")
    parser.add_argument("--max-stocks", type=int, default=0, help="仅调试用，限制股票池数量")
    parser.add_argument("--top-n", type=int, default=20, help="每日选股前 N 名")
    parser.add_argument("--min-final-score", type=float, default=0.0, help="仅保留 final_score 严格大于该阈值的股票")

    parser.add_argument("--capital", type=float, default=1_000_000)
    parser.add_argument(
        "--max-per-stock-capital",
        "--max_per_stock_capital",
        dest="max_per_stock_capital",
        type=float,
        default=100_000,
    )
    parser.add_argument(
        "--min-per-stock-capital",
        "--min_per_stock_capital",
        dest="min_per_stock_capital",
        type=float,
        default=10_000,
    )
    parser.add_argument("--rebalance-hour", type=int, default=9)
    parser.add_argument("--rebalance-minute", type=int, default=35)
    parser.add_argument("--price-add", type=float, default=0.01)
    parser.add_argument("--lot-size", type=int, default=1)
    parser.add_argument("--stop-loss-ratio", "--stop_loss_ratio", dest="stop_loss_ratio", type=float, default=0.03)
    parser.add_argument("--take-profit-ratio", "--take_profit_ratio", dest="take_profit_ratio", type=float, default=0.10)
    parser.add_argument(
        "--trailing-activate-ratio",
        "--trailing_activate_ratio",
        dest="trailing_activate_ratio",
        type=float,
        default=0.06,
    )
    parser.add_argument(
        "--trailing-stop-ratio",
        "--trailing_stop_ratio",
        dest="trailing_stop_ratio",
        type=float,
        default=0.03,
    )
    parser.add_argument(
        "--max-hold-bars",
        "--max-hold-days",
        dest="max_hold_bars",
        type=int,
        default=10,
    )
    parser.add_argument("--rate", type=float, default=2.5 / 10000)
    parser.add_argument("--slippage", type=float, default=0.01)
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--pricetick", type=float, default=0.01)

    parser.add_argument("--skip-prepare", action="store_true", help="跳过数据准备")
    parser.add_argument("--no-clean", action="store_true", help="准备数据时不清理旧数据")
    parser.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"], help="akshare 复权类型")

    parser.add_argument("--output-csv", default="", help="累计收益结果 CSV")
    parser.add_argument("--chart-file", default="", help="累计收益图 PNG 输出路径")
    parser.add_argument("--html-file", default="", help="累计收益图 HTML 输出路径")
    return parser


def validate_args(args: argparse.Namespace) -> None:
    selection_start = parse_date(args.selection_start_date)
    start_dt = parse_date(args.start_date)
    end_dt = parse_date(args.end_date)

    if selection_start > start_dt:
        raise ValueError("selection-start-date 不能晚于 start-date")
    if start_dt > end_dt:
        raise ValueError("start-date 不能晚于 end-date")


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)

    daily_selection_map, vt_symbols = build_daily_selection_plan(args)

    args.daily_selection_df = build_daily_selection_df(daily_selection_map)
    args.daily_selection_map = daily_selection_map
    print(f"调试: 每日候选行数={0 if args.daily_selection_df is None else len(args.daily_selection_df)}")

    output_path = args.output_csv or str(
        Path.cwd() / f"bt_topn_cum_return_{datetime.now().strftime('%Y%m%d')}.csv"
    )
    output_path_obj = Path(output_path)
    artifact_paths = build_output_paths(output_path_obj, args.chart_file, args.html_file)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    artifact_paths["selection_csv"].parent.mkdir(parents=True, exist_ok=True)
    artifact_paths["chart_path"].parent.mkdir(parents=True, exist_ok=True)

    if not vt_symbols:
        print("选股结果为空，退出")
        selection_df = args.daily_selection_df.copy() if isinstance(args.daily_selection_df, pd.DataFrame) else pd.DataFrame()
        selection_df.to_csv(artifact_paths["selection_csv"], index=False)
        # pd.DataFrame().to_csv(output_path_obj, index=False)
        pd.DataFrame().to_csv(artifact_paths["trade_ledger_csv"], index=False)
        # pd.DataFrame().to_csv(artifact_paths["symbol_summary_csv"], index=False)
        pd.DataFrame().to_csv(artifact_paths["trade_equity_csv"], index=False)
        pd.DataFrame().to_csv(artifact_paths["comparison_csv"], index=False)
        return

    print(f"选股区间: {args.selection_start_date} -> {args.end_date}")
    print(f"策略买入区间: {args.start_date} -> {args.end_date}")
    print("执行规则: 当日使用当日选股结果发单，下一根 bar 撮合成交")
    print(f"股票数量: {len(vt_symbols)}")
    print(f"股票列表: {vt_symbols}")
    print(f"调试: 导入的 vt_symbol 数={len(vt_symbols)}")

    if not args.skip_prepare:
        prepared = prepare_vnpy_data(vt_symbols, args)
        print("数据准备结果:")
        for vt_symbol, count in prepared.items():
            print(vt_symbol, count)

    active_result_df, stats, trade_df, trade_equity_df, symbol_summary_df, comparison_df, trading_dates = run_portfolio_backtest(args, vt_symbols)

    selection_df = build_daily_selection_df(daily_selection_map, trading_dates=trading_dates)
    selection_df.to_csv(artifact_paths["selection_csv"], index=False)
    trade_df.to_csv(artifact_paths["trade_ledger_csv"], index=False)
    symbol_summary_df.reset_index().to_csv(artifact_paths["symbol_summary_csv"], index=False)
    trade_equity_df.reset_index().to_csv(artifact_paths["trade_equity_csv"], index=False)
    comparison_df.reset_index().to_csv(artifact_paths["comparison_csv"], index=False)

    if active_result_df.empty:
        print("回测结果为空，已输出空记录文件")
        pd.DataFrame().to_csv(output_path_obj, index=False)
        return

    curve_df = active_result_df[["strategy_balance", "strategy_cum_return"]].copy()
    benchmark_start_date = resolve_benchmark_start_date(selection_df)
    benchmark_df = build_index_benchmark_curve(benchmark_start_date, args.end_date)
    chart_df = curve_df.join(benchmark_df, how="left")

    result_df = curve_df.reset_index().rename(columns={"index": "date"})
    result_df.to_csv(output_path_obj, index=False)

    if not chart_df.empty:
        save_cumulative_chart_png(curve_df=chart_df, chart_file=artifact_paths["chart_path"])
        try:
            save_cumulative_chart_html(curve_df=chart_df, html_file=artifact_paths["html_path"])
        except Exception as exc:
            print(f"HTML 图表生成失败: {exc}")

    comparison_df = comparison_df.copy()
    if not comparison_df.empty:
        final_compare = comparison_df.iloc[-1]
        print(
            "对账: "
            f"策略期末资金={final_compare['strategy_balance']:.2f}, "
            f"重放期末资金={final_compare['trade_equity']:.2f}, "
            f"资金差={final_compare['balance_gap']:.2f}, "
            f"策略累计收益={final_compare['strategy_cum_return']:.4%}, "
            f"重放累计收益={final_compare['trade_cum_return']:.4%}, "
            f"收益差={final_compare['return_gap']:.4%}"
        )

    print(f"输出CSV: {output_path_obj}")
    print(f"输出选股记录: {artifact_paths['selection_csv']}")
    print(f"输出成交台账: {artifact_paths['trade_ledger_csv']}")
    print(f"输出个股汇总: {artifact_paths['symbol_summary_csv']}")
    print(f"输出重放权益: {artifact_paths['trade_equity_csv']}")
    print(f"输出收益对账: {artifact_paths['comparison_csv']}")
    print(f"输出PNG: {artifact_paths['chart_path']}")
    print(f"输出HTML: {artifact_paths['html_path']}")
    print(pd.DataFrame([stats]).to_string(index=False))
    print(result_df.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()

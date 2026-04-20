from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd
from vnpy.trader.constant import Direction, Interval
from vnpy.trader.object import BarData, TradeData
from vnpy_portfoliostrategy import StrategyTemplate

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent

try:
    import sys

    if str(SRC_DIR) not in sys.path:
        sys.path.append(str(SRC_DIR))
except Exception:
    pass

try:
    from VnpyBacktesting.prepare_data import load_massbreak_symbols
except ModuleNotFoundError:
    from prepare_data import load_massbreak_symbols

try:
    from MassBreak.MassBreakAndInfosAlphaGo import (
        load_massbreak_candidates,
        load_news_good_or_bad,
        merge_and_score,
    )
except ModuleNotFoundError:
    from MassBreakAndInfosAlphaGo import (
        load_massbreak_candidates,
        load_news_good_or_bad,
        merge_and_score,
    )


def build_topn_selection_df(
    market: str,
    selection_start_date: str,
    as_of_date: str,
    ave_date: int,
    ratio: float,
    keep_days: int,
    price_stable_threshold: float,
    min_break_count: int,
    news_start_date: str,
    use_new_label: bool,
    max_stocks: int,
    top_n: int,
    min_final_score: float,
) -> pd.DataFrame:
    candidate_df = load_massbreak_candidates(
        market=market,
        start_date=selection_start_date,
        ave_date=ave_date,
        ratio=ratio,
        keep_days=keep_days,
        price_stable_threshold=price_stable_threshold,
        min_break_count=min_break_count,
        max_stocks=max_stocks,
        end_date=as_of_date,
    )
    if candidate_df.empty:
        return candidate_df

    label_field = "NewLabel" if use_new_label else "Label"
    news_df = load_news_good_or_bad(
        candidate_df=candidate_df,
        label_field=label_field,
        news_start_date=news_start_date,
        news_end_date=as_of_date,
    )
    final_df = merge_and_score(candidate_df, news_df, as_of_date=as_of_date)
    if final_df.empty:
        return final_df

    final_scores = pd.to_numeric(final_df["final_score"], errors="coerce")
    filtered_df = final_df[
        (final_df["LatestBreakDate"].astype(str) == as_of_date)
        & (final_scores > min_final_score)
    ].copy()
    if filtered_df.empty:
        return filtered_df

    filtered_df = filtered_df.sort_values(
        by=["final_score", "good_cnt", "TodayVolumeVsN"],
        ascending=False,
    ).reset_index(drop=True)
    filtered_df["rank"] = filtered_df.index + 1
    return filtered_df.head(top_n).copy()


def extract_candidate_symbols(selection_df: pd.DataFrame, market: str) -> List[str]:
    if selection_df is None or selection_df.empty:
        return []

    selected: List[str] = []
    seen: Set[str] = set()
    for _, row in selection_df.iterrows():
        joint_code = str(row.get("joint_quant_code", "") or row.get("code", "")).strip()
        if not joint_code:
            continue

        vt_symbols = load_massbreak_symbols([joint_code], market=market)
        if not vt_symbols:
            continue

        vt_symbol = vt_symbols[0]
        if vt_symbol in seen:
            continue

        seen.add(vt_symbol)
        selected.append(vt_symbol)

    return selected


def normalize_daily_selection_map(raw_map: Dict[str, List[str]] | None) -> Dict[str, List[str]]:
    if not raw_map:
        return {}

    normalized: Dict[str, List[str]] = {}
    for date_str, symbols in raw_map.items():
        if not date_str:
            continue

        unique_symbols: List[str] = []
        seen: Set[str] = set()
        for vt_symbol in symbols or []:
            vt_symbol_str = str(vt_symbol).strip()
            if not vt_symbol_str or vt_symbol_str in seen:
                continue
            seen.add(vt_symbol_str)
            unique_symbols.append(vt_symbol_str)

        normalized[str(date_str)] = unique_symbols

    return normalized


def _normalize_date_key(value: object) -> str:
    if value is None:
        return ""

    ts = pd.Timestamp(value)
    if pd.isna(ts):
        return ""
    return ts.strftime("%Y-%m-%d")


def _resolve_vt_symbol_from_value(raw_value: object, market: str) -> str:
    value = str(raw_value or "").strip()
    if not value:
        return ""

    if "." in value:
        return value.upper()

    vt_symbols = load_massbreak_symbols([value], market=market)
    return vt_symbols[0] if vt_symbols else ""


def build_daily_selection_map_from_df(selection_df: pd.DataFrame | None, market: str) -> Dict[str, List[str]]:
    if selection_df is None or selection_df.empty:
        return {}

    date_columns = ["date", "datetime", "trade_date", "LatestBreakDate", "as_of_date"]
    symbol_columns = ["vt_symbol", "symbol", "joint_quant_code", "code"]

    date_col = next((col for col in date_columns if col in selection_df.columns), "")
    symbol_col = next((col for col in symbol_columns if col in selection_df.columns), "")
    if not date_col or not symbol_col:
        return {}

    sorted_df = selection_df.copy()
    if "rank" in sorted_df.columns:
        sorted_df = sorted_df.sort_values(by=[date_col, "rank"])
    else:
        sorted_df = sorted_df.sort_values(by=[date_col])

    daily_selection_map: Dict[str, List[str]] = {}
    for _, row in sorted_df.iterrows():
        date_key = _normalize_date_key(row.get(date_col))
        vt_symbol = _resolve_vt_symbol_from_value(row.get(symbol_col), market=market)
        if not date_key or not vt_symbol:
            continue

        if date_key not in daily_selection_map:
            daily_selection_map[date_key] = []

        if vt_symbol not in daily_selection_map[date_key]:
            daily_selection_map[date_key].append(vt_symbol)

    return daily_selection_map


class DailyStockAllocateStrategy(StrategyTemplate):
    """基于 MassBreak TopN 的日频组合调仓策略。"""

    author: str = "OpenAI"

    # ===== 策略区间与选股参数 =====
    selection_start_date: str = "2024-01-01"
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    market: str = "cn"
    ave_date: int = 10
    ratio: float = 1.5
    keep_days: int = 3
    price_stable_threshold: float = 0.05
    min_break_count: int = 1
    news_start_date: str = ""
    use_new_label: bool = False
    max_stocks: int = 0
    top_n: int = 20
    min_final_score: float = 0.0
    daily_selection_df: pd.DataFrame | None = None
    daily_selection_map: Dict[str, List[str]] = {}
    stop_loss_ratio: float = 0.03
    take_profit_ratio: float = 0.10
    trailing_activate_ratio: float = 0.06
    trailing_stop_ratio: float = 0.03
    max_hold_bars: int = 5

    # ===== 资金与下单参数 =====
    initial_capital: float = 1_000_000
    max_per_stock_capital: float = 100_000
    min_per_stock_capital: float = 10_000

    rebalance_hour: int = 9
    rebalance_minute: int = 35

    price_add: float = 0.01
    lot_size: int = 1

    parameters: List[str] = [
        "selection_start_date",
        "start_date",
        "end_date",
        "market",
        "ave_date",
        "ratio",
        "keep_days",
        "price_stable_threshold",
        "min_break_count",
        "news_start_date",
        "use_new_label",
        "max_stocks",
        "top_n",
        "min_final_score",
        "daily_selection_df",
        "daily_selection_map",
        "stop_loss_ratio",
        "take_profit_ratio",
        "trailing_activate_ratio",
        "trailing_stop_ratio",
        "max_hold_bars",
        "initial_capital",
        "max_per_stock_capital",
        "min_per_stock_capital",
        "rebalance_hour",
        "rebalance_minute",
        "price_add",
        "lot_size",
    ]
    variables: List[str] = [
        "current_total_capital",
        "available_cash",
        "last_rebalance_date",
        "inited_capital",
        "entry_price_map",
        "highest_price_map",
        "holding_bars_map",
        "exit_reason_map",
        "buy_price_map",
    ]

    def __init__(self, strategy_engine, strategy_name: str, vt_symbols: List[str], setting: dict):
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)

        self.current_total_capital: float = float(self.initial_capital)
        self.available_cash: float = float(self.initial_capital)
        self.last_rebalance_date: str = ""
        self.inited_capital: bool = False

        self.entry_price_map: Dict[str, float] = {}
        self.entry_trade_date_map: Dict[str, str] = {}
        self.highest_price_map: Dict[str, float] = {}
        self.holding_bars_map: Dict[str, int] = {}
        self.exit_reason_map: Dict[str, str] = {}
        self.buy_price_map: Dict[str, float] = {}
        self.stop_loss_price_map: Dict[str, float] = {}
        self.take_profit_price_map: Dict[str, float] = {}
        self.today_exited_symbols: Set[str] = set()
        raw_selection_df = getattr(self, "daily_selection_df", None)
        if isinstance(raw_selection_df, pd.DataFrame) and not raw_selection_df.empty:
            self.daily_selection_map = build_daily_selection_map_from_df(raw_selection_df, self.market)
        else:
            self.daily_selection_map = normalize_daily_selection_map(getattr(self, "daily_selection_map", None))

        self.last_bars: Dict[str, BarData] = {}
        self.today_candidates: List[str] = []

    def on_init(self) -> None:
        self.write_log("策略初始化")
        self.load_bars(10)

    def on_start(self) -> None:
        self.write_log("策略启动")

        if not self.inited_capital:
            engine_capital = float(getattr(self.strategy_engine, "capital", 0) or 0)
            seed_capital = engine_capital if engine_capital > 0 else float(self.initial_capital)
            self.current_total_capital = seed_capital
            self.available_cash = seed_capital
            self.inited_capital = True

    def on_stop(self) -> None:
        self.write_log("策略停止")

    def on_bars(self, bars: Dict[str, BarData]) -> None:
        self.last_bars.update(bars)

        any_bar = next(iter(bars.values()), None)
        if not any_bar:
            return

        dt: datetime = any_bar.datetime
        current_date_str: str = dt.strftime("%Y-%m-%d")

        if current_date_str > self.end_date:
            return

        if not self._is_rebalance_time(any_bar):
            return

        if self.last_rebalance_date == current_date_str:
            return

        self.last_rebalance_date = current_date_str

        if current_date_str < self.start_date:
            self.put_event()
            return

        self.today_exited_symbols.clear()
        self._handle_exit_signals(bars)
        self._execute_intraday_exits(bars)
        self._mark_to_market_capital()

        self.today_candidates = self.get_today_candidates(current_date_str)
        self.write_log(f"{current_date_str} 使用当日信号，候选数={len(self.today_candidates)}")
        self._allocate_today_targets(bars, self.today_candidates)

        self.rebalance_portfolio(bars)
        self.put_event()

    def get_today_candidates(self, signal_date: str) -> List[str]:
        if not signal_date:
            return []

        selected = list(self.daily_selection_map.get(signal_date, []))
        if self.vt_symbols:
            selected = [vt_symbol for vt_symbol in selected if vt_symbol in self.vt_symbols]
        return selected

    def should_exit(self, vt_symbol: str, bar: BarData) -> bool:
        entry_price = float(self.entry_price_map.get(vt_symbol, 0.0) or 0.0)
        current_date_str = pd.Timestamp(bar.datetime).normalize().strftime("%Y-%m-%d")
        entry_trade_date = self.entry_trade_date_map.get(vt_symbol, "")
        if entry_trade_date and current_date_str <= entry_trade_date:
            return False

        if entry_price <= 0:
            self.entry_price_map[vt_symbol] = float(bar.close_price)
            self.highest_price_map[vt_symbol] = float(bar.close_price)
            self.holding_bars_map[vt_symbol] = 0
            self.exit_reason_map.pop(vt_symbol, None)
            return False

        highest_price = max(
            float(self.highest_price_map.get(vt_symbol, entry_price) or entry_price),
            float(bar.high_price),
            float(bar.close_price),
        )
        self.highest_price_map[vt_symbol] = highest_price
        self.holding_bars_map[vt_symbol] = int(self.holding_bars_map.get(vt_symbol, 0)) + 1

        if self._check_fixed_stop_loss(bar, entry_price):
            self.exit_reason_map[vt_symbol] = "fixed_stop_loss"
            stop_loss_price = float(entry_price) * (1 - float(self.stop_loss_ratio))
            if float(bar.open_price) <= stop_loss_price:
                fill_price = float(bar.open_price)
            else:
                fill_price = stop_loss_price
            self.stop_loss_price_map[vt_symbol] = round(
                fill_price,
                2,
            )
            return True

        take_profit_price = round(float(entry_price) * (1 + float(self.take_profit_ratio)), 2)
        if self._check_combo_take_profit(bar, entry_price, highest_price, take_profit_price):
            self.exit_reason_map[vt_symbol] = "combo_take_profit"
            self.take_profit_price_map[vt_symbol] = take_profit_price
            return True

        if self._check_time_exit(vt_symbol):
            self.exit_reason_map[vt_symbol] = "time_exit"
            return True

        self.exit_reason_map.pop(vt_symbol, None)
        return False

    def _handle_exit_signals(self, bars: Dict[str, BarData]) -> None:
        for vt_symbol in self.vt_symbols:
            current_pos = self.get_pos(vt_symbol)
            if current_pos <= 0:
                continue

            bar = bars.get(vt_symbol) or self.last_bars.get(vt_symbol)
            if not bar:
                continue

            if self.should_exit(vt_symbol, bar):
                self.set_target(vt_symbol, 0)
                self.write_log(f"{vt_symbol} 触发卖出条件，目标仓位设为0")

    def _execute_intraday_exits(self, bars: Dict[str, BarData]) -> None:
        exit_bars: Dict[str, BarData] = {}
        for vt_symbol in self.vt_symbols:
            if self.get_pos(vt_symbol) <= 0:
                continue
            if self.exit_reason_map.get(vt_symbol) not in {"fixed_stop_loss", "combo_take_profit"}:
                continue

            bar = bars.get(vt_symbol) or self.last_bars.get(vt_symbol)
            if not bar:
                continue

            exit_bars[vt_symbol] = bar

        if not exit_bars:
            return

        stop_loss_count = sum(1 for vt_symbol in exit_bars if self.exit_reason_map.get(vt_symbol) == "fixed_stop_loss")
        take_profit_count = len(exit_bars) - stop_loss_count
        self.write_log(
            f"触发当日退出，止损={stop_loss_count}, 止盈={take_profit_count}，立即撮合 {len(exit_bars)} 只股票"
        )
        self.rebalance_portfolio(exit_bars)
        cross_limit_order = getattr(self.strategy_engine, "cross_limit_order", None)
        if callable(cross_limit_order):
            cross_limit_order()
        self.today_exited_symbols.update(exit_bars.keys())

    def _mark_to_market_capital(self) -> None:
        total_value: float = 0.0
        size_map = getattr(self.strategy_engine, "sizes", {})

        for vt_symbol in self.vt_symbols:
            pos = self.get_pos(vt_symbol)
            if pos == 0:
                continue

            bar = self.last_bars.get(vt_symbol)
            if not bar:
                continue

            contract_size = float(size_map.get(vt_symbol, 1) or 1)
            total_value += float(pos) * contract_size * float(bar.close_price)

        self.current_total_capital = float(self.available_cash) + total_value

    def _allocate_today_targets(self, bars: Dict[str, BarData], candidates: List[str]) -> None:
        open_candidates: List[str] = []
        for vt_symbol in candidates:
            if vt_symbol in self.today_exited_symbols:
                continue
            if self.get_pos(vt_symbol) > 0:
                continue
            open_candidates.append(vt_symbol)

        n = len(open_candidates)
        if n == 0:
            self.write_log("今日无新增可买股票，维持现有持仓")
            return

        available_cash = max(float(self.available_cash), 0.0)
        per_stock_capital = min(self.max_per_stock_capital, available_cash / n)

        if per_stock_capital < self.min_per_stock_capital:
            self.write_log(
                f"单票可分配资金 {per_stock_capital:.2f} 小于最小门槛 {self.min_per_stock_capital:.2f}，今日不新开仓"
            )
            return

        allocated_capital: float = 0.0
        size_map = getattr(self.strategy_engine, "sizes", {})
        for vt_symbol in open_candidates:
            bar = bars.get(vt_symbol) or self.last_bars.get(vt_symbol)
            if not bar:
                self.write_log(f"{vt_symbol} 缺少行情，跳过")
                self.set_target(vt_symbol, 0)
                continue

            if float(bar.close_price) <= 0:
                self.write_log(f"{vt_symbol} 收盘价异常，跳过")
                self.set_target(vt_symbol, 0)
                continue

            contract_size = float(size_map.get(vt_symbol, 1) or 1)
            if contract_size <= 0:
                self.write_log(f"{vt_symbol} 合约乘数异常，跳过")
                self.set_target(vt_symbol, 0)
                continue

            # 用当日高点做保守定价，避免下一交易日开盘跳空导致实际买入金额超过单票上限。
            buy_limit_price = float(bar.high_price)
            if buy_limit_price <= 0:
                self.write_log(f"{vt_symbol} 最高价异常，跳过")
                self.set_target(vt_symbol, 0)
                continue

            # PortfolioStrategy 的 volume 是引擎下单单位；股票按 contract_size 计算名义金额。
            target_lots = int(per_stock_capital / (buy_limit_price * contract_size))
            target_lots = (target_lots // self.lot_size) * self.lot_size

            if target_lots <= 0:
                self.set_target(vt_symbol, 0)
                self.write_log(
                    f"{vt_symbol} 资金不足以买入最小交易单位，目标手数=0, 目标股数=0, 目标金额={per_stock_capital:.2f}"
                )
                continue

            target_shares = target_lots * contract_size
            target_amount = target_shares * buy_limit_price

            self.set_target(vt_symbol, target_lots)
            self.buy_price_map[vt_symbol] = round(buy_limit_price, 2)
            allocated_capital += target_amount
            self.write_log(
                f"{vt_symbol} 目标金额={per_stock_capital:.2f}, "
                f"目标手数={target_lots}, "
                f"目标股数={target_shares:.0f}, "
                f"参考价={buy_limit_price:.2f}, "
                f"实际占用资金={target_amount:.2f}"
            )

        estimated_remaining_cash = max(available_cash - allocated_capital, 0.0)
        self.write_log(
            f"总资产={self.current_total_capital:.2f}, 新增候选数={n}, 单票资金={per_stock_capital:.2f}, 估算剩余现金={estimated_remaining_cash:.2f}"
        )

    def _is_rebalance_time(self, bar: BarData) -> bool:
        if getattr(bar, "interval", None) == Interval.DAILY:
            return True

        t: time = bar.datetime.time()
        return (t.hour, t.minute) >= (self.rebalance_hour, self.rebalance_minute)

    def _check_fixed_stop_loss(self, bar: BarData, entry_price: float) -> bool:
        return bool(bar.low_price <= entry_price * (1 - self.stop_loss_ratio))

    def _check_combo_take_profit(
        self,
        bar: BarData,
        entry_price: float,
        highest_price: float,
        take_profit_price: float,
    ) -> bool:
        fixed_take_profit = bar.high_price >= take_profit_price
        trailing_active = highest_price >= entry_price * (1 + self.trailing_activate_ratio)
        trailing_take_profit = trailing_active and (
            bar.close_price <= highest_price * (1 - self.trailing_stop_ratio)
        )
        return bool(fixed_take_profit or trailing_take_profit)

    def _check_time_exit(self, vt_symbol: str) -> bool:
        return bool(self.holding_bars_map.get(vt_symbol, 0) >= self.max_hold_bars)

    def calculate_price(self, vt_symbol: str, direction: Direction, reference: float) -> float:
        # 日线回测里，委托在下一根 bar 撮合。
        # 买单用当日高点做保守限价，确保实际成交金额不超过单票预算；
        # 卖单用足够低的限价确保下一交易日开盘能够成交。
        if direction == Direction.LONG:
            buy_price = self.buy_price_map.get(vt_symbol)
            if buy_price is not None and buy_price > 0:
                return float(buy_price)
            return max(reference * 100.0, reference + self.price_add)
        if self.exit_reason_map.get(vt_symbol) == "fixed_stop_loss":
            return max(self.price_add, 0.01)
        if self.exit_reason_map.get(vt_symbol) == "combo_take_profit":
            return float(self.take_profit_price_map.get(vt_symbol, reference) or reference)
        return max(self.price_add, 0.01)

    def _reset_symbol_state(self, vt_symbol: str) -> None:
        self.entry_price_map.pop(vt_symbol, None)
        self.entry_trade_date_map.pop(vt_symbol, None)
        self.highest_price_map.pop(vt_symbol, None)
        self.holding_bars_map.pop(vt_symbol, None)
        self.exit_reason_map.pop(vt_symbol, None)
        self.buy_price_map.pop(vt_symbol, None)
        self.stop_loss_price_map.pop(vt_symbol, None)
        self.take_profit_price_map.pop(vt_symbol, None)

    def update_trade(self, trade: TradeData) -> None:
        previous_pos = self.get_pos(trade.vt_symbol)

        if trade.direction == Direction.SHORT and self.exit_reason_map.get(trade.vt_symbol) == "fixed_stop_loss":
            stop_loss_price = float(self.stop_loss_price_map.get(trade.vt_symbol, trade.price) or trade.price)
            trade.price = stop_loss_price

        size_map = getattr(self.strategy_engine, "sizes", {})
        rate_map = getattr(self.strategy_engine, "rates", {})
        slippage_map = getattr(self.strategy_engine, "slippages", {})
        contract_size = float(size_map.get(trade.vt_symbol, 1) or 1)
        rate = float(rate_map.get(trade.vt_symbol, 0) or 0)
        slippage = float(slippage_map.get(trade.vt_symbol, 0) or 0)
        trade_shares = float(trade.volume) * contract_size
        turnover = trade_shares * float(trade.price)
        commission = turnover * rate
        slippage_cost = trade_shares * slippage

        if trade.direction == Direction.LONG:
            self.available_cash = max(self.available_cash - turnover - commission - slippage_cost, 0.0)
        else:
            self.available_cash = max(self.available_cash + turnover - commission - slippage_cost, 0.0)

        super().update_trade(trade)
        current_pos = self.get_pos(trade.vt_symbol)

        if previous_pos <= 0 < current_pos and trade.direction == Direction.LONG:
            self.entry_price_map[trade.vt_symbol] = float(trade.price)
            self.entry_trade_date_map[trade.vt_symbol] = pd.Timestamp(trade.datetime).normalize().strftime("%Y-%m-%d")
            self.highest_price_map[trade.vt_symbol] = float(trade.price)
            self.holding_bars_map[trade.vt_symbol] = 0
            self.exit_reason_map.pop(trade.vt_symbol, None)
            self.buy_price_map.pop(trade.vt_symbol, None)
        elif current_pos <= 0:
            self._reset_symbol_state(trade.vt_symbol)

        self.put_event()

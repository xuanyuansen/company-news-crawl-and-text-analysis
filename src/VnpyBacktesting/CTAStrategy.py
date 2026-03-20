from __future__ import annotations

from vnpy.trader.constant import Direction, Offset
from vnpy_ctastrategy import (
    BarData,
    BarGenerator,
    CtaTemplate,
    OrderData,
    StopOrder,
    TickData,
    TradeData,
)


class CTAStrategy(CtaTemplate):
    """
    严格单次开仓策略：
    1. 仅在 buy_date 指定日期开仓一次
    2. 固定止损卖出
    3. 组合止盈（固定止盈 + 回撤止盈）卖出
    4. 超过持有天数卖出
    5. 除上述情况外不平仓，不再二次开仓
    """

    buy_date = ""

    stop_loss_ratio = 0.03
    take_profit_ratio = 0.12
    trailing_activate_ratio = 0.06
    trailing_stop_ratio = 0.03
    max_hold_bars = 10
    fixed_size = 100

    entry_price = 0.0
    highest_price = 0.0
    holding_bars = 0
    exit_reason = ""
    has_opened_once = False

    author = "codex"
    parameters = [
        "buy_date",
        "stop_loss_ratio",
        "take_profit_ratio",
        "trailing_activate_ratio",
        "trailing_stop_ratio",
        "max_hold_bars",
        "fixed_size",
    ]
    variables = [
        "entry_price",
        "highest_price",
        "holding_bars",
        "exit_reason",
        "has_opened_once",
    ]

    def __init__(self, cta_engine, strategy_name: str, vt_symbol: str, setting: dict):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.bg = BarGenerator(self.on_bar)

    def on_init(self) -> None:
        self.write_log("策略初始化")
        self.load_bar(2)

    def on_start(self) -> None:
        self.write_log("策略启动")

    def on_stop(self) -> None:
        self.write_log("策略停止")

    def on_tick(self, tick: TickData) -> None:
        self.bg.update_tick(tick)

    def _reset_position_state(self) -> None:
        self.entry_price = 0.0
        self.highest_price = 0.0
        self.holding_bars = 0
        self.exit_reason = ""

    def _check_fixed_stop_loss(self, bar: BarData) -> bool:
        return bool(bar.close_price <= self.entry_price * (1 - self.stop_loss_ratio))

    def _should_force_buy_on_date(self, bar: BarData) -> bool:
        if self.has_opened_once:
            return False
        if not self.buy_date:
            return False
        return bar.datetime.strftime("%Y-%m-%d") == self.buy_date

    def _check_combo_take_profit(self, bar: BarData) -> bool:
        fixed_take_profit = bar.close_price >= self.entry_price * (1 + self.take_profit_ratio)
        trailing_active = self.highest_price >= self.entry_price * (1 + self.trailing_activate_ratio)
        trailing_take_profit = trailing_active and (
            bar.close_price <= self.highest_price * (1 - self.trailing_stop_ratio)
        )
        return bool(fixed_take_profit or trailing_take_profit)

    def _check_time_exit(self) -> bool:
        return bool(self.holding_bars >= self.max_hold_bars)

    def on_bar(self, bar: BarData) -> None:
        self.cancel_all()

        if self.pos == 0 and self._should_force_buy_on_date(bar):
            self._reset_position_state()
            self.has_opened_once = True
            self.buy(bar.close_price, self.fixed_size)
            self.put_event()
            return

        if self.pos == 0:
            self.put_event()
            return

        if self.entry_price <= 0:
            self.entry_price = bar.close_price
            self.highest_price = bar.close_price

        self.highest_price = max(self.highest_price, bar.high_price, bar.close_price)
        self.holding_bars += 1

        if self._check_fixed_stop_loss(bar):
            self.exit_reason = "fixed_stop_loss"
            self.sell(bar.close_price, abs(self.pos))
        elif self._check_combo_take_profit(bar):
            self.exit_reason = "combo_take_profit"
            self.sell(bar.close_price, abs(self.pos))
        elif self._check_time_exit():
            self.exit_reason = "time_exit"
            self.sell(bar.close_price, abs(self.pos))

        self.put_event()

    def on_order(self, order: OrderData) -> None:
        pass

    def on_trade(self, trade: TradeData) -> None:
        if trade.direction == Direction.LONG and trade.offset == Offset.OPEN:
            self.entry_price = trade.price
            self.highest_price = trade.price
            self.holding_bars = 0
            self.exit_reason = ""
            self.has_opened_once = True
        elif trade.direction == Direction.SHORT:
            self._reset_position_state()
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder) -> None:
        pass

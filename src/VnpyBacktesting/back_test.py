from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd
from vnpy.trader.constant import Interval
from vnpy_ctastrategy.backtesting import BacktestingEngine

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]   # 黑体
plt.rcParams["axes.unicode_minus"] = False     # 解决负号显示问题

try:
    from VnpyBacktesting.CTAStrategy import CTAStrategy
    from VnpyBacktesting.prepare_data import load_massbreak_symbols, prepare_symbols
except ModuleNotFoundError:
    from CTAStrategy import CTAStrategy
    from prepare_data import load_massbreak_symbols, prepare_symbols

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


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def resolve_symbols(args: argparse.Namespace) -> tuple[list[str], str]:
    if args.single:
        return load_massbreak_symbols([args.single]), "single"
    if args.symbols:
        return load_massbreak_symbols(args.symbols), "list"
    raise ValueError("请通过 --single 或 --symbols 指定回测股票")


def build_strategy_setting(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "buy_date": args.buy_date,
        "stop_loss_ratio": args.stop_loss_ratio,
        "take_profit_ratio": args.take_profit_ratio,
        "trailing_activate_ratio": args.trailing_activate_ratio,
        "trailing_stop_ratio": args.trailing_stop_ratio,
        "max_hold_bars": args.max_hold_bars,
        "fixed_size": args.fixed_size,
    }


def parse_symbol_buy_dates(raw: str) -> dict[str, str]:
    """
    Parse per-symbol buy dates.
    Example:
    --symbol-buy-dates "sh603938:2026-03-04,sz000001:2026-03-05"
    """
    if not raw:
        return {}

    mapping: dict[str, str] = {}
    items = [x.strip() for x in raw.split(",") if x.strip()]
    for item in items:
        if ":" not in item:
            raise ValueError(f"symbol-buy-dates 格式错误: {item}，需为 code:YYYY-MM-DD")
        symbol_raw, buy_date_raw = item.split(":", 1)
        symbol_raw = symbol_raw.strip()
        buy_date_raw = buy_date_raw.strip()
        if not symbol_raw or not buy_date_raw:
            raise ValueError(f"symbol-buy-dates 存在空值: {item}")

        # 复用统一代码解析，转成 vt_symbol
        vt_symbols = load_massbreak_symbols([symbol_raw])
        if not vt_symbols:
            raise ValueError(f"无法解析股票代码: {symbol_raw}")
        vt_symbol = vt_symbols[0]

        # 校验日期格式
        parse_date(buy_date_raw)
        mapping[vt_symbol] = buy_date_raw

    return mapping


def save_backtest_png(result_df: pd.DataFrame, chart_file: Path) -> None:
    chart_file.parent.mkdir(parents=True, exist_ok=True)
    if result_df.empty:
        raise ValueError("result_df 为空，无法绘图")

    x = pd.to_datetime(result_df.index)
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    if "balance" in result_df.columns:
        axes[0].plot(x, result_df["balance"], color="#1f77b4", linewidth=1.6)
    axes[0].set_title("资金曲线")
    axes[0].grid(alpha=0.3, linestyle="--")

    if "drawdown" in result_df.columns:
        axes[1].fill_between(x, result_df["drawdown"], 0, color="#d62728", alpha=0.45)
    axes[1].set_title("回撤")
    axes[1].grid(alpha=0.3, linestyle="--")

    if "net_pnl" in result_df.columns:
        axes[2].bar(x, result_df["net_pnl"], color="#2ca02c", width=0.8)
    axes[2].set_title("每日净盈亏")
    axes[2].grid(alpha=0.3, linestyle="--")

    fig.tight_layout()
    fig.savefig(chart_file, dpi=160)
    plt.close(fig)


def run_one_backtest(
    vt_symbol: str,
    buy_date: str,
    args: argparse.Namespace,
    show_chart: bool = False,
    save_chart: bool = False,
) -> dict[str, Any]:
    engine = BacktestingEngine()
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=Interval.DAILY,
        start=parse_date(args.start_date),
        end=parse_date(args.end_date),
        rate=args.rate,
        slippage=args.slippage,
        size=args.size,
        pricetick=args.pricetick,
        capital=args.capital,
    )
    strategy_setting = build_strategy_setting(args)
    strategy_setting["buy_date"] = buy_date
    engine.add_strategy(CTAStrategy, strategy_setting)

    engine.load_data()
    if not engine.history_data:
        engine.clear_data()
        return {
            "股票": vt_symbol,
            "指定买入日期": buy_date or "",
            "成交笔数": 0,
            "错误信息": "no_history_data",
        }

    engine.run_backtesting()
    result_df = engine.calculate_result()
    stats = engine.calculate_statistics(df=result_df, output=False)
    trades = engine.get_all_trades()

    row: dict[str, Any] = {
        "股票": vt_symbol,
        "指定买入日期": buy_date or "",
        "成交笔数": len(trades),
    }
    if trades:
        row["最后成交日期"] = trades[-1].datetime.strftime("%Y-%m-%d")
        row["最后成交方向"] = str(trades[-1].direction)
        row["最后成交价格"] = trades[-1].price

    for key, chn_name in STATS_NAME_MAP.items():
        if key in stats:
            row[chn_name] = stats[key]

    if save_chart:
        chart_dir = Path(args.chart_dir)
        chart_file = chart_dir / f"{vt_symbol}_{args.start_date}_{args.end_date}.png"
        try:
            save_backtest_png(result_df=result_df, chart_file=chart_file)
            row["图表文件"] = str(chart_file)
            if show_chart:
                row["图表说明"] = "为避免卡死，已禁用阻塞式弹窗，仅保存PNG文件。"
        except Exception as exc:
            row["图表错误"] = str(exc)

    engine.clear_data()
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="vnpy CTA 回测（单票/列表）")

    parser.add_argument("--single", default="", help="单只股票：如 600000/sh600000/600000.SSE")
    parser.add_argument("--symbols", default="", help="股票列表，逗号分隔")
    parser.add_argument("--start-date", default="2024-01-01", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"), help="结束日期 YYYY-MM-DD")

    parser.add_argument("--skip-prepare", action="store_true", help="跳过数据准备")
    parser.add_argument("--no-clean", action="store_true", help="准备数据时不清理旧数据")
    parser.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"], help="akshare 复权类型")

    parser.add_argument("--capital", type=int, default=1_000_000)
    parser.add_argument("--rate", type=float, default=2.5 / 10000)
    parser.add_argument("--slippage", type=float, default=0.01)
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--pricetick", type=float, default=0.01)

    parser.add_argument("--buy-date", default="", help="指定买入日期 YYYY-MM-DD；为空则不主动开仓")
    parser.add_argument(
        "--symbol-buy-dates",
        default="",
        help="逐股票买入日期，格式 code:YYYY-MM-DD,code:YYYY-MM-DD",
    )
    parser.add_argument("--stop-loss-ratio", type=float, default=0.03)
    parser.add_argument("--take-profit-ratio", type=float, default=0.10)
    parser.add_argument("--trailing-activate-ratio", type=float, default=0.06)
    parser.add_argument("--trailing-stop-ratio", type=float, default=0.03)
    parser.add_argument("--max-hold-bars", type=int, default=5)
    parser.add_argument("--fixed-size", type=int, default=100)

    parser.add_argument("--show-chart", action="store_true", help="保留参数；当前仅保存PNG，不弹窗")
    parser.add_argument("--no-show-chart", action="store_true", help="关闭图表相关提示")
    parser.add_argument("--no-save-chart", action="store_true", help="不保存图表 PNG")
    parser.add_argument("--chart-dir", default="charts", help="图表输出目录（PNG）")

    parser.add_argument("--output-csv", default="", help="回测结果 CSV")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    symbols, mode = resolve_symbols(args)
    symbol_buy_dates = parse_symbol_buy_dates(args.symbol_buy_dates)
    print(f"模式: {mode}")
    print(f"股票列表: {symbols}")
    if symbol_buy_dates:
        print(f"逐股票买入日期: {symbol_buy_dates}")
        unknown_symbols = sorted(set(symbol_buy_dates.keys()) - set(symbols))
        if unknown_symbols:
            raise ValueError(f"symbol-buy-dates 包含未在 --symbols/--single 中声明的股票: {unknown_symbols}")

    if not args.skip_prepare:
        prepared = prepare_symbols(
            symbols=symbols,
            start=args.start_date,
            end=args.end_date,
            adjust=args.adjust,
            clean_before_save=not args.no_clean,
        )
        print("数据准备结果:")
        for vt_symbol, count in prepared.items():
            print(vt_symbol, count)

    is_single = len(symbols) == 1
    show_chart = (is_single and not args.no_show_chart) or args.show_chart
    save_chart = is_single and not args.no_save_chart

    results: list[dict[str, Any]] = []
    for vt_symbol in symbols:
        buy_date = symbol_buy_dates.get(vt_symbol, args.buy_date)
        try:
            results.append(
                run_one_backtest(
                    vt_symbol=vt_symbol,
                    buy_date=buy_date,
                    args=args,
                    show_chart=show_chart and is_single,
                    save_chart=save_chart and is_single,
                )
            )
        except Exception as exc:
            results.append({"股票": vt_symbol, "指定买入日期": buy_date or "", "错误信息": str(exc)})

    result_df = pd.DataFrame(results)
    if "错误信息" in result_df.columns:
        result_df = result_df.sort_values(by=["错误信息", "股票"], na_position="last")

    output_path = args.output_csv
    if not output_path:
        output_path = str(Path.cwd() / f"vnpy_backtest_result_{datetime.now().strftime('%Y-%m-%d')}.csv")
    result_df.to_csv(output_path, index=False)

    print(f"输出CSV: {output_path}")
    print(result_df.to_string(index=False))

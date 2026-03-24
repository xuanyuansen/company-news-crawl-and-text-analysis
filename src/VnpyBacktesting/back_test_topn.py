from __future__ import annotations

import argparse
import sys
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

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

try:
    from VnpyBacktesting.CTAStrategy import CTAStrategy
    from VnpyBacktesting.prepare_data import load_massbreak_symbols, prepare_symbols
    from MassBreak.MassBreakAndInfosAlphaGo import (
        load_massbreak_candidates,
        load_news_good_or_bad,
        merge_and_score,
    )
except ModuleNotFoundError:
    from CTAStrategy import CTAStrategy
    from prepare_data import load_massbreak_symbols, prepare_symbols
    from MassBreakAndInfosAlphaGo import (
        load_massbreak_candidates,
        load_news_good_or_bad,
        merge_and_score,
    )

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


def build_strategy_setting(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "stop_loss_ratio": args.stop_loss_ratio,
        "take_profit_ratio": args.take_profit_ratio,
        "trailing_activate_ratio": args.trailing_activate_ratio,
        "trailing_stop_ratio": args.trailing_stop_ratio,
        "max_hold_bars": args.max_hold_bars,
        "fixed_size": args.fixed_size,
    }


def build_massbreak_selection(args: argparse.Namespace) -> pd.DataFrame:
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
    if massbreak_candidates.empty:
        return massbreak_candidates

    label_field = "NewLabel" if args.use_new_label else "Label"
    news_df = load_news_good_or_bad(
        candidate_df=massbreak_candidates,
        label_field=label_field,
        news_start_date=args.news_start_date,
    )
    final_df = merge_and_score(massbreak_candidates, news_df, as_of_date=args.as_of_date)
    if final_df.empty:
        return final_df

    final_df = final_df.sort_values(by=["final_score", "good_cnt", "TodayVolumeVsN"], ascending=False)
    return final_df.head(args.top_n).copy()


def calc_per_stock_capital(total_capital: int, top_n: int) -> int:
    if top_n <= 0:
        raise ValueError("top_n 必须大于 0")
    if total_capital % top_n != 0:
        raise ValueError(f"总 capital={total_capital} 不能被 top_n={top_n} 整除")
    return total_capital // top_n


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
    selection_row: pd.Series | None = None,
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
        capital=calc_per_stock_capital(args.capital, args.top_n),
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
    if selection_row is not None:
        row["MassBreak排名"] = int(selection_row.get("rank", 0) or 0)
        row["MassBreak评分"] = float(selection_row.get("final_score", 0.0) or 0.0)
        row["MassBreak匹配类型"] = str(selection_row.get("match_type", "") or "")
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

    parser.add_argument("--start-date", default="2024-01-01", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"), help="结束日期 YYYY-MM-DD")

    parser.add_argument("--skip-prepare", action="store_true", help="跳过数据准备")
    parser.add_argument("--no-clean", action="store_true", help="准备数据时不清理旧数据")
    parser.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"], help="akshare 复权类型")

    parser.add_argument("--market", default="cn", help="市场类型: cn/us/hk")
    parser.add_argument("--ave-date", type=int, default=30, help="均量窗口天数")
    parser.add_argument("--ratio", type=float, default=2.0, help="放量倍数")
    parser.add_argument("--keep-days", type=int, default=2, help="连续放量天数")
    parser.add_argument(
        "--price-stable-threshold",
        type=float,
        default=0.12,
        help="放量期间 KeepDays 内价格稳定阈值",
    )
    parser.add_argument("--min-break-count", type=int, default=1, help="最小 BreakDateCnt")
    parser.add_argument("--news-start-date", default="", help="新闻统计起始日期 YYYY-MM-DD")
    parser.add_argument("--use-new-label", action="store_true", help="使用 NewLabel 代替 Label 聚合")
    parser.add_argument("--max-stocks", type=int, default=0, help="仅调试用，限制股票池数量")
    parser.add_argument("--as-of-date", default="", help="评分参考日期 YYYY-MM-DD，默认当天")
    parser.add_argument("--top-n", type=int, default=50, help="MassBreak 选出的前 N 只股票进行回测")

    parser.add_argument("--capital", type=int, default=1_000_000)
    parser.add_argument("--rate", type=float, default=2.5 / 10000)
    parser.add_argument("--slippage", type=float, default=0.01)
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--pricetick", type=float, default=0.01)
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
    selection_df = build_massbreak_selection(args)
    if selection_df.empty:
        print("MassBreak 候选为空，退出")
        output_path = args.output_csv or str(Path.cwd() / f"vnpy_backtest_result_{datetime.now().strftime('%Y-%m-%d')}.csv")
        selection_df.to_csv(output_path, index=False)
        sys.exit(0)

    symbols: list[str] = []
    buy_dates: dict[str, str] = {}
    rows: list[pd.Series] = []
    selection_by_vt_symbol: dict[str, pd.Series] = {}
    for _, row in selection_df.iterrows():
        joint_code = str(row.get("joint_quant_code", "") or row.get("code", "")).strip()
        if not joint_code:
            continue
        vt_symbols = load_massbreak_symbols([joint_code])
        if not vt_symbols:
            continue
        buy_date = str(row.get("LatestBreakDate", "") or "").strip()
        if not buy_date or buy_date in {"-1", "nan"}:
            continue
        vt_symbol = vt_symbols[0]
        if vt_symbol in buy_dates:
            continue
        symbols.append(vt_symbol)
        buy_dates[vt_symbol] = buy_date
        rows.append(row)
        selection_by_vt_symbol[vt_symbol] = row

    if not symbols:
        print("没有可用于回测的 MassBreak 股票，退出")
        output_path = args.output_csv or str(Path.cwd() / f"vnpy_backtest_result_{datetime.now().strftime('%Y-%m-%d')}.csv")
        selection_df.to_csv(output_path, index=False)
        sys.exit(0)

    print("MassBreak TopN 结果:")
    print(pd.DataFrame(rows)[["rank", "joint_quant_code", "code_name", "LatestBreakDate", "final_score", "match_type"]].to_string(index=False))
    print(f"回测股票数量: {len(symbols)}")
    print(f"回测股票列表: {symbols}")

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
        buy_date = buy_dates.get(vt_symbol, "")
        try:
            results.append(
                run_one_backtest(
                    vt_symbol=vt_symbol,
                    buy_date=buy_date,
                    args=args,
                    selection_row=selection_by_vt_symbol.get(vt_symbol),
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

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sko.PSO import PSO
from vnpy.trader.constant import Interval
from vnpy_portfoliostrategy import BacktestingEngine

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

try:
    from VnpyBacktesting.bt_topn_cum_return import (
        build_contract_settings,
        build_daily_selection_plan,
        build_strategy_setting,
        extract_active_result,
        parse_date,
        validate_args,
    )
    from VnpyBacktesting.PortfolioDailyStockAllocateStrategy import DailyStockAllocateStrategy
    from VnpyBacktesting.prepare_data import prepare_symbols
except ModuleNotFoundError:
    from bt_topn_cum_return import (
        build_contract_settings,
        build_daily_selection_plan,
        build_strategy_setting,
        extract_active_result,
        parse_date,
        validate_args,
    )
    from PortfolioDailyStockAllocateStrategy import DailyStockAllocateStrategy
    from prepare_data import prepare_symbols


OPTIMIZE_KEYS = (
    "ratio",
    "keep_days",
    "price_stable_threshold",
    "max_per_stock_capital",
    "take_profit_ratio",
    "stop_loss_ratio",
    "trailing_activate_ratio",
    "trailing_stop_ratio",
)

# 搜索区间保持保守，避免 PSO 在明显不合理的区域浪费迭代。
PSO_BOUNDS = {
    "ratio": (1.3, 3.0),
    "keep_days": (1, 5),
    "price_stable_threshold": (0.01, 0.15),
    "max_per_stock_capital": (20_000.0, 150_000.0),
    "take_profit_ratio": (0.03, 0.30),
    "stop_loss_ratio": (0.01, 0.15),
    "trailing_activate_ratio": (0.03, 0.30),
    "trailing_stop_ratio": (0.01, 0.15),
}


def _copy_namespace(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(**vars(args))


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def _clip_int(value: float, lower: int, upper: int) -> int:
    return int(np.clip(int(round(value)), lower, upper))


def build_parser() -> argparse.ArgumentParser:
    try:
        from VnpyBacktesting.bt_topn_cum_return import build_parser as build_base_parser
    except ModuleNotFoundError:
        from bt_topn_cum_return import build_parser as build_base_parser

    parser = build_base_parser()
    parser.description = "vnpy TopN PSO 参数寻优（目标：2026-03-17 ~ 2026-03-27 累计收益最大化）"
    parser.set_defaults(
        selection_start_date="2026-02-01",
        start_date="2026-03-17",
        end_date="2026-03-27",
        market="cn",
        ave_date=10,
        ratio=1.5,
        keep_days=3,
        price_stable_threshold=0.05,
        min_break_count=1,
        news_start_date="2026-03-01",
        top_n=20,
        capital=1_000_000,
        max_per_stock_capital=50_000,
        min_per_stock_capital=20_000,
        take_profit_ratio=0.25,
        stop_loss_ratio=0.10,
        trailing_activate_ratio=0.15,
        trailing_stop_ratio=0.05,
    )
    parser.add_argument("--pso-pop", type=int, default=12, help="PSO 粒子数")
    parser.add_argument("--pso-max-iter", type=int, default=20, help="PSO 迭代次数")
    parser.add_argument("--pso-w", type=float, default=0.8, help="PSO 惯性权重")
    parser.add_argument("--pso-c1", type=float, default=0.5, help="PSO 个体学习因子")
    parser.add_argument("--pso-c2", type=float, default=0.5, help="PSO 社会学习因子")
    parser.add_argument("--history-csv", default="", help="保存每次评估历史的 CSV 路径")
    parser.add_argument("--best-params-txt", default="", help="保存最优参数的 TXT 路径")
    return parser


class TopNPsoOptimizer:
    def __init__(self, base_args: argparse.Namespace):
        self.base_args = base_args
        self.selection_cache: dict[tuple[float, int, float], tuple[dict[str, list[str]], list[str]]] = {}
        self.objective_cache: dict[tuple[Any, ...], float] = {}
        self.prepared_symbols: set[str] = set()
        self.history_rows: list[dict[str, Any]] = []

    def _vector_to_params(self, x: np.ndarray) -> dict[str, Any]:
        ratio = _clamp(float(x[0]), *PSO_BOUNDS["ratio"])
        keep_days = _clip_int(float(x[1]), *PSO_BOUNDS["keep_days"])
        price_stable_threshold = _clamp(float(x[2]), *PSO_BOUNDS["price_stable_threshold"])
        max_per_stock_capital = _clamp(float(x[3]), *PSO_BOUNDS["max_per_stock_capital"])
        take_profit_ratio = _clamp(float(x[4]), *PSO_BOUNDS["take_profit_ratio"])
        stop_loss_ratio = _clamp(float(x[5]), *PSO_BOUNDS["stop_loss_ratio"])
        trailing_activate_ratio = _clamp(float(x[6]), *PSO_BOUNDS["trailing_activate_ratio"])
        trailing_stop_ratio = _clamp(float(x[7]), *PSO_BOUNDS["trailing_stop_ratio"])

        return {
            "ratio": round(ratio, 6),
            "keep_days": keep_days,
            "price_stable_threshold": round(price_stable_threshold, 6),
            "max_per_stock_capital": round(max_per_stock_capital, 2),
            "take_profit_ratio": round(take_profit_ratio, 6),
            "stop_loss_ratio": round(stop_loss_ratio, 6),
            "trailing_activate_ratio": round(trailing_activate_ratio, 6),
            "trailing_stop_ratio": round(trailing_stop_ratio, 6),
        }

    @staticmethod
    def _candidate_key(params: dict[str, Any]) -> tuple[Any, ...]:
        return tuple(params[key] for key in OPTIMIZE_KEYS)

    @staticmethod
    def _selection_key(params: dict[str, Any]) -> tuple[float, int, float]:
        return (
            float(params["ratio"]),
            int(params["keep_days"]),
            float(params["price_stable_threshold"]),
        )

    def _build_candidate_args(self, params: dict[str, Any], daily_selection_map: dict[str, list[str]]) -> argparse.Namespace:
        candidate_args = _copy_namespace(self.base_args)
        for key, value in params.items():
            setattr(candidate_args, key, value)
        candidate_args.daily_selection_df = pd.DataFrame()
        candidate_args.daily_selection_map = daily_selection_map
        return candidate_args

    def _get_selection_plan(self, params: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
        selection_key = self._selection_key(params)
        cached = self.selection_cache.get(selection_key)
        if cached is not None:
            return cached

        candidate_args = _copy_namespace(self.base_args)
        for key in ("ratio", "keep_days", "price_stable_threshold"):
            setattr(candidate_args, key, params[key])

        daily_selection_map, vt_symbols = build_daily_selection_plan(candidate_args)
        self.selection_cache[selection_key] = (daily_selection_map, vt_symbols)
        return daily_selection_map, vt_symbols

    def _prepare_missing_data(self, vt_symbols: list[str]) -> None:
        missing_symbols = [vt_symbol for vt_symbol in vt_symbols if vt_symbol not in self.prepared_symbols]
        if not missing_symbols or bool(self.base_args.skip_prepare):
            return

        with contextlib.redirect_stdout(io.StringIO()):
            try:
                prepared = prepare_symbols(
                    symbols=missing_symbols,
                    start=self.base_args.selection_start_date,
                    end=self.base_args.end_date,
                    adjust=self.base_args.adjust,
                    market=self.base_args.market,
                    clean_before_save=True,
                )
            except Exception:
                prepared = {}

        self.prepared_symbols.update(prepared.keys())

    def _run_single_backtest(self, candidate_args: argparse.Namespace, vt_symbols: list[str]) -> tuple[float, str]:
        engine = BacktestingEngine()
        rates, slippages, sizes, priceticks = build_contract_settings(vt_symbols, candidate_args)
        engine.set_parameters(
            vt_symbols=vt_symbols,
            interval=Interval.DAILY,
            start=parse_date(candidate_args.selection_start_date),
            end=parse_date(candidate_args.end_date),
            rates=rates,
            slippages=slippages,
            sizes=sizes,
            priceticks=priceticks,
            capital=float(candidate_args.capital),
        )
        engine.add_strategy(DailyStockAllocateStrategy, build_strategy_setting(candidate_args))

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                engine.load_data()
                if not engine.history_data:
                    return 1e6, "no_history_data"

                engine.run_backtesting()
                raw_result_df = engine.calculate_result()
                trades = list(engine.get_all_trades())

                if raw_result_df is None or raw_result_df.empty:
                    if not trades:
                        return 0.0, "no_trades"
                    return 1e6, "empty_result_with_trades"

                active_result_df = extract_active_result(
                    raw_result_df,
                    start_date=candidate_args.start_date,
                    end_date=candidate_args.end_date,
                    capital=float(candidate_args.capital),
                )
                if active_result_df.empty:
                    if not trades:
                        return 0.0, "no_trades"
                    return 1e6, "empty_active_result"

                final_return = float(active_result_df["strategy_cum_return"].iloc[-1])
                return -final_return, "ok"
        except Exception as exc:
            return 1e6, f"error:{type(exc).__name__}"
        finally:
            engine.clear_data()

    def evaluate(self, x: np.ndarray) -> float:
        params = self._vector_to_params(x)
        candidate_key = self._candidate_key(params)
        cached = self.objective_cache.get(candidate_key)
        if cached is not None:
            return cached

        daily_selection_map, vt_symbols = self._get_selection_plan(params)
        if not vt_symbols:
            objective = 0.0
            status = "empty_selection"
        else:
            self._prepare_missing_data(vt_symbols)
            candidate_args = self._build_candidate_args(params, daily_selection_map)
            objective, status = self._run_single_backtest(candidate_args, vt_symbols)

        self.objective_cache[candidate_key] = objective
        self.history_rows.append(
            {
                **params,
                "selected_symbols": len(vt_symbols),
                "objective": objective,
                "estimated_cum_return": -objective,
                "status": status,
            }
        )
        return objective

    def save_history(self, output_csv: str) -> None:
        if not output_csv or not self.history_rows:
            return

        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(self.history_rows).to_csv(output_path, index=False)


def save_best_params_txt(output_txt: str, params: dict[str, Any], best_objective: float) -> None:
    if not output_txt:
        return

    output_path = Path(output_txt)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "best_objective={:.6f}".format(best_objective),
        "best_cum_return={:.4%}".format(-best_objective),
    ]
    for key in OPTIMIZE_KEYS:
        lines.append(f"{key}={params[key]}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = build_parser().parse_args()
    validate_args(args)

    optimizer = TopNPsoOptimizer(args)
    lb = np.array(
        [
            PSO_BOUNDS["ratio"][0],
            PSO_BOUNDS["keep_days"][0],
            PSO_BOUNDS["price_stable_threshold"][0],
            PSO_BOUNDS["max_per_stock_capital"][0],
            PSO_BOUNDS["take_profit_ratio"][0],
            PSO_BOUNDS["stop_loss_ratio"][0],
            PSO_BOUNDS["trailing_activate_ratio"][0],
            PSO_BOUNDS["trailing_stop_ratio"][0],
        ],
        dtype=float,
    )
    ub = np.array(
        [
            PSO_BOUNDS["ratio"][1],
            PSO_BOUNDS["keep_days"][1],
            PSO_BOUNDS["price_stable_threshold"][1],
            PSO_BOUNDS["max_per_stock_capital"][1],
            PSO_BOUNDS["take_profit_ratio"][1],
            PSO_BOUNDS["stop_loss_ratio"][1],
            PSO_BOUNDS["trailing_activate_ratio"][1],
            PSO_BOUNDS["trailing_stop_ratio"][1],
        ],
        dtype=float,
    )

    pso = PSO(
        func=optimizer.evaluate,
        n_dim=len(OPTIMIZE_KEYS),
        pop=args.pso_pop,
        max_iter=args.pso_max_iter,
        lb=lb,
        ub=ub,
        w=args.pso_w,
        c1=args.pso_c1,
        c2=args.pso_c2,
    )
    best_x, best_y = pso.run()
    best_params = optimizer._vector_to_params(np.asarray(best_x, dtype=float))
    best_objective = float(np.asarray(best_y, dtype=float).reshape(-1)[0])

    print("最优参数:")
    print(pd.Series(best_params).to_string())
    print(f"最优目标值={best_objective:.6f}")
    print(f"最优累计收益={-best_objective:.4%}")

    optimizer.save_history(args.history_csv)
    save_best_params_txt(args.best_params_txt, best_params, best_objective)
    if args.history_csv:
        print(f"历史记录已输出: {args.history_csv}")
    if args.best_params_txt:
        print(f"最优参数已输出: {args.best_params_txt}")


if __name__ == "__main__":
    main()

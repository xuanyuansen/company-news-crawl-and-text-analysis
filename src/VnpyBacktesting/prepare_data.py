from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import akshare as ak
import pandas as pd
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import BarData

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))


_PREFIX_TO_EXCHANGE = {
    "SH": Exchange.SSE,
    "SZ": Exchange.SZSE,
    "BJ": Exchange.BSE,
}
_SUFFIX_TO_EXCHANGE = {
    "SSE": Exchange.SSE,
    "SZSE": Exchange.SZSE,
    "BSE": Exchange.BSE,
    "SH": Exchange.SSE,
    "SZ": Exchange.SZSE,
    "BJ": Exchange.BSE,
}


def parse_date(date_value: str | datetime) -> datetime:
    if isinstance(date_value, datetime):
        return date_value
    return datetime.strptime(str(date_value), "%Y-%m-%d")


def _infer_exchange(symbol: str) -> Exchange:
    if symbol.startswith(("6", "5", "9")):
        return Exchange.SSE
    if symbol.startswith(("0", "2", "3")):
        return Exchange.SZSE
    if symbol.startswith(("4", "8")):
        return Exchange.BSE
    return Exchange.SMART


def parse_symbol_exchange(raw_code: str) -> tuple[str, Exchange]:
    code = str(raw_code).strip().upper()
    if not code:
        raise ValueError("股票代码为空")

    if "." in code:
        left, right = code.split(".", 1)
        if left.isdigit() and right in _SUFFIX_TO_EXCHANGE:
            return left.zfill(6), _SUFFIX_TO_EXCHANGE[right]
        if left in _PREFIX_TO_EXCHANGE and right.isdigit():
            return right.zfill(6), _PREFIX_TO_EXCHANGE[left]
        if left.isdigit() and right in _PREFIX_TO_EXCHANGE:
            return left.zfill(6), _PREFIX_TO_EXCHANGE[right]

    if len(code) > 2 and code[:2] in _PREFIX_TO_EXCHANGE and code[2:].isdigit():
        return code[2:].zfill(6), _PREFIX_TO_EXCHANGE[code[:2]]

    if code.isdigit():
        symbol = code.zfill(6)
        return symbol, _infer_exchange(symbol)

    raise ValueError(f"无法解析股票代码: {raw_code}")


def to_vt_symbol(raw_code: str) -> str:
    symbol, exchange = parse_symbol_exchange(raw_code)
    return f"{symbol}.{exchange.value}"


def split_symbols_arg(symbols_text: str) -> list[str]:
    if not symbols_text:
        return []
    cleaned = symbols_text.replace("，", ",")
    return [s.strip() for s in cleaned.split(",") if s.strip()]


def load_massbreak_symbols(
    symbols: str | Iterable[str],
    top_n: int = 0,
) -> list[str]:
    if isinstance(symbols, str):
        raw_symbols = split_symbols_arg(symbols)
    else:
        raw_symbols = [str(s).strip() for s in symbols if str(s).strip()]

    if top_n and top_n > 0:
        raw_symbols = raw_symbols[:top_n]

    vt_symbols: list[str] = []
    seen: set[str] = set()
    for raw in raw_symbols:
        try:
            vt_symbol = to_vt_symbol(str(raw))
        except Exception:
            continue
        if vt_symbol not in seen:
            seen.add(vt_symbol)
            vt_symbols.append(vt_symbol)

    return vt_symbols


def _mongo_symbol_candidates(symbol: str) -> list[str]:
    value = str(symbol).strip().lower()
    if not value:
        return []

    candidates: list[str] = []
    if value.startswith(("sh", "sz", "bj")) and len(value) > 2 and value[2:].isdigit():
        candidates.append(value)
        candidates.append(value[2:])
    elif value.isdigit():
        if value.startswith(("6", "5", "9")):
            candidates.append(f"sh{value}")
        elif value.startswith(("0", "2", "3")):
            candidates.append(f"sz{value}")
        elif value.startswith(("4", "8")):
            candidates.append(f"bj{value}")
        candidates.extend([f"sh{value}", f"sz{value}", f"bj{value}", value])
    else:
        candidates.append(value)

    uniq: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            uniq.append(item)
    return uniq


def _fetch_daily_mongo_data(symbol: str, start: datetime, end: datetime) -> pd.DataFrame | None:
    try:
        from Utils.database import Database
        from Utils import config
    except Exception:
        return None

    db_name = getattr(config, "STOCK_DATABASE_NAME", "stock")
    query = {
        "date": {
            "$gte": start.strftime("%Y-%m-%d"),
            "$lte": end.strftime("%Y-%m-%d"),
        }
    }
    keys = ["date", "open", "high", "low", "close", "volume", "amount", "turnover"]

    db = Database()
    for collection_name in _mongo_symbol_candidates(symbol):
        try:
            raw_df = db.get_data(
                db_name,
                collection_name,
                query=query,
                keys=keys,
                sort=True,
                sort_key=["date"],
            )
        except Exception:
            continue
        if raw_df is None or raw_df.empty:
            continue

        df = raw_df.copy()
        df["日期"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        df["开盘"] = pd.to_numeric(df["open"], errors="coerce")
        df["收盘"] = pd.to_numeric(df["close"], errors="coerce")
        df["最高"] = pd.to_numeric(df["high"], errors="coerce")
        df["最低"] = pd.to_numeric(df["low"], errors="coerce")
        df["成交量"] = pd.to_numeric(df["volume"], errors="coerce")
        if "amount" in df.columns:
            df["成交额"] = pd.to_numeric(df["amount"], errors="coerce")
        else:
            df["成交额"] = 0.25 * (df["开盘"] + df["收盘"] + df["最高"] + df["最低"]) * df["成交量"]

        use_cols = ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额"]
        df = df[use_cols].dropna(subset=["日期", "开盘", "收盘", "最高", "最低", "成交量"])
        if not df.empty:
            return df.reset_index(drop=True)

    return None


def fetch_daily_ak_data(
    symbol: str,
    start: datetime,
    end: datetime,
    adjust: str = "qfq",
    max_retry: int = 3,
) -> pd.DataFrame:
    params = dict(
        symbol=symbol,
        # period="daily",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        adjust=adjust,
    )
    last_err: Exception | None = None

    for i in range(max_retry):
        try:
            df = ak.stock_zh_a_daily(**params)
            if df is None or df.empty:
                raise ValueError(f"{symbol} 无可用日线数据")
            return df
        except Exception as exc:
            last_err = exc
            time.sleep(1 + i)

    proxy_keys = (
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "all_proxy",
        "ALL_PROXY",
    )
    backup = {k: os.environ.get(k) for k in proxy_keys}
    for k in proxy_keys:
        os.environ.pop(k, None)

    try:
        for i in range(max_retry):
            try:
                df = ak.stock_zh_a_daily(**params)
                if df is None or df.empty:
                    raise ValueError(f"{symbol} 无可用日线数据")
                return df
            except Exception as exc:
                last_err = exc
                time.sleep(1 + i)
    finally:
        for k, v in backup.items():
            if v:
                os.environ[k] = v

    mongo_df = _fetch_daily_mongo_data(symbol=symbol, start=start, end=end)
    if mongo_df is not None and not mongo_df.empty:
        return mongo_df

    raise RuntimeError(f"{symbol} 拉取数据失败，且MongoDB回退无数据: {last_err}")


def convert_ak_to_bars(
    df: pd.DataFrame,
    symbol: str,
    exchange: Exchange,
) -> list[BarData]:
    bars: list[BarData] = []
    for row in df.itertuples(index=False):
        dt_value = datetime.strptime(str(row.日期), "%Y-%m-%d")
        bars.append(
            BarData(
                gateway_name="AKSHARE",
                symbol=symbol,
                exchange=exchange,
                datetime=dt_value,
                interval=Interval.DAILY,
                volume=float(row.成交量),
                turnover=float(row.成交额),
                open_price=float(row.开盘),
                high_price=float(row.最高),
                low_price=float(row.最低),
                close_price=float(row.收盘),
            )
        )
    return bars


def save_bars_to_vnpy(
    symbol: str,
    exchange: Exchange,
    bars: list[BarData],
    clean_before_save: bool = True,
) -> int:
    db = get_database()
    if clean_before_save:
        db.delete_bar_data(symbol=symbol, exchange=exchange, interval=Interval.DAILY)
    db.save_bar_data(bars)
    return len(bars)


def prepare_single_symbol(
    raw_code: str,
    start: str | datetime,
    end: str | datetime,
    adjust: str = "qfq",
    clean_before_save: bool = True,
) -> tuple[str, int]:
    start_dt = parse_date(start)
    end_dt = parse_date(end)
    symbol, exchange = parse_symbol_exchange(raw_code)
    df = fetch_daily_ak_data(symbol=symbol, start=start_dt, end=end_dt, adjust=adjust)
    print(f"stock {symbol} data is {df}")
    bars = convert_ak_to_bars(df=df, symbol=symbol, exchange=exchange)
    saved_count = save_bars_to_vnpy(
        symbol=symbol,
        exchange=exchange,
        bars=bars,
        clean_before_save=clean_before_save,
    )
    return f"{symbol}.{exchange.value}", saved_count


def prepare_symbols(
    symbols: Iterable[str],
    start: str | datetime,
    end: str | datetime,
    adjust: str = "qfq",
    clean_before_save: bool = True,
    raise_on_error: bool = False,
) -> dict[str, int]:
    result: dict[str, int] = {}
    for raw_code in symbols:
        try:
            vt_symbol, count = prepare_single_symbol(
                raw_code=raw_code,
                start=start,
                end=end,
                adjust=adjust,
                clean_before_save=clean_before_save,
            )
            result[vt_symbol] = count
        except Exception as exc:
            if raise_on_error:
                raise
            print(f"prepare failed: {raw_code}, err={exc}")
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="准备 vnpy 回测所需历史数据（akshare -> vnpy_sqlite）")
    parser.add_argument("--single", default="", help="单只股票代码")
    parser.add_argument("--symbols", default="", help="多个股票代码，逗号分隔")
    parser.add_argument("--start-date", default="2024-01-01", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"), help="结束日期 YYYY-MM-DD")
    parser.add_argument("--adjust", default="qfq", choices=["", "qfq", "hfq"], help="复权类型")
    parser.add_argument("--no-clean", action="store_true", help="不清理旧数据，直接追加")
    parser.add_argument("--strict", action="store_true", help="任意一只失败即退出")
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    targets: list[str]

    if args.single:
        targets = load_massbreak_symbols([args.single])
    elif args.symbols:
        targets = load_massbreak_symbols(args.symbols)
    else:
        raise ValueError("请通过 --single 或 --symbols 显式指定标的")

    if not targets:
        raise ValueError("没有可准备的数据标的")

    prepared = prepare_symbols(
        symbols=targets,
        start=args.start_date,
        end=args.end_date,
        adjust=args.adjust,
        clean_before_save=not args.no_clean,
        raise_on_error=args.strict,
    )
    print("prepared:")
    for vt_symbol, count in prepared.items():
        print(vt_symbol, count)

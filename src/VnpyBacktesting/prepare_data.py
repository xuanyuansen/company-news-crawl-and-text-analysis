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
    "SEHK": Exchange.SEHK,
    "HK": Exchange.SEHK,
    "SMART": Exchange.SMART,
    "NYSE": Exchange.NYSE,
    "NASDAQ": Exchange.NASDAQ,
    "ARCA": Exchange.ARCA,
    "AMEX": Exchange.AMEX,
    "BATS": Exchange.BATS,
    "IEX": Exchange.IEX,
    "EDGEA": Exchange.EDGEA,
    "ISLAND": Exchange.ISLAND,
}
_US_EXCHANGE_BY_NAME = {
    "SMART": Exchange.SMART,
    "NYSE": Exchange.NYSE,
    "NASDAQ": Exchange.NASDAQ,
    "ARCA": Exchange.ARCA,
    "AMEX": Exchange.AMEX,
    "BATS": Exchange.BATS,
    "IEX": Exchange.IEX,
    "EDGEA": Exchange.EDGEA,
    "ISLAND": Exchange.ISLAND,
}
_CN_EXCHANGES = {Exchange.SSE, Exchange.SZSE, Exchange.BSE}
SUPPORTED_MARKETS = {"cn", "us", "hk"}


def parse_date(date_value: str | datetime) -> datetime:
    if isinstance(date_value, datetime):
        return date_value
    return datetime.strptime(str(date_value), "%Y-%m-%d")


def normalize_market(market: str) -> str:
    market_l = str(market).strip().lower()
    if market_l not in SUPPORTED_MARKETS:
        raise ValueError(f"不支持的 market: {market}，仅支持 cn/us/hk")
    return market_l


def _split_known_exchange_suffix(code: str) -> tuple[str, Exchange | None]:
    value = str(code).strip()
    if "." not in value:
        return value, None

    left, right = value.rsplit(".", 1)
    exchange = _SUFFIX_TO_EXCHANGE.get(right.upper())
    if exchange is None:
        return value, None
    return left, exchange


def _strip_vt_symbol_suffix(code: str) -> str:
    value, _ = _split_known_exchange_suffix(code)
    return value


def _infer_exchange(symbol: str) -> Exchange:
    if symbol.startswith(("6", "5", "9")):
        return Exchange.SSE
    if symbol.startswith(("0", "2", "3")):
        return Exchange.SZSE
    if symbol.startswith(("4", "8")):
        return Exchange.BSE
    return Exchange.SMART


def _normalize_symbol_for_exchange(symbol: str, exchange: Exchange) -> str:
    value = str(symbol).strip().upper()
    if not value:
        raise ValueError("股票代码为空")

    if exchange in _CN_EXCHANGES:
        if not value.isdigit():
            raise ValueError(f"A股代码格式错误: {symbol}")
        return value.zfill(6)

    if exchange == Exchange.SEHK:
        if not value.isdigit():
            raise ValueError(f"港股代码格式错误: {symbol}")
        return value.zfill(5)

    return value


def _normalize_ak_daily_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("无可用日线数据")

    working_df = df.copy()
    if "日期" not in working_df.columns and "date" not in working_df.columns:
        working_df = working_df.reset_index()

    def pick_col(*candidates: str) -> str:
        for col in candidates:
            if col in working_df.columns:
                return col
        raise ValueError(f"缺少必要列: {candidates}")

    date_col = pick_col("日期", "date", "datetime", "index")
    open_col = pick_col("开盘", "open")
    close_col = pick_col("收盘", "close")
    high_col = pick_col("最高", "high")
    low_col = pick_col("最低", "low")
    volume_col = pick_col("成交量", "volume")
    amount_col = next(
        (
            col
            for col in ("成交额", "amount", "money", "turnover")
            if col in working_df.columns
        ),
        "",
    )

    normalized_df = pd.DataFrame(
        {
            "日期": pd.to_datetime(working_df[date_col], errors="coerce").dt.strftime("%Y-%m-%d"),
            "开盘": pd.to_numeric(working_df[open_col], errors="coerce"),
            "收盘": pd.to_numeric(working_df[close_col], errors="coerce"),
            "最高": pd.to_numeric(working_df[high_col], errors="coerce"),
            "最低": pd.to_numeric(working_df[low_col], errors="coerce"),
            "成交量": pd.to_numeric(working_df[volume_col], errors="coerce"),
        }
    )

    if amount_col:
        normalized_df["成交额"] = pd.to_numeric(working_df[amount_col], errors="coerce")
    else:
        normalized_df["成交额"] = (
            0.25
            * (
                normalized_df["开盘"]
                + normalized_df["收盘"]
                + normalized_df["最高"]
                + normalized_df["最低"]
            )
            * normalized_df["成交量"]
        )

    normalized_df = normalized_df.dropna(subset=["日期", "开盘", "收盘", "最高", "最低", "成交量"])
    normalized_df = normalized_df.sort_values("日期").reset_index(drop=True)
    return normalized_df


def parse_symbol_exchange(raw_code: str, market: str = "cn") -> tuple[str, Exchange]:
    code = str(raw_code).strip().upper()
    if not code:
        raise ValueError("股票代码为空")

    stripped_code, explicit_exchange = _split_known_exchange_suffix(code)
    if explicit_exchange is not None:
        return _normalize_symbol_for_exchange(stripped_code, explicit_exchange), explicit_exchange

    if "." in code:
        left, right = code.split(".", 1)
        if left in _PREFIX_TO_EXCHANGE and right.isdigit():
            exchange = _PREFIX_TO_EXCHANGE[left]
            return _normalize_symbol_for_exchange(right, exchange), exchange
        if left.isdigit() and right in _PREFIX_TO_EXCHANGE:
            exchange = _PREFIX_TO_EXCHANGE[right]
            return _normalize_symbol_for_exchange(left, exchange), exchange

    market_l = normalize_market(market)

    if market_l == "cn":
        if len(code) > 2 and code[:2] in _PREFIX_TO_EXCHANGE and code[2:].isdigit():
            return code[2:].zfill(6), _PREFIX_TO_EXCHANGE[code[:2]]

        if code.isdigit():
            symbol = code.zfill(6)
            return symbol, _infer_exchange(symbol)

    elif market_l == "hk":
        if len(code) > 2 and code[:2] == "HK" and code[2:].isdigit():
            return code[2:].zfill(5), Exchange.SEHK
        if code.isdigit():
            return code.zfill(5), Exchange.SEHK

    elif market_l == "us":
        if len(code) > 3 and code[:3] == "US.":
            code = code[3:]
        if code in _US_EXCHANGE_BY_NAME:
            raise ValueError(f"美股代码格式错误: {raw_code}")
        if any(ch.isalnum() for ch in code):
            return code, Exchange.SMART

    raise ValueError(f"无法解析股票代码: {raw_code}, market={market_l}")


def to_vt_symbol(raw_code: str, market: str = "cn") -> str:
    symbol, exchange = parse_symbol_exchange(raw_code, market=market)
    return f"{symbol}.{exchange.value}"


def split_symbols_arg(symbols_text: str) -> list[str]:
    if not symbols_text:
        return []
    cleaned = symbols_text.replace("，", ",")
    return [s.strip() for s in cleaned.split(",") if s.strip()]


def load_massbreak_symbols(
    symbols: str | Iterable[str],
    top_n: int = 0,
    market: str = "cn",
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
            vt_symbol = to_vt_symbol(str(raw), market=market)
        except Exception:
            continue
        if vt_symbol not in seen:
            seen.add(vt_symbol)
            vt_symbols.append(vt_symbol)

    return vt_symbols


def _mongo_symbol_candidates(symbol: str, market: str = "cn") -> list[str]:
    market_l = normalize_market(market)
    value = _strip_vt_symbol_suffix(symbol)
    if not value:
        return []

    candidates: list[str] = []
    if market_l == "cn":
        value_l = value.lower()
        if value_l.startswith(("sh", "sz", "bj")) and len(value_l) > 2 and value_l[2:].isdigit():
            candidates.append(value_l)
            candidates.append(value_l[2:])
        elif value_l.isdigit():
            if value_l.startswith(("6", "5", "9")):
                candidates.append(f"sh{value_l}")
            elif value_l.startswith(("0", "2", "3")):
                candidates.append(f"sz{value_l}")
            elif value_l.startswith(("4", "8")):
                candidates.append(f"bj{value_l}")
            candidates.extend([f"sh{value_l}", f"sz{value_l}", f"bj{value_l}", value_l])
        else:
            candidates.append(value_l)
    elif market_l == "hk":
        if value.isdigit():
            candidates.extend([value.zfill(5), value])
        else:
            value_l = value.lower()
            if value_l.startswith("hk") and value_l[2:].isdigit():
                candidates.extend([value_l[2:].zfill(5), value_l[2:], value_l])
            else:
                candidates.extend([value, value_l])
    else:
        candidates.extend([value.upper(), value.lower(), value])

    uniq: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            uniq.append(item)
    return uniq


def _resolve_stock_database_name(market: str) -> str:
    market_l = normalize_market(market)
    try:
        from Utils import config
    except Exception:
        return "stock"

    if market_l == "cn":
        return getattr(config, "STOCK_DATABASE_NAME", "stock")
    if market_l == "hk":
        return getattr(config, "HK_STOCK_DATABASE_NAME", "stock_hk")
    return getattr(config, "US_STOCK_DATABASE_NAME", "stock_us")


def _fetch_daily_mongo_data(
    symbol: str,
    start: datetime,
    end: datetime,
    market: str = "cn",
) -> pd.DataFrame | None:
    try:
        from Utils.database import Database
    except Exception:
        return None
    print(f"fetching {symbol} data from mongo, start={start}, end={end}, market={market}")
    db_name = _resolve_stock_database_name(market)
    query = {
        "date": {
            "$gte": start.strftime("%Y-%m-%d"),
            "$lte": end.strftime("%Y-%m-%d"),
        }
    }
    keys = ["date", "open", "high", "low", "close", "volume", "amount", "turnover"]

    db = Database()
    for collection_name in _mongo_symbol_candidates(symbol, market=market):
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

        try:
            return _normalize_ak_daily_df(raw_df)
        except Exception:
            continue

    return None


def fetch_daily_ak_data(
    symbol: str,
    start: datetime,
    end: datetime,
    adjust: str = "qfq",
    max_retry: int = 3,
    market: str = "cn",
) -> pd.DataFrame:
    
    market_l = normalize_market(market)
    fetch_symbol = _strip_vt_symbol_suffix(symbol)
    last_err: Exception | None = None
    start_s = start.strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")

    def fetch_from_akshare() -> pd.DataFrame:
        print(f"fetching {symbol} data from akshare, start={start}, end={end}, adjust={adjust}, market={market}")
        if market_l == "cn":
            raw_df = ak.stock_zh_a_daily(
                symbol=fetch_symbol,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust=adjust,
            )
        elif market_l == "hk":
            raw_df = ak.stock_hk_daily(symbol=fetch_symbol, adjust=adjust)
        else:
            raw_df = ak.stock_us_daily(fetch_symbol)

        normalized_df = _normalize_ak_daily_df(raw_df)
        normalized_df = normalized_df[
            (normalized_df["日期"] >= start_s) & (normalized_df["日期"] <= end_s)
        ].reset_index(drop=True)
        if normalized_df.empty:
            raise ValueError(f"{fetch_symbol} 无可用日线数据")
        return normalized_df

    for i in range(max_retry):
        try:
            return fetch_from_akshare()
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
                return fetch_from_akshare()
            except Exception as exc:
                last_err = exc
                time.sleep(1 + i)
    finally:
        for k, v in backup.items():
            if v:
                os.environ[k] = v

    mongo_df = _fetch_daily_mongo_data(symbol=fetch_symbol, start=start, end=end, market=market_l)
    if mongo_df is not None and not mongo_df.empty:
        return mongo_df

    raise RuntimeError(f"{fetch_symbol} 拉取数据失败，且MongoDB回退无数据: {last_err}")


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
    market: str = "cn",
    clean_before_save: bool = True,
) -> tuple[str, int]:
    start_dt = parse_date(start)
    end_dt = parse_date(end)
    symbol, exchange = parse_symbol_exchange(raw_code, market=market)
    fetch_symbol = _strip_vt_symbol_suffix(symbol)
    df = fetch_daily_ak_data(symbol=fetch_symbol, start=start_dt, end=end_dt, adjust=adjust, market=market)
    # print(f"stock {symbol} data is {df}")
    bars = convert_ak_to_bars(df=df, symbol=symbol, exchange=exchange)
    vt_symbol = f"{symbol}.{exchange.value}"
    saved_count = save_bars_to_vnpy(
        symbol=symbol,
        exchange=exchange,
        bars=bars,
        clean_before_save=clean_before_save,
    )
    return vt_symbol, saved_count


def prepare_symbols(
    symbols: Iterable[str],
    start: str | datetime,
    end: str | datetime,
    adjust: str = "qfq",
    market: str = "cn",
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
                market=market,
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
    parser.add_argument("--market", default="cn", choices=["cn", "us", "hk"], help="市场类型: cn/us/hk")
    parser.add_argument("--no-clean", action="store_true", help="不清理旧数据，直接追加")
    parser.add_argument("--strict", action="store_true", help="任意一只失败即退出")
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    targets: list[str]

    if args.single:
        targets = load_massbreak_symbols([args.single], market=args.market)
    elif args.symbols:
        targets = load_massbreak_symbols(args.symbols, market=args.market)
    else:
        raise ValueError("请通过 --single 或 --symbols 显式指定标的")

    if not targets:
        raise ValueError("没有可准备的数据标的")

    prepared = prepare_symbols(
        symbols=targets,
        start=args.start_date,
        end=args.end_date,
        adjust=args.adjust,
        market=args.market,
        clean_before_save=not args.no_clean,
        raise_on_error=args.strict,
    )
    print("prepared:")
    for vt_symbol, count in prepared.items():
        print(vt_symbol, count)

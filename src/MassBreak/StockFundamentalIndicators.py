# -*- coding:utf-8 -*-
# 获取指定股票的基本面指标：PS、PE、利润同比增长、营业收入同比增长等
# 数据来源：akshare (东方财富、新浪财经等)

import akshare as ak
import pandas as pd
from typing import Optional, Dict, Any, Tuple


def normalize_stock_code(stock_code: str) -> tuple:
    """
    支持的输入格式:
    - "sh600938", "sz000547" (joint_quant_code)
    - "600938", "000547" (纯6位代码)
    - "600938.SH", "000547.SZ" (带市场后缀)

    Returns:
        tuple: (code_6digit, suffix) 如 ("600938", "SH") 或 ("000547", "SZ")
    """
    code = str(stock_code).strip().upper()
    # 移除可能的 .SH/.SZ 后缀后处理
    if "." in code:
        code, suffix = code.split(".", 1)
        suffix = suffix.upper() if suffix.upper() in ("SH", "SZ") else "SH"
    elif code.startswith("SH"):
        code = code[2:]
        suffix = "SH"
    elif code.startswith("SZ"):
        code = code[2:]
        suffix = "SZ"
    else:
        # 纯6位代码：6开头为沪市，其余一般为深市
        suffix = "SH" if code.startswith("6") else "SZ"
    return code, suffix


def get_fundamental_indicators(stock_code: str) -> Optional[Dict[str, Any]]:
    """
    包含指标:
    - pe_ttm: 市盈率(TTM)
    - pe_static: 市盈率(静)
    - ps: 市销率
    - pb: 市净率
    - revenue_yoy: 营业收入同比增长(%)
    - profit_yoy: 归属净利润同比增长(%)
    - total_market_cap: 总市值
    - latest_price: 最新价

    Args:
        stock_code: 股票代码，支持 "sh600938"、"600938"、"600938.SH" 等格式

    Returns:
        dict: 基本面指标字典，获取失败返回 None
    """
    code_6, suffix = normalize_stock_code(stock_code)
    symbol_6 = code_6
    symbol_em = f"{code_6}.{suffix}"  # 东方财富格式: 600938.SH

    result = {}

    # 1. 估值指标：PE、PS、PB 等 (东方财富 - 个股估值)
    try:
        value_df = ak.stock_value_em(symbol=symbol_6)
        if value_df is not None and not value_df.empty:
            latest = value_df.iloc[-1]
            result["pe_ttm"] = _safe_float(latest.get("PE(TTM)"))
            result["pe_static"] = _safe_float(latest.get("PE(静)"))
            result["ps"] = _safe_float(latest.get("市销率"))
            result["pb"] = _safe_float(latest.get("市净率"))
            result["total_market_cap"] = _safe_float(latest.get("总市值"))
            result["float_market_cap"] = _safe_float(latest.get("流通市值"))
            result["latest_price"] = _safe_float(latest.get("当日收盘价"))
            result["data_date"] = str(latest.get("数据日期", ""))
    except Exception as e:
        result["value_error"] = str(e)

    # 2. 财务同比增长：营业收入、净利润 (东方财富 - 主要指标)
    try:
        indicator_df = ak.stock_financial_analysis_indicator_em(
            symbol=symbol_em, indicator="按报告期"
        )
        if indicator_df is not None and not indicator_df.empty:
            latest_row = indicator_df.iloc[0]
            result["revenue_yoy"] = _safe_float(
                latest_row.get("TOTALOPERATEREVETZ")
            )  # 营业总收入同比增长(%)
            result["profit_yoy"] = _safe_float(
                latest_row.get("PARENTNETPROFITTZ")
            )  # 归属净利润同比增长(%)
            result["profit_kf_yoy"] = _safe_float(
                latest_row.get("KCFJCXSYJLRTZ")
            )  # 扣非净利润同比增长(%)
            result["revenue"] = _safe_float(latest_row.get("TOTALOPERATEREVE"))
            result["net_profit"] = _safe_float(latest_row.get("PARENTNETPROFIT"))
            result["report_date"] = str(latest_row.get("REPORT_DATE", ""))
    except Exception as e:
        result["indicator_error"] = str(e)

    if not result:
        return None
    return result


def get_fundamental_indicators_df(
    stock_code: str,
) -> Optional[Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]]:
    """
    获取指定股票的基本面指标原始 DataFrame，便于进一步分析。

    Args:
        stock_code: 股票代码

    Returns:
        (估值df, 财务指标df) 或 None
    """
    code_6, suffix = normalize_stock_code(stock_code)
    symbol_em = f"{code_6}.{suffix}"

    value_df = None
    indicator_df = None

    try:
        value_df = ak.stock_value_em(symbol=code_6)
    except Exception:
        pass

    try:
        indicator_df = ak.stock_financial_analysis_indicator_em(
            symbol=symbol_em, indicator="按报告期"
        )
    except Exception:
        pass

    if value_df is None and indicator_df is None:
        return None
    return (value_df, indicator_df)


def _safe_float(val) -> Optional[float]:
    """安全转换为 float，无效值返回 None"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def print_fundamental_indicators(stock_code: str) -> None:
    """打印指定股票的基本面指标（便于命令行使用）"""
    indicators = get_fundamental_indicators(stock_code)
    if indicators is None:
        print(f"无法获取股票 {stock_code} 的基本面数据")
        return

    print(f"\n===== {stock_code} 基本面指标 =====\n")

    # 估值指标
    if "pe_ttm" in indicators or "pe_static" in indicators:
        print("【估值指标】")
        if indicators.get("pe_ttm") is not None:
            print(f"  市盈率(TTM): {indicators['pe_ttm']:.2f}")
        if indicators.get("pe_static") is not None:
            print(f"  市盈率(静): {indicators['pe_static']:.2f}")
        if indicators.get("ps") is not None:
            print(f"  市销率(PS): {indicators['ps']:.2f}")
        if indicators.get("pb") is not None:
            print(f"  市净率(PB): {indicators['pb']:.2f}")
        if indicators.get("total_market_cap") is not None:
            cap_yi = indicators["total_market_cap"] / 1e8
            print(f"  总市值: {cap_yi:.2f} 亿元")
        if indicators.get("latest_price") is not None:
            print(f"  最新价: {indicators['latest_price']:.2f} 元")
        if indicators.get("data_date"):
            print(f"  数据日期: {indicators['data_date']}")
        print()

    # 同比增速
    if any(
        k in indicators
        for k in ("revenue_yoy", "profit_yoy", "profit_kf_yoy")
    ):
        print("【同比增长】")
        if indicators.get("revenue_yoy") is not None:
            print(f"  营业收入同比增长: {indicators['revenue_yoy']:.2f}%")
        if indicators.get("profit_yoy") is not None:
            print(f"  归属净利润同比增长: {indicators['profit_yoy']:.2f}%")
        if indicators.get("profit_kf_yoy") is not None:
            print(f"  扣非净利润同比增长: {indicators['profit_kf_yoy']:.2f}%")
        if indicators.get("report_date"):
            print(f"  报告期: {indicators['report_date']}")
        print()

    if indicators.get("value_error"):
        print(f"估值数据获取异常: {indicators['value_error']}")
    if indicators.get("indicator_error"):
        print(f"财务指标获取异常: {indicators['indicator_error']}")


if __name__ == "__main__":
    import sys

    # 默认测试股票
    test_codes = ["600938", "sh600938", "sz000547"]
    if len(sys.argv) > 1:
        test_codes = sys.argv[1:]

    for code in test_codes:
        print_fundamental_indicators(code)

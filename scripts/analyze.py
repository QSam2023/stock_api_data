#!/usr/bin/env python3
"""输出格式化的技术指标分析文本，供 LLM 阅读和总结。

用法:
    python scripts/analyze.py <股票代码> [周期天数]

示例:
    python scripts/analyze.py 600519
    python scripts/analyze.py sz000001 60

输出:
    格式化文本到标准输出
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import error_exit, fetch_fund_flow_data, fetch_kline_data, parse_stock_code


MAIN_FUND_FLOW_COL_WHITELIST = [
    "主力净流入-净额",
    "主力净流入净额",
    "主力净流入(净额)",
    "主力净流入",
]

MAIN_FUND_FLOW_BLACKLIST_TOKENS = ("净占比", "占比", "比率")


def interpret_rsi(value: float) -> str:
    if value > 80:
        return "超买"
    elif value > 60:
        return "偏强"
    elif value > 40:
        return "中性"
    elif value > 20:
        return "偏弱"
    else:
        return "超卖"


def interpret_macd(dif: float, dea: float) -> str:
    if dif > dea and dif > 0:
        return "金叉且在零轴上方，强势"
    elif dif > dea:
        return "金叉趋势"
    elif dif < dea and dif < 0:
        return "死叉且在零轴下方，弱势"
    else:
        return "死叉趋势"


def interpret_kdj(k: float, d: float, j: float) -> str:
    if j > 100:
        return "超买区"
    elif k > d and j > 50:
        return "偏多"
    elif k < d and j < 50:
        return "偏空"
    else:
        return "中性"


def interpret_boll(close: float, upper: float, mid: float, lower: float) -> str:
    if close > upper:
        return "价格突破上轨，可能超买"
    elif close > mid:
        return "价格位于中轨上方"
    elif close > lower:
        return "价格位于中轨下方"
    else:
        return "价格跌破下轨，可能超卖"


def pick_main_fund_flow_col(columns) -> Optional[str]:
    """优先匹配主力净流入净额列，避免误命中净占比。"""
    str_cols = [str(c).strip() for c in columns]
    for target in MAIN_FUND_FLOW_COL_WHITELIST:
        for col in str_cols:
            if col == target:
                return col

    for col in str_cols:
        if "主力净流入" not in col:
            continue
        if any(token in col for token in MAIN_FUND_FLOW_BLACKLIST_TOKENS):
            continue
        if "净额" in col:
            return col

    for col in str_cols:
        if "主力净流入" in col and not any(
            token in col for token in MAIN_FUND_FLOW_BLACKLIST_TOKENS
        ):
            return col

    return None


def main():
    parser = argparse.ArgumentParser(description="A 股技术指标分析")
    parser.add_argument("code", help="股票代码，如 600519 或 sh600519")
    parser.add_argument(
        "days", nargs="?", type=int, default=30, help="分析周期天数（默认: 30）"
    )
    args = parser.parse_args()

    try:
        code, market = parse_stock_code(args.code)
    except ValueError as e:
        error_exit(str(e))

    # 为了获取足够的技术指标预热数据，多取 120 天
    today = datetime.now()
    warmup_days = args.days + 120
    start_date = (today - timedelta(days=warmup_days)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    print(f"正在获取 {market}{code} 数据...", file=sys.stderr)
    df = fetch_kline_data(code, start_date, end_date)

    try:
        import pandas_ta as ta
    except ImportError:
        error_exit("未安装 pandas-ta，请运行: pip install -r requirements.txt")

    # 计算技术指标（使用全部数据以确保预热充分）
    # MACD
    macd_result = ta.macd(df["close"], fast=12, slow=26, signal=9)
    # RSI
    rsi = ta.rsi(df["close"], length=14)
    # BOLL
    bbands = ta.bbands(df["close"], length=20, std=2)
    # KDJ (Stochastic)
    stoch = ta.stoch(df["high"], df["low"], df["close"], k=9, d=3, smooth_k=3)

    # 截取分析周期内的数据
    analysis_df = df.tail(args.days)
    if analysis_df.empty:
        error_exit(f"分析周期内无数据（请求 {args.days} 天）。")

    latest = analysis_df.iloc[-1]
    first = analysis_df.iloc[0]
    latest_close = latest["close"]
    first_close = first["close"]
    change_pct = (latest_close - first_close) / first_close * 100

    # MACD
    dif_val = dea_val = hist_val = None
    macd_text = "数据不足"
    if macd_result is not None:
        macd_cols = macd_result.columns.tolist()
        dif_col = [c for c in macd_cols if "MACD_" in c and "MACDs" not in c and "MACDh" not in c]
        dea_col = [c for c in macd_cols if "MACDs" in c]
        hist_col = [c for c in macd_cols if "MACDh" in c]
        if dif_col:
            dif_val = macd_result[dif_col[0]].iloc[-1]
        if dea_col:
            dea_val = macd_result[dea_col[0]].iloc[-1]
        if hist_col:
            hist_val = macd_result[hist_col[0]].iloc[-1]
        if dif_val is not None and dea_val is not None:
            macd_text = interpret_macd(dif_val, dea_val)

    # RSI
    rsi_val = rsi.iloc[-1] if rsi is not None else None
    rsi_text = interpret_rsi(rsi_val) if rsi_val is not None else "数据不足"

    # BOLL
    boll_upper = boll_mid = boll_lower = None
    boll_text = "数据不足"
    if bbands is not None:
        upper_col = [c for c in bbands.columns if "BBU" in c]
        mid_col = [c for c in bbands.columns if "BBM" in c]
        lower_col = [c for c in bbands.columns if "BBL" in c]
        if upper_col:
            boll_upper = bbands[upper_col[0]].iloc[-1]
        if mid_col:
            boll_mid = bbands[mid_col[0]].iloc[-1]
        if lower_col:
            boll_lower = bbands[lower_col[0]].iloc[-1]
        if all(v is not None for v in [boll_upper, boll_mid, boll_lower]):
            boll_text = interpret_boll(latest_close, boll_upper, boll_mid, boll_lower)

    # KDJ
    k_val = d_val = j_val = None
    kdj_text = "数据不足"
    if stoch is not None:
        k_col = [c for c in stoch.columns if "STOCHk" in c]
        d_col = [c for c in stoch.columns if "STOCHd" in c]
        if k_col:
            k_val = stoch[k_col[0]].iloc[-1]
        if d_col:
            d_val = stoch[d_col[0]].iloc[-1]
        if k_val is not None and d_val is not None:
            j_val = 3 * k_val - 2 * d_val
            kdj_text = interpret_kdj(k_val, d_val, j_val)

    # 输出格式化分析文本
    sign = "+" if change_pct >= 0 else ""
    output = f"""股票：{market.upper()}{code}
分析周期：最近 {args.days} 个交易日（实际 {len(analysis_df)} 个交易日有数据）
最新收盘价：{latest_close:.2f} 元
涨跌幅（{args.days}日）：{sign}{change_pct:.2f}%

技术指标（最新值）：
  MACD（DIF）: {f'{dif_val:.2f}' if dif_val is not None else 'N/A'} | MACD（DEA）: {f'{dea_val:.2f}' if dea_val is not None else 'N/A'} | 柱状值: {f'{hist_val:.2f}' if hist_val is not None else 'N/A'} → {macd_text}
  RSI（14日）: {f'{rsi_val:.1f}' if rsi_val is not None else 'N/A'} → {rsi_text}
  BOLL 上轨: {f'{boll_upper:.2f}' if boll_upper is not None else 'N/A'}  中轨: {f'{boll_mid:.2f}' if boll_mid is not None else 'N/A'}  下轨: {f'{boll_lower:.2f}' if boll_lower is not None else 'N/A'} → {boll_text}
  KDJ：K={f'{k_val:.1f}' if k_val is not None else 'N/A'}  D={f'{d_val:.1f}' if d_val is not None else 'N/A'}  J={f'{j_val:.1f}' if j_val is not None else 'N/A'} → {kdj_text}
"""

    # 尝试获取资金流向（可能失败，非关键）
    fund_text = ""
    try:
        fund_df = fetch_fund_flow_data(code=code, market=market)
        if fund_df is not None and not fund_df.empty:
            if "日期" in fund_df.columns:
                fund_df = fund_df.sort_values("日期")
            recent_5 = fund_df.tail(5)
            main_col = pick_main_fund_flow_col(recent_5.columns)
            if main_col:
                values = pd.to_numeric(
                    recent_5[main_col].astype(str).str.replace(",", "", regex=False),
                    errors="coerce",
                ).dropna()
                total = float(values.sum())
                unit = "亿" if abs(total) > 1e8 else "万"
                val = total / 1e8 if abs(total) > 1e8 else total / 1e4
                sign_f = "+" if val >= 0 else ""
                fund_text = f"\n资金流向（近 5 日）：主力净流入 {sign_f}{val:.1f} {unit}\n"
            else:
                fund_text = "\n资金流向：获取成功，但未识别到“主力净流入-净额”列\n"
    except RuntimeError as e:
        fund_text = f"\n资金流向：获取失败（{e}）\n"
    except Exception:
        fund_text = "\n资金流向：获取失败（接口不可用或代码不支持）\n"

    print(output + fund_text)


if __name__ == "__main__":
    main()

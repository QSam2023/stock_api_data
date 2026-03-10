#!/usr/bin/env python3
"""
analyze.py — 计算 A 股技术指标并输出格式化分析报告

用法：
    python scripts/analyze.py <股票代码> [days=30]

示例：
    python scripts/analyze.py 600519
    python scripts/analyze.py sh600519 60
    python scripts/analyze.py sz000001 30
"""

import sys
import os
import json
import re
import glob
from datetime import datetime, timedelta

import pandas as pd
import numpy as np


def normalize_code(code: str) -> str:
    """去掉 sh/sz 前缀，返回纯数字代码"""
    code = code.strip().lower()
    if code.startswith("sh") or code.startswith("sz"):
        return code[2:]
    return code


def find_or_fetch_csv(code: str, days: int) -> str:
    """
    优先在 data/ 目录查找已有的 CSV；
    若没有或数据太旧，重新调用 fetch_kline.py 获取。
    """
    import subprocess
    os.makedirs("data", exist_ok=True)

    # 查找匹配的 CSV 文件
    pattern = f"data/{code}_*.csv"
    files = sorted(glob.glob(pattern), reverse=True)

    if files:
        # 检查最新文件的最后一行日期是否在最近 2 天内
        try:
            df_check = pd.read_csv(files[0], parse_dates=["date"])
            last_date = pd.to_datetime(df_check["date"].max())
            if (datetime.today() - last_date).days <= 3:
                return files[0]
        except Exception:
            pass

    # 重新获取
    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=days + 30)).strftime("%Y%m%d")

    print(f"📡 正在获取最新数据...", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "scripts/fetch_kline.py", code, start_date, end_date],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    csv_path = result.stdout.strip()
    return csv_path


def compute_indicators(df: pd.DataFrame) -> dict:
    """
    使用 pandas-ta 计算 MACD、RSI、BOLL、KDJ。
    返回最新指标值字典。
    """
    try:
        import pandas_ta as ta
    except ImportError:
        print("❌ 未安装 pandas-ta，请运行 pip install pandas-ta", file=sys.stderr)
        sys.exit(1)

    result = {}
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # ── MACD ──
    if len(df) >= 35:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            last = macd_df.iloc[-1]
            dif = round(float(last.iloc[0]), 4)
            dea = round(float(last.iloc[2]), 4)
            hist = round(float(last.iloc[1]), 4)
            trend = "金叉趋势 📈" if dif > dea else "死叉趋势 📉"
            result["macd"] = {"dif": dif, "dea": dea, "hist": hist, "trend": trend}

    # ── RSI ──
    if len(df) >= 15:
        rsi_series = ta.rsi(close, length=14)
        if rsi_series is not None:
            rsi_val = round(float(rsi_series.iloc[-1]), 2)
            if rsi_val >= 70:
                rsi_status = "超买区间 ⚠️"
            elif rsi_val <= 30:
                rsi_status = "超卖区间 💡"
            else:
                rsi_status = "中性偏强" if rsi_val >= 50 else "中性偏弱"
            result["rsi"] = {"value": rsi_val, "status": rsi_status}

    # ── BOLL ──
    if len(df) >= 20:
        bbands = ta.bbands(close, length=20, std=2)
        if bbands is not None and not bbands.empty:
            upper = round(float(bbands.iloc[-1, 0]), 2)
            mid = round(float(bbands.iloc[-1, 1]), 2)
            lower = round(float(bbands.iloc[-1, 2]), 2)
            last_close = round(float(close.iloc[-1]), 2)
            if last_close > upper:
                boll_pos = "突破上轨（强势）"
            elif last_close > mid:
                boll_pos = "中轨上方（偏多）"
            elif last_close > lower:
                boll_pos = "中轨下方（偏空）"
            else:
                boll_pos = "跌破下轨（弱势）"
            result["boll"] = {"upper": upper, "mid": mid, "lower": lower, "position": boll_pos}

    # ── KDJ ──
    if len(df) >= 10:
        low_min = low.rolling(9).min()
        high_max = high.rolling(9).max()
        rsv = (close - low_min) / (high_max - low_min + 1e-10) * 100
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        J = 3 * K - 2 * D

        k_val = round(float(K.iloc[-1]), 2)
        d_val = round(float(D.iloc[-1]), 2)
        j_val = round(float(J.iloc[-1]), 2)

        if k_val > d_val and K.iloc[-2] <= D.iloc[-2]:
            kdj_signal = "K线上穿D线，金叉买入信号 📈"
        elif k_val < d_val and K.iloc[-2] >= D.iloc[-2]:
            kdj_signal = "K线下穿D线，死叉卖出信号 📉"
        elif k_val > 80:
            kdj_signal = "超买区间，注意回调风险"
        elif k_val < 20:
            kdj_signal = "超卖区间，关注反弹机会"
        else:
            kdj_signal = "偏多" if k_val > 50 else "偏空"

        result["kdj"] = {"K": k_val, "D": d_val, "J": j_val, "signal": kdj_signal}

    return result


def get_stock_name(code: str) -> str:
    """尝试通过 AKShare 获取股票名称，失败则返回代码"""
    try:
        import akshare as ak
        spot = ak.stock_zh_a_spot_em()
        row = spot[spot["代码"] == code]
        if not row.empty:
            return str(row.iloc[0]["名称"])
    except Exception:
        pass
    return code


def format_report(code: str, df: pd.DataFrame, indicators: dict, days: int) -> str:
    """生成格式化的文本分析报告"""
    name = get_stock_name(code)
    last_close = round(float(df["close"].iloc[-1]), 2)
    first_close = round(float(df["close"].iloc[0]), 2)
    pct_change = round((last_close - first_close) / first_close * 100, 2)
    pct_str = f"+{pct_change}%" if pct_change >= 0 else f"{pct_change}%"

    lines = [
        f"{'='*50}",
        f"股票：{name}（{code}）",
        f"分析周期：最近 {days} 个交易日",
        f"最新收盘价：{last_close} 元",
        f"涨跌幅（{days}日）：{pct_str}",
        f"{'='*50}",
        "",
        "【技术指标（最新值）】",
    ]

    if "macd" in indicators:
        m = indicators["macd"]
        lines.append(f"  MACD（DIF）: {m['dif']}  |  DEA: {m['dea']}  |  柱状值: {m['hist']}  → {m['trend']}")

    if "rsi" in indicators:
        r = indicators["rsi"]
        lines.append(f"  RSI（14日）: {r['value']}  → {r['status']}")

    if "boll" in indicators:
        b = indicators["boll"]
        lines.append(f"  BOLL 上轨: {b['upper']}  中轨: {b['mid']}  下轨: {b['lower']}  → {b['position']}")

    if "kdj" in indicators:
        k = indicators["kdj"]
        lines.append(f"  KDJ：K={k['K']}  D={k['D']}  J={k['J']}  → {k['signal']}")

    # 资金流向（尝试获取，失败跳过）
    lines.append("")
    lines.append("【资金流向】")
    try:
        import akshare as ak
        flow_df = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith("6") else "sz")
        if flow_df is not None and len(flow_df) >= 5:
            recent = flow_df.tail(5)
            total_net = round(recent["主力净流入-净额"].sum() / 1e8, 2)
            sign = "+" if total_net >= 0 else ""
            lines.append(f"  近 5 日主力净流入：{sign}{total_net} 亿")
        else:
            lines.append("  近 5 日资金流向：数据暂不可用")
    except Exception:
        lines.append("  近 5 日资金流向：数据暂不可用")

    lines.append("")
    lines.append(f"{'='*50}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/analyze.py <股票代码> [days=30]", file=sys.stderr)
        sys.exit(1)

    code_raw = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) >= 3 else 30
    code = normalize_code(code_raw)

    # 获取数据
    csv_path = find_or_fetch_csv(code, days)
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 只取最近 days 条
    df_recent = df.tail(days).reset_index(drop=True)

    if df_recent.empty:
        print(f"❌ 数据不足，无法分析", file=sys.stderr)
        sys.exit(1)

    # 计算指标
    indicators = compute_indicators(df_recent)

    # 打印报告
    report = format_report(code, df_recent, indicators, days)
    print(report)

    # 最后一行输出 JSON，方便程序解析
    json_data = {
        "code": code,
        "days": days,
        "last_close": round(float(df_recent["close"].iloc[-1]), 2),
        "indicators": indicators,
    }
    print(f"JSON_DATA: {json.dumps(json_data, ensure_ascii=False)}")
    sys.exit(0)


if __name__ == "__main__":
    main()

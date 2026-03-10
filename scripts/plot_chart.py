#!/usr/bin/env python3
"""读取 K 线 CSV 并生成专业 K 线图。

用法:
    python scripts/plot_chart.py <CSV路径> [--indicators ma,macd,boll,rsi]

示例:
    python scripts/plot_chart.py data/600519_20240101_20241231.csv
    python scripts/plot_chart.py data/600519_20240101_20241231.csv --indicators ma,macd,rsi

输出:
    output/<股票代码>_chart.png
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import OUTPUT_DIR, ensure_dirs, error_exit


def load_csv(csv_path: str):
    """加载 CSV 并转换为 mplfinance 要求的格式。"""
    import pandas as pd

    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        error_exit(f"文件不存在: {csv_path}")
    except Exception as e:
        error_exit(f"读取 CSV 失败: {e}")

    if df.empty:
        error_exit("CSV 文件为空，无法绘图。")

    # 确保列名正确
    required = {"date", "open", "close", "high", "low", "volume"}
    if not required.issubset(set(df.columns)):
        error_exit(f"CSV 缺少必要列。需要: {required}，实际: {set(df.columns)}")

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    df = df.sort_index()

    return df


def compute_indicators(df, indicators: list[str]):
    """计算技术指标，返回 (addplot_list, panel_count)。"""
    import mplfinance as mpf
    import pandas_ta as ta

    plots = []
    panel = 2  # panel 0 = 主图, panel 1 = 成交量

    if "ma" in indicators:
        for period in [5, 10, 20, 60]:
            col = f"MA{period}"
            df[col] = ta.sma(df["close"], length=period)
            if df[col].notna().any():
                plots.append(mpf.make_addplot(df[col], panel=0, width=0.8))

    if "boll" in indicators:
        bbands = ta.bbands(df["close"], length=20, std=2)
        if bbands is not None:
            for col_name in bbands.columns:
                df[col_name] = bbands[col_name]
            upper = [c for c in bbands.columns if "BBU" in c]
            mid = [c for c in bbands.columns if "BBM" in c]
            lower = [c for c in bbands.columns if "BBL" in c]
            if upper:
                plots.append(
                    mpf.make_addplot(df[upper[0]], panel=0, color="purple", width=0.7)
                )
            if mid:
                plots.append(
                    mpf.make_addplot(df[mid[0]], panel=0, color="orange", width=0.7)
                )
            if lower:
                plots.append(
                    mpf.make_addplot(df[lower[0]], panel=0, color="purple", width=0.7)
                )

    if "macd" in indicators:
        macd_result = ta.macd(df["close"], fast=12, slow=26, signal=9)
        if macd_result is not None:
            for col_name in macd_result.columns:
                df[col_name] = macd_result[col_name]
            macd_col = [c for c in macd_result.columns if "MACD_" in c and "MACDs" not in c and "MACDh" not in c]
            signal_col = [c for c in macd_result.columns if "MACDs" in c]
            hist_col = [c for c in macd_result.columns if "MACDh" in c]

            if macd_col:
                plots.append(
                    mpf.make_addplot(
                        df[macd_col[0]], panel=panel, color="blue", width=0.8
                    )
                )
            if signal_col:
                plots.append(
                    mpf.make_addplot(
                        df[signal_col[0]], panel=panel, color="red", width=0.8
                    )
                )
            if hist_col:
                colors = [
                    "green" if v >= 0 else "red"
                    for v in df[hist_col[0]].fillna(0)
                ]
                plots.append(
                    mpf.make_addplot(
                        df[hist_col[0]],
                        panel=panel,
                        type="bar",
                        color=colors,
                        width=0.6,
                    )
                )
            panel += 1

    if "rsi" in indicators:
        rsi = ta.rsi(df["close"], length=14)
        if rsi is not None:
            df["RSI_14"] = rsi
            plots.append(
                mpf.make_addplot(df["RSI_14"], panel=panel, color="magenta", width=0.8)
            )
            panel += 1

    return plots


def main():
    parser = argparse.ArgumentParser(description="生成 K 线图")
    parser.add_argument("csv_path", help="K 线数据 CSV 文件路径")
    parser.add_argument(
        "--indicators",
        default="ma,macd",
        help="叠加指标，逗号分隔（可选: ma,macd,boll,rsi）默认: ma,macd",
    )
    args = parser.parse_args()

    # 解析指标列表
    indicators = [i.strip().lower() for i in args.indicators.split(",") if i.strip()]
    valid = {"ma", "macd", "boll", "rsi"}
    invalid = set(indicators) - valid
    if invalid:
        error_exit(f"不支持的指标: {invalid}。可选: {valid}")

    print(f"正在加载数据: {args.csv_path}")
    df = load_csv(args.csv_path)
    print(f"数据行数: {len(df)}，指标: {indicators}")

    # 计算指标并构建副图
    import mplfinance as mpf

    addplots = compute_indicators(df, indicators)

    # 从文件名提取股票代码
    csv_name = Path(args.csv_path).stem
    code_match = re.match(r"(\d{6})", csv_name)
    code_label = code_match.group(1) if code_match else csv_name

    # 绘图
    ensure_dirs()
    output_path = OUTPUT_DIR / f"{code_label}_chart.png"

    style = mpf.make_mpf_style(
        base_mpf_style="charles",
        rc={"font.size": 9},
    )

    kwargs = {
        "type": "candle",
        "volume": True,
        "style": style,
        "title": f"{code_label} K线图",
        "figsize": (14, 8),
        "savefig": str(output_path),
        "warn_too_much_data": 500,
    }
    if addplots:
        kwargs["addplot"] = addplots

    mpf.plot(df, **kwargs)
    print(f"图表已保存: {output_path}")


if __name__ == "__main__":
    main()

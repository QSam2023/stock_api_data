#!/usr/bin/env python3
"""
plot_chart.py — 读取 K 线 CSV，生成专业蜡烛图（.png）

用法：
    python scripts/plot_chart.py <CSV路径> [--indicators ma,macd,boll,rsi,kdj]

示例：
    python scripts/plot_chart.py data/600519_20240101_20241231.csv
    python scripts/plot_chart.py data/600519.csv --indicators ma,macd,boll
    python scripts/plot_chart.py data/000001.csv --indicators ma,macd,rsi,kdj
"""

import sys
import os
import argparse
import re

import pandas as pd
import numpy as np


def setup_chinese_font():
    """配置 matplotlib 中文字体，自动检测系统可用字体"""
    import matplotlib
    import matplotlib.pyplot as plt

    font_candidates = [
        "SimHei",
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
        "Source Han Sans CN",
    ]
    from matplotlib.font_manager import findfont, FontProperties
    for font in font_candidates:
        try:
            path = findfont(FontProperties(family=font), fallback_to_default=False)
            if path and "DejaVu" not in path:
                matplotlib.rcParams["font.family"] = font
                matplotlib.rcParams["axes.unicode_minus"] = False
                return font
        except Exception:
            continue

    # 回退：使用默认字体，关闭 unicode minus 避免报错
    matplotlib.rcParams["axes.unicode_minus"] = False
    return "default"


def load_csv(csv_path: str) -> pd.DataFrame:
    """读取 K 线 CSV，返回标准化 DataFrame"""
    if not os.path.exists(csv_path):
        print(f"❌ 文件不存在：{csv_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    required = ["date", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"❌ CSV 缺少必要列：{missing}", file=sys.stderr)
        sys.exit(1)

    df = df.set_index("date")
    return df


def extract_code_from_path(csv_path: str) -> str:
    """从 CSV 路径提取股票代码"""
    base = os.path.basename(csv_path)
    match = re.match(r"(\d{6})", base)
    return match.group(1) if match else base.replace(".csv", "")


def plot_chart(csv_path: str, indicators: list[str]):
    """
    生成 K 线图并保存为 PNG。

    参数：
        csv_path: K 线 CSV 文件路径
        indicators: 要叠加的指标列表，如 ['ma', 'macd', 'boll', 'rsi']
    """
    import mplfinance as mpf
    import matplotlib.pyplot as plt

    font_used = setup_chinese_font()
    df = load_csv(csv_path)
    code = extract_code_from_path(csv_path)

    if len(df) < 5:
        print(f"❌ 数据量不足（{len(df)} 条），无法生成图表", file=sys.stderr)
        sys.exit(1)

    # 确保 output/ 目录存在
    os.makedirs("output", exist_ok=True)
    out_path = f"output/{code}_chart.png"

    # ── 均线配置 ──
    ma_colors = {"ma5": "#FF6B35", "ma10": "#FFB347", "ma20": "#4ECDC4", "ma60": "#45B7D1"}
    addplots = []

    if "ma" in indicators:
        for period, color in [(5, "#FF6B35"), (10, "#FFB347"), (20, "#4ECDC4"), (60, "#45B7D1")]:
            if len(df) >= period:
                ma = df["close"].rolling(period).mean()
                addplots.append(mpf.make_addplot(ma, color=color, width=1.0, label=f"MA{period}"))

    # ── BOLL 布林带（叠加主图）──
    if "boll" in indicators and len(df) >= 20:
        mid = df["close"].rolling(20).mean()
        std = df["close"].rolling(20).std()
        upper = mid + 2 * std
        lower = mid - 2 * std
        addplots.append(mpf.make_addplot(upper, color="#9B59B6", width=0.8, linestyle="--", label="BOLL上轨"))
        addplots.append(mpf.make_addplot(mid, color="#8E44AD", width=0.8, label="BOLL中轨"))
        addplots.append(mpf.make_addplot(lower, color="#9B59B6", width=0.8, linestyle="--", label="BOLL下轨"))

    # ── 副图：MACD ──
    macd_plots = []
    if "macd" in indicators and len(df) >= 35:
        exp12 = df["close"].ewm(span=12, adjust=False).mean()
        exp26 = df["close"].ewm(span=26, adjust=False).mean()
        dif = exp12 - exp26
        dea = dif.ewm(span=9, adjust=False).mean()
        hist = (dif - dea) * 2

        colors_hist = ["#E74C3C" if v >= 0 else "#2ECC71" for v in hist]
        macd_plots = [
            mpf.make_addplot(dif, panel=2, color="#E74C3C", width=1.0, ylabel="MACD", label="DIF"),
            mpf.make_addplot(dea, panel=2, color="#3498DB", width=1.0, label="DEA"),
            mpf.make_addplot(hist, panel=2, type="bar", color=colors_hist, alpha=0.7),
        ]

    # ── 副图：RSI ──
    rsi_plots = []
    if "rsi" in indicators and len(df) >= 15:
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        panel_rsi = 3 if "macd" in indicators else 2
        rsi_plots = [
            mpf.make_addplot(rsi, panel=panel_rsi, color="#F39C12", width=1.2, ylabel="RSI(14)", label="RSI"),
            mpf.make_addplot(pd.Series(70, index=df.index), panel=panel_rsi, color="#E74C3C", width=0.5, linestyle="--", alpha=0.5),
            mpf.make_addplot(pd.Series(30, index=df.index), panel=panel_rsi, color="#2ECC71", width=0.5, linestyle="--", alpha=0.5),
        ]

    # ── 副图：KDJ ──
    kdj_plots = []
    if "kdj" in indicators and len(df) >= 10:
        low_min = df["low"].rolling(9).min()
        high_max = df["high"].rolling(9).max()
        rsv = (df["close"] - low_min) / (high_max - low_min + 1e-10) * 100
        K = rsv.ewm(com=2, adjust=False).mean()
        D = K.ewm(com=2, adjust=False).mean()
        J = 3 * K - 2 * D

        panel_kdj = 2
        if "macd" in indicators:
            panel_kdj += 1
        if "rsi" in indicators:
            panel_kdj += 1

        kdj_plots = [
            mpf.make_addplot(K, panel=panel_kdj, color="#E74C3C", width=1.0, ylabel="KDJ", label="K"),
            mpf.make_addplot(D, panel=panel_kdj, color="#3498DB", width=1.0, label="D"),
            mpf.make_addplot(J, panel=panel_kdj, color="#9B59B6", width=1.0, label="J"),
        ]

    all_addplots = addplots + macd_plots + rsi_plots + kdj_plots

    # ── 计算副图数量，动态调整图高比例 ──
    num_panels = 1  # 主图
    if macd_plots:
        num_panels += 1
    if rsi_plots:
        num_panels += 1
    if kdj_plots:
        num_panels += 1

    panel_ratios = [4] + [1.5] * (num_panels - 1) + [1]  # 最后 1 是成交量
    if num_panels == 1:
        panel_ratios = [4, 1]

    # ── 图表样式 ──
    mc = mpf.make_marketcolors(
        up="#E74C3C", down="#2ECC71",
        edge="inherit",
        wick="inherit",
        volume={"up": "#E74C3C", "down": "#2ECC71"},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle="--",
        gridcolor="#F0F0F0",
        facecolor="#FAFAFA",
        figcolor="#FFFFFF",
        rc={"axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8},
    )

    date_range = f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}"
    title = f"{code}  {date_range}  ({len(df)} 日)"

    kwargs = dict(
        type="candle",
        style=style,
        title=title,
        ylabel="价格（元）",
        ylabel_lower="成交量",
        volume=True,
        figsize=(14, 4 + 2.5 * (num_panels - 1)),
        savefig=dict(fname=out_path, dpi=150, bbox_inches="tight"),
        warn_too_much_data=999999,
    )
    if all_addplots:
        kwargs["addplot"] = all_addplots

    try:
        mpf.plot(df, **kwargs)
        plt.close("all")
    except Exception as e:
        print(f"❌ 绘图失败：{e}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ 图表已保存：{out_path}", file=sys.stderr)
    print(out_path)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="A股K线图生成工具")
    parser.add_argument("csv_path", help="K线CSV文件路径")
    parser.add_argument("--indicators", default="ma", help="叠加指标，逗号分隔：ma,macd,boll,rsi,kdj")
    args = parser.parse_args()

    indicators = [i.strip().lower() for i in args.indicators.split(",")]
    plot_chart(args.csv_path, indicators)


if __name__ == "__main__":
    main()

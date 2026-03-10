#!/usr/bin/env python3
"""
fetch_kline.py — 获取 A 股 K 线数据并保存为 CSV

用法：
    python scripts/fetch_kline.py <股票代码> [start_date] [end_date]

示例：
    python scripts/fetch_kline.py 600519
    python scripts/fetch_kline.py sh600519 20240101 20241231
    python scripts/fetch_kline.py sz000001 20230601 20231231
"""

import sys
import os
import re
from datetime import datetime, timedelta

import pandas as pd


def normalize_code(code: str) -> str:
    """将股票代码统一转换为纯数字格式（去掉 sh/sz 前缀）"""
    code = code.strip().lower()
    if code.startswith("sh") or code.startswith("sz"):
        return code[2:]
    return code


def get_default_dates() -> tuple[str, str]:
    """默认取最近 90 个自然日的数据"""
    end = datetime.today()
    start = end - timedelta(days=90)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def fetch_kline(code_raw: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    通过 AKShare 获取日 K 线数据。

    参数：
        code_raw: 股票代码（支持 sh/sz 前缀或纯数字）
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD

    返回：
        包含 OHLCV 数据的 DataFrame
    """
    try:
        import akshare as ak
    except ImportError:
        print("❌ 错误：未安装 akshare，请运行 pip install akshare", file=sys.stderr)
        sys.exit(1)

    code = normalize_code(code_raw)

    # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（akshare 要求）
    start_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
    end_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

    print(f"📡 正在获取 {code} 的 K 线数据（{start_fmt} ~ {end_fmt}）...", file=sys.stderr)

    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_fmt,
            end_date=end_fmt,
            adjust="qfq",  # 前复权
        )
    except Exception as e:
        print(f"❌ 数据获取失败：{e}", file=sys.stderr)
        print("  请检查：1) 股票代码是否正确  2) 网络连接是否正常  3) 日期范围是否有交易数据", file=sys.stderr)
        sys.exit(1)

    if df is None or df.empty:
        print(f"❌ 未获取到数据：股票代码 {code} 在指定日期范围内无数据", file=sys.stderr)
        sys.exit(1)

    # 列名标准化
    col_map = {
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "price_change",
        "换手率": "turnover",
    }
    df = df.rename(columns=col_map)

    # 保留核心字段
    keep_cols = [c for c in ["date", "open", "high", "low", "close", "volume", "amount"] if c in df.columns]
    df = df[keep_cols].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    return df


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/fetch_kline.py <股票代码> [start_date YYYYMMDD] [end_date YYYYMMDD]", file=sys.stderr)
        print("示例：python scripts/fetch_kline.py 600519 20240101 20241231", file=sys.stderr)
        sys.exit(1)

    code_raw = sys.argv[1]
    start_date, end_date = get_default_dates()

    if len(sys.argv) >= 3:
        start_date = sys.argv[2]
    if len(sys.argv) >= 4:
        end_date = sys.argv[3]

    # 日期格式校验
    for d, label in [(start_date, "start_date"), (end_date, "end_date")]:
        if not re.match(r"^\d{8}$", d):
            print(f"❌ 日期格式错误（{label}={d}），应为 YYYYMMDD", file=sys.stderr)
            sys.exit(1)

    df = fetch_kline(code_raw, start_date, end_date)
    code = normalize_code(code_raw)

    # 确保 data/ 目录存在
    os.makedirs("data", exist_ok=True)
    out_path = f"data/{code}_{start_date}_{end_date}.csv"
    df.to_csv(out_path, index=False)

    print(f"✅ 数据已保存：{out_path}（共 {len(df)} 条记录）", file=sys.stderr)
    print(f"\n📊 最近 5 行预览：", file=sys.stderr)
    print(df.tail(5).to_string(index=False), file=sys.stderr)

    # stdout 输出 CSV 路径，供其他脚本调用
    print(out_path)
    sys.exit(0)


if __name__ == "__main__":
    main()

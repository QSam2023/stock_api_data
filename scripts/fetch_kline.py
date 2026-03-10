#!/usr/bin/env python3
"""获取 A 股 K 线数据并保存为 CSV。

用法:
    python scripts/fetch_kline.py <股票代码> [开始日期] [结束日期]

示例:
    python scripts/fetch_kline.py 600519
    python scripts/fetch_kline.py sh600519 20240101 20241231

输出:
    data/<股票代码>_<开始日期>_<结束日期>.csv
"""

import argparse
import sys
from datetime import datetime, timedelta

# 将 scripts/ 目录加入 path 以支持直接运行
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import (
    DATA_DIR,
    ensure_dirs,
    error_exit,
    fetch_kline_data,
    parse_stock_code,
)


def main():
    parser = argparse.ArgumentParser(description="获取 A 股 K 线数据")
    parser.add_argument("code", help="股票代码，如 600519 或 sh600519")
    parser.add_argument(
        "start_date",
        nargs="?",
        default=None,
        help="开始日期 YYYYMMDD（默认: 90天前）",
    )
    parser.add_argument(
        "end_date",
        nargs="?",
        default=None,
        help="结束日期 YYYYMMDD（默认: 今天）",
    )
    args = parser.parse_args()

    # 解析股票代码
    try:
        code, market = parse_stock_code(args.code)
    except ValueError as e:
        error_exit(str(e))

    # 处理日期
    today = datetime.now()
    end_date = args.end_date or today.strftime("%Y%m%d")
    if args.start_date:
        start_date = args.start_date
    else:
        start_date = (today - timedelta(days=90)).strftime("%Y%m%d")

    print(f"正在获取 {market}{code} 的日K数据 ({start_date} ~ {end_date}) ...")

    # 获取数据
    df = fetch_kline_data(code, start_date, end_date)

    # 保存 CSV
    ensure_dirs()
    filename = f"{code}_{start_date}_{end_date}.csv"
    filepath = DATA_DIR / filename
    df.to_csv(filepath, index=False, encoding="utf-8-sig")

    print(f"数据已保存: {filepath}")
    print(f"共 {len(df)} 条记录")


if __name__ == "__main__":
    main()

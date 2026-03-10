"""共享工具函数：股票代码解析、目录管理、AKShare 数据获取封装。"""

import os
import re
import sys
from pathlib import Path

# 项目根目录（scripts/ 的上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"


def ensure_dirs():
    """确保 data/ 和 output/ 目录存在。"""
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def parse_stock_code(raw_code: str) -> tuple[str, str]:
    """解析用户输入的股票代码，返回 (纯数字代码, 市场前缀)。

    支持格式：
      - 纯数字：600519, 000001
      - 带前缀：sh600519, sz000001, SH600519, SZ000001

    Returns:
        (code, market) 例如 ("600519", "sh") 或 ("000001", "sz")

    Raises:
        ValueError: 无法识别的代码格式
    """
    raw = raw_code.strip().lower()

    # 带 sh/sz 前缀
    m = re.match(r"^(sh|sz)(\d{6})$", raw)
    if m:
        return m.group(2), m.group(1)

    # 纯 6 位数字，根据首位推断市场
    m = re.match(r"^(\d{6})$", raw)
    if m:
        code = m.group(1)
        if code.startswith(("6", "9")):
            return code, "sh"
        elif code.startswith(("0", "2", "3")):
            return code, "sz"
        else:
            return code, "sh"  # 默认上交所

    raise ValueError(
        f"无法识别的股票代码格式: '{raw_code}'。"
        f"请使用 6 位纯数字（如 600519）或带前缀格式（如 sh600519）。"
    )


def format_market_code(code: str, market: str) -> str:
    """返回带市场前缀的代码，如 sh600519。"""
    return f"{market}{code}"


def error_exit(msg: str, exit_code: int = 1):
    """打印错误信息并以非 0 退出码退出。"""
    print(f"错误: {msg}", file=sys.stderr)
    sys.exit(exit_code)


def fetch_kline_data(code: str, start_date: str, end_date: str):
    """通过 AKShare 获取日 K 线数据。

    Args:
        code: 纯 6 位数字代码
        start_date: YYYYMMDD 格式
        end_date: YYYYMMDD 格式

    Returns:
        pandas DataFrame，包含 日期/开盘/收盘/最高/最低/成交量/成交额 列
    """
    try:
        import akshare as ak
    except ImportError:
        error_exit("未安装 akshare，请运行: pip install -r requirements.txt")

    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",  # 前复权
        )
    except Exception as e:
        error_exit(f"获取股票 {code} 数据失败: {e}")

    if df is None or df.empty:
        error_exit(f"股票 {code} 在 {start_date}~{end_date} 期间无数据。")

    # 统一列名
    col_map = {
        "日期": "date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
    }
    df = df.rename(columns=col_map)

    # 只保留需要的列（AKShare 可能返回额外列）
    keep_cols = ["date", "open", "close", "high", "low", "volume", "amount"]
    available = [c for c in keep_cols if c in df.columns]
    df = df[available]

    return df

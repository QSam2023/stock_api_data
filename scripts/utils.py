"""共享工具函数：股票代码解析、目录管理、AKShare 数据获取封装。"""

import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime
from pathlib import Path
from typing import Optional

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


def parse_yyyymmdd(date_str: str, field_name: str = "日期") -> datetime:
    """校验 YYYYMMDD 日期格式并返回 datetime 对象。"""
    if not re.fullmatch(r"\d{8}", date_str):
        raise ValueError(f"{field_name}格式错误: {date_str}，应为 YYYYMMDD。")

    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError as e:
        raise ValueError(f"{field_name}不是有效日期: {date_str}。") from e


def _is_retryable_ak_error(err: Exception) -> bool:
    """判断 AKShare 错误是否属于可重试的网络/服务抖动。"""
    msg = str(err).lower()
    retryable_keywords = (
        "timeout",
        "timed out",
        "connection",
        "proxy",
        "dns",
        "temporar",
        "429",
        "502",
        "503",
        "504",
        "max retries",
        "reset by peer",
        "read timed out",
        "connecttimeout",
        "readtimeout",
    )
    return any(k in msg for k in retryable_keywords)


def run_akshare_with_retry(
    call,
    operation: str,
    retries: int = 3,
    timeout_sec: int = 15,
    retry_delay_sec: float = 1.0,
):
    """执行 AKShare 请求，提供超时、有限重试与错误分类信息。"""
    last_err: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(call)
        try:
            result = future.result(timeout=timeout_sec)
            executor.shutdown(wait=False, cancel_futures=False)
            return result
        except FutureTimeoutError as err:
            last_err = err
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            if attempt < retries:
                time.sleep(retry_delay_sec)
            continue
        except Exception as err:  # noqa: BLE001
            last_err = err
            executor.shutdown(wait=False, cancel_futures=True)
            if _is_retryable_ak_error(err) and attempt < retries:
                time.sleep(retry_delay_sec)
                continue
            break

    if isinstance(last_err, FutureTimeoutError):
        raise RuntimeError(
            f"{operation}失败：请求超时（{timeout_sec}s），已重试 {retries} 次。"
        ) from last_err

    if last_err is not None and _is_retryable_ak_error(last_err):
        raise RuntimeError(
            f"{operation}失败：网络抖动或服务暂不可用，已重试 {retries} 次。原始错误: {last_err}"
        ) from last_err

    raise RuntimeError(
        f"{operation}失败：参数或接口响应异常（不可重试）。原始错误: {last_err}"
    ) from last_err


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
        df = run_akshare_with_retry(
            lambda: ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",  # 前复权
            ),
            operation=f"获取股票 {code} 日K数据",
            retries=3,
            timeout_sec=15,
            retry_delay_sec=1.0,
        )
    except RuntimeError as e:
        error_exit(str(e))

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


def fetch_fund_flow_data(code: str, market: str):
    """通过 AKShare 获取个股资金流向，带超时与重试。"""
    try:
        import akshare as ak
    except ImportError:
        error_exit("未安装 akshare，请运行: pip install -r requirements.txt")

    return run_akshare_with_retry(
        lambda: ak.stock_individual_fund_flow(stock=code, market=market),
        operation=f"获取股票 {market}{code} 资金流",
        retries=2,
        timeout_sec=12,
        retry_delay_sec=1.0,
    )

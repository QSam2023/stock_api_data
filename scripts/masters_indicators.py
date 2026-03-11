#!/usr/bin/env python3
"""
masters_indicators.py — 大师级量价指标过滤模型

基于 reference_strategy.md 的三步过滤逻辑：
    Step 1: 温斯顿 & 欧奈尔均线过滤（防守）
    Step 2: 威科夫量价体检（透视）
    Step 3: 达瓦斯 & 利弗莫尔突破信号（进攻）

用法：
    python scripts/masters_indicators.py <股票代码> [days=250]

示例：
    python scripts/masters_indicators.py 600519
    python scripts/masters_indicators.py sz000001 250
"""

import sys
import os
import json
import glob
import subprocess
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np


def _format_ratio(numerator: float, denominator: float) -> str:
    """安全格式化比值，避免分母为 0 时崩溃。"""
    if denominator == 0:
        if numerator == 0:
            return "1.00"
        return "∞"
    return f"{numerator / denominator:.2f}"


def normalize_code(code: str) -> str:
    """去掉 sh/sz 前缀，返回纯数字代码"""
    code = code.strip().lower()
    if code.startswith("sh") or code.startswith("sz"):
        return code[2:]
    return code


def _extract_saved_csv_path(stdout_text: str) -> Optional[str]:
    """从 fetch_kline 输出中提取 CSV 路径。"""
    for raw_line in stdout_text.splitlines():
        line = raw_line.strip()
        if line.startswith("数据已保存:"):
            path = line.split(":", 1)[1].strip()
            if path:
                return path
    return None


def _safe_mtime(path: str) -> float:
    """获取文件修改时间；文件不存在时返回 0，便于回退排序。"""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def find_or_fetch_csv(code: str, days: int) -> str:
    """查找已有 CSV 或重新获取"""
    os.makedirs("data", exist_ok=True)
    pattern = f"data/{code}_*.csv"
    files = sorted(glob.glob(pattern), reverse=True)

    if files:
        try:
            df_check = pd.read_csv(files[0], parse_dates=["date"])
            last_date = pd.to_datetime(df_check["date"].max())
            if len(df_check) >= days and (datetime.today() - last_date).days <= 3:
                return files[0]
        except Exception:
            pass

    end_date = datetime.today().strftime("%Y%m%d")
    start_date = (datetime.today() - timedelta(days=days + 60)).strftime("%Y%m%d")

    print(f"📡 正在获取 {days} 日 K 线数据...", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "scripts/fetch_kline.py", code, start_date, end_date],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    parsed_path = _extract_saved_csv_path(result.stdout)
    if parsed_path and os.path.exists(parsed_path):
        return parsed_path

    # 兼容输出格式变化：回退到抓取后最新匹配文件
    files = sorted(glob.glob(pattern), key=_safe_mtime, reverse=True)
    if files:
        return files[0]

    print("错误: 拉取K线成功，但未能定位生成的 CSV 文件路径。", file=sys.stderr)
    print(result.stdout, file=sys.stderr)
    sys.exit(1)


def step1_weinstein_filter(df: pd.DataFrame) -> dict:
    """
    Step 1: 温斯顿四阶段 + 欧奈尔均线过滤
    条件：
    - Close > 150日均线
    - 150日均线斜率 > 0（过去20日斜率，用线性回归斜率判断）
    """
    result = {"name": "温斯顿均线过滤", "status": "FAIL", "details": []}

    if len(df) < 150:
        result["status"] = "NEUTRAL"
        result["details"].append(f"⚠️ 数据量不足 150 日（当前 {len(df)} 日），无法判断")
        return result

    ma150 = df["close"].rolling(150).mean()
    last_ma150 = float(ma150.iloc[-1])
    last_close = float(df["close"].iloc[-1])

    # 计算 150 日均线最近 20 日的斜率（归一化）
    recent_ma = ma150.iloc[-20:].values
    x = np.arange(len(recent_ma))
    slope = np.polyfit(x, recent_ma, 1)[0]
    slope_pct = slope / last_ma150 * 100  # 转为百分比变化

    cond1 = last_close > last_ma150
    cond2 = slope_pct > 0

    result["details"].append(f"当前收盘价：{last_close:.2f}  |  150日均线：{last_ma150:.2f}")
    result["details"].append(f"150日均线斜率（近20日）：{slope_pct:.4f}%/日  →  {'向上 ✅' if cond2 else '向下 ❌'}")
    result["details"].append(f"收盘价 > 150日均线：{'✅ 是' if cond1 else '❌ 否'}")

    if cond1 and cond2:
        result["status"] = "PASS"
        result["details"].append("🟢 判断：股价在生命线上方且均线向上，处于温斯顿第二阶段（上升期）")
    elif not cond1:
        result["status"] = "FAIL"
        result["details"].append("🔴 判断：股价低于150日均线，拒绝进入（可能处于第三/四阶段）")
    else:
        result["status"] = "FAIL"
        result["details"].append("🔴 判断：150日均线仍向下倾斜，趋势未确立，观望")

    return result


def step2_wyckoff_volume(df: pd.DataFrame) -> dict:
    """
    Step 2: 威科夫量价体检
    逻辑：最近 10 个交易日，上涨日平均成交量 vs 下跌日平均成交量
    健康 = 上涨日放量，下跌日缩量
    异常 = 下跌日放量（主力出货信号）
    """
    result = {"name": "威科夫量价体检", "status": "FAIL", "details": []}

    if len(df) < 10:
        result["status"] = "NEUTRAL"
        result["details"].append(f"⚠️ 数据量不足 10 日，跳过")
        return result

    recent = df.tail(10).copy()
    recent["price_chg"] = recent["close"].diff()

    up_days = recent[recent["price_chg"] > 0]
    down_days = recent[recent["price_chg"] < 0]

    avg_vol_up = float(up_days["volume"].mean()) if len(up_days) > 0 else 0
    avg_vol_down = float(down_days["volume"].mean()) if len(down_days) > 0 else 0

    result["details"].append(f"近10日：上涨 {len(up_days)} 天，下跌 {len(down_days)} 天")
    result["details"].append(f"上涨日均量：{avg_vol_up/1e4:.1f} 万手  |  下跌日均量：{avg_vol_down/1e4:.1f} 万手")

    # 异常量价信号：大量下跌
    effort_no_result = recent[
        (recent["volume"] > recent["volume"].mean() * 1.8) &
        ((recent["close"] - recent["open"]).abs() / recent["close"] < 0.01)
    ]

    if avg_vol_up > avg_vol_down * 1.2:
        result["status"] = "PASS"
        ratio = _format_ratio(avg_vol_up, avg_vol_down)
        result["details"].append(
            f"🟢 量价关系健康：上涨日成交量明显大于下跌日（比值 {ratio}x）"
        )
    elif avg_vol_down > avg_vol_up * 1.3:
        result["status"] = "FAIL"
        ratio = _format_ratio(avg_vol_down, avg_vol_up)
        result["details"].append(
            f"🔴 异常信号：下跌日放量（比值 {ratio}x），可能存在主力出货"
        )
    else:
        result["status"] = "NEUTRAL"
        result["details"].append(f"🟡 量价关系中性：上涨/下跌日成交量差异不显著")

    if len(effort_no_result) > 0:
        result["details"].append(f"⚠️ 威科夫警告：发现 {len(effort_no_result)} 日出现'努力无果'形态（大量小实体）")

    return result


def step3_darvas_breakout(df: pd.DataFrame) -> dict:
    """
    Step 3: 达瓦斯箱体突破 + 利弗莫尔关键点
    逻辑：
    1. 识别最近30日的震荡箱体（振幅 < 15%）
    2. 判断最新收盘是否放量突破箱顶
    3. 检查是否创250日新高（利弗莫尔关键点）
    """
    result = {"name": "达瓦斯/利弗莫尔突破信号", "status": "NEUTRAL", "details": []}

    if len(df) < 30:
        result["status"] = "NEUTRAL"
        result["details"].append(f"⚠️ 数据量不足 30 日，跳过箱体分析")
        return result

    recent_30 = df.tail(30)
    box_high = float(recent_30["high"].max())
    box_low = float(recent_30["low"].min())
    box_range_pct = (box_high - box_low) / box_low * 100

    last_close = float(df["close"].iloc[-1])
    last_vol = float(df["volume"].iloc[-1])
    avg_vol_50 = float(df["volume"].tail(50).mean()) if len(df) >= 50 else float(df["volume"].mean())

    vol_ratio = last_vol / avg_vol_50 if avg_vol_50 > 0 else 0.0

    result["details"].append(f"近30日箱体：高 {box_high:.2f}  低 {box_low:.2f}  振幅 {box_range_pct:.1f}%")
    result["details"].append(f"当前收盘：{last_close:.2f}  |  今日量比（vs50日均量）：{vol_ratio:.2f}x")
    if avg_vol_50 <= 0:
        result["details"].append("⚠️ 成交量基准为 0，量比按 0.00x 处理")

    # 250日新高检测（利弗莫尔）
    high_250 = float(df["high"].tail(250).max()) if len(df) >= 250 else float(df["high"].max())
    is_new_high = last_close >= high_250 * 0.995  # 允许 0.5% 误差

    if is_new_high:
        result["details"].append(f"🚀 利弗莫尔信号：创250日新高！上方无套牢盘，阻力最小路线向上")

    # 达瓦斯箱体判断
    if box_range_pct < 15:
        result["details"].append(f"📦 发现箱体形态（振幅 {box_range_pct:.1f}% < 15%）")
        if last_close > box_high * 0.99 and vol_ratio >= 1.5:
            result["status"] = "PASS"
            result["details"].append(f"🟢 突破信号：收盘接近/突破箱顶（{box_high:.2f}），且成交量放大 {vol_ratio:.1f}x（>1.5x）")
        elif last_close > box_high * 0.99:
            result["status"] = "NEUTRAL"
            result["details"].append(f"🟡 价格突破箱顶但成交量不足（{vol_ratio:.1f}x < 1.5x），待放量确认")
        else:
            result["status"] = "NEUTRAL"
            result["details"].append(f"🟡 价格仍在箱体内，等待突破时机")
    else:
        result["details"].append(f"📊 近30日振幅 {box_range_pct:.1f}% > 15%，尚未形成有效箱体，趋势延续中")
        if last_close > df["close"].tail(20).max() * 0.98 and vol_ratio >= 1.5:
            result["status"] = "PASS"
            result["details"].append(f"🟢 创近期新高且放量，动能延续信号")

    return result


def overall_verdict(results: list[dict]) -> str:
    """综合三步判断，给出最终建议"""
    statuses = [r["status"] for r in results]

    if statuses[0] == "FAIL":
        return "🔴 综合判断：均线趋势不支持，建议观望或回避"
    elif statuses[0] == "NEUTRAL":
        return "🟡 综合判断：趋势条件不完备，数据不足，谨慎参考"
    elif statuses[1] == "FAIL":
        return "🟠 综合判断：均线通过，但量价关系异常（可能出货），不建议追入"
    elif statuses[2] == "PASS" and statuses[1] in ("PASS", "NEUTRAL"):
        return "🟢 综合判断：三步过滤通过！均线健康 + 量价正常 + 突破信号，关注做多机会"
    elif statuses[1] == "PASS":
        return "🟡 综合判断：均线 + 量价均健康，但尚无突破信号，可继续观察"
    else:
        return "🟡 综合判断：条件部分满足，建议结合更多信息判断"


def main():
    if len(sys.argv) < 2:
        print("用法：python scripts/masters_indicators.py <股票代码> [days=250]", file=sys.stderr)
        sys.exit(1)

    code_raw = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) >= 3 else 250
    code = normalize_code(code_raw)

    # 获取数据
    csv_path = find_or_fetch_csv(code, days)
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    print(f"\n{'='*55}")
    print(f"  大师级指标分析 — {code}  （{len(df)} 个交易日）")
    print(f"{'='*55}\n")

    # 三步过滤
    results = []

    step1 = step1_weinstein_filter(df)
    results.append(step1)
    print(f"【Step 1 · {step1['name']}】  [{step1['status']}]")
    for d in step1["details"]:
        print(f"  {d}")
    print()

    step2 = step2_wyckoff_volume(df)
    results.append(step2)
    print(f"【Step 2 · {step2['name']}】  [{step2['status']}]")
    for d in step2["details"]:
        print(f"  {d}")
    print()

    step3 = step3_darvas_breakout(df)
    results.append(step3)
    print(f"【Step 3 · {step3['name']}】  [{step3['status']}]")
    for d in step3["details"]:
        print(f"  {d}")
    print()

    verdict = overall_verdict(results)
    print(f"{'='*55}")
    print(f"  {verdict}")
    print(f"{'='*55}\n")

    # JSON 输出
    json_data = {
        "code": code,
        "days": len(df),
        "analysis_date": datetime.today().strftime("%Y-%m-%d"),
        "steps": [
            {"step": i + 1, "name": r["name"], "status": r["status"], "details": r["details"]}
            for i, r in enumerate(results)
        ],
        "verdict": verdict,
    }
    print(f"JSON_DATA: {json.dumps(json_data, ensure_ascii=False)}")
    sys.exit(0)


if __name__ == "__main__":
    main()

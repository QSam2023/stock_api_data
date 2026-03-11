#!/usr/bin/env python3
"""记录“接口结果 vs 网页结果”对比基线快照。

用法:
    python scripts/record_web_snapshot.py TC-ANL-003 Eastmoney \
      "https://quote.eastmoney.com/sh601869.html" \
      --api-values '{"main_flow": 175185488}' \
      --web-values '{"main_flow": 176000000}' \
      --note "2026-03-11 收盘后抓取"
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_json_arg(raw: str, field_name: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"{field_name} 不是合法 JSON: {e}") from e
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} 必须是 JSON 对象")
    return value


def main():
    parser = argparse.ArgumentParser(description="记录网页对比基线快照")
    parser.add_argument("case_id", help="测试用例 ID，例如 TC-ANL-003")
    parser.add_argument("source", help="网页数据来源，例如 Yahoo Finance / Eastmoney")
    parser.add_argument("url", help="网页来源 URL")
    parser.add_argument(
        "--api-values",
        default="{}",
        help="接口结果关键字段（JSON 对象字符串）",
    )
    parser.add_argument(
        "--web-values",
        default="{}",
        help="网页结果关键字段（JSON 对象字符串）",
    )
    parser.add_argument(
        "--note",
        default="",
        help="补充说明",
    )
    parser.add_argument(
        "--report-date",
        default=datetime.now().strftime("%Y%m%d"),
        help="报告日期（默认: 今天，格式 YYYYMMDD）",
    )
    args = parser.parse_args()

    api_values = parse_json_arg(args.api_values, "--api-values")
    web_values = parse_json_arg(args.web_values, "--web-values")

    report_dir = Path("output") / "test_reports" / args.report_date
    report_dir.mkdir(parents=True, exist_ok=True)
    output_file = report_dir / "web_baseline_snapshots.jsonl"

    record = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "case_id": args.case_id,
        "source": args.source,
        "url": args.url,
        "api_values": api_values,
        "web_values": web_values,
        "note": args.note,
    }

    with output_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"快照已写入: {output_file}")


if __name__ == "__main__":
    main()

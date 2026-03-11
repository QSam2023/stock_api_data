#!/usr/bin/env bash

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

INCLUDE_P2=0
ONLY_CASE=""

usage() {
  cat <<'EOF'
用法:
  bash scripts/run_regression.sh [--include-p2] [--only CASE_ID] [--help]

说明:
  - 默认执行 P0/P1 回归用例
  - --include-p2: 额外执行 P2 用例
  - --only CASE_ID: 仅执行指定用例（例如 TC-PLOT-002）

输出:
  output/test_reports/<YYYYMMDD_HHMMSS>/
    ├── summary.md
    └── logs/<CASE_ID>.log
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --include-p2)
      INCLUDE_P2=1
      shift
      ;;
    --only)
      if [[ -z "${2:-}" ]]; then
        echo "错误: --only 需要传入 CASE_ID" >&2
        exit 2
      fi
      ONLY_CASE="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "错误: 未知参数 $1" >&2
      usage
      exit 2
      ;;
  esac
done

run_date="$(date '+%Y%m%d_%H%M%S')"
report_dir="$ROOT_DIR/output/test_reports/$run_date"
log_dir="$report_dir/logs"
summary_file="$report_dir/summary.md"

mkdir -p "$log_dir"

# 格式: CASE_ID|PRIORITY|EXPECT(exit_zero/exit_nonzero)|COMMAND|DESCRIPTION
all_cases=(
  "TC-FETCH-001|P0|exit_zero|python scripts/fetch_kline.py 600519 20260201 20260311|上证股票行情对齐"
  "TC-FETCH-002|P0|exit_zero|python scripts/fetch_kline.py 000001 20260201 20260311|深证股票行情对齐"
  "TC-ANL-001|P0|exit_zero|python scripts/analyze.py 601869 30|最新收盘价对齐"
  "TC-ANL-002|P0|exit_zero|python scripts/analyze.py 601869 30|30 日涨跌幅对齐"
  "TC-ANL-003|P0|exit_zero|python scripts/analyze.py 601869 30|主力资金最新 1 日对齐"
  "TC-ANL-004|P0|exit_zero|python scripts/analyze.py 601869 30|主力资金近 5 日对齐"
  "TC-MST-001|P0|exit_zero|python scripts/masters_indicators.py 600519 250|数据拉取路径正确"
  "TC-FETCH-003|P1|exit_zero|python scripts/fetch_kline.py sh600519 20260201 20260311|前缀代码兼容"
  "TC-FETCH-004|P1|exit_nonzero|python scripts/fetch_kline.py abcdef|无效代码异常"
  "TC-ANL-005|P1|exit_zero|python scripts/analyze.py 601869 30|接口失败降级"
  "TC-MST-002|P1|exit_zero|python scripts/masters_indicators.py 600519 250|Step1 均线趋势一致"
  "TC-MST-003|P1|exit_zero|python scripts/masters_indicators.py 601869 250|Step3 新高信号一致"
  "TC-PLOT-001|P1|exit_zero|python scripts/plot_chart.py data/600519_20260201_20260311.csv --indicators ma,macd,boll|图表产物生成"
  "TC-PLOT-002|P2|exit_nonzero|python scripts/plot_chart.py data/600519_20260201_20260311.csv --indicators ma,foo|非法指标参数"
)

selected_cases=()
for case_line in "${all_cases[@]}"; do
  IFS='|' read -r case_id priority _ _ _ <<<"$case_line"

  if [[ -n "$ONLY_CASE" && "$case_id" != "$ONLY_CASE" ]]; then
    continue
  fi
  if [[ "$priority" == "P2" && "$INCLUDE_P2" -ne 1 ]]; then
    continue
  fi

  selected_cases+=("$case_line")
done

if [[ ${#selected_cases[@]} -eq 0 ]]; then
  echo "错误: 没有匹配到可执行用例（only=$ONLY_CASE include_p2=$INCLUDE_P2）" >&2
  exit 2
fi

start_at="$(date '+%F %T %z')"
branch_name="$(git branch --show-current 2>/dev/null || echo unknown)"
commit_id="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

pass_count=0
fail_count=0
total_count=0
rows=()

for case_line in "${selected_cases[@]}"; do
  IFS='|' read -r case_id priority expect command desc <<<"$case_line"
  total_count=$((total_count + 1))

  log_file="$log_dir/${case_id}.log"

  {
    echo "CASE_ID: $case_id"
    echo "PRIORITY: $priority"
    echo "DESCRIPTION: $desc"
    echo "COMMAND: $command"
    echo "START: $(date '+%F %T %z')"
    echo "----- OUTPUT -----"
  } >"$log_file"

  bash -lc "$command" >>"$log_file" 2>&1
  exit_code=$?

  {
    echo "----- END OUTPUT -----"
    echo "EXIT_CODE: $exit_code"
    echo "END: $(date '+%F %T %z')"
  } >>"$log_file"

  status="FAIL"
  if [[ "$expect" == "exit_zero" && $exit_code -eq 0 ]]; then
    status="PASS"
  elif [[ "$expect" == "exit_nonzero" && $exit_code -ne 0 ]]; then
    status="PASS"
  fi

  if [[ "$status" == "PASS" ]]; then
    pass_count=$((pass_count + 1))
  else
    fail_count=$((fail_count + 1))
  fi

  echo "[$status] $case_id ($priority) -> exit=$exit_code"
  rows+=("| $case_id | $priority | $expect | $status | $exit_code | \`$command\` | \`output/test_reports/$run_date/logs/${case_id}.log\` |")
done

end_at="$(date '+%F %T %z')"

{
  echo "# Regression Summary"
  echo
  echo "- 运行时间: $start_at ~ $end_at"
  echo "- 分支: $branch_name"
  echo "- 提交: $commit_id"
  echo "- 报告目录: \`output/test_reports/$run_date\`"
  echo
  echo "## 统计"
  echo
  echo "- 总数: $total_count"
  echo "- 通过: $pass_count"
  echo "- 失败: $fail_count"
  echo
  echo "## 用例明细"
  echo
  echo "| Case ID | Priority | Expect | Status | Exit Code | Command | Log |"
  echo "|---|---|---|---|---:|---|---|"
  for row in "${rows[@]}"; do
    echo "$row"
  done
} >"$summary_file"

echo
echo "回归执行完成，报告已生成: $summary_file"
if [[ $fail_count -gt 0 ]]; then
  exit 1
fi
exit 0

# Skill 接口测试集设计（接口结果 vs 网页搜索结果）

## 1. 目标

- 验证本 Skill 核心接口输出与公开网页行情/资金数据在同一时间窗口下是否一致。
- 发现因口径差异、日期对齐错误、字段映射错误导致的结果偏差。
- 为后续自动化回归测试与缺陷修复提供可复用测试集。

## 2. 覆盖接口

- `scripts/fetch_kline.py`
- `scripts/analyze.py`
- `scripts/masters_indicators.py`
- `scripts/plot_chart.py`

## 3. 对比口径

- 对齐时区：`Asia/Shanghai`。
- 对齐交易日：默认比较最新已收盘交易日；若在交易时段内执行，统一回退到前一交易日。
- 代码映射：`sh600519 -> 600519.SS`，`sz000001 -> 000001.SZ`。
- 价格字段：收盘价优先比较 `Close`；允许四舍五入差异。
- 资金流字段：优先比较“主力净流入-净额”（单位统一换算为元）。

## 4. 网页搜索基准源

- Yahoo Finance（价格/成交量）：
  - https://finance.yahoo.com/quote/<TICKER>/
  - https://finance.yahoo.com/quote/<TICKER>/history/
- 东方财富个股资金流（主力资金）：
  - 示例搜索词：`<股票代码> 主力净流入 东方财富`

说明：Yahoo 对中国 A 股通常不提供“主力净流入”字段，因此资金流对比以东方财富网页为主；Yahoo 用于行情字段交叉校验。

## 5. 判定规则

- 价格一致：`abs(api_close - web_close) <= 0.02`。
- 涨跌幅一致：`abs(api_pct - web_pct) <= 0.10`（百分点）。
- 成交量一致：`abs(api_vol - web_vol) / max(web_vol, 1) <= 0.02`。
- 主力净流入一致：`abs(api_main_flow - web_main_flow) <= 5e6`（500 万元，考虑页面刷新/口径轻微差异）。
- 文本类结论（如 PASS/FAIL）：按规则重算结果与接口输出是否匹配。

## 6. 执行流程

1. 跑接口命令，保存标准输出和产物文件路径。
2. 通过网页搜索获取同日基准值，记录来源 URL 和抓取时间。
3. 按 `docs/skill_interface_testcases.csv` 的字段级规则逐项比对。
4. 生成差异报告：字段、偏差值、可能原因、是否提 bug。

## 7. 交付物

- 用例清单：`docs/skill_interface_testcases.csv`
- 本轮缺陷修复计划：`docs/test_and_fix_todolist.md`
- 执行证据：建议落盘到 `output/test_reports/YYYYMMDD/`


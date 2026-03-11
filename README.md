# A 股数据分析 OpenClaw Skill

通过自然语言指令完成 A 股行情获取、技术指标计算、K 线图可视化与回归测试。

当前仓库提供一套可直接被 Agent 调用的 Python CLI：数据拉取、图表绘制、指标解读，以及基于大师策略的三步过滤模型。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 获取贵州茅台最近 90 天日 K 数据
python scripts/fetch_kline.py 600519

# 生成 K 线图（含均线和 MACD）
python scripts/plot_chart.py data/600519_*.csv --indicators ma,macd,boll

# 输出技术指标分析文本
python scripts/analyze.py 600519 30

# 执行大师策略三步过滤（温斯顿/威科夫/达瓦斯+利弗莫尔）
python scripts/masters_indicators.py 600519 250

# 记录“接口 vs 网页”对比快照
python scripts/record_web_snapshot.py TC-ANL-003 Eastmoney \
  "https://quote.eastmoney.com/sh601869.html" \
  --api-values '{"main_flow": 175185488}' \
  --web-values '{"main_flow": 176000000}'

# 执行 P0/P1 一键回归
bash scripts/run_regression.sh
```

## 目录结构

```
├── CLAUDE.md              # 项目说明与开发规范
├── SKILL.md               # OpenClaw Skill 定义（YAML frontmatter + SOP）
├── requirements.txt       # Python 依赖
├── scripts/
│   ├── utils.py               # 共享工具（代码解析、数据获取）
│   ├── fetch_kline.py         # 获取 K 线数据 → CSV
│   ├── plot_chart.py          # 生成 K 线图 → PNG
│   ├── analyze.py             # 输出技术指标分析文本
│   ├── masters_indicators.py  # 大师策略三步过滤分析
│   ├── record_web_snapshot.py # 记录网页对比基线快照
│   └── run_regression.sh      # P0/P1 一键回归并归档测试报告
├── tests/
│   └── test_masters_indicators.py # masters_indicators 单元测试
├── docs/
│   ├── Stock_API_PRD.md           # 产品需求文档
│   ├── reference_strategy.md      # 投机大师方法论参考
│   ├── skill_interface_testset.md # 接口 vs 网页搜索对比测试设计
│   ├── skill_interface_testcases.csv # 可执行测试用例清单
│   ├── test_and_fix_todolist.md   # 缺陷测试与修复待办
│   └── data_source_diff_template.md # 跨数据源差异解释模板
├── references/
│   ├── akshare_api.md     # AKShare 接口参考
│   └── stock_codes.md     # 股票代码规则
├── data/                  # 运行时生成的 CSV（已 gitignore）
└── output/                # 运行时生成的图表与测试报告（已 gitignore）
```

## 脚本用法

### fetch_kline.py — 获取 K 线数据

```bash
python scripts/fetch_kline.py <股票代码> [开始日期] [结束日期]
```

- 股票代码：`600519` 或 `sh600519` / `sz000001`
- 日期格式：`YYYYMMDD`，不指定则默认近 90 天
- 输出：`data/<代码>_<开始>_<结束>.csv`

### plot_chart.py — 生成 K 线图

```bash
python scripts/plot_chart.py <CSV路径> [--indicators ma,macd,boll,rsi]
```

- 支持指标：`ma`（均线）、`macd`、`boll`（布林带）、`rsi`
- 默认：`ma,macd`
- 输出：`output/<代码>_chart.png`

### analyze.py — 技术指标分析

```bash
python scripts/analyze.py <股票代码> [周期天数]
```

- 默认分析最近 30 个交易日
- 输出 MACD、RSI、BOLL、KDJ 等指标及解读

### masters_indicators.py — 大师策略过滤模型

```bash
python scripts/masters_indicators.py <股票代码> [周期天数]
```

- 默认分析 250 个交易日
- 三步过滤逻辑：
  - 温斯顿 + 欧奈尔：均线趋势过滤
  - 威科夫：量价健康体检
  - 达瓦斯 + 利弗莫尔：箱体/突破信号
- 输出终端文本结论，并附带 `JSON_DATA` 结果供自动化消费

### record_web_snapshot.py — 网页基线快照

```bash
python scripts/record_web_snapshot.py <CASE_ID> <SOURCE> <URL> \
  --api-values '{"close": 250.01}' \
  --web-values '{"close": 250.00}'
```

- 输出到 `output/test_reports/<YYYYMMDD>/web_baseline_snapshots.jsonl`
- 用于保留接口与网页对比的可追溯证据

### run_regression.sh — 统一回归入口

```bash
# 执行全部 P0/P1 用例
bash scripts/run_regression.sh

# 在 P0/P1 基础上附加执行 P2 用例
bash scripts/run_regression.sh --include-p2

# 只执行单个用例
bash scripts/run_regression.sh --only TC-PLOT-002
```

- 产物归档目录：`output/test_reports/<YYYYMMDD_HHMMSS>/`
- 产物内容：`summary.md` 与 `logs/<CASE_ID>.log`

## 跨数据源差异解释

- 模板文件：`docs/data_source_diff_template.md`
- 适用场景：复权口径差异、成交量单位差异、停牌与交易日错位、实时/收盘时间窗差异

## 技术栈

- **数据源**：[AKShare](https://github.com/akfamily/akshare)（免费，无需注册）
- **技术指标**：pandas-ta（纯 Python，无需 C 编译器）
- **K 线图**：mplfinance

## 注意事项

- 所有计算通过脚本完成，确保数值准确性
- 输出为 PNG 静态图片，适合 OpenClaw 直接展示
- AKShare 有请求频率限制，避免短时间大量调用
- 分析结果仅供参考，不构成投资建议

## 测试

```bash
# 单元测试
python -m unittest discover -s tests -p "test_*.py"

# 回归测试（默认 P0/P1）
bash scripts/run_regression.sh

# 回归测试（含 P2）
bash scripts/run_regression.sh --include-p2
```

## 版本历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-03-11 | v1.4.0 | 完成 P2 迭代：新增 `scripts/run_regression.sh` 统一回归入口，测试结果归档到 `output/test_reports/`，并新增 `docs/data_source_diff_template.md` 跨数据源差异解释模板 |
| 2026-03-11 | v1.3.1 | 修复 `masters_indicators.py` 首次拉取 CSV 路径解析错误（不再将 stdout 当文件路径），并补充对应单元测试 |
| 2026-03-11 | v1.3.0 | 完成 P1 修复：`fetch_kline.py` 日期校验、`analyze.py` 资金流列白名单、AKShare 超时重试与错误分类、`masters_indicators.py` 边界单元测试 |
| 2026-03-11 | v1.2.1 | 修复 P0 问题：`analyze.py` 近5日资金流取值、`masters_indicators.py` 首次拉取 CSV 路径解析；新增网页对比快照脚本 |
| 2026-03-11 | v1.2.0 | 新增 Skill 接口测试集设计、接口对比用例清单与 `test and fix bugs` TodoList |
| 2026-03-11 | v1.1.0 | 初始化 `AGENTS.md`；README 补充项目总结、`masters_indicators.py` 说明与维护信息 |
| 2026-03-10 | v1.0.0 | 初始版本：支持 K 线获取、图表生成、技术指标分析 |

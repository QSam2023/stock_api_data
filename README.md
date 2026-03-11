# A 股数据分析 OpenClaw Skill

通过自然语言指令完成 A 股行情获取、技术指标计算和 K 线图可视化的 OpenClaw Skill。

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

# 执行大师策略三步过滤
python scripts/masters_indicators.py 600519 250

# 记录“接口 vs 网页”对比快照
python scripts/record_web_snapshot.py TC-ANL-003 Eastmoney \
  "https://quote.eastmoney.com/sh601869.html" \
  --api-values '{"main_flow": 175185488}' \
  --web-values '{"main_flow": 176000000}'
```

## 目录结构

```
├── CLAUDE.md              # 项目说明与开发规范
├── SKILL.md               # OpenClaw Skill 定义（YAML frontmatter + SOP）
├── requirements.txt       # Python 依赖
├── scripts/
│   ├── utils.py           # 共享工具（代码解析、数据获取）
│   ├── fetch_kline.py     # 获取 K 线数据 → CSV
│   ├── plot_chart.py      # 生成 K 线图 → PNG
│   ├── analyze.py         # 输出技术指标分析文本
│   ├── masters_indicators.py # 大师策略三步过滤分析
│   └── record_web_snapshot.py # 记录网页对比基线快照
├── references/
│   ├── akshare_api.md     # AKShare 接口参考
│   └── stock_codes.md     # 股票代码规则
├── data/                  # 运行时生成的 CSV（已 gitignore）
└── output/                # 运行时生成的图表（已 gitignore）
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
- 输出三步过滤结论和 `JSON_DATA`

### record_web_snapshot.py — 网页基线快照

```bash
python scripts/record_web_snapshot.py <CASE_ID> <SOURCE> <URL> \
  --api-values '{"close": 250.01}' \
  --web-values '{"close": 250.00}'
```

- 输出到 `output/test_reports/<YYYYMMDD>/web_baseline_snapshots.jsonl`
- 用于保留接口与网页对比的可追溯证据

## 技术栈

- **数据源**：[AKShare](https://github.com/akfamily/akshare)（免费，无需注册）
- **技术指标**：pandas-ta（纯 Python，无需 C 编译器）
- **K 线图**：mplfinance

## 注意事项

- 所有计算通过脚本完成，确保数值准确性
- 输出为 PNG 静态图片，适合 OpenClaw 直接展示
- AKShare 有请求频率限制，避免短时间大量调用
- 分析结果仅供参考，不构成投资建议

## 版本历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-03-11 | v1.1.1 | 修复 P0 问题：`analyze.py` 近5日资金流取值、`masters_indicators.py` 首次拉取 CSV 路径解析；新增网页对比快照脚本 |
| 2026-03-10 | v1.0.0 | 初始版本：支持 K 线获取、图表生成、技术指标分析 |

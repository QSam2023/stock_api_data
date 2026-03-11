# AGENTS.md

## 项目定位
- 本仓库是一个 A 股数据分析工具集，核心能力是：
  - 拉取历史日 K 数据（AKShare）
  - 计算技术指标（MACD/RSI/BOLL/KDJ 等）
  - 生成 K 线图（PNG）
  - 输出文本化分析结果，供 LLM/Agent 二次解读
- 目标是让 Agent 通过脚本而不是手算指标，保证数值准确和流程可复用。

## 仓库结构与职责
- `scripts/utils.py`：公共函数（代码解析、目录创建、数据获取、错误退出）。
- `scripts/fetch_kline.py`：按股票代码与日期拉取数据到 `data/*.csv`。
- `scripts/plot_chart.py`：读取 CSV 生成 `output/*_chart.png`。
- `scripts/analyze.py`：输出技术指标文字分析（标准输出）。
- `scripts/masters_indicators.py`：执行“三步大师过滤模型”并输出结论与 JSON。
- `references/`：接口与代码规则参考文档。
- `docs/`：PRD 与策略方法论文档。

## 开发约束
- 修改脚本时优先复用 `scripts/utils.py`，避免重复实现代码解析与错误处理。
- 新增 CLI 参数时保持向后兼容，现有命令调用方式不可随意破坏。
- 所有异常需给出明确报错信息，并在失败时返回非 0 退出码。
- 运行产物仅写入 `data/` 和 `output/`，禁止提交临时数据到仓库。
- 依赖新增或替换时同步更新 `requirements.txt` 和 `README.md`。

## 常用命令
```bash
pip install -r requirements.txt

# 拉取 K 线
python scripts/fetch_kline.py 600519
python scripts/fetch_kline.py sh600519 20240101 20241231

# 生成图表
python scripts/plot_chart.py data/600519_20240101_20241231.csv --indicators ma,macd,boll,rsi

# 技术分析
python scripts/analyze.py 600519 30

# 大师策略过滤
python scripts/masters_indicators.py 600519 250
```

## 手动测试基线
- 在提交代码前至少跑通以下检查：
  - `python scripts/fetch_kline.py 600519 20250101 20250301`
  - `python scripts/plot_chart.py data/600519_20250101_20250301.csv --indicators ma,macd,boll`
  - `python scripts/analyze.py 600519 30`
  - `python scripts/masters_indicators.py 600519 250`
- 系统升级或通知工具更新后，必须重新执行以上手动测试。

## 文档维护规则
- 初始化项目 `AGENTS.md` 时，必须同步构建/更新 `README.md` 的项目总结。
- 重大变更（架构、脚本接口、数据源、指标逻辑）必须记录到 `README.md` 的版本历史。
- 若脚本接口变更，需同步更新 `README.md`、`SKILL.md` 与相关 `docs/` 文档。

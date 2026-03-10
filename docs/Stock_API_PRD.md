# A 股数据分析 OpenClaw Skill — 产品需求文档（PRD）

**版本**：v1.0
**日期**：2026-03-10
**项目名**：`a-share-analyzer`

---

## 1. 背景与目标

### 1.1 背景

A 股散户和研究者通常依赖手动查看行情软件来判断走势，缺乏系统性的技术指标辅助。大语言模型（LLM）虽然具备金融领域的背景知识，但直接处理海量行情数据容易出错。

### 1.2 目标

开发一个 **OpenClaw Skill**，使用户能够通过自然语言指令完成以下任务：
- 查询 A 股个股/指数的历史与实时行情
- 自动计算常用技术指标（MACD、RSI、BOLL、KDJ）
- 生成专业 K 线图并直观展示
- 获取结构化的量化分析摘要

---

## 2. 数据源

### 2.1 主要数据源

| 数据源 | 类型 | 是否需要注册 | 推荐度 |
|--------|------|------------|--------|
| **AKShare** | 开源免费 | 否 | ★★★★★（默认） |
| **BaoStock** | 免费 | 否 | ★★★★☆（备选） |
| **Tushare Pro** | 积分制 | 是（需 Token） | ★★★☆☆（可选） |

### 2.2 数据覆盖范围

- A 股全市场个股（沪深两市）
- 主要指数（上证指数、沪深 300、创业板指等）
- 历史日 K / 周 K / 月 K 数据
- 实时行情（T 日盘中/收盘）
- 核心财务指标（市盈率、市净率、营收、净利润等）
- 资金流向（主力/散户净流入）

---

## 3. 功能需求

### 3.1 数据获取模块（`fetch_kline.py`）

**功能**：通过 AKShare 获取指定股票的 K 线数据并持久化为 CSV。

**接口**：
```bash
python scripts/fetch_kline.py <股票代码> [开始日期] [结束日期]
# 示例：python scripts/fetch_kline.py 600519 20240101 20241231
```

**输出**：`data/<股票代码>_<开始日期>_<结束日期>.csv`

**字段**：日期、开盘价、最高价、最低价、收盘价、成交量、成交额

**异常处理**：
- 网络超时：打印提示并以非 0 退出码退出
- 无效代码：打印明确错误信息

---

### 3.2 可视化模块（`plot_chart.py`）

**功能**：读取 K 线 CSV，使用 `mplfinance` 生成专业 K 线图（蜡烛图）。

**接口**：
```bash
python scripts/plot_chart.py <CSV路径> [--indicators ma,macd,boll]
# 示例：python scripts/plot_chart.py data/600519.csv --indicators ma,macd,rsi
```

**输出**：`output/<股票代码>_chart.png`（OpenClaw 可直接展示）

**支持指标叠加**：
- 均线（MA5 / MA10 / MA20 / MA60）
- 布林带（BOLL）
- MACD（副图）
- RSI（副图）
- 成交量柱状图（默认显示）

---

### 3.3 分析模块（`analyze.py`）

**功能**：输出格式化的技术指标文本，供 LLM 阅读和总结。

**接口**：
```bash
python scripts/analyze.py <股票代码> [周期天数，默认30]
# 示例：python scripts/analyze.py 600519 60
```

**输出**（标准输出，纯文本）：
```
股票：贵州茅台（600519）
分析周期：最近 30 个交易日
最新收盘价：1680.00 元
涨跌幅（30日）：+5.23%

技术指标（最新值）：
  MACD（DIF）: 12.35 | MACD（DEA）: 10.20 | 柱状值: 2.15 → 金叉趋势
  RSI（14日）: 58.4 → 中性偏强
  BOLL 上轨: 1750  中轨: 1660  下轨: 1570 → 价格位于中轨上方
  KDJ：K=65  D=60  J=75 → 偏多

资金流向（近 5 日）：主力净流入 +12.3 亿
```

---

### 3.4 参考文档

| 文件 | 内容 |
|------|------|
| `references/akshare_api.md` | AKShare 常用接口清单、参数说明、返回字段说明 |
| `references/stock_codes.md` | 股票代码格式规则（sh/sz 前缀、指数代码等） |

---

## 4. 技术栈

```
# requirements.txt
akshare>=1.12.0
pandas>=2.0.0
numpy>=1.24.0
pandas-ta>=0.3.14b
mplfinance>=0.12.10b0
```

> **为什么选择 `pandas-ta` 而非 `TA-Lib`**：`pandas-ta` 为纯 Python 实现，无需 C 编译器，`pip install` 即可使用，大幅降低部署门槛。

---

## 5. OpenClaw Skill 交互流（SOP）

```
用户输入
  ↓ 意图识别：提取股票代码 / 名称 / 时间范围
  ↓ 获取数据：调用 fetch_kline.py
  ↓ 绘制图表：调用 plot_chart.py → 生成 .png
  ↓ 分析指标：调用 analyze.py → 获取文本指标
  ↓ 生成分析报告：LLM 结合指标数值 + 金融知识 输出解读
用户获得：K 线图 + 文字分析报告
```

### 典型交互示例

> **用户**：分析一下贵州茅台最近一个月的走势
> **Skill 执行**：
> 1. 解析股票代码 → `600519`，周期 → 近 30 交易日
> 2. 运行 `fetch_kline.py 600519`
> 3. 运行 `plot_chart.py data/600519.csv --indicators ma,macd,boll`
> 4. 运行 `analyze.py 600519 30`
> 5. LLM 读取指标文本 + 展示图表，输出人话解读

---

## 6. 非功能需求

| 维度 | 要求 |
|------|------|
| **易用性** | 用户无需了解 AKShare API 或 Python，自然语言即可使用 |
| **可扩展性** | 数据源可通过配置切换（AKShare / BaoStock / Tushare） |
| **错误透明度** | 脚本错误信息清晰，LLM 可根据退出码判断是否重试 |
| **低门槛部署** | 默认依赖（AKShare）无需注册，`pip install -r requirements.txt` 即可运行 |
| **图片兼容** | 输出 `.png` 静态图，确保 OpenClaw 能直接渲染展示 |

---

## 7. 配置说明

若用户选用 **Tushare Pro** 作为数据源，需在环境变量中配置：

```bash
export TUSHARE_TOKEN=your_token_here
```

此配置要求需在 `SKILL.md` 的安装说明中明确标注。

---

## 8. 后续迭代方向（Backlog）

- [ ] 支持板块 / 行业横向对比分析
- [ ] 增加财务报表分析（营收、净利润趋势）
- [ ] 支持自选股列表批量分析
- [ ] 集成 `pyecharts` 生成可交互 HTML 图表
- [ ] 添加市场情绪指标（北向资金、融资融券等）

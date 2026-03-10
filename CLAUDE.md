# A股数据分析 OpenClaw Skill - 项目说明

## 项目概述

本项目是一个针对 A 股市场数据分析的 **OpenClaw Skill**，命名为 `a-share-analyzer`。
目标是让大模型（LLM）通过调用预置 Python 脚本，完成 A 股行情获取、技术指标计算和 K 线图可视化。

## 目录结构

```
a-share-analyzer/
├── CLAUDE.md            # 本文件
├── SKILL.md             # OpenClaw 核心文件：YAML frontmatter + SOP 指令
├── requirements.txt     # 依赖声明
├── scripts/             # 预置 Python 脚本
│   ├── fetch_kline.py   # 获取 K 线数据并保存为 CSV
│   ├── plot_chart.py    # 读取 CSV 并生成 K 线图（.png）
│   └── analyze.py       # 输出格式化财务/技术指标文本
└── references/          # 供模型按需读取的参考文档
    ├── akshare_api.md   # AKShare 常用接口与参数说明
    └── stock_codes.md   # 股票代码规则说明
```

## 技术栈

### 数据源（优先级排序）
1. **AKShare**（默认）：开源免费，无需 Token，支持 A 股历史/实时行情、财务报表、资金流向
2. **BaoStock**（备选）：免费，无需注册，支持离线数据
3. **Tushare Pro**（备选）：接口标准化高，但需注册 Token 和积分，门槛较高

### 核心依赖
```
akshare
pandas
numpy
pandas-ta      # 技术指标：MACD, RSI, BOLL, KDJ 等
mplfinance     # K 线图可视化（推荐，易安装）
```

### 可选依赖
```
pyecharts      # 可交互 HTML 图表（按需使用）
```

## 开发规范

### 脚本接口约定
- `fetch_kline.py <股票代码> [start_date] [end_date]`：输出 CSV 到 `data/` 目录
- `plot_chart.py <CSV路径> [指标列表]`：输出 PNG 到 `output/` 目录
- `analyze.py <股票代码>`：打印格式化文本供 LLM 阅读

### 股票代码格式
- 上交所：`sh600519`（如贵州茅台）
- 深交所：`sz000001`（如平安银行）
- AKShare 内部使用纯数字代码如 `600519`，脚本需处理前缀转换

### 错误处理原则
- 所有脚本须捕获网络异常并打印友好错误信息
- 数据获取失败时退出码为非 0，方便 LLM 判断是否重试

## LLM 工作流（SOP）

1. **意图识别**：解析用户请求中的股票名称/代码和时间范围
2. **获取数据**：调用 `scripts/fetch_kline.py`
3. **计算指标 & 绘图**：调用 `scripts/plot_chart.py`，生成图表
4. **读取分析数据**：调用 `scripts/analyze.py`，获取 MACD/RSI 等数值
5. **总结解读**：结合指标数值和金融背景知识，输出人类可读的分析报告

## 注意事项

- 若使用 Tushare，用户需在环境变量中配置 `TUSHARE_TOKEN`，需在 `SKILL.md` 中说明
- 图表生成为 `.png` 静态图片，OpenClaw 可直接展示给用户
- 大模型不应直接计算数值，所有计算均通过脚本完成以保证准确性

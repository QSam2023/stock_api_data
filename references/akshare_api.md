# AKShare 常用 A 股接口参考

AKShare 是开源免费的 Python 金融数据库，无需注册，`pip install akshare` 即可使用。
官方文档：https://akshare.akfamily.xyz/

---

## 1. 日 K 线历史数据

```python
import akshare as ak

df = ak.stock_zh_a_hist(
    symbol="600519",       # 纯数字代码，不带 sh/sz 前缀
    period="daily",        # 周期：daily / weekly / monthly
    start_date="2024-01-01",  # 格式：YYYY-MM-DD
    end_date="2024-12-31",
    adjust="qfq",          # 复权：qfq（前复权）/ hfq（后复权）/ ""（不复权）
)
```

**返回字段（中文列名，需手动重命名）：**

| 原始列名 | 英文映射 | 说明 |
|---------|---------|------|
| 日期 | date | 交易日 |
| 开盘 | open | 开盘价 |
| 最高 | high | 最高价 |
| 最低 | low | 最低价 |
| 收盘 | close | 收盘价 |
| 成交量 | volume | 单位：手（100股） |
| 成交额 | amount | 单位：元 |
| 振幅 | amplitude | % |
| 涨跌幅 | pct_change | % |
| 涨跌额 | price_change | 元 |
| 换手率 | turnover | % |

**注意**：`symbol` 必须是纯数字（如 `600519`），不接受 `sh600519`。

---

## 2. 实时行情（全市场）

```python
spot_df = ak.stock_zh_a_spot_em()
```

**返回字段（部分）：**

| 列名 | 说明 |
|-----|------|
| 代码 | 股票代码（纯数字） |
| 名称 | 股票名称 |
| 最新价 | 当前价格 |
| 涨跌幅 | % |
| 成交量 | 手 |
| 成交额 | 元 |
| 市盈率-动态 | PE（TTM） |
| 市净率 | PB |

**用途**：通过股票名称查找代码，或获取全市场实时快照。

```python
# 示例：通过名称查找代码
row = spot_df[spot_df["名称"] == "贵州茅台"]
code = row.iloc[0]["代码"]  # "600519"
```

---

## 3. 个股资金流向

```python
flow_df = ak.stock_individual_fund_flow(
    stock="600519",   # 纯数字代码
    market="sh",      # sh（上交所）或 sz（深交所）
)
```

**返回字段（部分）：**

| 列名 | 说明 |
|-----|------|
| 日期 | 交易日 |
| 主力净流入-净额 | 元，正=净流入，负=净流出 |
| 主力净流入-净占比 | % |
| 超大单净流入-净额 | 元 |
| 大单净流入-净额 | 元 |
| 中单净流入-净额 | 元 |
| 小单净流入-净额 | 元 |

**判断市场归属**：
- 代码以 `6` 开头 → `market="sh"`（上交所）
- 代码以 `0` 或 `3` 开头 → `market="sz"`（深交所）
- 代码以 `4` 或 `8` 开头 → 北交所（北交所接口不同，暂不支持）

---

## 4. 指数历史数据

```python
index_df = ak.index_zh_a_hist(
    symbol="000300",      # 沪深300指数代码
    period="daily",
    start_date="2024-01-01",
    end_date="2024-12-31",
)
```

**常用指数代码：**

| 指数名称 | 代码 |
|---------|-----|
| 上证指数 | 000001 |
| 沪深 300 | 000300 |
| 中证 500 | 000905 |
| 中证 1000 | 000852 |
| 创业板指 | 399006 |
| 科创 50 | 000688 |
| 深证成指 | 399001 |

**注意**：指数接口与股票接口不同，不要混用。

---

## 5. 股票基本信息

```python
# 获取单只股票基本面数据
info_df = ak.stock_individual_info_em(symbol="600519")
```

---

## 6. 常见错误与处理

| 错误类型 | 可能原因 | 处理方式 |
|---------|---------|---------|
| `KeyError: '日期'` | AKShare 版本更新导致列名变化 | 打印 `df.columns` 查看实际列名 |
| `ConnectionError` | 网络问题或 AKShare 数据源变化 | 重试，或检查 akshare 版本 |
| 返回空 DataFrame | 股票代码错误、退市、或日期无数据 | 检查代码和日期范围 |
| `symbol` 格式错误 | 传入了 `sh600519` 而非 `600519` | 去掉前缀 |

---

## 7. 版本与更新

```bash
# 安装/更新
pip install akshare --upgrade

# 查看当前版本
python -c "import akshare; print(akshare.__version__)"
```

AKShare 更新较频繁，接口名称或字段偶有变动。遇到问题优先查阅官方文档：
https://akshare.akfamily.xyz/data/stock/stock.html

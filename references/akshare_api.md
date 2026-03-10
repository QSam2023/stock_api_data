# AKShare 常用接口说明

本文档列出本项目使用的 AKShare 接口及其参数，供 LLM 在需要时参考。

## 1. 个股日 K 线数据

```python
import akshare as ak
df = ak.stock_zh_a_hist(
    symbol="600519",       # 纯 6 位数字代码
    period="daily",        # daily / weekly / monthly
    start_date="20240101", # YYYYMMDD
    end_date="20241231",   # YYYYMMDD
    adjust="qfq",          # qfq=前复权, hfq=后复权, ""=不复权
)
```

**返回字段**：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率

## 2. 个股资金流向

```python
df = ak.stock_individual_fund_flow(
    stock="600519",   # 纯 6 位数字代码
    market="sh",      # sh=上交所, sz=深交所
)
```

**返回字段**：日期、收盘价、涨跌幅、主力净流入-净额、主力净流入-净占比、超大单净流入-净额等

**注意**：此接口不一定对所有股票都可用，调用时需捕获异常。

## 3. 实时行情

```python
df = ak.stock_zh_a_spot_em()
```

返回全市场实时行情快照，字段包含：代码、名称、最新价、涨跌幅、成交量等。
数据量较大，建议按需筛选。

## 4. 股票名称查询

```python
df = ak.stock_info_a_code_name()
```

返回所有 A 股代码与名称的对照表，可用于名称到代码的转换。

## 5. 常见问题

- **symbol 参数只接受纯数字**：不要传 `sh600519`，应传 `600519`
- **日期格式**：统一使用 `YYYYMMDD` 字符串
- **adjust 参数**：交易分析推荐使用前复权（`qfq`）
- **频率限制**：AKShare 底层数据源有反爬机制，短时间大量请求可能被限流
- **数据延迟**：日 K 数据在收盘后更新，盘中数据需使用实时行情接口

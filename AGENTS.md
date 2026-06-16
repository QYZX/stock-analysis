# AGENTS.md

本文件为 AGENTS 在此仓库中工作时提供指引。

## 项目概述

基于富途 OpenD API（`futu-api`）的股票行情监控工具。连接本地运行的 Futu OpenD 网关（默认 `127.0.0.1:11111`），获取实时报价、K线数据，并计算技术指标（MACD、KDJ、RSI），支持港股、美股和A股市场。

## 开发环境

- **Python**: >=3.14
- **包管理器**: uv（存在 `uv.lock`）
- **安装依赖**: `uv sync`
- **运行**: `uv run python monitor_stock.py`
- **前置条件**: 运行任何 API 调用前，必须先启动本地 Futu OpenD，否则脚本会报连接错误。

## 架构

### 源码模块（`src/`）

| 模块 | 职责 |
|------|------|
| `quote_context.py` | `QuoteContext` 上下文管理器，封装 `OpenQuoteContext`。另提供 `create_quote_ctx()` 用于非上下文管理器场景。单一共享连接模式——各模块共用同一个 `quote_ctx` 实例。 |
| `subscribe_stock.py` | `SubscriptionManager`——订阅/取消订阅股票数据推送（QUOTE、RT_DATA、K_1M、K_5M、K_DAY、ORDER_BOOK、TICKER）。获取实时数据前必须先订阅。 |
| `realtime_indicators.py` | `RealtimeIndicators`——获取K线/报价/分时数据，通过 `talib` 计算 MACD、KDJ、RSI。另提供 `monitor_realtime()` 用于持续轮询。 |
| `util.py` | `clear_screen()` 辅助函数（兼容 Windows/Unix）。 |

### 数据流

```
OpenD（本地网关）
  → OpenQuoteContext（单一共享连接）
    → SubscriptionManager.subscribe()（实时查询前必须订阅）
      → RealtimeIndicators.get_realtime_info()
        → get_cur_kline() / get_rt_data() / get_stock_quote()
        → calculate_macd() / calculate_kdj() / calculate_rsi()
```

### 入口

`monitor_stock.py` 是主入口。使用 `QuoteContext` 上下文管理器，订阅后查询一次指标，可选择进入轮询循环。

## 技术指标计算约定

指标遵循**国内股票软件标准**（同花顺/东方财富）：

- **MACD**：柱状图为 `2 * (DIF - DEA)`，而非 `talib.MACD` 返回的 `DIF - DEA`。
- **KDJ**：使用 `talib.STOCHF` 获取原始 RSV，然后手动递推计算 `K = 2/3 * 前K + 1/3 * RSV`、`D = 2/3 * 前D + 1/3 * K`、`J = 3K - 2D`，初始 K=D=50。切勿直接使用 `talib.STOCH`——其 SMA 平滑方式与国内标准不同。
- **RSI**：使用 `talib.RSI`（Wilder's 平滑 / EMA alpha=1/N），为标准算法。

## Claude Skills 参考（`.claude/skills/futuapi/`）

Futu OpenAPI 的参考脚本和文档，按领域组织：

- `docs/API_REFERENCE.md` — 行情/交易/订阅的完整 API 函数签名
- `docs/API_LIMITS.md` — 频率限制、订阅额度、历史K线额度
- `docs/FIELD_MAPPING.md` — API 字段与 APP 显示值的映射（持仓/盈亏相关，关键）
- `docs/TROUBLESHOOTING.md` — 已知问题与错误处理模式
- `scripts/common.py` — 公共工具：`ensure_futu_api()`、`create_quote_context()`、`create_trade_context()`、`safe_float()`、`safe_int()`、`check_ret()`、`df_to_records()`
- `scripts/quote/` — 各 API 的参考脚本（如 `get_kline.py`、`get_stock_quote.py`）
- `scripts/subscribe/` — 订阅与推送处理示例
- `scripts/trade/` — 交易操作脚本

新增 API 功能时，遵循 `.claude/skills/futuapi/scripts/` 中的模式——使用 `common.py` 工具函数处理连接和错误。

## 关键 API 约束

- **先订阅再查询**：实时 API（报价、K线、分时、逐笔、摆盘）需先通过 `SubscriptionManager` 订阅。
- **订阅冷却**：订阅后至少 1 分钟才能反订阅。
- **频率限制**：`place_order` 15次/30秒，`modify_order` 20次/30秒，`order_list_query` 10次/30秒。循环中需加 `time.sleep()`。
- **历史K线额度**：每只股票每 30 天窗口消耗 1 个额度。批量请求前先检查 `get_history_kl_quota()`。
- **单一连接模式**：所有模块共享一个 `OpenQuoteContext`，不要创建多个连接。

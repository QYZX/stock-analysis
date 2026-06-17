# AGENTS.md

本文件为 AGENTS 在此仓库中工作时提供指引。

## 项目概述

基于富途 OpenD API（`futu-api`）的股票行情监控工具。连接本地运行的 Futu OpenD 网关（默认 `127.0.0.1:11111`），获取实时报价、K线、分时数据，计算技术指标（MACD、KDJ、RSI），并依据指标触发买卖信号、发送 Windows 系统通知。支持港股、美股和A股市场，可批量并发监控多只股票。

## 开发环境

- **Python**: >=3.14（`.python-version` 锁定 3.14）
- **包管理器**: uv（存在 `uv.lock`）
- **安装依赖**: `uv sync`
- **运行**: `uv run python main.py`
- **前置条件**: 运行任何 API 调用前，必须先启动本地 Futu OpenD，否则脚本会报连接错误。
- **主要依赖**（`pyproject.toml`）: `futu-api`、`ta-lib`、`pyyaml`、`winotify`（Windows 通知）

## 配置

运行参数从根目录 `config.yaml` 读取：

| 字段 | 说明 |
|------|------|
| `stock_codes` | 股票代码列表，每项为 `{code: "SH.515050"}` 或直接字符串 |
| `sub_types` | 订阅类型，默认 `["QUOTE", "RT_DATA", "KL_1MIN"]` |
| `interval` | 轮询刷新间隔（秒），默认 5 |
| `max_workers` | 批量监控的并发线程数，默认 5 |

## 架构

### 入口与配置层（根目录）

| 文件 | 职责 |
|------|------|
| `main.py` | 真正的主入口。加载 `config.yaml`，用 `ThreadPoolExecutor` 并发调用 `monitor_stock` 监控多只股票，汇总成功/失败结果。 |
| `config.yaml` | 股票列表与运行参数（见上节）。 |
| `logging_config.py` | `setup_logging()` 通过 `dictConfig` 初始化日志：控制台 + `log/log.log` 文件，并为交易信号专用 logger `signal`（输出到 `log/signals.log`）。 |

### 源码模块（`src/`）

| 模块 | 职责 |
|------|------|
| `quote_context.py` | `QuoteContext` 上下文管理器，封装 `OpenQuoteContext`。另提供 `create_quote_ctx()` 用于非上下文管理器场景。单一共享连接模式——各模块共用同一个 `quote_ctx` 实例。 |
| `subscribe_stock.py` | `SubscriptionManager`——订阅/取消订阅股票数据推送。订阅类型对外用字符串键：`QUOTE`、`RT_DATA`、`ORDER_BOOK`、`TICKER`、`KL_DAY`、`KL_1MIN`、`KL_5MIN`（内部映射到 `SubType.K_DAY`/`K_1M`/`K_5M` 等）。获取实时数据前必须先订阅。 |
| `realtime_indicators.py` | `RealtimeIndicators`——获取K线/报价/分时数据，通过 `talib` 计算 MACD、KDJ、RSI。`get_realtime_info()` 一次性返回 `RealtimeInfo` 数据类；`monitor_realtime()` 用于持续轮询。另定义 `MACDResult`/`KDJResult`/`RSIResult` 数据类。 |
| `monitor_stock.py` | 单只股票监控逻辑。`monitor_stock()` 在 `QuoteContext` 内订阅后查询指标；`callback()` 依据 KDJ+RSI 双重条件判断买卖信号；`send_notification()` 根据信号经 `notification.notify` 发系统通知，并通过 `signal_logger` 写入信号日志。 |
| `notification.py` | 基于 `winotify` 的 Windows 10 系统通知。`notify(title, message, key, cooldown)` 带 key 去重（默认冷却 1 分钟），线程安全；另提供 `reset_key()`/`reset_all()`。 |
| `util.py` | `clear_screen()` 辅助函数（兼容 Windows/Unix）。 |

### 数据流

```
config.yaml
  → main.py（ThreadPoolExecutor 并发，每只股票一个任务）
    → monitor_stock(code, sub_types, interval)
      → QuoteContext（OpenQuoteContext，单一共享连接）
        → SubscriptionManager.subscribe()（实时查询前必须订阅）
          → RealtimeIndicators.get_realtime_info()
            → get_cur_kline() / get_rt_data() / get_stock_quote()
            → calculate_macd() / calculate_kdj() / calculate_rsi()
          → callback(info) → 判断买卖信号（KDJ + RSI 双重确认）
            → send_notification() → notification.notify()（Windows 通知）
            → signal_logger → log/signals.log
```

### 入口

- **批量监控**：`uv run python main.py`（推荐，根目录 `main.py`）。从 `config.yaml` 读取股票列表，并发执行。
- **单只股票**：`src/monitor_stock.py` 中的 `monitor_stock()` 可独立调用；其 `if __name__ == "__main__"` 入口尚未启用（`monitor_stock.py` 自身无 `__main__` 块，需通过 `main.py` 调用）。

## 技术指标计算约定

指标遵循**国内股票软件标准**（同花顺/东方财富）：

- **MACD**：柱状图为 `2 * (DIF - DEA)`，而非 `talib.MACD` 返回的 `DIF - DEA`。实现见 `realtime_indicators.py:calculate_macd`。
- **KDJ**：使用 `talib.STOCHF`（`fastd_period=1`）获取原始 RSV，然后手动递推 `K = 2/3 * 前K + 1/3 * RSV`、`D = 2/3 * 前D + 1/3 * K`、`J = 3K - 2D`，初始 K=D=50。切勿直接使用 `talib.STOCH`——其 SMA 平滑方式与国内标准不同。
- **RSI**：使用 `talib.RSI`（Wilder's 平滑 / EMA alpha=1/N），周期为 `(6, 12, 24)`，对应 `RSIResult.rsi1/rsi2/rsi3`。

## 交易信号判断（`monitor_stock.callback`）

需 KDJ 与 RSI **同时**满足条件才触发信号：

- **卖出信号**（`flag=2`）：`K >= 90 且 J >= 100` 且 `RSI1 >= 90`
- **买入信号**（`flag=1`）：`K <= 10 且 J <= 0` 且 `RSI1 <= 10`
- 任一指标为 `None` 时不触发（`flag=0`）。

触发后由 `send_notification` 发送 Windows 通知（key 为 `{code}_buy`/`{code}_sell`，冷却 1 分钟去重），并写入 `log/signals.log`。

## 日志

`logging_config.setup_logging()` 配置：

- **根 logger** → 控制台（`standard` 格式）
- **文件 handler** → `log/log.log`（在 `LOGGING_CONFIG` 中定义，注意根 logger 默认未挂载 file handler，仅控制台）
- **`signal` logger** → `log/signals.log`（`signal` 格式）+ 控制台，`propagate=False`

`log/` 目录已在 `.gitignore` 中忽略。

## Claude Skills 参考（`.claude/skills/futuapi/`）

Futu OpenAPI 的参考脚本和文档，按领域组织：

- `SKILL.md` — 主参考文档
- `docs/API_REFERENCE.md` — 行情/交易/订阅的完整 API 函数签名
- `docs/API_LIMITS.md` — 频率限制、订阅额度、历史K线额度
- `docs/FIELD_MAPPING.md` — API 字段与 APP 显示值的映射（持仓/盈亏相关，关键）
- `docs/FUTURES_TRADING.md` — 期货交易相关
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
- **并发注意**：`main.py` 通过线程池并发监控多只股票，但富途 OpenD 的连接为单一共享实例；调整 `max_workers` 时留意 OpenD 的订阅额度与频率限制。

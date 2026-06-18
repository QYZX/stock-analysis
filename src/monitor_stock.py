"""股票实时行情监控脚本"""
import logging
import time
from src.quote_context import QuoteContext
from src.realtime_indicators import RealtimeIndicators, RealtimeInfo
from src.subscribe_stock import SubscriptionManager
from src.util import clear_screen
from src.notification import notify

logger = logging.getLogger(__name__)
signal_logger = logging.getLogger('signal')  # 交易信号专用 logger


def monitor_stock(stock_code: str, sub_types: list = None, interval: int = 5):
    """主函数

    Args:
        stock_code: 股票代码，如 'SH.515050'
        sub_types: 订阅类型列表，默认为 ['QUOTE', 'RT_DATA', 'KL_1MIN']
        interval: 刷新间隔(秒)，默认为 5 秒
    """
    # 配置参数
    if sub_types is None:
        sub_types = ['QUOTE', 'RT_DATA', 'KL_1MIN']

    logger.info("股票代码: %s", stock_code)
    logger.info("刷新间隔: %s秒", interval)

    with QuoteContext() as quote_ctx:
        try:
            sub_manager = SubscriptionManager(quote_ctx)
            sub_manager.subscribe(stock_code, sub_types)

            monitor = RealtimeIndicators(quote_ctx)

            # 单次查询示例
            logger.info("=" * 60)

            # 询问是否开启实时监控
            logger.info("是否开启实时监控? (输入 y 继续, 其他键单次查询)")
            choice = 'y' #input().strip().lower()

            # 清屏
            # clear_screen()

            def _monitor():
                indicators = monitor.get_realtime_info(stock_code)
                monitor.print_realtime_info(indicators)
                # 通过函数判断是否符合需要指标条件
                result = callback(indicators)
                # 根据返回结果发送通知
                send_notification(stock_code, result)

            if choice == 'y':
                while True:
                    _monitor()
                    time.sleep(interval)
            else:
                _monitor()

            logger.info("程序退出")

        except KeyboardInterrupt:
            logger.info("用户中断，程序退出")
        except Exception as e:
            logger.error("错误: %s", e)

def send_notification(stock_code: str, result: dict):
    """根据交易信号发送系统通知

    Args:
        stock_code: 股票代码
        result: callback 返回的结果字典，包含 flag 和 signals
    """
    flag = result.get("flag", 0)
    signals = result.get("signals", [])

    if flag == 0:
        # 无信号，不发送通知
        return

    # 构造通知内容
    if flag == 1:
        title = f"买入信号 - {stock_code}"
        key = f"{stock_code}_buy"
    elif flag == 2:
        title = f"卖出信号 - {stock_code}"
        key = f"{stock_code}_sell"
    else:
        return

    # 将信号列表组合成消息
    message = "\n".join(signals) if signals else "技术指标达到阈值"

    # 发送通知，1分钟内相同信号不重复发送
    sent = notify(title=title, message=message, key=key, cooldown=1.0)

    if sent:
        logger.info("已发送系统通知: %s", title)
        # 记录通知发送到信号日志
        signal_logger.info("已发送系统通知: %s - %s", title, message.replace('\n', ' | '))
    else:
        logger.info("通知在冷却期内，已跳过")


def callback(info: RealtimeInfo):
    """根据技术指标判断买卖信号（需要 KDJ 和 RSI 同时满足）"""
    signals = []
    flag = 0  # 0=无信号 1=买入信号 2=卖出信号

    # 检查指标是否存在
    if info.kdj is None or info.rsi is None:
        return {"flag": flag, "signals": signals}

    k = info.kdj.k
    d = info.kdj.d
    j = info.kdj.j
    rsi1 = info.rsi.rsi1

    # 确保所有必需的指标值都存在
    if k is None or j is None or rsi1 is None:
        return {"flag": flag, "signals": signals}

    # 判断超买：KDJ (K>=85 且 J>=100) 且 RSI (RSI1>=85)
    kdj_overbought = k >= 85 and j >= 100
    rsi_overbought = rsi1 >= 85

    if kdj_overbought and rsi_overbought:
        signals.append(f"KDJ超买: K={k:.2f}, D={d:.2f}, J={j:.2f}")
        signals.append(f"RSI超买: RSI1={rsi1:.2f}")
        flag = 2  # 卖出信号

    # 判断超卖：KDJ (K<=15 且 J<=0) 且 RSI (RSI1<=15)
    kdj_oversold = k <= 15 and j <= 0
    rsi_oversold = rsi1 <= 15

    if kdj_oversold and rsi_oversold:
        signals.append(f"KDJ超卖: K={k:.2f}, D={d:.2f}, J={j:.2f}")
        signals.append(f"RSI超卖: RSI1={rsi1:.2f}")
        flag = 1  # 买入信号

    # 打印信号
    if signals:
        signal_type = "买入" if flag == 1 else "卖出" if flag == 2 else "无"
        logger.info("\n%s", "=" * 60)
        logger.info("交易信号: %s", signal_type)
        for signal in signals:
            logger.info("  - %s", signal)
        logger.info("%s", "=" * 60)

        # 将信号写入专用日志文件
        signal_logger.info("=" * 60)
        signal_logger.info("交易信号: %s", signal_type)
        for signal in signals:
            signal_logger.info("  %s", signal)
        signal_logger.info("=" * 60)

    return {
        "flag": flag,
        "signals": signals,
    }


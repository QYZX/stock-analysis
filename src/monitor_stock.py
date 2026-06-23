"""股票实时行情监控脚本"""
import logging
import time
from src.quote_context import QuoteContext
from src.realtime_indicators import RealtimeIndicators, RealtimeInfo
from src.subscribe_stock import SubscriptionManager
from src.util import clear_screen
from src.notification import notify
from src.signal_callback import on_realtime_info as callback, SignalResult

logger = logging.getLogger(__name__)
signal_logger = logging.getLogger('signal')  # 交易信号专用 logger


def monitor_stock(stock_code: str, sub_types: list = None, interval: int = 5, loop: bool = True):
    """主函数

    Args:
        stock_code: 股票代码，如 'SH.515050'
        sub_types: 订阅类型列表，默认为 ['QUOTE', 'RT_DATA', 'KL_1MIN']
        interval: 刷新间隔(秒)，默认为 5 秒
        loop: 是否循环监控，True 为循环监控，False 为单次查询
    """
    # 配置参数
    if sub_types is None:
        sub_types = ['QUOTE', 'RT_DATA', 'KL_1MIN']

    logger.info("股票代码: %s", stock_code)
    logger.info("刷新间隔: %s秒", interval)
    logger.info("循环监控: %s", loop)

    with QuoteContext() as quote_ctx:
        try:
            sub_manager = SubscriptionManager(quote_ctx)
            sub_manager.subscribe(stock_code, sub_types)

            monitor = RealtimeIndicators(quote_ctx)

            # 单次查询示例
            logger.info("=" * 60)

            # 清屏
            # clear_screen()

            def _monitor():
                indicators = monitor.get_realtime_info(stock_code)
                monitor.print_realtime_info(indicators)
                # 通过函数判断是否符合需要指标条件
                result = callback(indicators)
                # 根据返回结果发送通知
                send_notification(indicators, result)

            if loop:
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

def send_notification(info: RealtimeInfo, result: SignalResult):
    """根据交易信号发送系统通知

    Args:
        info: 实时行情信息
        result: 交易信号结果对象
    """
    if not result.has_signal:
        # 无信号，不发送通知
        return

    signals = result.signals
    signal_type = result.signal_type_name
    stock_code = info.stock_code
    stock_name = info.stock_name
    stock_label = f"{stock_code} {stock_name}"

    # 涨跌幅
    change_info = ""
    if info.change_rate is not None and info.change_val is not None:
        change_info = f" 涨跌: {info.change_val:+.3f}  涨幅: {info.change_rate:+.2f}%"

    # 打印信号日志
    logger.info("\n%s", "=" * 60)
    logger.info("[%s] 信号: %s%s", stock_label, signal_type, change_info)
    for signal in signals:
        logger.info("  - %s", signal)
    logger.info("%s", "=" * 60)

    # 将信号写入专用日志文件
    signal_logger.info("=" * 60)
    signal_logger.info("[%s] 信号: %s%s", stock_label, signal_type, change_info)
    for signal in signals:
        signal_logger.info("  %s", signal)
    signal_logger.info("=" * 60)

    # 构造通知内容
    if result.is_oversold:
        title = f"超卖信号 - {stock_label} 📉"
        key = f"{stock_code}_oversold"
    elif result.is_overbought:
        title = f"超买信号 - {stock_label} 📈"
        key = f"{stock_code}_overbought"
    else:
        return

    # 将信号列表组合成消息
    message = "\n".join(result.signals) if result.signals else "技术指标达到阈值"

    # 发送通知，1分钟内相同信号不重复发送
    sent = notify(title=title, message=message, key=key, cooldown=30)





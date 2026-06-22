"""交易信号回调函数 - 根据技术指标判断超买超卖信号"""
import logging
from dataclasses import dataclass

from src.realtime_indicators import RealtimeInfo

logger = logging.getLogger(__name__)
signal_logger = logging.getLogger('signal')  # 交易信号专用 logger


@dataclass
class SignalResult:
    """交易信号结果

    Attributes:
        flag: 信号标志 (0=无信号, 1=超卖信号, 2=超买信号)
        signals: 信号描述列表
    """
    flag: int
    signals: list[str]

    @property
    def has_signal(self) -> bool:
        """是否有信号"""
        return self.flag != 0

    @property
    def is_oversold(self) -> bool:
        """是否为超卖信号"""
        return self.flag == 1

    @property
    def is_overbought(self) -> bool:
        """是否为超买信号"""
        return self.flag == 2

    @property
    def signal_type_name(self) -> str:
        """信号类型名称"""
        if self.flag == 1:
            return "超卖 📉"
        elif self.flag == 2:
            return "超买 📈"
        else:
            return "无信号"


def on_realtime_info(info: RealtimeInfo) -> SignalResult:
    """根据技术指标判断超买超卖信号（需要 KDJ 和 RSI 同时满足）

    Args:
        info: 实时行情信息

    Returns:
        SignalResult: 交易信号结果对象
    """
    signals = []
    flag = 0  # 0=无信号 1=超卖信号 2=超买信号

    # 检查指标是否存在
    if info.kdj is None or info.rsi is None:
        return SignalResult(flag=flag, signals=signals)

    k = info.kdj.k
    d = info.kdj.d
    j = info.kdj.j
    rsi1 = info.rsi.rsi1

    # 确保所有必需的指标值都存在
    if k is None or j is None or rsi1 is None:
        return SignalResult(flag=flag, signals=signals)

    # 判断超买：KDJ (K>=85 且 J>=100) 且 RSI (RSI1>=85)
    kdj_overbought = k >= 85 and j >= 100
    rsi_overbought = rsi1 >= 85

    if kdj_overbought and rsi_overbought:
        signals.append(f"KDJ超买: K={k:.2f}, D={d:.2f}, J={j:.2f}")
        signals.append(f"RSI超买: RSI1={rsi1:.2f}")
        flag = 2  # 超买信号

    # 判断超卖：KDJ (K<=15 且 J<=0) 且 RSI (RSI1<=15)
    kdj_oversold = k <= 15 and j <= 0
    rsi_oversold = rsi1 <= 15

    if kdj_oversold and rsi_oversold:
        signals.append(f"KDJ超卖: K={k:.2f}, D={d:.2f}, J={j:.2f}")
        signals.append(f"RSI超卖: RSI1={rsi1:.2f}")
        flag = 1  # 超卖信号

    # 打印信号
    if signals:
        signal_type = result.signal_type_name
        stock_label = f"{info.stock_code} {info.stock_name}"
        logger.info("\n%s", "=" * 60)
        logger.info("[%s] 信号: %s", stock_label, signal_type)
        for signal in signals:
            logger.info("  - %s", signal)
        logger.info("%s", "=" * 60)

        # 将信号写入专用日志文件
        signal_logger.info("=" * 60)
        signal_logger.info("[%s] 信号: %s", stock_label, signal_type)
        for signal in signals:
            signal_logger.info("  %s", signal)
        signal_logger.info("=" * 60)

    result = SignalResult(flag=flag, signals=signals)
    return result
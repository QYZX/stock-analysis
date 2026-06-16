"""实时获取股票行情并计算技术指标"""
import time
from dataclasses import dataclass
from datetime import datetime
from futu import *
import talib
import numpy as np


@dataclass
class MACDResult:
    """MACD指标结果"""
    dif: float | None
    dea: float | None
    macd: float | None


@dataclass
class KDJResult:
    """KDJ指标结果"""
    k: float | None
    d: float | None
    j: float | None


@dataclass
class RSIResult:
    """RSI指标结果"""
    rsi1: float | None
    rsi2: float | None
    rsi3: float | None


@dataclass
class RealtimeInfo:
    """实时行情信息"""
    stock_code: str
    timestamp: str
    current_price: float | None
    open_price: float | None
    high_price: float | None
    low_price: float | None
    prev_close_price: float | None
    volume: float | None
    turnover: float | None
    change_val: float | None
    change_rate: float | None
    cur_price: float | None
    avg_price: float | None
    macd: MACDResult | None
    kdj: KDJResult | None
    rsi: RSIResult | None


class RealtimeIndicators:
    """实时行情技术指标计算器"""

    def __init__(self, quote_ctx):
        """初始化

        Args:
            quote_ctx: OpenQuoteContext 实例，由外部统一创建和管理生命周期
        """
        self.quote_ctx = quote_ctx

    def get_rt_data(self, stock_code):
        """获取实时分时数据（需先订阅 RT_DATA）

        Args:
            stock_code: 股票代码

        Returns:
            DataFrame: 分时数据
        """
        ret, data = self.quote_ctx.get_rt_data(code=stock_code)
        if ret == RET_OK:
            return data
        else:
            print(f'获取分时数据失败: {data}')
            return None

    def get_cur_kline(self, stock_code, ktype=KLType.K_1M, num=100):
        """获取实时K线数据（需先订阅对应K线类型）

        Args:
            stock_code: 股票代码
            ktype: K线类型
            num: 返回K线条数

        Returns:
            DataFrame: K线数据
        """
        ret, data = self.quote_ctx.get_cur_kline(
            code=stock_code,
            num=num,
            ktype=ktype
        )
        if ret == RET_OK:
            return data
        else:
            print(f'获取实时K线数据失败: {data}')
            return None

    def get_realtime_quote(self, stock_code):
        """获取实时报价"""
        ret, data = self.quote_ctx.get_stock_quote([stock_code])
        if ret == RET_OK:
            return data.iloc[0]
        else:
            print(f'获取实时报价失败: {data}')
            return None

    def calculate_macd(self, close_prices, fastperiod=12, slowperiod=26, signalperiod=9):
        """计算MACD指标（国内标准：MACD柱 = 2*(DIF-DEA)）"""
        dif, dea, hist = talib.MACD(
            close_prices,
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )
        # 国内软件MACD柱状图为2倍差值
        macd_bar = 2 * hist
        return MACDResult(
            dif=dif[-1] if len(dif) > 0 else None,
            dea=dea[-1] if len(dea) > 0 else None,
            macd=macd_bar[-1] if len(macd_bar) > 0 else None,
        )

    def calculate_kdj(self, high_prices, low_prices, close_prices,
                      fastk_period=9, slowk_period=3, slowd_period=3):
        """计算KDJ指标（国内标准：K/D按2/3、1/3递推平滑）"""
        # 使用STOCHF获取原始RSV
        fastk, _ = talib.STOCHF(
            high_prices,
            low_prices,
            close_prices,
            fastk_period=fastk_period,
            fastd_period=1,
            fastd_matype=0
        )
        # RSV即为fastk，手动按国内标准递推计算K和D
        rsv = fastk
        k = np.zeros_like(rsv)
        d = np.zeros_like(rsv)
        # 初始值：第一根有效K线K=D=50
        k[0] = 50.0
        d[0] = 50.0
        for i in range(1, len(rsv)):
            if np.isnan(rsv[i]):
                k[i] = k[i-1]
                d[i] = d[i-1]
            else:
                k[i] = 2.0/3.0 * k[i-1] + 1.0/3.0 * rsv[i]
                d[i] = 2.0/3.0 * d[i-1] + 1.0/3.0 * k[i]
        j = 3 * k - 2 * d

        return KDJResult(
            k=k[-1] if len(k) > 0 else None,
            d=d[-1] if len(d) > 0 else None,
            j=j[-1] if len(j) > 0 else None,
        )

    def calculate_rsi(self, close_prices, periods=(6, 12, 24)):
        """计算RSI指标（国内标准：同时显示RSI6、RSI12、RSI24）"""
        values = {}
        for period in periods:
            rsi = talib.RSI(close_prices, timeperiod=period)
            values[period] = rsi[-1] if len(rsi) > 0 else None
        return RSIResult(
            rsi1=values.get(6),
            rsi2=values.get(12),
            rsi3=values.get(24),
        )

    def get_realtime_info(self, stock_code):
        """获取实时行情信息（含技术指标）"""
        # 获取分时数据
        rt_data = self.get_rt_data(stock_code)
        # 获取K线数据（用于计算技术指标）
        kline_data = self.get_cur_kline(stock_code, num=100)
        # 获取实时报价
        quote = self.get_realtime_quote(stock_code)

        # 分时最新数据
        latest_tick = None
        if rt_data is not None and len(rt_data) > 0:
            latest_tick = rt_data.iloc[-1]

        # 计算技术指标
        macd = kdj = rsi = None
        if kline_data is not None and len(kline_data) > 0:
            close_prices = np.array(kline_data['close'].values, dtype=float)
            high_prices = np.array(kline_data['high'].values, dtype=float)
            low_prices = np.array(kline_data['low'].values, dtype=float)
            macd = self.calculate_macd(close_prices)
            kdj = self.calculate_kdj(high_prices, low_prices, close_prices)
            rsi = self.calculate_rsi(close_prices)

        # 计算涨跌额和涨跌幅
        change_val = None
        change_rate = None
        if quote is not None and quote['last_price'] is not None and quote['prev_close_price'] not in (None, 0):
            change_val = quote['last_price'] - quote['prev_close_price']
            change_rate = change_val / quote['prev_close_price'] * 100

        return RealtimeInfo(
            stock_code=stock_code,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            current_price=quote['last_price'] if quote is not None else None,
            open_price=quote['open_price'] if quote is not None else None,
            high_price=quote['high_price'] if quote is not None else None,
            low_price=quote['low_price'] if quote is not None else None,
            prev_close_price=quote['prev_close_price'] if quote is not None else None,
            volume=quote['volume'] if quote is not None else None,
            turnover=quote['turnover'] if quote is not None else None,
            change_val=change_val,
            change_rate=change_rate,
            cur_price=latest_tick['cur_price'] if latest_tick is not None else None,
            avg_price=latest_tick['avg_price'] if latest_tick is not None else None,
            macd=macd,
            kdj=kdj,
            rsi=rsi,
        )

    def print_realtime_info(self, info: RealtimeInfo):
        """打印实时行情信息"""
        if info is None:
            print('无法获取行情数据')
            return

        print(f"\n{'='*60}")
        print(f"股票代码: {info.stock_code}")
        print(f"时间: {info.timestamp}")
        print(f"{'-'*60}")

        current = info.current_price
        prev_close = info.prev_close_price
        if current is not None and prev_close and prev_close > 0:
            print(f"最新价: {current:.3f}  涨跌: {info.change_val:.3f}  涨幅: {info.change_rate:.2f}%")
        else:
            print(f"最新价: N/A")

        print(f"开盘: {info.open_price:.3f}" if info.open_price else "开盘: N/A", end='  ')
        print(f"最高: {info.high_price:.3f}" if info.high_price else "最高: N/A", end='  ')
        print(f"最低: {info.low_price:.3f}" if info.low_price else "最低: N/A")
        print(f"昨收: {info.prev_close_price:.3f}" if info.prev_close_price else "昨收: N/A")

        print(f"{'-'*60}")
        print(f"成交量: {info.volume}" if info.volume is not None else "成交量: N/A", end='  ')
        print(f"成交额: {info.turnover}" if info.turnover is not None else "成交额: N/A")

        if info.cur_price is not None:
            avg_str = f"  均价: {info.avg_price:.3f}" if info.avg_price else ""
            print(f"分时当前价: {info.cur_price:.3f}{avg_str}")

        # 技术指标
        if info.macd is not None:
            macd = info.macd
            print(f"{'-'*60}")
            dif_str = f"{macd.dif:.4f}" if macd.dif is not None else "N/A"
            dea_str = f"{macd.dea:.4f}" if macd.dea is not None else "N/A"
            macd_str = f"{macd.macd:.4f}" if macd.macd is not None else "N/A"
            print(f"MACD  DIF: {dif_str}  DEA: {dea_str}  MACD: {macd_str}")

        if info.kdj is not None:
            kdj = info.kdj
            k_str = f"{kdj.k:.2f}" if kdj.k is not None else "N/A"
            d_str = f"{kdj.d:.2f}" if kdj.d is not None else "N/A"
            j_str = f"{kdj.j:.2f}" if kdj.j is not None else "N/A"
            print(f"KDJ   K: {k_str}  D: {d_str}  J: {j_str}")

        if info.rsi is not None:
            rsi = info.rsi
            r1_str = f"{rsi.rsi1:.2f}" if rsi.rsi1 is not None else "N/A"
            r2_str = f"{rsi.rsi2:.2f}" if rsi.rsi2 is not None else "N/A"
            r3_str = f"{rsi.rsi3:.2f}" if rsi.rsi3 is not None else "N/A"
            print(f"RSI   RSI1: {r1_str}  RSI2: {r2_str}  RSI3: {r3_str}")

        print(f"{'='*60}\n")

    def monitor_realtime(self, stock_code, interval=3):
        """实时监控股票行情

        Args:
            stock_code: 股票代码,如 'HK.00700' (腾讯)
            interval: 刷新间隔(秒)
        """
        print(f"开始监控 {stock_code} 的实时行情...")
        print(f"刷新间隔: {interval}秒")
        print("按 Ctrl+C 停止监控\n")

        try:
            while True:
                info = self.get_realtime_info(stock_code)
                self.print_realtime_info(info)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n监控已停止")


def main():
    """主函数示例"""
    from src.subscribe_stock import SubscriptionManager
    from src.quote_context import create_quote_ctx

    quote_ctx = create_quote_ctx()

    stock_code = 'SH.515050'
    sub_manager = SubscriptionManager(quote_ctx)
    sub_manager.subscribe(stock_code, ['QUOTE', 'RT_DATA', 'KL_1MIN'])

    monitor = RealtimeIndicators(quote_ctx)

    info = monitor.get_realtime_info(stock_code)
    monitor.print_realtime_info(info)

    # 实时监控 (取消注释以启用)
    # monitor.monitor_realtime(stock_code, interval=3)

    sub_manager.unsubscribe(stock_code, ['QUOTE', 'RT_DATA', 'KL_1MIN'])
    quote_ctx.close()


if __name__ == '__main__':
    main()

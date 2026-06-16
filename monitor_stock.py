"""股票实时行情监控脚本"""
from src.quote_context import QuoteContext
from src.realtime_indicators import RealtimeIndicators
from src.subscribe_stock import SubscriptionManager
from src.util import clear_screen


def main():
    """主函数"""
    # 配置参数
    stock_code = 'SH.515050'  # 可改为你想监控的股票代码
    sub_types = ['QUOTE', 'RT_DATA', 'KL_1MIN']
    interval = 3  # 刷新间隔(秒)

    print(f"正在连接富途OpenD...")
    print(f"股票代码: {stock_code}")
    print(f"刷新间隔: {interval}秒\n")

    with QuoteContext() as quote_ctx:
        try:
            sub_manager = SubscriptionManager(quote_ctx)
            sub_manager.subscribe(stock_code, sub_types)

            monitor = RealtimeIndicators(quote_ctx)

            # 单次查询示例
            print("=" * 60)
            print("单次查询模式")
            print("=" * 60)
            indicators = monitor.get_realtime_info(stock_code)
            monitor.print_realtime_info(indicators)

            # 询问是否开启实时监控
            print("\n是否开启实时监控? (输入 y 继续, 其他键退出)")
            choice = 'n' #input().strip().lower()

            # 清屏
            # clear_screen()

            if choice == 'y':
                monitor.monitor_realtime(stock_code, interval=interval)
            else:
                print("程序退出")

        except Exception as e:
            print(e)
            print(f"\n错误: {e}")
            print("\n请确保:")
            print("1. 已启动富途OpenD")
            print("2. OpenD监听在 127.0.0.1:11111")
            print("3. 已安装依赖: pip install futu-api")


if __name__ == '__main__':
    main()

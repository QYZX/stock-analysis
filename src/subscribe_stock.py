"""股票数据订阅管理脚本

提供简单的订阅/取消订阅函数，可直接在代码中调用
"""

from futu import *


class SubscriptionManager:
    """订阅管理器"""

    def __init__(self, quote_ctx):
        """初始化

        Args:
            quote_ctx: OpenQuoteContext 实例，由外部统一创建和管理生命周期
        """
        self.quote_ctx = quote_ctx

        self.type_mapping = {
            'QUOTE': SubType.QUOTE,
            'ORDER_BOOK': SubType.ORDER_BOOK,
            'TICKER': SubType.TICKER,
            'RT_DATA': SubType.RT_DATA,
            'KL_DAY': SubType.K_DAY,
            'KL_1MIN': SubType.K_1M,
            'KL_5MIN': SubType.K_5M,
        }

    def subscribe(self, stock_codes, sub_types):
        """订阅股票数据

        Args:
            stock_codes: 股票代码列表或单个代码，如 ['HK.00700'] 或 'HK.00700'
            sub_types: 订阅类型列表或单个类型，如 ['QUOTE'] 或 'QUOTE'

        Returns:
            tuple: (ret_code, err_msg)
        """
        # 统一转换为列表
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        if isinstance(sub_types, str):
            sub_types = [sub_types]

        # 转换订阅类型
        subtype_list = [self.type_mapping[t] for t in sub_types if t in self.type_mapping]

        if not subtype_list:
            return RET_ERROR, "没有有效的订阅类型"

        # 执行订阅
        ret_code, err_msg = self.quote_ctx.subscribe(
            code_list=stock_codes,
            subtype_list=subtype_list
        )

        if ret_code == RET_OK:
            print(f"✓ 订阅成功: {stock_codes} - {sub_types}")
        else:
            print(f"✗ 订阅失败: {err_msg}")

        return ret_code, err_msg

    def unsubscribe(self, stock_codes, sub_types):
        """取消订阅

        Args:
            stock_codes: 股票代码列表或单个代码
            sub_types: 订阅类型列表或单个类型

        Returns:
            tuple: (ret_code, err_msg)
        """
        # 统一转换为列表
        if isinstance(stock_codes, str):
            stock_codes = [stock_codes]
        if isinstance(sub_types, str):
            sub_types = [sub_types]

        # 转换订阅类型
        subtype_list = [self.type_mapping[t] for t in sub_types if t in self.type_mapping]

        if not subtype_list:
            return RET_ERROR, "没有有效的订阅类型"

        # 执行取消订阅
        ret_code, err_msg = self.quote_ctx.unsubscribe(
            code_list=stock_codes,
            subtype_list=subtype_list
        )

        if ret_code == RET_OK:
            print(f"✓ 取消订阅成功: {stock_codes} - {sub_types}")
        else:
            print(f"✗ 取消订阅失败: {err_msg}")

        return ret_code, err_msg

    def unsubscribe_all(self):
        """取消所有订阅

        Returns:
            bool: 是否成功
        """
        ret_code, data = self.quote_ctx.query_subscription()
        if ret_code != RET_OK:
            print(f"查询订阅失败: {data}")
            return False

        # 检查是否为空
        is_empty = False
        if isinstance(data, dict):
            is_empty = len(data) == 0
        elif hasattr(data, 'empty'):
            is_empty = data.empty

        if is_empty:
            print("当前没有任何订阅")
            return True

        # 按订阅类型分组取消
        if hasattr(data, 'iterrows'):
            # DataFrame
            for _, row in data.iterrows():
                self.quote_ctx.unsubscribe([row['code']], [row['sub_type']])
        else:
            print("无法处理的数据格式，请手动取消订阅")
            return False

        print("✓ 所有订阅已取消")
        return True

    def list_subscriptions(self):
        """列出当前所有订阅

        Returns:
            DataFrame: 订阅信息
        """
        ret_code, data = self.quote_ctx.query_subscription()
        if ret_code != RET_OK:
            print(f"查询订阅失败: {data}")
            return None

        # 检查是否为空
        is_empty = False
        if isinstance(data, dict):
            is_empty = len(data) == 0
        elif hasattr(data, 'empty'):
            is_empty = data.empty

        if is_empty:
            print("当前没有任何订阅")
            return data if not isinstance(data, dict) else None

        print("\n当前订阅列表:")
        print("=" * 70)

        # 判断数据类型并遍历
        if hasattr(data, 'iterrows'):
            # DataFrame
            for _, row in data.iterrows():
                print(f"{row['code']:<15} {row['sub_type']:<20} "
                      f"已用: {row['used_quota']:<5} 剩余: {row['remain_quota']:<5}")
        else:
            # 其他格式，直接打印
            print(data)

        print("=" * 70)

        return data

def main():
    """示例用法"""
    from src.quote_context import create_quote_ctx

    quote_ctx = create_quote_ctx()
    manager = SubscriptionManager(quote_ctx)

    # 订阅示例
    # manager.subscribe(['SH.515050'], ['QUOTE', 'RT_DATA'])

    # 查看订阅
    manager.list_subscriptions()

    # 取消订阅
    # manager.unsubscribe('HK.00700', 'QUOTE')

    # 取消所有订阅
    # manager.unsubscribe_all()

    # 关闭连接
    quote_ctx.close()


def example_with_realtime_indicators():
    """示例：与 RealtimeIndicators 共享连接"""
    from src.realtime_indicators import RealtimeIndicators
    from src.quote_context import create_quote_ctx

    quote_ctx = create_quote_ctx()

    indicators = RealtimeIndicators(quote_ctx)
    manager = SubscriptionManager(quote_ctx)

    # 订阅股票数据
    manager.subscribe('HK.00700', ['QUOTE', 'RT_DATA'])

    # 查看订阅
    manager.list_subscriptions()

    # 计算技术指标（使用同一连接）
    result = indicators.calculate_all_indicators('HK.00700')
    indicators.print_indicators(result)

    # 取消订阅
    manager.unsubscribe('HK.00700', ['QUOTE', 'RT_DATA'])

    # 统一关闭连接
    quote_ctx.close()


if __name__ == '__main__':
    main()

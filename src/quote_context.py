"""富途行情上下文管理

集中管理 OpenQuoteContext 的创建和关闭，
避免各模块各自创建连接导致资源泄漏。
"""

import logging

from futu import OpenQuoteContext

logger = logging.getLogger(__name__)

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 11111


class QuoteContext:
    """行情上下文，支持 with 语句自动关闭"""

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.ctx = OpenQuoteContext(host=host, port=port)

    def __enter__(self):
        return self.ctx

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        """关闭连接"""
        if self.ctx is not None:
            self.ctx.close()
            self.ctx = None


def create_quote_ctx(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """创建并返回 OpenQuoteContext 实例

    调用方负责在程序结束时调用 quote_ctx.close() 关闭连接，
    或使用 QuoteContext 上下文管理器自动关闭。
    """
    logger.info("正在连接富途OpenD...")
    return OpenQuoteContext(host=host, port=port)

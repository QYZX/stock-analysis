"""主程序入口：批量监控多个股票"""
import logging

import yaml
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.monitor_stock import monitor_stock
from logging_config import setup_logging

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    """从 YAML 文件加载配置

    Args:
        config_path: 配置文件路径，默认为 config.yaml

    Returns:
        配置字典
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


def monitor_single_stock(stock_item, sub_types: list, interval: int, idx: int, total: int):
    """监控单个股票的工作函数

    Args:
        stock_item: 股票配置项（字典或字符串）
        sub_types: 订阅类型列表
        interval: 刷新间隔
        idx: 当前索引
        total: 总数

    Returns:
        tuple: (stock_code, success, error_message)
    """
    # 从对象中提取股票代码
    stock_code = stock_item.get('code') if isinstance(stock_item, dict) else stock_item

    if not stock_code:
        return (None, False, "股票代码为空")

    logger.info("[%d/%d] 正在查询: %s", idx, total, stock_code)
    logger.info("-" * 60)

    try:
        # 调用 monitor_stock 的 main 函数进行单次查询
        monitor_stock(stock_code, sub_types=sub_types, interval=interval)
        logger.info("[%d/%d] %s 查询完成", idx, total, stock_code)
        return (stock_code, True, None)
    except Exception as e:
        error_msg = f"{stock_code} 查询失败: {e}"
        logger.error("[%d/%d] %s", idx, total, error_msg)
        return (stock_code, False, str(e))


def main():
    """主函数：监控多个股票代码"""
    # 从配置文件读取
    try:
        config = load_config()
    except FileNotFoundError as e:
        logger.error("%s", e)
        logger.error("请创建 config.yaml 文件")
        return
    except Exception as e:
        logger.error("配置文件格式错误: %s", e)
        return

    # 从配置中获取参数
    stock_codes_config = config.get('stock_codes', [])
    sub_types = config.get('sub_types', ['QUOTE', 'RT_DATA', 'KL_1MIN'])
    interval = config.get('interval', 5)
    max_workers = config.get('max_workers', 5)  # 最大线程数，默认5个

    # 验证配置
    if not stock_codes_config:
        logger.error("配置文件中没有股票代码")
        return

    logger.info("=" * 60)
    logger.info("开始监控 %d 只股票（最大并发数: %d）", len(stock_codes_config), max_workers)
    logger.info("=" * 60)

    # 使用线程池并发执行
    total = len(stock_codes_config)
    success_count = 0
    failed_stocks = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = [
            executor.submit(
                monitor_single_stock,
                stock_item,
                sub_types,
                interval,
                idx,
                total
            )
            for idx, stock_item in enumerate(stock_codes_config, 1)
        ]

        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                stock_code, success, error_msg = future.result()
                if success:
                    success_count += 1
                elif stock_code:
                    failed_stocks.append((stock_code, error_msg))
            except Exception as e:
                logger.error("线程执行异常: %s", e)

    logger.info("=" * 60)
    logger.info("所有股票查询完成 - 成功: %d/%d, 失败: %d", success_count, total, len(failed_stocks))

    if failed_stocks:
        logger.warning("失败的股票:")
        for stock_code, error_msg in failed_stocks:
            logger.warning("  - %s: %s", stock_code, error_msg)

    logger.info("=" * 60)


if __name__ == "__main__":
    setup_logging()
    main()
    

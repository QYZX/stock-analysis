"""日志配置模块"""
import logging
import logging.config


LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {                     # 定义日志格式
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {                       # 定义处理器（输出目的地）
        'console': {                    # 控制台处理器
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {                       # 文件处理器
            'class': 'logging.FileHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'filename': 'log.log',
            'mode': 'a',
            'encoding': 'utf-8'         # 使用 UTF-8 编码
        }
    },
    'root': {                           # 配置根记录器
        'level': 'INFO',
        'handlers': ['console']         # 默认只输出到控制台
    }
}


def setup_logging(log_level: str = 'INFO'):
    """初始化日志配置

    Args:
        enable_file_log: 是否启用文件日志，默认为 False
        log_level: 日志级别，默认为 'INFO'
    """
    config = LOGGING_CONFIG.copy()

    # 应用配置
    logging.config.dictConfig(config)


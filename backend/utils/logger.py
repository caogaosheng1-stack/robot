"""
日志系统 - 用于系统日志记录和调试
"""
import logging
import os
from datetime import datetime
from config.constants import LOG_LEVEL, LOG_DIR, LOG_FORMAT


class LoggerManager:
    """日志管理器 - 单例模式"""
    
    _instance = None
    _logger = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance
    
    def _init_logger(self):
        """初始化日志系统"""
        # 创建日志目录
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        # 配置日志格式
        log_format = logging.Formatter(LOG_FORMAT)
        
        # 创建logger
        self._logger = logging.getLogger('RobotSortingSystem')
        self._logger.setLevel(LOG_LEVEL)
        
        # 文件处理器
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = os.path.join(LOG_DIR, f'simulation_{timestamp}.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(LOG_LEVEL)
        file_handler.setFormatter(log_format)
        self._logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL)
        console_handler.setFormatter(log_format)
        self._logger.addHandler(console_handler)
    
    @staticmethod
    def get_logger():
        """获取logger实例"""
        manager = LoggerManager()
        return manager._logger


def get_logger():
    """便利函数 - 获取logger"""
    return LoggerManager.get_logger()

# 装饰器模块
# 提供通用装饰器功能

from functools import wraps
from typing import Any, Callable, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def handle_tool_errors(
    default_response: Any = None,
    error_message: str = "抱歉，操作失败"
) -> Callable:
    """
    工具函数错误处理装饰器
    
    Args:
        default_response: 默认返回值
        error_message: 错误提示消息
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError:
                return {"error": "暂无数据，请先导入跑步数据"}
            except ValueError as e:
                return {"error": f"参数错误：{str(e)}"}
            except KeyError as e:
                return {"error": f"数据字段缺失：{str(e)}"}
            except Exception as e:
                logger.error(f"工具调用失败：{func.__name__} - {e}", exc_info=True)
                return default_response or {"error": error_message}
        return wrapper
    return decorator


def require_storage(func: Callable) -> Callable:
    """
    确保 StorageManager 已初始化的装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.storage is None:
            from src.core.storage import StorageManager
            self.storage = StorageManager()
        return func(self, *args, **kwargs)
    return wrapper


def validate_date_format(date_str: str) -> bool:
    """
    验证日期格式
    
    Args:
        date_str: 日期字符串
        
    Returns:
        bool: 是否为有效日期格式
    """
    from datetime import datetime
    if not date_str or not isinstance(date_str, str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def handle_empty_data(default_message: str = "暂无数据") -> Callable:
    """
    处理空数据的装饰器
    
    Args:
        default_message: 默认消息
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if result is None or (isinstance(result, (list, dict)) and len(result) == 0):
                return {"message": default_message}
            return result
        return wrapper
    return decorator

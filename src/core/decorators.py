# 装饰器模块
# 提供通用装饰器功能

import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from src.core.exceptions import NanobotRunnerError, ToolResult, ValidationError

logger = logging.getLogger(__name__)


def tool_wrapper(func: Callable) -> Callable:
    """
    工具统一异常处理装饰器

    将所有异常转换为统一的 ToolResult 格式返回

    Args:
        func: 被装饰的工具函数

    Returns:
        Callable: 装饰后的函数
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            result = func(*args, **kwargs)
            if isinstance(result, ToolResult):
                return result.to_json()
            return ToolResult(success=True, data=result).to_json()
        except ValidationError as e:
            logger.error(f"输入验证失败: {e.message}", exc_info=True)
            return ToolResult(success=False, error=f"输入验证失败: {e.message}").to_json()
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {e}", exc_info=True)
            return ToolResult(success=False, error=f"文件不存在: {e}").to_json()
        except NanobotRunnerError as e:
            logger.error(f"业务错误: {e.message}", exc_info=True)
            return ToolResult(success=False, error=e.message).to_json()
        except Exception as e:
            logger.error(f"内部错误: {e}", exc_info=True)
            return ToolResult(success=False, error=f"内部错误: {e}").to_json()

    return wrapper


def handle_tool_errors(
    default_response: Any = None, error_message: str = "抱歉，操作失败"
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
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except NanobotRunnerError as e:
                logger.error(f"工具调用失败：{func.__name__} - {e.message}", exc_info=True)
                return e.to_dict()
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


def handle_errors(default_response: Any = None, log_traceback: bool = True) -> Callable:
    """
    统一错误处理装饰器

    Args:
        default_response: 默认返回值
        log_traceback: 是否记录完整堆栈

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except NanobotRunnerError as e:
                if log_traceback:
                    logger.error(
                        f"操作失败 [{e.error_code}]: {e.message}",
                        exc_info=True,
                    )
                else:
                    logger.error(f"操作失败 [{e.error_code}]: {e.message}")
                return default_response or e.to_dict()
            except FileNotFoundError as e:
                logger.error(f"文件未找到: {e}", exc_info=log_traceback)
                return default_response or {
                    "error": f"文件未找到: {str(e)}",
                    "error_code": "FILE_NOT_FOUND",
                    "recovery_suggestion": "请确认文件路径是否正确",
                }
            except ValueError as e:
                logger.error(f"参数错误: {e}", exc_info=log_traceback)
                return default_response or {
                    "error": f"参数错误: {str(e)}",
                    "error_code": "VALUE_ERROR",
                    "recovery_suggestion": "请检查输入参数是否正确",
                }
            except KeyError as e:
                logger.error(f"键错误: {e}", exc_info=log_traceback)
                return default_response or {
                    "error": f"数据字段缺失: {str(e)}",
                    "error_code": "KEY_ERROR",
                    "recovery_suggestion": "请检查数据结构是否完整",
                }
            except Exception as e:
                logger.error(f"未知错误: {e}", exc_info=log_traceback)
                return default_response or {
                    "error": f"操作失败: {str(e)}",
                    "error_code": "UNKNOWN_ERROR",
                    "recovery_suggestion": "请稍后重试或联系支持",
                }

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
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
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
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            if result is None or (
                isinstance(result, (list, dict)) and len(result) == 0
            ):
                return {"message": default_message}
            return result

        return wrapper

    return decorator

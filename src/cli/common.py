# CLI 公共模块
# 包含错误处理、状态输出等公共功能

from typing import Any

from rich.console import Console

console = Console()


class CLIError:
    """CLI错误消息和恢复建议"""

    @staticmethod
    def path_not_found(path: str) -> dict:
        return {
            "message": f"路径不存在: {path}",
            "suggestion": "请检查路径是否正确，或使用绝对路径",
        }

    @staticmethod
    def import_failed(error: str) -> dict:
        return {
            "message": f"导入失败: {error}",
            "suggestion": "请确保文件是有效的FIT格式，或使用 --force 参数强制导入",
        }

    @staticmethod
    def config_missing(key: str) -> dict:
        return {
            "message": f"缺少配置: {key}",
            "suggestion": f"请运行 'nanobotrun config --set {key}' 进行配置",
        }

    @staticmethod
    def storage_error(error: str) -> dict:
        return {
            "message": f"存储错误: {error}",
            "suggestion": "请检查数据目录权限，或运行 'nanobotrun data import <路径>' 导入数据",
        }

    @staticmethod
    def schedule_not_found() -> dict:
        return {
            "message": "未找到定时任务",
            "suggestion": "请先使用 'nanobotrun report --schedule HH:MM' 配置定时推送",
        }

    @staticmethod
    def push_failed(error: str) -> dict:
        return {
            "message": f"推送失败: {error}",
            "suggestion": "请检查飞书 Webhook 配置，或运行 'nanobotrun config --show' 查看当前配置",
        }

    @staticmethod
    def execution_record_failed(error: str) -> dict:
        return {
            "message": f"执行反馈记录失败: {error}",
            "suggestion": "请检查计划ID和日期是否正确，使用 'nanobotrun plan stats <plan_id>' 查看计划状态",
        }


def print_error(error_info: dict[str, Any] | str) -> None:
    """打印带恢复建议的错误消息

    Args:
        error_info: 错误信息字典（包含 message 和 suggestion 键）或字符串
    """
    if isinstance(error_info, str):
        console.print(f"[red bold]错误:[/red bold] {error_info}")
        return
    console.print(f"[red bold]错误:[/red bold] {error_info['message']}")
    console.print(f"[yellow]建议:[/yellow] {error_info['suggestion']}")


def print_status(message: str, status: str = "info") -> None:
    """打印带状态颜色的消息

    Args:
        message: 消息内容
        status: 状态类型 (success/error/warning/info)
    """
    colors = {
        "success": "green",
        "error": "red",
        "warning": "yellow",
        "info": "cyan",
    }
    color = colors.get(status, "white")
    console.print(f"[{color}]{message}[/{color}]")

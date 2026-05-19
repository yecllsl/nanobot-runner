# Nanobot Runner - 桌面端私人AI跑步助理
# 主模块初始化

import tomllib
from pathlib import Path

from src.core.base.exceptions import NanobotRunnerError


def _get_version() -> str:
    """从 pyproject.toml 动态读取版本号"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except NanobotRunnerError:
        return "0.0.0"


__version__ = _get_version()
__author__ = "Trae IDE Dev Agent"

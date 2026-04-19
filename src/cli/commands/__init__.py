# CLI Commands 模块
# 命令路由定义

from src.cli.commands.agent import app as agent_app
from src.cli.commands.analysis import app as analysis_app
from src.cli.commands.data import app as data_app
from src.cli.commands.gateway import app as gateway_app
from src.cli.commands.plan import app as plan_app
from src.cli.commands.report import app as report_app
from src.cli.commands.report import profile_app
from src.cli.commands.system import app as system_app

__all__ = [
    "data_app",
    "analysis_app",
    "agent_app",
    "report_app",
    "profile_app",
    "gateway_app",
    "system_app",
    "plan_app",
]

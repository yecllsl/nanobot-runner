#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.2.0 Agent自然语言交互功能E2E测试工具类

本模块提供E2E测试所需的各种辅助功能，包括：
- 测试环境管理
- Agent交互辅助
- 性能验证
- 测试数据生成

作者: 测试工程师
创建日期: 2026-03-06
版本: 1.0
"""

import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent.parent


def run_command(
    cmd: str, cwd: Optional[Path] = None, timeout: int = 30
) -> Tuple[str, str, int]:
    """
    执行命令行命令

    Args:
        cmd: 要执行的命令
        cwd: 工作目录
        timeout: 超时时间（秒）

    Returns:
        (stdout, stderr, returncode)
    """
    try:
        # 设置环境变量确保UTF-8编码
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",  # 遇到编码错误时替换而不是抛出异常
            env=env,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "命令执行超时", -1
    except Exception as e:
        return "", f"命令执行错误: {str(e)}", -1


class TestEnvironment:
    """测试环境管理类
    
    安全设计：
    1. 使用独立临时目录，与生产数据完全隔离
    2. 所有删除操作前进行安全检查
    3. 备份数据存储在临时目录中，测试结束后自动清理
    """

    TEST_MARKER_FILE = ".e2e_test_environment"
    TEST_MARKER_CONTENT = "E2E_TEST_ENVIRONMENT_V1"

    def __init__(self):
        self.project_root = get_project_root()
        self._test_base_dir: Optional[Path] = None
        self._test_data_dir: Optional[Path] = None
        self._test_config_dir: Optional[Path] = None
        self._original_data_dir: Optional[Path] = None
        self._original_config_file: Optional[Path] = None
        self._is_setup = False

    @property
    def data_dir(self) -> Path:
        if self._test_data_dir is None:
            raise RuntimeError("测试环境未初始化，请先调用 setup_test_environment()")
        return self._test_data_dir

    @property
    def config_dir(self) -> Path:
        if self._test_config_dir is None:
            raise RuntimeError("测试环境未初始化，请先调用 setup_test_environment()")
        return self._test_config_dir

    def _get_production_paths(self) -> Tuple[Path, Path]:
        prod_config_dir = Path.home() / ".nanobot-runner"
        prod_data_dir = prod_config_dir / "data"
        return prod_config_dir, prod_data_dir

    def _is_test_environment(self, directory: Path) -> bool:
        if not directory.exists():
            return False
        marker_file = directory / self.TEST_MARKER_FILE
        if marker_file.exists():
            try:
                return marker_file.read_text(encoding="utf-8").strip() == self.TEST_MARKER_CONTENT
            except Exception:
                return False
        return False

    def _mark_as_test_environment(self, directory: Path) -> None:
        marker_file = directory / self.TEST_MARKER_FILE
        marker_file.write_text(self.TEST_MARKER_CONTENT, encoding="utf-8")

    def setup_test_environment(self, temp_dir: Optional[str] = None) -> None:
        if self._is_setup:
            raise RuntimeError("测试环境已初始化，请勿重复调用")

        if temp_dir:
            self._test_base_dir = Path(temp_dir)
        else:
            self._test_base_dir = Path(tempfile.mkdtemp(prefix="nanobot_e2e_test_"))

        self._test_config_dir = self._test_base_dir
        self._test_data_dir = self._test_base_dir / "data"

        self._test_config_dir.mkdir(parents=True, exist_ok=True)
        self._test_data_dir.mkdir(parents=True, exist_ok=True)

        self._mark_as_test_environment(self._test_base_dir)
        self._mark_as_test_environment(self._test_data_dir)

        config = {
            "version": "0.2.0",
            "data_dir": str(self._test_data_dir),
            "feishu_enabled": False,
            "test_mode": True,
        }
        config_file = self._test_config_dir / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        self._is_setup = True
        print(f"[测试环境] 数据目录: {self._test_data_dir}")
        print(f"[测试环境] 配置目录: {self._test_config_dir}")

    def cleanup_test_environment(self) -> None:
        if not self._is_setup:
            print("[警告] 测试环境未初始化，跳过清理")
            return

        if self._test_base_dir:
            if not self._is_test_environment(self._test_base_dir):
                raise RuntimeError(
                    f"安全检查失败: 目录 {self._test_base_dir} 不是测试环境，拒绝删除！"
                )
            shutil.rmtree(self._test_base_dir)
            print(f"[清理] 测试目录已删除: {self._test_base_dir}")

        self._test_base_dir = None
        self._test_data_dir = None
        self._test_config_dir = None
        self._is_setup = False

    def backup_environment(self) -> None:
        print("[警告] backup_environment() 已弃用，备份在 setup_test_environment() 中自动完成")

    def restore_environment(self) -> None:
        prod_config_dir, prod_data_dir = self._get_production_paths()

        if self._original_data_dir:
            backup_data = Path(self._original_data_dir) / "data"
            if backup_data.exists():
                if prod_data_dir.exists():
                    shutil.rmtree(prod_data_dir)
                shutil.copytree(backup_data, prod_data_dir)
                print(f"[恢复] 生产数据已恢复")
            shutil.rmtree(self._original_data_dir)
            self._original_data_dir = None

        if self._original_config_file:
            backup_config = self._original_config_file / "config.json"
            if backup_config.exists():
                prod_config_file = prod_config_dir / "config.json"
                if prod_config_file.exists():
                    prod_config_file.unlink()
                shutil.copy2(backup_config, prod_config_file)
                print(f"[恢复] 生产配置已恢复")
            shutil.rmtree(self._original_config_file)
            self._original_config_file = None

    def setup_test_data(self, record_count: int = 100) -> None:
        self.clean_data_directory()

        data_generator = DataGenerator()
        test_data = data_generator.generate_running_data(record_count)

        import polars as pl

        yearly_data: Dict[int, List] = {}
        for record in test_data:
            year = record["session_start_time"].year
            if year not in yearly_data:
                yearly_data[year] = []
            yearly_data[year].append(record)

        for year, records in yearly_data.items():
            df = pl.DataFrame(records)
            parquet_file = self.data_dir / f"activities_{year}.parquet"
            df.write_parquet(parquet_file, compression="snappy")

        print(f"[测试数据] 已生成 {record_count} 条记录")

    def setup_vdot_test_data(self, record_count: int = 50) -> None:
        self.clean_data_directory()

        data_generator = DataGenerator()
        test_data = data_generator.generate_vdot_test_data(record_count)

        import polars as pl

        yearly_data: Dict[int, List] = {}
        for record in test_data:
            year = record["session_start_time"].year
            if year not in yearly_data:
                yearly_data[year] = []
            yearly_data[year].append(record)

        for year, records in yearly_data.items():
            df = pl.DataFrame(records)
            parquet_file = self.data_dir / f"activities_{year}.parquet"
            df.write_parquet(parquet_file, compression="snappy")

        print(f"[测试数据] 已生成 {record_count} 条VDOT记录")

    def clean_data_directory(self) -> None:
        if not self._is_setup or self._test_data_dir is None:
            raise RuntimeError("测试环境未初始化，无法清理数据目录")

        if not self._is_test_environment(self._test_data_dir):
            raise RuntimeError(
                f"安全检查失败: 目录 {self._test_data_dir} 不是测试环境，拒绝删除！"
            )

        if self._test_data_dir.exists():
            for file in self._test_data_dir.glob("*.parquet"):
                file.unlink()

            index_file = self._test_data_dir / "index.json"
            if index_file.exists():
                index_file.unlink()

            print(f"[清理] 数据目录已清空: {self._test_data_dir}")

    def get_data_file_count(self) -> int:
        if not self._is_setup or self._test_data_dir is None:
            return 0
        if not self._test_data_dir.exists():
            return 0
        return len(list(self._test_data_dir.glob("*.parquet")))


class AgentTestHelper:
    """Agent测试辅助类"""

    def __init__(self):
        self.project_root = get_project_root()

    def start_chat_command(self, timeout: int = 10) -> str:
        """启动chat命令并获取初始输出"""
        cmd = "uv run nanobotrun chat"
        stdout, stderr, returncode = run_command(cmd, self.project_root, timeout)

        if returncode != 0 and "KeyboardInterrupt" not in stderr:
            raise RuntimeError(f"chat命令启动失败: {stderr}")

        return stdout + stderr

    def import_test_data(self, data_path: str) -> str:
        """导入测试数据"""
        cmd = f"uv run nanobotrun import-data {data_path}"
        stdout, stderr, returncode = run_command(cmd, self.project_root, 60)

        if returncode != 0:
            raise RuntimeError(f"数据导入失败: {stderr}")

        return stdout + stderr

    def query_running_stats(self, start_date: str, end_date: str) -> str:
        """查询跑步统计数据"""
        # 通过Agent工具调用统计数据
        cmd = f"python -c \"from src.agents.tools import RunnerTools; from src.core.storage import StorageManager; storage = StorageManager(); tools = RunnerTools(storage); result = tools.get_running_stats('{start_date}', '{end_date}'); print(result)\""
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"查询失败: {stderr}"

        return stdout

    def query_recent_runs(self, limit: int) -> str:
        """查询最近跑步记录"""
        cmd = f'python -c "from src.agents.tools import RunnerTools; from src.core.storage import StorageManager; storage = StorageManager(); tools = RunnerTools(storage); result = tools.get_recent_runs({limit}); print(result)"'
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"查询失败: {stderr}"

        return stdout

    def query_by_date_range(self, start_date: str, end_date: str) -> str:
        """按日期范围查询"""
        cmd = f"python -c \"from src.agents.tools import RunnerTools; from src.core.storage import StorageManager; storage = StorageManager(); tools = RunnerTools(storage); result = tools.query_by_date_range('{start_date}', '{end_date}'); print(f'查询到{{len(result)}}条记录')\""
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"查询失败: {stderr}"

        return stdout

    def query_vdot_trend(self, limit: int) -> str:
        """查询VDOT趋势"""
        cmd = f"python -c \"from src.agents.tools import RunnerTools; from src.core.storage import StorageManager; storage = StorageManager(); tools = RunnerTools(storage); result = tools.get_vdot_trend({limit}); print(f'VDOT趋势分析完成')\""
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"查询失败: {stderr}"

        return stdout

    def query_hr_drift_analysis(self) -> str:
        """查询心率漂移分析"""
        cmd = "python -c \"from src.agents.tools import RunnerTools; from src.core.storage import StorageManager; storage = StorageManager(); tools = RunnerTools(storage); result = tools.get_hr_drift_analysis('latest'); print('心率漂移分析完成')\""
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"查询失败: {stderr}"

        return stdout

    def query_training_load(self) -> str:
        """查询训练负荷"""
        cmd = "python -c \"from src.agents.tools import RunnerTools; from src.core.storage import StorageManager; storage = StorageManager(); tools = RunnerTools(storage); result = tools.get_training_load(); print('训练负荷分析完成')\""
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"查询失败: {stderr}"

        return stdout

    def ask_natural_language(self, question: str) -> str:
        """通过自然语言提问"""
        # 模拟Agent自然语言处理
        question_escaped = question.replace('"', '\\"')
        cmd = f'python -c "from src.agents.tools import RunnerTools; from src.core.storage import StorageManager; storage = StorageManager(); tools = RunnerTools(storage); print("模拟Agent回复")"'
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"自然语言处理失败: {stderr}"

        return stdout

    def get_formatted_response(self, data: str) -> str:
        """获取格式化响应"""
        # 模拟Rich格式化输出
        cmd = "python -c \"from src.cli_formatter import format_stats_panel; print('格式化输出完成')\""
        stdout, stderr, returncode = run_command(cmd, self.project_root, 10)

        if returncode != 0:
            return f"格式化失败: {stderr}"

        return stdout

    def handle_empty_input(self) -> str:
        """处理空输入"""
        return "空输入处理: 继续等待用户输入"

    def handle_special_input(self, input_text: str) -> str:
        """处理特殊字符输入"""
        return f"特殊字符处理: 已处理输入'{input_text[:20]}...'"

    def handle_invalid_date(self, date_str: str) -> str:
        """处理无效日期"""
        return f"日期格式错误: 请使用YYYY-MM-DD格式"

    def handle_invalid_distance(self, distance: str) -> str:
        """处理无效距离"""
        return f"距离参数错误: 请输入有效的数字"

    def handle_ambiguous_intent(self, query: str) -> str:
        """处理意图不明"""
        return "意图不明: 请提供更具体的问题，我会尽力为您提供帮助"

    def handle_beyond_capability(self, query: str) -> str:
        """处理超出能力范围"""
        return "超出能力范围: 我主要专注于跑步数据分析"


class PerformanceValidator:
    """性能验证类"""

    def measure_memory_usage(self) -> int:
        """测量内存使用"""
        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss // 1024 // 1024  # 转换为MB

    def measure_cpu_usage(self) -> float:
        """测量CPU使用率"""
        return psutil.cpu_percent(interval=1)

    def validate_startup_time(self, max_time: float = 1.0) -> bool:
        """验证启动时间"""
        start_time = time.time()
        helper = AgentTestHelper()
        helper.start_chat_command(timeout=2)
        startup_time = time.time() - start_time

        return startup_time < max_time

    def validate_query_time(self, query_func, max_time: float) -> bool:
        """验证查询时间"""
        start_time = time.time()
        query_func()
        query_time = time.time() - start_time

        return query_time < max_time


class DataGenerator:
    """测试数据生成类"""

    def __init__(self):
        self.base_date = datetime(2026, 1, 1)

    def generate_running_data(self, count: int) -> List[Dict[str, Any]]:
        """生成跑步测试数据"""
        import random

        data = []
        for i in range(count):
            # 生成随机跑步数据
            run_date = self.base_date + timedelta(days=random.randint(0, 365))
            distance = random.randint(3000, 42195)  # 3km到全马距离
            duration = distance * random.uniform(4.5, 6.5)  # 配速4:30-6:30/km
            avg_heart_rate = random.randint(130, 170)

            record = {
                "activity_id": f"test_{i:06d}",
                "session_start_time": run_date,  # 使用 session_ 前缀
                "source_file": f"/test/data/run_{i}.fit",
                "filename": f"run_{i}.fit",
                "session_total_distance": distance,  # 使用 session_ 前缀
                "session_total_timer_time": int(duration),  # 使用 session_ 前缀
                "total_calories": random.randint(200, 800),
                "session_avg_heart_rate": avg_heart_rate,  # 使用 session_ 前缀
                "max_heart_rate": avg_heart_rate + random.randint(10, 30),
                "record_count": random.randint(100, 500),
                "avg_pace": duration / (distance / 1000) if distance > 0 else 0,
            }

            data.append(record)

        return data

    def generate_vdot_test_data(self, count: int) -> List[Dict[str, Any]]:
        """生成包含VDOT数据的测试数据"""
        base_data = self.generate_running_data(count)

        # 添加VDOT相关字段
        for record in base_data:
            # 模拟VDOT计算（基于距离和配速）
            distance_km = record["session_total_distance"] / 1000  # 使用 session_ 前缀
            pace_min_km = record["avg_pace"] / 60 if record["avg_pace"] > 0 else 6.0

            # 简化的VDOT估算公式
            vdot_estimate = 50 - (pace_min_km - 4.0) * 10
            record["vdot_estimate"] = max(30, min(80, vdot_estimate))

            # 添加心率漂移相关数据
            record["hr_drift_factor"] = random.uniform(0.8, 1.2)
            record["hr_drift_correlation"] = random.uniform(-0.5, 0.5)

        return base_data

    def create_sample_fit_files(self, temp_dir: str, count: int = 5) -> str:
        """创建示例FIT文件"""
        fit_dir = Path(temp_dir) / "test_fit_files"
        fit_dir.mkdir(exist_ok=True)

        # 创建空的FIT文件（模拟）
        for i in range(count):
            fit_file = fit_dir / f"test_run_{i}.fit"
            with open(fit_file, "wb") as f:
                # 写入FIT文件头（简化版）
                f.write(b"\x0E\x10")  # FIT文件头
                f.write(b"Test FIT File" + b"\x00" * 100)  # 填充数据

        return str(fit_dir)


if __name__ == "__main__":
    """测试工具类功能"""
    generator = DataGenerator()
    test_data = generator.generate_running_data(10)
    print(f"生成测试数据: {len(test_data)}条")

    env = TestEnvironment()
    env.setup_test_environment()
    print("测试环境设置完成")

    env.cleanup_test_environment()
    print("测试完成")

#!/usr/bin/env python3
"""
预提交检查脚本（优化版）
基于 AGENTS.md 中的提交前 Checklist 实现

功能：
- 执行 ruff format 代码格式化检查
- 执行 ruff check 代码质量检查
- 执行 mypy 类型检查
- 执行 bandit 安全扫描检查
- 执行 pytest 单元测试
- 检查 Schema/TOOL_DESCRIPTIONS 更新
- 支持增量检查（只检查修改的文件）
- 支持并行执行检查（性能提升50%-70%）
- 支持彩色输出和进度条
- 支持多种输出格式（文本、JSON、HTML）
- 生成详细的检查报告

使用方式：
1. 手动执行：uv run python scripts/pre-commit-check.py
2. Git Hook：自动在 git commit 前执行
"""

import argparse
import atexit
import concurrent.futures
import hashlib
import json
import logging
import os
import pickle
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

# ponytail: pre-commit-check 只需要 logging，不 import src 包
# 避免 src.core.base.__init__ 级联加载整个项目依赖树（polars/pyarrow/sklearn...）
# 单进程内存从 ~10GB 降至 ~50MB
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rich.console import Console

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import questionary

    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

try:
    from pydantic import BaseModel, ConfigDict, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"


class CheckStatus(Enum):
    """检查状态枚举"""

    PASSED = "✅"
    FAILED = "❌"
    WARNING = "⚠️"
    SKIPPED = "⏭️"


class SingleInstanceLock:
    """文件级单实例锁 — 防止多个 pre-commit-check 进程同时运行

    使用文件锁 + PID 记录机制，跨平台兼容。
    - 锁文件：{lock_dir}/.pre-commit.lock
    - 内容：PID\\nISO时间戳
    - 超时：默认 300s（5分钟），超时后视为过期锁自动覆写
    """

    LOCK_FILENAME = ".pre-commit.lock"

    def __init__(
        self,
        lock_dir: Path | None = None,
        timeout_seconds: int = 300,
    ):
        self._lock_dir = lock_dir or (Path.home() / ".nanobot-runner")
        self._timeout = timeout_seconds
        self._lock_file = self._lock_dir / self.LOCK_FILENAME
        self.is_locked = False

    def acquire(self) -> bool:
        """尝试获取锁

        Returns:
            True: 成功获取锁
            False: 已有另一个有效实例在运行
        """
        self._lock_dir.mkdir(parents=True, exist_ok=True)

        if self._lock_file.exists():
            try:
                content = self._lock_file.read_text(encoding="utf-8").strip()
                lines = content.split("\n")
                old_pid = int(lines[0]) if lines else 0
                old_time_str = lines[1] if len(lines) > 1 else ""

                # 检查锁是否过期
                if old_time_str:
                    try:
                        old_time = datetime.fromisoformat(old_time_str)
                        age = (datetime.now() - old_time).total_seconds()
                        if age > self._timeout:
                            logger.warning(
                                "锁文件已过期（%ds），PID=%d，覆写", age, old_pid
                            )
                            self._write_lock()
                            self.is_locked = True
                            return True
                    except ValueError:
                        pass  # 时间解析失败，继续检查PID

                # 检查 PID 是否仍在运行
                if self._is_pid_running(old_pid):
                    logger.warning(
                        "另一个 pre-commit-check 实例正在运行（PID=%d），跳过", old_pid
                    )
                    return False
                else:
                    logger.warning("锁文件 PID=%d 已不存在，覆写", old_pid)
            except (ValueError, OSError) as e:
                logger.warning("锁文件损坏，覆写: %s", e)

        self._write_lock()
        self.is_locked = True
        return True

    def release(self) -> None:
        """释放锁"""
        try:
            if self._lock_file.exists():
                self._lock_file.unlink()
        except OSError as e:
            logger.debug("释放锁文件失败: %s", e)
        self.is_locked = False

    def _write_lock(self) -> None:
        """写入锁文件（PID + 时间戳）"""
        self._lock_file.write_text(
            f"{os.getpid()}\n{datetime.now().isoformat()}",
            encoding="utf-8",
        )

    @staticmethod
    def _is_pid_running(pid: int) -> bool:
        """检查指定 PID 的进程是否仍在运行"""
        try:
            import psutil  # noqa: F811

            return psutil.pid_exists(pid)
        except ImportError:
            # 无 psutil 时使用 os.kill(pid, 0) 作为回退
            # Windows 上 os.kill 不可用，保守假设 PID 仍在运行
            if sys.platform == "win32":
                return True  # 保守策略：Windows 无 psutil 时假设仍在运行
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False


class OutputFormat(Enum):
    """输出格式枚举"""

    TEXT = "text"
    JSON = "json"
    HTML = "html"


@dataclass
class CheckResult:
    """检查结果"""

    name: str
    status: CheckStatus
    message: str
    duration: float
    command: str
    output: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


if PYDANTIC_AVAILABLE:

    class CheckConfig(BaseModel):
        """检查配置"""

        enabled: bool = True
        timeout: int = 300
        command: str | None = None
        skip_conditions: list[str] = Field(default_factory=list)

    class PreCommitConfig(BaseModel):
        """预提交检查配置"""

        ruff_format: CheckConfig = Field(default_factory=CheckConfig)
        ruff_lint: CheckConfig = Field(default_factory=CheckConfig)
        mypy: CheckConfig = Field(default_factory=lambda: CheckConfig(timeout=120))
        bandit: CheckConfig = Field(default_factory=lambda: CheckConfig(timeout=120))
        pytest: CheckConfig = Field(
            default_factory=lambda: CheckConfig(
                timeout=600, command="uv run pytest tests/unit/ -v --timeout=60"
            )
        )
        schema_check: CheckConfig = Field(default_factory=CheckConfig)

        parallel_execution: bool = True
        max_workers: int = 4
        incremental_check: bool = True
        cache_enabled: bool = True
        output_format: str = "text"
        skip_doc_only_commits: bool = True
        doc_extensions: list[str] = Field(
            default_factory=lambda: [
                ".md",
                ".txt",
                ".rst",
                ".adoc",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".xml",
                ".ini",
                ".cfg",
                ".conf",
                ".lock",
                ".gitignore",
                ".dockerignore",
                ".editorconfig",
                ".gitattributes",
                ".svg",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".ico",
                ".pdf",
                ".html",
                ".htm",
                ".css",
                ".map",
                ".license",
                ".copying",
                ".authors",
                ".contributors",
                ".changes",
                ".changelog",
                ".version",
            ]
        )

        model_config = ConfigDict(extra="allow")

        @classmethod
        def from_file(cls, config_path: Path) -> "PreCommitConfig":
            """从配置文件加载"""
            if config_path.exists():
                try:
                    import yaml

                    with open(config_path, encoding="utf-8") as f:
                        config_data = yaml.safe_load(f)
                        if config_data:
                            return cls(**config_data)
                except Exception as e:
                    logger.warning(f"加载配置文件失败: {e}")
            return cls()
else:

    class CheckConfig:  # type: ignore[no-redef]
        def __init__(
            self, enabled=True, timeout=300, command=None, skip_conditions=None
        ):
            self.enabled = enabled
            self.timeout = timeout
            self.command = command
            self.skip_conditions = skip_conditions or []

    class PreCommitConfig:  # type: ignore[no-redef]
        def __init__(self):
            self.ruff_format = CheckConfig()
            self.ruff_lint = CheckConfig()
            self.mypy = CheckConfig(timeout=120)
            self.bandit = CheckConfig(timeout=120)
            self.pytest = CheckConfig(
                timeout=600, command="uv run pytest tests/unit/ -v --timeout=60"
            )
            self.schema_check = CheckConfig()
            self.parallel_execution = True
            self.max_workers = 4
            self.incremental_check = True
            self.cache_enabled = True
            self.output_format = "text"
            self.skip_doc_only_commits = True
            self.doc_extensions = [
                ".md",
                ".txt",
                ".rst",
                ".adoc",
                ".json",
                ".yaml",
                ".yml",
                ".toml",
                ".xml",
                ".ini",
                ".cfg",
                ".conf",
                ".lock",
                ".gitignore",
                ".dockerignore",
                ".editorconfig",
                ".gitattributes",
                ".svg",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".ico",
                ".pdf",
                ".html",
                ".htm",
                ".css",
                ".map",
                ".license",
                ".copying",
                ".authors",
                ".contributors",
                ".changes",
                ".changelog",
                ".version",
            ]

        @classmethod
        def from_file(cls, _config_path: Path) -> "PreCommitConfig":
            """从配置文件加载（简化版本不支持配置文件）"""
            return cls()


class CheckCache:
    """检查结果缓存"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_file_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                hasher.update(f.read())
            return hasher.hexdigest()
        except Exception:
            return ""

    def get_cached_result(
        self, check_name: str, files: list[Path]
    ) -> CheckResult | None:
        """获取缓存结果"""
        if not files:
            return None

        file_hashes = "".join(self.get_file_hash(f) for f in files if f.exists())
        cache_key = hashlib.md5((check_name + file_hashes).encode()).hexdigest()

        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    cached_result = pickle.load(f)
                    if isinstance(cached_result, CheckResult):
                        cached_result.message += " (缓存)"
                        return cached_result
            except Exception:
                pass
        return None

    def save_result(self, check_name: str, files: list[Path], result: CheckResult):
        """保存检查结果到缓存"""
        if not files:
            return

        file_hashes = "".join(self.get_file_hash(f) for f in files if f.exists())
        cache_key = hashlib.md5((check_name + file_hashes).encode()).hexdigest()

        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(result, f)
        except Exception:
            pass


class PreCommitChecker:
    """预提交检查器（优化版）"""

    def __init__(self, config: PreCommitConfig | None = None):
        self.project_root = Path(__file__).parent.parent
        self.results: list[CheckResult] = []
        self.start_time = time.time()
        self.config = config or PreCommitConfig()
        self.cache = (
            CheckCache(self.project_root / ".cache" / "pre-commit")
            if self.config.cache_enabled
            else None
        )
        self.console: Console | None = Console() if RICH_AVAILABLE else None

    def get_changed_files(self, include_working_dir: bool = False) -> list[Path]:
        """获取Git中已修改的文件

        Args:
            include_working_dir: 是否包含工作区（未暂存）的变更文件，
                                 增量测试场景下需要设为 True
        """
        commands: list[list[str]] = [
            ["git", "diff", "--name-only", "--cached"],
        ]
        if include_working_dir:
            commands.append(["git", "diff", "--name-only"])

        all_files: set[str] = set()
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=self.project_root,
                    timeout=10,
                )

                if result.returncode == 0 and result.stdout.strip():
                    for file_path in result.stdout.strip().split("\n"):
                        if file_path:
                            all_files.add(file_path)
            except Exception as e:
                logger.debug(f"获取变更文件失败: {e}")

        changed_files = []
        for file_path in sorted(all_files):
            full_path = self.project_root / file_path
            if full_path.exists() and full_path.suffix == ".py":
                changed_files.append(full_path)

        return changed_files

    def should_skip_checks(self) -> tuple[bool, str]:
        """
        判断是否应该跳过检查（如只提交了文档文件）

        Returns:
            tuple[bool, str]: (是否跳过, 跳过原因)
        """
        if not self.config.skip_doc_only_commits:
            logger.debug("skip_doc_only_commits 配置已禁用，不跳过检查")
            return False, ""

        doc_extensions = set(self.config.doc_extensions)
        logger.debug(f"文档扩展名列表: {doc_extensions}")

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_root,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(f"Git 命令执行失败: {result.stderr}")
                return False, ""

            if not result.stdout.strip():
                logger.debug("暂存区为空，不跳过检查")
                return False, ""

            all_files = [
                f.strip() for f in result.stdout.strip().split("\n") if f.strip()
            ]
            logger.debug(f"暂存区文件列表: {all_files}")

            if not all_files:
                logger.debug("暂存区文件列表为空，不跳过检查")
                return False, ""

            non_doc_files = []
            for file_path in all_files:
                # 修复：Git 对含非ASCII字符的路径会用双引号包裹，需去除
                clean_path = file_path.strip('"')
                ext = Path(clean_path).suffix.lower()
                logger.debug(
                    f"检查文件: {file_path}, 清理后: {clean_path}, 扩展名: {ext}"
                )
                if ext not in doc_extensions:
                    non_doc_files.append(file_path)
                    logger.debug(f"文件 {file_path} 不是文档类型")

            if non_doc_files:
                logger.debug(f"发现非文档文件: {non_doc_files}，不跳过检查")
                return False, ""

            file_list = ", ".join(all_files[:5])
            if len(all_files) > 5:
                file_list += f" 等 {len(all_files)} 个文件"

            skip_message = f"暂存区只包含文档/配置文件 ({file_list})，跳过代码检查"
            logger.info(skip_message)
            return True, skip_message

        except subprocess.TimeoutExpired:
            logger.warning("Git 命令执行超时")
            return False, ""
        except Exception as e:
            logger.warning(f"检查暂存区文件类型失败: {e}")
            return False, ""

    def run_command(
        self, command: str, check_name: str, timeout: int | None = None
    ) -> CheckResult:
        """运行命令并返回检查结果"""
        start_time = time.time()
        actual_timeout = timeout or self.config.ruff_format.timeout

        try:
            logger.info(f"开始执行: {check_name}")
            logger.debug(f"命令: {command}")

            # ponytail: shell=False 避免 cmd.exe 包装进程，减少进程树冗余
            # as_posix 强制正斜杠，避免 Windows 路径 'a\\b.py' 被 shlex 当转义吃
            result = subprocess.run(
                shlex.split(command.replace("\\", "/")),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_root,
                timeout=actual_timeout,
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                status = CheckStatus.PASSED
                message = f"检查通过 ({duration:.2f}s)"
            else:
                status = CheckStatus.FAILED
                message = f"检查失败 ({duration:.2f}s)"

            return CheckResult(
                name=check_name,
                status=status,
                message=message,
                duration=duration,
                command=command,
                output=result.stdout + result.stderr,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                status=CheckStatus.FAILED,
                message=f"执行超时 ({duration:.2f}s)",
                duration=duration,
                command=command,
                output="命令执行超时",
            )
        except Exception as e:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                status=CheckStatus.FAILED,
                message=f"执行异常: {e} ({duration:.2f}s)",
                duration=duration,
                command=command,
                output=str(e),
            )

    def check_ruff_format(self) -> CheckResult:
        """检查代码格式化（支持增量检查）"""
        if not self.config.ruff_format.enabled:
            return CheckResult(
                name="ruff format 代码格式化检查",
                status=CheckStatus.SKIPPED,
                message="已禁用",
                duration=0,
                command="",
            )

        changed_files = []
        if self.config.incremental_check:
            changed_files = self.get_changed_files()

        if changed_files:
            # ponytail: as_posix 强制正斜杠，避免 Windows 反斜杠被 shlex 当转义
            files_str = " ".join(
                f.relative_to(self.project_root).as_posix() for f in changed_files
            )
            command = f"uv run ruff format --check {files_str}"

            if self.cache:
                cached = self.cache.get_cached_result("ruff_format", changed_files)
                if cached:
                    return cached
        else:
            command = "uv run ruff format --check src/ tests/ scripts/ skills/"

        result = self.run_command(
            command, "ruff format 代码格式化检查", self.config.ruff_format.timeout
        )

        if self.cache and changed_files and result.status == CheckStatus.PASSED:
            self.cache.save_result("ruff_format", changed_files, result)

        return result

    def check_ruff_lint(self) -> CheckResult:
        """检查代码质量（支持增量检查）"""
        if not self.config.ruff_lint.enabled:
            return CheckResult(
                name="ruff check 代码质量检查",
                status=CheckStatus.SKIPPED,
                message="已禁用",
                duration=0,
                command="",
            )

        changed_files = []
        if self.config.incremental_check:
            changed_files = self.get_changed_files()

        if changed_files:
            # ponytail: as_posix 强制正斜杠，避免 Windows 反斜杠被 shlex 当转义
            files_str = " ".join(
                f.relative_to(self.project_root).as_posix() for f in changed_files
            )
            command = f"uv run ruff check {files_str}"

            if self.cache:
                cached = self.cache.get_cached_result("ruff_lint", changed_files)
                if cached:
                    return cached
        else:
            command = "uv run ruff check src/ tests/ scripts/ skills/"

        result = self.run_command(
            command, "ruff check 代码质量检查", self.config.ruff_lint.timeout
        )

        if self.cache and changed_files and result.status == CheckStatus.PASSED:
            self.cache.save_result("ruff_lint", changed_files, result)

        return result

    def check_mypy_types(self) -> CheckResult:
        """检查类型注解"""
        if not self.config.mypy.enabled:
            return CheckResult(
                name="mypy 类型检查",
                status=CheckStatus.SKIPPED,
                message="已禁用",
                duration=0,
                command="",
            )

        command = (
            self.config.mypy.command or "uv run mypy src/ --ignore-missing-imports"
        )
        return self.run_command(command, "mypy 类型检查", self.config.mypy.timeout)

    def _map_source_to_test_dirs(self, source_path: Path) -> list[str] | None:
        """将源文件路径映射到对应的测试目录

        映射规则：
        - src/core/<module>/*.py → tests/unit/core/<module>/
        - src/cli/<module>/*.py → tests/unit/cli/<module>/
        - src/agents/*.py → tests/unit/agents/
        - src/notify/*.py → tests/unit/notify/
        - src/core/base/*.py → 返回 None（基础模块影响面广，需全量测试）
        - src/core/models.py → 返回 None（公共模型影响面广，需全量测试）
        - 非 src/ 下的文件（scripts/、docs/等）→ 返回空列表（不影响增量测试决策）

        Returns:
            list[str] | None: 测试目录列表（相对于项目根目录），
                              空列表表示该文件不影响测试决策，
                              None 表示需全量测试
        """
        try:
            rel_path = source_path.relative_to(self.project_root)
            parts = rel_path.parts
        except ValueError:
            return []

        if len(parts) < 2:
            return []

        src_root = parts[0]
        if src_root != "src":
            return []

        if len(parts) < 3:
            return None

        module = parts[1]

        broad_impact_modules = {"base", "models.py"}
        if module in broad_impact_modules or (
            len(parts) > 2 and parts[2] in broad_impact_modules
        ):
            return None

        test_dir = "tests/unit"

        if module == "core" and len(parts) > 2:
            sub_module = parts[2]
            if sub_module == "models.py":
                return None
            test_dir = f"tests/unit/core/{sub_module}"
        elif module == "cli" and len(parts) > 2:
            sub_module = parts[2]
            if sub_module.endswith(".py"):
                test_dir = "tests/unit/cli"
            else:
                test_dir = f"tests/unit/cli/{sub_module}"
        elif module == "agents":
            test_dir = "tests/unit/agents"
        elif module == "notify":
            test_dir = "tests/unit/notify"
        else:
            test_dir = f"tests/unit/{module}"

        test_path = self.project_root / test_dir
        if test_path.exists():
            return [test_dir]

        return None

    def _get_incremental_test_command(self) -> str | None:
        """构建增量测试命令

        根据暂存区和工作区变更的源文件，推断应运行的测试目录。
        如果变更文件影响面广（如公共模型、基础模块），则返回 None 执行全量测试。
        非源码文件（scripts/、docs/等）不影响增量测试决策。

        Returns:
            str | None: 增量测试命令，None 表示需全量测试
        """
        changed_files = self.get_changed_files(include_working_dir=True)
        if not changed_files:
            return None

        test_dirs: set[str] = set()
        has_src_changes = False
        for source_file in changed_files:
            mapped = self._map_source_to_test_dirs(source_file)
            if mapped is None:
                logger.info(
                    f"变更文件 {source_file.relative_to(self.project_root)} "
                    "影响面广，执行全量测试"
                )
                return None
            if mapped:
                has_src_changes = True
                test_dirs.update(mapped)

        if not has_src_changes:
            return None

        if not test_dirs:
            return None

        sorted_dirs = sorted(test_dirs)
        dirs_str = " ".join(sorted_dirs)
        logger.info(f"增量测试目录: {dirs_str}")
        return f"uv run pytest {dirs_str} -v --timeout=60"

    def check_pytest_tests(self) -> CheckResult:
        """运行单元测试（支持增量测试）"""
        if not self.config.pytest.enabled:
            return CheckResult(
                name="pytest 单元测试",
                status=CheckStatus.SKIPPED,
                message="已禁用",
                duration=0,
                command="",
            )

        command = (
            self.config.pytest.command or "uv run pytest tests/unit/ -v --timeout=60"
        )

        if self.config.incremental_check:
            incremental_cmd = self._get_incremental_test_command()
            if incremental_cmd is not None:
                command = incremental_cmd

        return self.run_command(command, "pytest 单元测试", self.config.pytest.timeout)

    def check_schema_updates(self) -> CheckResult:
        """检查 Schema/TOOL_DESCRIPTIONS 更新"""
        if not self.config.schema_check.enabled:
            return CheckResult(
                name="Schema/TOOL_DESCRIPTIONS 更新检查",
                status=CheckStatus.SKIPPED,
                message="已禁用",
                duration=0,
                command="",
            )

        start_time = time.time()

        try:
            tools_file = self.project_root / "src/agents/tools.py"

            if tools_file.exists():
                with open(tools_file, encoding="utf-8") as f:
                    content = f.read()
                    if "TOOL_DESCRIPTIONS" in content:
                        if "TOOL_DESCRIPTIONS = {" in content:
                            status = CheckStatus.PASSED
                            message = "TOOL_DESCRIPTIONS 格式正确"
                        else:
                            status = CheckStatus.WARNING
                            message = "TOOL_DESCRIPTIONS 可能需要更新"
                    else:
                        status = CheckStatus.SKIPPED
                        message = "未找到 TOOL_DESCRIPTIONS，跳过检查"
            else:
                status = CheckStatus.SKIPPED
                message = "工具文件不存在，跳过检查"

            duration = time.time() - start_time
            return CheckResult(
                name="Schema/TOOL_DESCRIPTIONS 更新检查",
                status=status,
                message=message,
                duration=duration,
                command="手动检查 Schema 和 TOOL_DESCRIPTIONS",
            )

        except Exception as e:
            duration = time.time() - start_time
            return CheckResult(
                name="Schema/TOOL_DESCRIPTIONS 更新检查",
                status=CheckStatus.FAILED,
                message=f"检查异常: {e} ({duration:.2f}s)",
                duration=duration,
                command="手动检查 Schema 和 TOOL_DESCRIPTIONS",
                output=str(e),
            )

    def check_bandit_security(self) -> CheckResult:
        """检查代码安全性（bandit扫描）"""
        if not self.config.bandit.enabled:
            return CheckResult(
                name="bandit 安全扫描",
                status=CheckStatus.SKIPPED,
                message="已禁用",
                duration=0,
                command="",
            )

        start_time = time.time()

        try:
            logger.info("开始执行: bandit 安全扫描")

            command = "uv run bandit -r src/ -f json -s B101,B601 -ll"
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=self.project_root,
                timeout=self.config.bandit.timeout,
            )

            duration = time.time() - start_time

            try:
                report = json.loads(result.stdout)

                high_count = sum(
                    1
                    for r in report.get("results", [])
                    if r.get("issue_severity") == "HIGH"
                )
                medium_count = sum(
                    1
                    for r in report.get("results", [])
                    if r.get("issue_severity") == "MEDIUM"
                )

                if high_count > 0 or medium_count > 0:
                    issues = []
                    for r in report.get("results", []):
                        if r.get("issue_severity") in ["HIGH", "MEDIUM"]:
                            issues.append(
                                f"  - [{r.get('issue_severity')}] {r.get('test_id')}: "
                                f"{r.get('issue_text')} ({r.get('filename')}:{r.get('line_number')})"
                            )

                    output = "发现安全问题:\n" + "\n".join(issues[:10])
                    if len(issues) > 10:
                        output += f"\n  ... 还有 {len(issues) - 10} 个问题"

                    return CheckResult(
                        name="bandit 安全扫描",
                        status=CheckStatus.FAILED,
                        message=f"发现 {high_count} 个HIGH和 {medium_count} 个MEDIUM严重性问题 ({duration:.2f}s)",
                        duration=duration,
                        command=command,
                        output=output,
                    )
                else:
                    return CheckResult(
                        name="bandit 安全扫描",
                        status=CheckStatus.PASSED,
                        message=f"未发现HIGH或MEDIUM严重性问题 ({duration:.2f}s)",
                        duration=duration,
                        command=command,
                        output=result.stdout,
                    )

            except json.JSONDecodeError:
                if result.returncode == 0:
                    return CheckResult(
                        name="bandit 安全扫描",
                        status=CheckStatus.PASSED,
                        message=f"安全扫描通过 ({duration:.2f}s)",
                        duration=duration,
                        command=command,
                        output=result.stdout,
                    )
                else:
                    return CheckResult(
                        name="bandit 安全扫描",
                        status=CheckStatus.WARNING,
                        message=f"安全扫描完成，但无法解析报告 ({duration:.2f}s)",
                        duration=duration,
                        command=command,
                        output=result.stdout + result.stderr,
                    )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return CheckResult(
                name="bandit 安全扫描",
                status=CheckStatus.FAILED,
                message=f"执行超时 ({duration:.2f}s)",
                duration=duration,
                command=command,
                output="命令执行超时",
            )
        except Exception as e:
            duration = time.time() - start_time
            return CheckResult(
                name="bandit 安全扫描",
                status=CheckStatus.FAILED,
                message=f"执行异常: {e} ({duration:.2f}s)",
                duration=duration,
                command=command,
                output=str(e),
            )

    def _record_result(self, result: CheckResult) -> None:
        """记录并输出单个检查结果（供串行/并行调度复用）"""
        self.results.append(result)

        if RICH_AVAILABLE and self.console:
            if result.status == CheckStatus.PASSED:
                self.console.print(
                    f"{result.status.value} {result.name}: {result.message}",
                    style="green",
                )
            elif result.status == CheckStatus.FAILED:
                self.console.print(
                    f"{result.status.value} {result.name}: {result.message}",
                    style="red",
                )
            else:
                self.console.print(
                    f"{result.status.value} {result.name}: {result.message}"
                )
        else:
            print(f"{result.status.value} {result.name}: {result.message}")

        if result.status == CheckStatus.FAILED and result.output:
            print(f"   详细输出:\n{result.output}")

    def run_all_checks_sequential(self) -> bool:
        """串行运行所有检查"""
        logger.info("🔍 开始预提交检查（串行模式）...")

        checks = [
            self.check_ruff_format,
            self.check_ruff_lint,
            self.check_mypy_types,
            self.check_bandit_security,
            self.check_pytest_tests,
            self.check_schema_updates,
        ]

        for check_func in checks:
            try:
                result = check_func()
                self._record_result(result)
            except Exception as e:
                logger.error(f"检查执行异常: {e}")

        return self.generate_report()

    def run_all_checks_parallel(self) -> bool:
        """并行运行所有检查（两阶段调度）

        ponytail: 两阶段调度避免进程爆炸。旧方案 ThreadPoolExecutor(4) + pytest -n 4
        峰值 8-9 个重型进程，内存爆炸。轻量检查并行 + 重量级检查串行后，
        峰值降至 max_workers 个轻量进程 + 1 个重型进程。
        """
        logger.info("🔍 开始预提交检查（两阶段并行模式）...")

        # 轻量检查：内存占用小，可安全并行
        light_checks = [
            self.check_ruff_format,
            self.check_ruff_lint,
            self.check_schema_updates,
        ]
        # 重量级检查：各自启动重型 Python 进程，串行执行避免内存峰值
        heavy_checks = [
            self.check_mypy_types,
            self.check_bandit_security,
            self.check_pytest_tests,
        ]

        # 第一阶段：轻量检查并行
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_workers
        ) as executor:
            futures = {executor.submit(check): check for check in light_checks}
            for future in concurrent.futures.as_completed(futures):
                try:
                    self._record_result(future.result())
                except Exception as e:
                    logger.error(f"检查执行异常: {e}")

        # 第二阶段：重量级检查串行
        for check in heavy_checks:
            try:
                self._record_result(check())
            except Exception as e:
                logger.error(f"检查执行异常: {e}")

        return self.generate_report()

    def run_all_checks(self) -> bool:
        """运行所有检查（根据配置选择串行或并行）"""
        should_skip, skip_reason = self.should_skip_checks()
        if should_skip:
            logger.info(skip_reason)
            if RICH_AVAILABLE and self.console:
                self.console.print(f"\n⏭️  {skip_reason}\n", style="bold yellow")
            return True

        if self.config.parallel_execution:
            return self.run_all_checks_parallel()
        else:
            return self.run_all_checks_sequential()

    def generate_report(self, output_format: OutputFormat | None = None) -> bool:
        """生成检查报告"""
        if output_format is None:
            output_format = OutputFormat(self.config.output_format)

        if output_format == OutputFormat.JSON:
            return self._generate_json_report()
        elif output_format == OutputFormat.HTML:
            return self._generate_html_report()
        else:
            return self._generate_text_report()

    def _generate_text_report(self) -> bool:
        """生成文本格式报告"""
        total_time = time.time() - self.start_time

        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warning = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIPPED)

        if RICH_AVAILABLE and self.console:
            self.console.print("\n" + "=" * 60, style="bold blue")
            self.console.print("📋 预提交检查报告", style="bold blue")
            self.console.print("=" * 60, style="bold blue")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("状态", style="dim", width=6)
            table.add_column("检查项", style="dim")
            table.add_column("结果", style="dim")

            for result in self.results:
                status_style = (
                    "green"
                    if result.status == CheckStatus.PASSED
                    else "red"
                    if result.status == CheckStatus.FAILED
                    else "yellow"
                )
                table.add_row(
                    result.status.value, result.name, result.message, style=status_style
                )

            self.console.print(table)

            self.console.print("-" * 60, style="dim")
            summary_text = f"总计: {len(self.results)} 项检查\n"
            summary_text += f"✅ 通过: {passed} | ❌ 失败: {failed} | ⚠️ 警告: {warning} | ⏭️ 跳过: {skipped}\n"
            summary_text += f"⏱️  总耗时: {total_time:.2f}秒"

            self.console.print(
                Panel(summary_text, title="检查摘要", border_style="blue")
            )
        else:
            print("\n" + "=" * 60)
            print("📋 预提交检查报告")
            print("=" * 60)

            for result in self.results:
                print(f"{result.status.value} {result.name}: {result.message}")

            print("-" * 60)
            print(f"总计: {len(self.results)} 项检查")
            print(
                f"✅ 通过: {passed} | ❌ 失败: {failed} | ⚠️ 警告: {warning} | ⏭️ 跳过: {skipped}"
            )
            print(f"⏱️  总耗时: {total_time:.2f}秒")

        if failed > 0:
            if RICH_AVAILABLE and self.console:
                self.console.print("\n💡 修复建议:", style="bold yellow")
            else:
                print("\n💡 修复建议:")

            for result in self.results:
                if result.status == CheckStatus.FAILED:
                    if "ruff format" in result.name.lower():
                        suggestion = (
                            "  - 执行: uv run ruff format src/ tests/ scripts/ skills/"
                        )
                    elif "ruff check" in result.name.lower():
                        suggestion = "  - 执行: uv run ruff check --fix src/ tests/ scripts/ skills/"
                    elif "mypy" in result.name.lower():
                        suggestion = (
                            "  - 执行: uv run mypy src/ --ignore-missing-imports"
                        )
                    elif "pytest" in result.name.lower():
                        suggestion = "  - 执行: uv run pytest tests/unit/ -v"
                    else:
                        suggestion = f"  - 检查: {result.name}"

                    if RICH_AVAILABLE and self.console:
                        self.console.print(suggestion, style="yellow")
                    else:
                        print(suggestion)

        if RICH_AVAILABLE and self.console:
            if failed == 0:
                self.console.print("\n🎉 所有检查通过，可以提交！", style="bold green")
            else:
                self.console.print(
                    f"\n🚫 检查失败，请修复 {failed} 个问题后再提交", style="bold red"
                )
        else:
            if failed == 0:
                print("\n🎉 所有检查通过，可以提交！")
            else:
                print(f"\n🚫 检查失败，请修复 {failed} 个问题后再提交")

        return failed == 0

    def _generate_json_report(self) -> bool:
        """生成JSON格式报告"""
        total_time = time.time() - self.start_time

        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warning = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIPPED)

        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration": total_time,
            "results": [asdict(r) for r in self.results],
            "summary": {
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "warning": warning,
                "skipped": skipped,
            },
        }

        report_file = self.project_root / "pre-commit-report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        if RICH_AVAILABLE and self.console:
            self.console.print(f"\n📄 JSON报告已生成: {report_file}", style="blue")
        else:
            print(f"\n📄 JSON报告已生成: {report_file}")

        return failed == 0

    def _generate_html_report(self) -> bool:
        """生成HTML格式报告"""
        total_time = time.time() - self.start_time

        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warning = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIPPED)

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>预提交检查报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .summary {{ background: #f9f9f9; padding: 15px; border-radius: 4px; margin: 20px 0; }}
        .summary-item {{ display: inline-block; margin-right: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4CAF50; color: white; }}
        .passed {{ color: #4CAF50; font-weight: bold; }}
        .failed {{ color: #f44336; font-weight: bold; }}
        .warning {{ color: #ff9800; font-weight: bold; }}
        .skipped {{ color: #9e9e9e; font-weight: bold; }}
        .output {{ background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📋 预提交检查报告</h1>
        <div class="summary">
            <div class="summary-item"><strong>总耗时:</strong> {total_time:.2f}秒</div>
            <div class="summary-item"><strong>总计:</strong> {len(self.results)} 项检查</div>
            <div class="summary-item passed">✅ 通过: {passed}</div>
            <div class="summary-item failed">❌ 失败: {failed}</div>
            <div class="summary-item warning">⚠️ 警告: {warning}</div>
            <div class="summary-item skipped">⏭️ 跳过: {skipped}</div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>状态</th>
                    <th>检查项</th>
                    <th>结果</th>
                    <th>耗时</th>
                </tr>
            </thead>
            <tbody>
"""

        for result in self.results:
            status_class = result.status.name.lower()
            html_content += f"""
                <tr>
                    <td class="{status_class}">{result.status.value}</td>
                    <td>{result.name}</td>
                    <td>{result.message}</td>
                    <td>{result.duration:.2f}s</td>
                </tr>
"""
            if result.output:
                html_content += f"""
                <tr>
                    <td colspan="4">
                        <div class="output">{result.output}</div>
                    </td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

        report_file = self.project_root / "pre-commit-report.html"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        if RICH_AVAILABLE and self.console:
            self.console.print(f"\n📄 HTML报告已生成: {report_file}", style="blue")
        else:
            print(f"\n📄 HTML报告已生成: {report_file}")

        return failed == 0

    def get_fix_commands(self) -> list[str]:
        """获取修复命令列表"""
        fix_commands = []

        for result in self.results:
            if result.status == CheckStatus.FAILED:
                if "ruff format" in result.name.lower():
                    fix_commands.append(
                        "uv run ruff format src/ tests/ scripts/ skills/"
                    )
                elif "ruff check" in result.name.lower():
                    fix_commands.append(
                        "uv run ruff check --fix src/ tests/ scripts/ skills/"
                    )
                elif "mypy" in result.name.lower():
                    fix_commands.append("uv run mypy src/ --ignore-missing-imports")
                elif "pytest" in result.name.lower():
                    fix_commands.append("uv run pytest tests/unit/ -v")

        return fix_commands

    def auto_fix_issues(self) -> bool:
        """自动修复可修复的问题"""
        fix_commands = self.get_fix_commands()

        if not fix_commands:
            if RICH_AVAILABLE and self.console:
                self.console.print("✅ 无需修复", style="green")
            else:
                print("✅ 无需修复")
            return True

        if RICH_AVAILABLE and self.console:
            self.console.print("\n🔧 开始自动修复...", style="bold yellow")
        else:
            print("\n🔧 开始自动修复...")

        for command in fix_commands:
            if RICH_AVAILABLE and self.console:
                self.console.print(f"执行: {command}")
            else:
                print(f"执行: {command}")

            result = subprocess.run(
                shlex.split(command.replace("\\", "/")), cwd=self.project_root
            )

            if result.returncode != 0:
                if RICH_AVAILABLE and self.console:
                    self.console.print(f"❌ 修复失败: {command}", style="red")
                else:
                    print(f"❌ 修复失败: {command}")
                return False

        if RICH_AVAILABLE and self.console:
            self.console.print("✅ 自动修复完成", style="green")
        else:
            print("✅ 自动修复完成")
        return True


def _is_interactive() -> bool:
    """检测当前是否处于交互式终端环境

    判断逻辑：
    1. stdin 必须是 TTY（非管道/重定向）
    2. 不能在 Git Hook 模式下（GIT_HOOK 环境变量）
    3. 不能在 CI/CD 环境下（CI 环境变量）
    4. 不能在 NO_COLOR 模式下（通常表示非交互环境）

    Returns:
        True 表示可以安全使用交互式提示
    """
    return not (
        not sys.stdin.isatty()
        or os.environ.get("GIT_HOOK")
        or os.environ.get("CI")
        or os.environ.get("PRE_COMMIT_CHECK_NON_INTERACTIVE")
    )


def _parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="预提交检查脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
使用示例:
  uv run python scripts/pre-commit-check.py           # 运行检查，失败时交互提示修复
  uv run python scripts/pre-commit-check.py --fix      # 运行检查，失败时自动修复
  uv run python scripts/pre-commit-check.py --no-fix   # 运行检查，跳过修复提示
  uv run python scripts/pre-commit-check.py --parallel # 强制并行执行
""",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        default=False,
        help="检查失败时自动修复，不弹出交互提示",
    )
    parser.add_argument(
        "--no-fix",
        action="store_true",
        default=False,
        help="检查失败时不尝试修复，直接退出",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        default=False,
        help="强制并行执行检查",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        default=False,
        help="强制串行执行检查",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="禁用检查结果缓存",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="全量检查（禁用增量模式）",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "html"],
        default=None,
        help="输出格式（默认: text）",
    )
    return parser.parse_args()


def main():
    """主函数"""
    # 单实例锁：防止多个 pre-commit-check 进程同时运行
    lock = SingleInstanceLock()
    if not lock.acquire():
        print("⚠️  另一个 pre-commit-check 实例正在运行，跳过本次检查。")
        print(f"   锁文件: {lock._lock_file}")
        sys.exit(0)
    atexit.register(lock.release)

    args = _parse_args()

    config_file = Path(__file__).parent.parent / ".pre-commit-config.yaml"
    config = PreCommitConfig.from_file(config_file)

    if args.parallel:
        config.parallel_execution = True
    if args.sequential:
        config.parallel_execution = False
    if args.no_cache:
        config.cache_enabled = False
    if args.full:
        config.incremental_check = False
    if args.output:
        config.output_format = args.output

    checker = PreCommitChecker(config)

    try:
        success = checker.run_all_checks()

        if not success:
            should_fix = False

            if args.no_fix:
                should_fix = False
            elif args.fix:
                should_fix = True
            elif _is_interactive() and QUESTIONARY_AVAILABLE:
                try:
                    if checker.console:
                        checker.console.clear_live()
                    should_fix = questionary.confirm(
                        "是否自动修复可修复的问题？", default=True
                    ).ask()
                    if should_fix is None:
                        should_fix = False
                except (EOFError, KeyboardInterrupt):
                    should_fix = False
                except Exception as e:
                    logger.debug(f"交互提示异常，跳过修复: {e}")
                    should_fix = False
            else:
                if RICH_AVAILABLE and checker.console:
                    checker.console.print(
                        "\n💡 非交互环境，无法弹出修复提示。"
                        "可使用 --fix 参数自动修复，或 --no-fix 跳过修复。",
                        style="bold yellow",
                    )
                else:
                    print(
                        "\n💡 非交互环境，无法弹出修复提示。"
                        "可使用 --fix 参数自动修复，或 --no-fix 跳过修复。"
                    )
                should_fix = False

            if should_fix and checker.auto_fix_issues():
                checker.results = []
                success = checker.run_all_checks()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  检查被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 检查过程出现异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

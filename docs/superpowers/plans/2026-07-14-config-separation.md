# 配置物理分离实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 `config.json` → `nanobot_config.json` 运行时转换层，让 `nanobot_config.json` 成为 nanobot 配置的唯一真实源，`config.json` 仅保留 Runner 专有字段。

**Architecture:** `nanobot_config.json` 由用户直接按 nanobot 原生格式维护，包含 providers/agents/channels/model_presets/tools。`config.json` 精简为 5 个 Runner 专有字段（version/data_dir/timezone/auto_push_feishu/user_id）。不再有运行时转换，gateway 启动时直接 `set_config_path(nanobot_config.json)`。

**Tech Stack:** Python 3.11+, Pydantic (nanobot-ai 0.2.2), pytest, Typer CLI

---

## 文件结构

### 需要修改的文件

| 文件 | 职责 | 变更类型 |
|------|------|----------|
| `src/core/config/schema.py` | AppConfig Schema 定义 | 精简：移除 nanobot 字段验证 |
| `src/core/config/manager.py` | 配置管理器 | 新增 `load_nanobot_config()`；删除 LLM/WS/WebUI 方法；精简默认配置和 ENV 映射；迁移 `resolve_webui_dist()` |
| `src/core/config_injector.py` | 配置注入器 | 删除整个文件 |
| `src/core/provider_adapter.py` | Provider 适配器 | 删除转换方法，改为从 nanobot_config.json 读取 |
| `src/core/tools/mcp_connector.py` | MCP 连接器 | 读取源从 config.json 改为 nanobot_config.json |
| `src/core/tools/mcp_config_helper.py` | MCP 配置辅助 | 适配从 nanobot_config.json 的 `tools.mcpServers` 读取 |
| `src/cli/commands/gateway.py` | Gateway 启动命令 | 直接 `set_config_path()`；ChannelManager 从 nanobot_config.json 加载；MCP 配置源改造 |
| `src/cli/commands/agent.py` | Agent chat 命令 | MCP 配置源改造 |
| `src/cli/commands/system.py` | 系统管理命令 | 新增 `migrate-config` 命令 |
| `src/core/init/prompts.py` | 初始化向导提示 | 返回结构改造为 nanobot 原生格式 |
| `src/core/init/generator.py` | 配置文件生成器 | 写入 nanobot_config.json + .gitignore |
| `src/core/init/wizard.py` | 初始化向导 | 适配双文件输出 |
| `src/core/init/migrate.py` | 配置迁移器 | 新增 `migrate_config()` 和 `build_nanobot_config_from_legacy()` |
| `src/core/config/env_manager.py` | 环境变量管理器 | 简化 .env.local 模板 |
| `src/core/webui/app.py` | WebUI FastAPI 应用 | 适配 WebUI 配置读取 |
| `src/core/webui/routes/settings.py` | WebUI 设置路由 | 适配配置读取 |

### 需要删除的文件

| 文件 | 原因 |
|------|------|
| `src/core/config_injector.py` | ConfigInjector 类整体删除，`resolve_webui_dist()` 迁移至 ConfigManager |

### 需要更新/删除的测试文件

| 测试文件 | 处理方式 |
|----------|----------|
| `tests/unit/core/test_config_injector.py` | 删除（ConfigInjector 已删除） |
| `tests/unit/core/config/test_webui_config.py` | 删除（get_webui_config 已删除） |
| `tests/unit/config/test_websocket_config.py` | 删除（get_websocket_config 已删除） |
| `tests/integration/test_config_injection_flow.py` | 删除（ConfigInjector 已删除） |
| `tests/unit/core/test_provider_adapter.py` | 更新（适配新接口） |
| `tests/unit/core/config/test_manager.py` | 更新（适配新接口） |
| `tests/unit/core/config/test_schema.py` | 更新（适配精简后 Schema） |
| `tests/unit/core/test_init_wizard.py` | 更新（适配双文件输出） |
| `tests/unit/core/test_init_prompts.py` | 更新（适配 nanobot 原生格式） |
| `tests/unit/core/test_init_generator.py` | 更新（适配 nanobot_config.json 写入） |
| `tests/unit/core/test_mcp_connector.py` | 更新（适配 nanobot_config.json 读取） |

---

## Task 1: AppConfig Schema 精简

**Files:**
- Modify: `src/core/config/schema.py`
- Test: `tests/unit/core/config/test_schema.py`

- [ ] **Step 1: 编写精简后 AppConfig 的失败测试**

在 `tests/unit/core/config/test_schema.py` 末尾追加：

```python
class TestAppConfigSlimSchema:
    """测试 v0.32.0 精简后 AppConfig Schema"""

    def test_slim_config_valid(self):
        """精简后仅含 Runner 专有字段的配置应验证通过"""
        config = {
            "version": "0.32.0",
            "data_dir": "/data",
            "timezone": "Asia/Shanghai",
            "auto_push_feishu": True,
            "user_id": "default_user",
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_legacy_llm_fields_ignored(self):
        """旧版 llm 字段不应导致验证失败（向后兼容）"""
        config = {
            "version": "0.32.0",
            "data_dir": "/data",
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is True

    def test_user_id_field_accepted(self):
        """user_id 字段应被接受"""
        config = {
            "version": "0.32.0",
            "data_dir": "/data",
            "user_id": "my_user",
        }
        is_valid, _ = AppConfig.validate(config)
        assert is_valid is True

    def test_from_dict_slim(self):
        """from_dict 应能创建精简后的 AppConfig 实例"""
        config = {
            "version": "0.32.0",
            "data_dir": "/data",
            "timezone": "Asia/Shanghai",
            "auto_push_feishu": False,
            "user_id": "default_user",
        }
        app_config = AppConfig.from_dict(config)
        assert app_config.version == "0.32.0"
        assert app_config.user_id == "default_user"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/config/test_schema.py::TestAppConfigSlimSchema -v`
Expected: FAIL — `user_id` 字段不存在于 AppConfig

- [ ] **Step 3: 精简 AppConfig 实现**

将 `src/core/config/schema.py` 中的 `AppConfig` 类替换为：

```python
@dataclass
class AppConfig:
    """应用配置 Schema 数据类（v0.32.0 精简版）

    仅包含 Runner 专有字段。nanobot 相关配置（providers/agents/channels等）
    由 nanobot_config.json 管理，不在本 Schema 中验证。

    Attributes:
        version: 配置文件版本号，格式为 x.y.z
        data_dir: 数据目录路径
        timezone: 时区，用于训练数据时间显示、VDOT 计算等
        auto_push_feishu: 是否自动推送到飞书
        user_id: 用户标识，用于数据隔离
    """

    version: str
    data_dir: str
    timezone: str = "Asia/Shanghai"
    auto_push_feishu: bool = False
    user_id: str = "default_user"

    REQUIRED_FIELDS: ClassVar[list[str]] = ["version", "data_dir"]

    FIELD_TYPES: ClassVar[dict[str, type | tuple[type, ...]]] = {
        "version": str,
        "data_dir": str,
        "timezone": str,
        "auto_push_feishu": bool,
        "user_id": str,
    }

    @classmethod
    def validate(cls, config: dict) -> tuple[bool, list[str]]:
        """验证配置是否符合 Schema

        仅验证 Runner 专有字段。旧版 nanobot 字段（llm_provider 等）
        如果存在会被忽略，不导致验证失败（向后兼容）。

        Args:
            config: 配置字典

        Returns:
            tuple[bool, list[str]]: (是否验证通过，错误消息列表)
        """
        errors: list[str] = []

        cls._validate_required_fields(config, errors)
        cls._validate_field_types(config, errors)
        cls._validate_version(config, errors)

        return len(errors) == 0, errors

    @classmethod
    def _validate_required_fields(cls, config: dict, errors: list[str]) -> None:
        """验证必填字段是否存在且非空"""
        for field_name in cls.REQUIRED_FIELDS:
            if field_name not in config:
                errors.append(f"缺少必填字段：{field_name}")
            elif config[field_name] is None or config[field_name] == "":
                errors.append(f"必填字段不能为空：{field_name}")

    @classmethod
    def _validate_field_types(cls, config: dict, errors: list[str]) -> None:
        """验证字段类型是否正确（仅检查 Schema 中定义的字段）"""
        for field_name, value in config.items():
            if field_name not in cls.FIELD_TYPES:
                continue

            expected_type = cls.FIELD_TYPES[field_name]
            if isinstance(expected_type, tuple):
                if not any(isinstance(value, t) for t in expected_type):
                    type_names = " | ".join(
                        getattr(t, "__name__", str(t)) for t in expected_type
                    )
                    errors.append(
                        f"字段 '{field_name}' 类型错误，期望 {type_names}，实际 {type(value).__name__}"
                    )
            elif not isinstance(value, expected_type):
                errors.append(
                    f"字段 '{field_name}' 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
                )

    @classmethod
    def _validate_version(cls, config: dict, errors: list[str]) -> None:
        """验证版本号格式"""
        if "version" in config and config["version"]:
            version = config["version"]
            if not cls._is_valid_version(version):
                errors.append(f"版本号格式错误：'{version}'，应为 x.y.z 格式")

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """检查版本号格式是否有效"""
        import re

        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    @classmethod
    def from_dict(cls, config: dict) -> "AppConfig":
        """从字典创建 AppConfig 实例

        仅提取 Schema 中定义的字段，忽略旧版 nanobot 字段。

        Args:
            config: 配置字典

        Returns:
            AppConfig: 配置实例

        Raises:
            ValueError: 配置验证失败时抛出
        """
        is_valid, errors = cls.validate(config)
        if not is_valid:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

        known_fields = {k: v for k, v in config.items() if k in cls.FIELD_TYPES}

        return cls(**known_fields)

    def to_dict(self) -> dict:
        """将配置实例转换为字典"""
        return asdict(self)

    def __post_init__(self) -> None:
        """数据类初始化后验证"""
        is_valid, errors = self.validate(self.to_dict())
        if not is_valid:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/config/test_schema.py -v`
Expected: PASS — 所有测试通过（包括旧测试，因为旧字段被忽略而非拒绝）

- [ ] **Step 5: 提交**

```bash
git add src/core/config/schema.py tests/unit/core/config/test_schema.py
git commit -m "refactor(config): 精简 AppConfig Schema，移除 nanobot 字段验证"
```

---

## Task 2: ConfigManager 核心改造

**Files:**
- Modify: `src/core/config/manager.py`
- Test: `tests/unit/core/config/test_manager.py`

- [ ] **Step 1: 编写 load_nanobot_config 和 has_llm_config 新逻辑的失败测试**

在 `tests/unit/core/config/test_manager.py` 中追加：

```python
class TestNanobotConfigLoading:
    """测试 nanobot_config.json 读取功能（v0.32.0）"""

    def test_get_nanobot_config_path(self, tmp_path):
        """测试获取 nanobot_config.json 路径"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.get_nanobot_config_path() == tmp_path / "nanobot_config.json"

    def test_load_nanobot_config_not_exists(self, tmp_path):
        """nanobot_config.json 不存在时返回空 dict"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            result = cm.load_nanobot_config()
            assert result == {}

    def test_load_nanobot_config_exists(self, tmp_path):
        """nanobot_config.json 存在时返回配置字典"""
        nano_config = {
            "providers": {
                "default": "custom",
                "custom": {"apiKey": "sk-test", "apiBase": "https://api.test.com/v1"},
            },
            "agents": {"defaults": {"model": "test-model"}},
        }
        nano_path = tmp_path / "nanobot_config.json"
        nano_path.write_text(json.dumps(nano_config), encoding="utf-8")

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            result = cm.load_nanobot_config()
            assert result["providers"]["default"] == "custom"
            assert result["agents"]["defaults"]["model"] == "test-model"

    def test_has_llm_config_true(self, tmp_path):
        """nanobot_config.json 有有效 provider+apiKey 时 has_llm_config 返回 True"""
        nano_config = {
            "providers": {
                "default": "custom",
                "custom": {"apiKey": "sk-test", "apiBase": "https://api.test.com/v1"},
            },
        }
        nano_path = tmp_path / "nanobot_config.json"
        nano_path.write_text(json.dumps(nano_config), encoding="utf-8")

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.has_llm_config() is True

    def test_has_llm_config_false_no_file(self, tmp_path):
        """nanobot_config.json 不存在时 has_llm_config 返回 False"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.has_llm_config() is False

    def test_has_llm_config_false_no_api_key(self, tmp_path):
        """provider 存在但 apiKey 为空时 has_llm_config 返回 False"""
        nano_config = {
            "providers": {
                "default": "custom",
                "custom": {"apiKey": "", "apiBase": "https://api.test.com/v1"},
            },
        }
        nano_path = tmp_path / "nanobot_config.json"
        nano_path.write_text(json.dumps(nano_config), encoding="utf-8")

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.has_llm_config() is False

    def test_resolve_webui_dist_returns_path_or_none(self, tmp_path):
        """resolve_webui_dist 返回 Path 或 None"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            result = cm.resolve_webui_dist()
            assert result is None or isinstance(result, Path)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/config/test_manager.py::TestNanobotConfigLoading -v`
Expected: FAIL — `get_nanobot_config_path` 方法不存在

- [ ] **Step 3: 实现 ConfigManager 改造**

在 `src/core/config/manager.py` 中进行以下改动：

**3a. 精简 `_get_default_config()` 和 `ENV_KEY_MAPPING`**

将 `_get_default_config` 方法替换为：

```python
    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        """获取默认配置（仅 Runner 专有字段）

        Returns:
            dict: 默认配置字典
        """
        return {
            "version": "0.32.0",
            "data_dir": str(Path.home() / ".nanobot-runner" / "data"),
            "timezone": "Asia/Shanghai",
            "auto_push_feishu": False,
            "user_id": "default_user",
        }
```

将模块级 `ENV_KEY_MAPPING` 替换为空字典（Runner 专有字段不再需要环境变量覆盖）：

```python
# Runner 专有字段无需环境变量覆盖
ENV_KEY_MAPPING: dict[str, str] = {}
```

删除 `WS_ENV_KEY_MAPPING` 和 `WEBUI_ENV_KEY_MAPPING` 常量。

**3b. 新增 nanobot_config.json 读取方法**

在 `ConfigManager` 类中添加（放在 `load_config` 方法之后）：

```python
    def get_nanobot_config_path(self) -> Path:
        """获取 nanobot_config.json 路径

        Returns:
            Path: nanobot_config.json 文件路径
        """
        return self.base_dir / "nanobot_config.json"

    def load_nanobot_config(self) -> dict[str, Any]:
        """加载 nanobot_config.json

        nanobot_config.json 是 nanobot 配置的唯一真实源，包含
        providers/agents/channels/model_presets/tools 等字段。

        Returns:
            dict[str, Any]: nanobot 配置字典，文件不存在时返回空 dict

        Raises:
            ConfigError: JSON 格式错误时抛出（规格 7.3 错误处理要求）
        """
        path = self.get_nanobot_config_path()
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"配置文件格式错误，请检查 nanobot_config.json: {e}",
                recovery_suggestion="请修正 JSON 语法错误",
            ) from e
```

**3c. 改写 `has_llm_config()` 方法**

将 `has_llm_config` 方法替换为：

```python
    def has_llm_config(self) -> bool:
        """检查是否配置了有效的 LLM

        检查 nanobot_config.json 是否有 providers.default
        且对应 provider 有非空 apiKey。

        Returns:
            bool: 是否存在有效 LLM 配置
        """
        nano_cfg = self.load_nanobot_config()
        providers = nano_cfg.get("providers", {})
        default_provider = providers.get("default", "")
        if not default_provider:
            return False
        provider_cfg = providers.get(default_provider, {})
        return bool(provider_cfg.get("apiKey"))
```

**3d. 迁移 `resolve_webui_dist()` 方法**

在 `ConfigManager` 类中添加（从 ConfigInjector 迁移）：

```python
    def resolve_webui_dist(self) -> Path | None:
        """解析 WebUI dist 目录

        优先使用 RunFlowAgent 自有 dist（项目根/webui/dist），
        回退到 nanobot 内置 dist（nanobot/web/dist）。

        Returns:
            Path | None: dist 目录路径，不存在则返回 None
        """
        custom_dist = Path(__file__).parent.parent.parent.parent / "webui" / "dist"
        if custom_dist.exists():
            return custom_dist

        try:
            import nanobot.web as web_pkg

            nanobot_dist = Path(web_pkg.__file__).parent / "dist"
            if nanobot_dist.exists():
                return nanobot_dist
        except (ImportError, AttributeError):
            pass

        return None
```

**3e. 删除以下方法**

删除 `ConfigManager` 中的以下方法（整段删除）：
- `get_llm_config()`
- `save_llm_config()`
- `get_fallback_api_key()`
- `get_fallback_models()`
- `get_websocket_config()`
- `get_webui_config()`

**3f. 简化 `load_config_with_env_override()`**

将 `load_config_with_env_override` 方法替换为：

```python
    def load_config_with_env_override(self) -> dict[str, Any]:
        """加载配置并支持环境变量覆盖

        配置加载优先级：环境变量 > 配置文件 > 默认值

        Returns:
            dict[str, Any]: 合并后的配置字典
        """
        config = self.load_config()

        for config_key, env_key in ENV_KEY_MAPPING.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                config[config_key] = self._cast_env_value(config_key, env_value)

        return config
```

**3g. 精简 `validate_config_consistency()`**

将 `validate_config_consistency` 方法替换为（ENV_KEY_MAPPING 为空，直接返回空列表）：

```python
    def validate_config_consistency(self) -> list[dict[str, str]]:
        """验证配置一致性

        Returns:
            list[dict[str, str]]: 不一致项列表
        """
        return []
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/config/test_manager.py::TestNanobotConfigLoading -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/config/manager.py tests/unit/core/config/test_manager.py
git commit -m "refactor(config): ConfigManager 改造，新增 load_nanobot_config，删除 LLM/WS/WebUI 方法"
```

---

## Task 3: 删除 ConfigInjector

**Files:**
- Delete: `src/core/config_injector.py`
- Delete: `tests/unit/core/test_config_injector.py`
- Delete: `tests/integration/test_config_injection_flow.py`
- Modify: `src/core/provider_adapter.py` (移除 ConfigInjector 导入)
- Modify: `src/core/sdk_adapter.py` (移除 config_injector 参数)

- [ ] **Step 1: 移除 provider_adapter.py 对 ConfigInjector 的引用**

在 `src/core/provider_adapter.py` 中：

删除导入行：
```python
from src.core.config_injector import ConfigInjector
```

删除 `RunnerProviderAdapter.__init__` 中的 `_config_injector` 字段和 `set_config_injector` 方法：

将 `__init__` 方法改为：
```python
    def __init__(
        self, runner_config: ConfigManager, *, webui_enabled: bool = False
    ) -> None:
        """初始化配置注入器

        Args:
            runner_config: 项目配置管理器实例
            webui_enabled: 是否启用 WebUI，启用时自动激活 WebSocket 通道
        """
        self._runner_config = runner_config
        self._webui_enabled = webui_enabled
        self._provider_instance: Any | None = None
```

删除 `set_config_injector` 方法整段。

删除 `__init__` 中的 `self._nanobot_config: Any | None = None` 行。

- [ ] **Step 2: 移除 sdk_adapter.py 对 ConfigInjector 的引用**

在 `src/core/sdk_adapter.py` 中，将 `__init__` 方法签名中的 `config_injector` 参数移除：

找到 `def __init__(self, workspace: str | Path | None = None, config_injector: Any = None):` 改为：
```python
    def __init__(self, workspace: str | Path | None = None):
```

删除方法体中 `self._injector = config_injector` 行及相关的 `config_injector` 文档说明。

- [ ] **Step 3: 删除 ConfigInjector 文件和相关测试**

删除以下文件：
- `src/core/config_injector.py`
- `tests/unit/core/test_config_injector.py`
- `tests/integration/test_config_injection_flow.py`

- [ ] **Step 4: 验证无残留引用**

Run: `uv run python -c "from src.core.provider_adapter import RunnerProviderAdapter; print('OK')"`
Expected: 输出 `OK`，无 ImportError

Run: `uv run python -c "from src.core.sdk_adapter import SDKAdapter; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 5: 提交**

```bash
git add src/core/config_injector.py src/core/provider_adapter.py src/core/sdk_adapter.py
git rm src/core/config_injector.py tests/unit/core/test_config_injector.py tests/integration/test_config_injection_flow.py
git commit -m "refactor: 删除 ConfigInjector，resolve_webui_dist 迁移至 ConfigManager"
```

---

## Task 4: RunnerProviderAdapter 改造

**Files:**
- Modify: `src/core/provider_adapter.py`
- Test: `tests/unit/core/test_provider_adapter.py`

- [ ] **Step 1: 编写新接口的失败测试**

在 `tests/unit/core/test_provider_adapter.py` 中追加新的测试类：

```python
class TestRunnerProviderAdapterFromNanobotConfig:
    """测试从 nanobot_config.json 读取配置（v0.32.0）"""

    @pytest.fixture
    def mock_config_with_nanobot(self):
        """模拟带 nanobot_config.json 的 ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        config.load_nanobot_config.return_value = {
            "providers": {
                "default": "custom",
                "custom": {
                    "apiKey": "sk-test-key",
                    "apiBase": "https://api.test.com/v1",
                    "apiType": "auto",
                },
            },
            "agents": {
                "defaults": {
                    "model": "test-model",
                    "maxToolIterations": 200,
                    "contextWindowTokens": 200000,
                }
            },
        }
        config.has_llm_config.return_value = True

        def _mock_get(key: str, default: Any = None) -> Any:
            if key == "timezone":
                return "Asia/Shanghai"
            return default

        config.get.side_effect = _mock_get
        config.base_dir = Path("/test/runner")
        return config

    def test_get_llm_config_from_nanobot(self, mock_config_with_nanobot):
        """从 nanobot_config.json 读取 LLM 配置"""
        adapter = RunnerProviderAdapter(mock_config_with_nanobot)
        llm_config = adapter.get_llm_config()
        assert llm_config.provider == "custom"
        assert llm_config.model == "test-model"
        assert llm_config.api_key == "sk-test-key"
        assert llm_config.base_url == "https://api.test.com/v1"

    def test_get_agent_defaults_from_nanobot(self, mock_config_with_nanobot):
        """从 nanobot_config.json 读取 Agent 默认配置"""
        adapter = RunnerProviderAdapter(mock_config_with_nanobot)
        defaults = adapter.get_agent_defaults()
        assert defaults.model == "test-model"
        assert defaults.max_tool_iterations == 200
        assert defaults.context_window_tokens == 200000
        assert defaults.timezone == "Asia/Shanghai"

    def test_is_available_true(self, mock_config_with_nanobot):
        """nanobot_config.json 有效时 is_available 返回 True"""
        adapter = RunnerProviderAdapter(mock_config_with_nanobot)
        assert adapter.is_available() is True

    def test_is_available_false_no_nanobot_config(self):
        """nanobot_config.json 无效时 is_available 返回 False"""
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)
        assert adapter.is_available() is False

    def test_get_llm_config_raises_when_no_config(self):
        """无 nanobot_config.json 时 get_llm_config 抛出 LLMError"""
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)
        with pytest.raises(LLMError, match="未配置LLM"):
            adapter.get_llm_config()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/test_provider_adapter.py::TestRunnerProviderAdapterFromNanobotConfig -v`
Expected: FAIL — `get_llm_config` 仍调用旧接口

- [ ] **Step 3: 改造 RunnerProviderAdapter 实现**

在 `src/core/provider_adapter.py` 中进行以下改动：

**3a. 改写 `get_llm_config()`**

```python
    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置

        从 nanobot_config.json 读取 providers 和 agents.defaults.model。

        Returns:
            LLMConfig: LLM配置数据类实例

        Raises:
            LLMError: 未配置LLM时抛出
        """
        if not self._has_runner_llm_config():
            raise LLMError(
                "未配置LLM，请运行 'nanobotrun system init' 完成配置",
                recovery_suggestion="运行 nanobotrun system init 配置LLM",
            )
        return self._from_nanobot_config()
```

**3b. 改写 `_from_runner_config()` 为 `_from_nanobot_config()`**

删除 `_from_runner_config` 方法，替换为：

```python
    def _from_nanobot_config(self) -> LLMConfig:
        """从 nanobot_config.json 提取 LLM 配置

        Returns:
            LLMConfig: LLM配置数据类实例
        """
        nano_cfg = self._runner_config.load_nanobot_config()
        providers = nano_cfg.get("providers", {})
        default_provider = providers.get("default", "")
        provider_cfg = providers.get(default_provider, {})

        return LLMConfig(
            provider=default_provider,
            model=nano_cfg.get("agents", {})
            .get("defaults", {})
            .get("model", ""),
            api_key=provider_cfg.get("apiKey", ""),
            base_url=provider_cfg.get("apiBase"),
        )
```

**3c. 改写 `get_agent_defaults()`**

```python
    def get_agent_defaults(self) -> AgentDefaults:
        """获取Agent默认配置

        从 nanobot_config.json 的 agents.defaults 读取。

        Returns:
            AgentDefaults: Agent默认配置实例
        """
        nano_cfg = self._runner_config.load_nanobot_config()
        defaults = nano_cfg.get("agents", {}).get("defaults", {})

        raw_timezone = self._runner_config.get("timezone")
        timezone = raw_timezone if isinstance(raw_timezone, str) else "UTC"

        return AgentDefaults(
            model=defaults.get("model", ""),
            max_tool_iterations=defaults.get("maxToolIterations", 200),
            context_window_tokens=defaults.get("contextWindowTokens", 200000),
            timezone=timezone,
        )
```

**3d. 改写 `_resolve_fallback_presets()`**

```python
    def _resolve_fallback_presets(self) -> list[Any]:
        """解析 fallback 预设列表

        从 nanobot_config.json 的 agents.defaults.fallbackModels 读取。

        Returns:
            list[Any]: ModelPresetConfig 列表
        """
        try:
            from nanobot.config.schema import ModelPresetConfig
        except ImportError:
            logger.warning("nanobot-ai 不支持 ModelPresetConfig，跳过 fallback 配置")
            return []

        nano_cfg = self._runner_config.load_nanobot_config()
        fallback_list = (
            nano_cfg.get("agents", {}).get("defaults", {}).get("fallbackModels", [])
        )
        if not fallback_list:
            return []

        presets: list[Any] = []
        for fb in fallback_list:
            model = fb.get("model", "")
            provider = fb.get("provider", "")
            if not model or not provider:
                continue
            preset = ModelPresetConfig(model=model, provider=provider)
            presets.append(preset)

        return presets
```

**3e. 改写 `_create_fallback_provider()`**

```python
    def _create_fallback_provider(self, preset: Any) -> Any:
        """为 fallback 预设创建 Provider 实例

        从 nanobot_config.json 的 providers 读取对应 provider 的 apiKey 和 apiBase。

        Args:
            preset: ModelPresetConfig 实例

        Returns:
            Any: nanobot Provider 实例
        """
        from nanobot.providers.openai_compat_provider import OpenAICompatProvider
        from nanobot.providers.registry import find_by_name

        nano_cfg = self._runner_config.load_nanobot_config()
        providers = nano_cfg.get("providers", {})
        provider_cfg = providers.get(preset.provider, {})

        api_key = provider_cfg.get("apiKey", "")
        base_url = provider_cfg.get("apiBase")
        spec = find_by_name(preset.provider)

        return OpenAICompatProvider(
            api_key=api_key,
            api_base=base_url,
            default_model=preset.model,
            spec=spec,
        )
```

**3f. 删除以下方法（整段删除）**

- `_get_or_create_nanobot_config()`
- `save_nanobot_config()`
- `_build_nanobot_config_from_runner()`
- `_build_feishu_channel_config()`
- `_build_websocket_channel_config()`
- `_parse_env_file()`

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/test_provider_adapter.py -v`
Expected: PASS — 新增测试通过。旧测试中引用已删除方法的会失败，需在 Step 5 中更新。

- [ ] **Step 5: 更新旧测试**

在 `tests/unit/core/test_provider_adapter.py` 中，删除或更新引用已删除方法的测试类。具体：
- 删除 `mock_runner_config` fixture 中对 `get_llm_config` / `get_websocket_config` 的 mock 设置
- 更新 `TestRunnerProviderAdapterGetLlmConfig` 使用新的 `mock_config_with_nanobot` fixture
- 更新 `TestRunnerProviderAdapterGetAgentDefaults` 使用新的 fixture
- 删除所有引用 `_build_nanobot_config_from_runner` / `save_nanobot_config` / `_get_or_create_nanobot_config` 的测试

- [ ] **Step 6: 提交**

```bash
git add src/core/provider_adapter.py tests/unit/core/test_provider_adapter.py
git commit -m "refactor(adapter): RunnerProviderAdapter 改为从 nanobot_config.json 读取配置"
```

---

## Task 5: MCP 配置读取源改造

**Files:**
- Modify: `src/core/tools/mcp_config_helper.py`
- Modify: `src/core/tools/mcp_connector.py`
- Test: `tests/unit/core/test_mcp_connector.py`

- [ ] **Step 1: 编写从 nanobot_config.json 读取 MCP 配置的失败测试**

在 `tests/unit/core/test_mcp_connector.py` 中追加：

```python
@pytest.fixture
def nanobot_config_with_mcp(tmp_path: Path) -> Path:
    """创建包含 MCP 配置的 nanobot_config.json"""
    config_path = tmp_path / "nanobot_config.json"
    config = {
        "providers": {"default": "custom"},
        "agents": {"defaults": {"model": "test"}},
        "tools": {
            "mcpServers": {
                "weather": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@dangahagan/weather-mcp"],
                    "toolTimeout": 30,
                    "enabledTools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


class TestLoadMcpFromNanobotConfig:
    """测试从 nanobot_config.json 读取 MCP 配置"""

    def test_load_mcp_servers_from_nanobot_config(self, nanobot_config_with_mcp):
        """从 nanobot_config.json 的 tools.mcpServers 加载 MCP 配置"""
        result = load_mcp_servers_config(nanobot_config_with_mcp)
        assert "weather" in result
        assert result["weather"].command == "npx"

    def test_load_mcp_servers_empty_config(self, tmp_path):
        """nanobot_config.json 无 tools.mcpServers 时返回空 dict"""
        config_path = tmp_path / "nanobot_config.json"
        config_path.write_text(
            json.dumps({"providers": {}}), encoding="utf-8"
        )
        result = load_mcp_servers_config(config_path)
        assert result == {}

    def test_load_mcp_servers_file_not_exists(self, tmp_path):
        """文件不存在时返回空 dict"""
        result = load_mcp_servers_config(tmp_path / "nonexistent.json")
        assert result == {}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/test_mcp_connector.py::TestLoadMcpFromNanobotConfig -v`
Expected: FAIL — 当前 `MCPConfigHelper` 读取 `tools.mcp_servers`（snake_case），而 nanobot_config.json 用 `tools.mcpServers`（camelCase）

- [ ] **Step 3: 改造 MCPConfigHelper 适配 nanobot_config.json 格式**

在 `src/core/tools/mcp_config_helper.py` 中，修改 `load_tools_config` 方法，使其同时支持 `mcpServers`（nanobot 格式）和 `mcp_servers`（旧格式）：

将 `load_tools_config` 方法替换为：

```python
    def load_tools_config(self) -> ToolsConfig:
        """加载工具配置

        从配置文件中读取 tools 字段，解析为 ToolsConfig 实例。
        支持 nanobot 原生格式（tools.mcpServers，camelCase）和
        旧版格式（tools.mcp_servers，snake_case）。

        Returns:
            ToolsConfig: 工具配置实例，配置文件不存在或无 tools 字段时返回空配置
        """
        if not self.config_path.exists():
            logger.debug(f"配置文件不存在: {self.config_path}")
            return ToolsConfig()

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取配置文件失败: {e}")
            return ToolsConfig()

        tools_section = config.get("tools", {})
        if not isinstance(tools_section, dict):
            logger.warning("配置文件中tools字段格式错误，应为字典类型")
            return ToolsConfig()

        # 兼容 nanobot 原生格式（mcpServers）和旧版格式（mcp_servers）
        mcp_servers_raw = tools_section.get("mcpServers")
        if mcp_servers_raw is None:
            mcp_servers_raw = tools_section.get("mcp_servers", {})

        # 转换为旧版格式以复用 ToolsConfig.from_config_dict
        adapted_section = dict(tools_section)
        adapted_section["mcp_servers"] = mcp_servers_raw

        return ToolsConfig.from_config_dict(adapted_section)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/test_mcp_connector.py -v`
Expected: PASS — 新旧格式测试均通过

- [ ] **Step 5: 提交**

```bash
git add src/core/tools/mcp_config_helper.py tests/unit/core/test_mcp_connector.py
git commit -m "refactor(mcp): MCP 配置读取适配 nanobot_config.json 的 tools.mcpServers 格式"
```

---

## Task 6: gateway.py 改造

**Files:**
- Modify: `src/cli/commands/gateway.py`

- [ ] **Step 1: 改造 `_init_gateway_context` — 直接 set_config_path**

在 `src/cli/commands/gateway.py` 的 `_init_gateway_context` 函数中，将 LLM 配置检查块替换为：

```python
        if context.config.has_llm_config():
            adapter = RunnerProviderAdapter(context.config, webui_enabled=webui)
            # v0.32.0: 直接指向用户维护的 nanobot_config.json，
            # 不再调用 save_nanobot_config() 自动生成
            from nanobot.config.loader import set_config_path

            nanobot_config_path = context.config.get_nanobot_config_path()
            if nanobot_config_path.exists():
                set_config_path(nanobot_config_path)
```

- [ ] **Step 2: 改造 MCP 配置读取源**

在 `start` 函数中，找到 MCP 配置加载行：

```python
        mcp_servers = load_mcp_servers_config(context.config.config_file)
```

替换为：

```python
        mcp_servers = load_mcp_servers_config(context.config.get_nanobot_config_path())
```

- [ ] **Step 3: 改造 ChannelManager 初始化**

在 `start` 函数中，找到 ChannelManager 初始化块：

```python
    channels = ChannelManager(
        config=adapter._get_or_create_nanobot_config(),
        bus=bus,
        session_manager=session_manager,
        webui_runtime_model_name=get_runtime_model_name,
    )
```

替换为：

```python
    # v0.32.0: ChannelManager 直接从 nanobot_config.json 加载 Config 对象
    from nanobot.config.loader import load_config as load_nanobot_config_obj

    nanobot_config_path = context.config.get_nanobot_config_path()
    nanobot_cfg = load_nanobot_config_obj(nanobot_config_path)
    channels = ChannelManager(
        config=nanobot_cfg,
        bus=bus,
        session_manager=session_manager,
        webui_runtime_model_name=get_runtime_model_name,
    )
```

- [ ] **Step 4: 改造 WebUI 配置读取**

在 `_setup_fastapi_server` 函数中，找到：

```python
    webui_config = context.config.get_webui_config()
```

替换为使用硬编码默认值（WebUI REST API 是 Runner 专有，不在 nanobot_config.json 中）：

```python
    # v0.32.0: WebUI REST API 配置使用默认值（nanobot_config.json 无 webui 节）
    webui_config = {
        "host": "127.0.0.1",
        "port": 8766,
    }
```

在 `_display_channel_status` 函数中，找到所有 `context.config.get_websocket_config()` 调用，替换为从 nanobot_config.json 读取：

```python
        ws_config = context.config.load_nanobot_config().get("channels", {}).get("websocket", {})
```

在 `_display_webui_info` 函数中，同样将 `context.config.get_websocket_config()` 替换为：

```python
    ws_config = context.config.load_nanobot_config().get("channels", {}).get("websocket", {})
```

在 `_display_webui_info` 函数中，将 `context.config.get_webui_config()` 替换为：

```python
        webui_config = {"host": "127.0.0.1", "port": 8766}
```

- [ ] **Step 5: 验证语法正确**

Run: `uv run python -c "from src.cli.commands.gateway import app; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 6: 提交**

```bash
git add src/cli/commands/gateway.py
git commit -m "refactor(gateway): 直接 set_config_path，ChannelManager 从 nanobot_config.json 加载"
```

---

## Task 7: agent.py 改造

**Files:**
- Modify: `src/cli/commands/agent.py`

- [ ] **Step 1: 改造 MCP 配置读取源**

在 `src/cli/commands/agent.py` 的 `_run_chat` 函数中，找到：

```python
        mcp_config = load_mcp_servers_config(context.config.config_file)
```

替换为：

```python
        mcp_config = load_mcp_servers_config(context.config.get_nanobot_config_path())
```

- [ ] **Step 2: 验证语法正确**

Run: `uv run python -c "from src.cli.commands.agent import app; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 3: 提交**

```bash
git add src/cli/commands/agent.py
git commit -m "refactor(agent): MCP 配置读取源改为 nanobot_config.json"
```

---

## Task 8: WebUI 模块适配

**Files:**
- Modify: `src/core/webui/app.py`
- Modify: `src/core/webui/routes/settings.py`

- [ ] **Step 1: 改造 webui/app.py 中的 get_webui_config 调用**

在 `src/core/webui/app.py` 中，找到所有 `context.config.get_webui_config()` 调用（约 2 处），替换为使用默认值：

第一处（`create_server` 函数中，约第 70 行）：
```python
    webui_config = {"host": "127.0.0.1", "port": 8766}
```

第二处（`_create_uvicorn_server` 函数中，约第 213 行）：
```python
    webui_config = {"host": "127.0.0.1", "port": 8766}
    host = webui_config.get("host", "127.0.0.1")
    port = webui_config.get("port", 8766)
```

- [ ] **Step 2: 改造 webui/routes/settings.py 中的配置读取**

在 `src/core/webui/routes/settings.py` 的 `_get_system_config` 函数中，找到 `context.config.get_webui_config()` 调用，替换为：

```python
    webui_config = {"host": "127.0.0.1", "port": 8766}
```

如果该函数还调用了 `get_llm_config()` 或 `has_llm_config()`，将其改为从 nanobot_config.json 读取：

```python
    nano_cfg = context.config.load_nanobot_config()
    providers = nano_cfg.get("providers", {})
    default_provider = providers.get("default", "")
    llm_config = {
        "provider": default_provider,
        "model": nano_cfg.get("agents", {}).get("defaults", {}).get("model", ""),
    }
```

- [ ] **Step 3: 验证语法正确**

Run: `uv run python -c "from src.core.webui.app import create_server; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 4: 提交**

```bash
git add src/core/webui/app.py src/core/webui/routes/settings.py
git commit -m "refactor(webui): 适配配置分离，WebUI 配置使用默认值"
```

---

## Task 9: 初始化向导改造

**Files:**
- Modify: `src/core/init/prompts.py`
- Modify: `src/core/init/generator.py`
- Modify: `src/core/init/wizard.py`
- Test: `tests/unit/core/test_init_prompts.py`
- Test: `tests/unit/core/test_init_generator.py`
- Test: `tests/unit/core/test_init_wizard.py`

- [ ] **Step 1: 编写 InitPrompts 返回 nanobot 原生格式的失败测试**

在 `tests/unit/core/test_init_prompts.py` 中追加：

```python
class TestInitPromptsNanobotFormat:
    """测试向导返回 nanobot 原生格式（v0.32.0）"""

    def test_run_full_wizard_data_mode(self):
        """数据模式不生成 nanobot_config"""
        with patch.dict("sys.modules", {"questionary": None}):
            result = InitPrompts.run_full_wizard(agent_mode=False)
            assert "nanobot_config" not in result or result.get("nanobot_config") is None
            assert "runner_config" in result or "config" in result

    def test_run_full_wizard_agent_mode_structure(self):
        """Agent 模式返回包含 runner_config 和 nanobot_config"""
        mock_questionary = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "openai"
        mock_questionary.text.return_value.ask.return_value = "gpt-4o-mini"
        mock_questionary.password.return_value.ask.return_value = "sk-test"
        mock_questionary.confirm.return_value.ask.return_value = False

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            with patch.object(
                InitPrompts,
                "run_fallback_wizard",
                return_value={"_model_presets": {}, "_fallback_models": []},
            ):
                result = InitPrompts.run_full_wizard(agent_mode=True)
                # 验证返回结构包含 nanobot_config
                assert "nanobot_config" in result
                nano_cfg = result["nanobot_config"]
                assert "providers" in nano_cfg
                assert nano_cfg["providers"]["default"] == "openai"
                assert "apiKey" in nano_cfg["providers"]["openai"]
                assert "agents" in nano_cfg
                assert "model" in nano_cfg["agents"]["defaults"]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/test_init_prompts.py::TestInitPromptsNanobotFormat -v`
Expected: FAIL — 当前 `run_full_wizard` 返回 `{"config": ..., "env_vars": ...}` 结构

- [ ] **Step 3: 改造 InitPrompts.run_full_wizard() 返回双文件结构**

在 `src/core/init/prompts.py` 中，将 `run_full_wizard` 方法替换为：

```python
    @staticmethod
    def run_full_wizard(
        skip_optional: bool = False,
        agent_mode: bool = True,
    ) -> dict[str, Any]:
        """运行完整的配置向导

        v0.32.0: 返回 runner_config 和 nanobot_config 双文件结构。

        Args:
            skip_optional: 是否跳过可选项
            agent_mode: 是否配置LLM（True=Agent模式，False=数据模式）

        Returns:
            dict[str, Any]: 包含 runner_config、nanobot_config 的字典
        """
        runner_config: dict[str, Any] = {"version": __version__}
        nanobot_config: dict[str, Any] = {}

        if agent_mode:
            llm_result = InitPrompts.run_llm_provider_wizard()

            # 构建 nanobot_config.json 的 providers 节
            provider_name = llm_result["config"].get("llm_provider", "openai")
            model = llm_result["config"].get("llm_model", "gpt-4o-mini")
            base_url = llm_result["config"].get("llm_base_url")
            api_key = llm_result.get("env_vars", {}).get("NANOBOT_LLM_API_KEY", "")

            providers: dict[str, Any] = {"default": provider_name}
            provider_cfg: dict[str, Any] = {"apiKey": api_key, "apiType": "auto"}
            if base_url:
                provider_cfg["apiBase"] = base_url
            providers[provider_name] = provider_cfg

            # 备选供应商的 apiKey 写入 providers
            for k, v in llm_result.get("env_vars", {}).items():
                if k.startswith("NANOBOT_LLM_API_KEY_") and v:
                    fb_provider = k.replace("NANOBOT_LLM_API_KEY_", "").lower()
                    if fb_provider not in providers:
                        providers[fb_provider] = {"apiKey": v, "apiType": "auto"}

            nanobot_config["providers"] = providers

            # 构建 agents.defaults 节
            business_config = InitPrompts.run_business_config_wizard()
            timezone = business_config.get("timezone", "Asia/Shanghai")

            agents_defaults: dict[str, Any] = {
                "model": model,
                "provider": "auto",
                "timezone": timezone,
                "workspace": "~/.nanobot-runner",
                "botName": "nanobot-runner",
                "botIcon": "🍀",
            }

            # fallbackModels
            fallback_models = llm_result.get("_fallback_models", [])
            model_presets = llm_result.get("_model_presets", {})
            if fallback_models:
                fb_list: list[dict[str, Any]] = []
                for name in fallback_models:
                    preset = model_presets.get(name, {})
                    if preset.get("provider") and preset.get("model"):
                        fb_list.append(
                            {"model": preset["model"], "provider": preset["provider"]}
                        )
                if fb_list:
                    agents_defaults["fallbackModels"] = fb_list

            nanobot_config["agents"] = {"defaults": agents_defaults}

            # model_presets（nanobot 原生格式）
            nano_presets: dict[str, Any] = {}
            for name, preset in model_presets.items():
                nano_presets[name] = {
                    "model": preset.get("model", ""),
                    "provider": preset.get("provider", "auto"),
                }
            nanobot_config["model_presets"] = nano_presets

            # tools（MCP 配置）
            nanobot_config["tools"] = InitPrompts._default_tools_config_nanobot()

            # channels（飞书可选）
            nanobot_config["channels"] = {}

            runner_config["timezone"] = timezone
        else:
            business_config = InitPrompts.run_business_config_wizard()
            runner_config["timezone"] = business_config.get("timezone", "Asia/Shanghai")

        # 飞书配置
        if not skip_optional:
            feishu_result = InitPrompts.run_feishu_config_wizard()
            runner_config["auto_push_feishu"] = feishu_result["config"].get(
                "auto_push_feishu", False
            )
            # 飞书凭证写入 nanobot_config.json 的 channels.feishu
            if runner_config["auto_push_feishu"]:
                env_vars = feishu_result.get("env_vars", {})
                nanobot_config.setdefault("channels", {})["feishu"] = {
                    "enabled": True,
                    "app_id": env_vars.get("NANOBOT_FEISHU_APP_ID", ""),
                    "app_secret": env_vars.get("NANOBOT_FEISHU_APP_SECRET", ""),
                    "receive_id": env_vars.get("NANOBOT_FEISHU_RECEIVE_ID", ""),
                    "receive_id_type": "user_id",
                    "allowFrom": ["*"],
                }
        else:
            runner_config["auto_push_feishu"] = False

        return {
            "runner_config": runner_config,
            "nanobot_config": nanobot_config if agent_mode else None,
        }
```

在 `InitPrompts` 类中添加 `_default_tools_config_nanobot` 方法（返回 camelCase 格式）：

```python
    @staticmethod
    def _default_tools_config_nanobot() -> dict[str, Any]:
        """获取默认工具生态配置（nanobot 原生 camelCase 格式）

        Returns:
            dict[str, Any]: 默认工具配置字典
        """
        return {
            "mcpServers": {
                "Chrome DevTools MCP": {
                    "command": "npx",
                    "args": ["-y", "chrome-devtools-mcp@latest", "--autoConnect"],
                    "env": {},
                },
                "weather": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@dangahagan/weather-mcp"],
                    "toolTimeout": 30,
                    "enabledTools": ["*"],
                },
                "osm": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["osm-mcp-server"],
                    "toolTimeout": 30,
                    "enabledTools": ["*"],
                },
                "coros": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "coros-cli", "mcp"],
                    "toolTimeout": 30,
                    "enabledTools": ["*"],
                },
            }
        }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/test_init_prompts.py::TestInitPromptsNanobotFormat -v`
Expected: PASS

- [ ] **Step 5: 改造 ConfigGenerator.write_config_files() 写入双文件**

在 `src/core/init/generator.py` 中，将 `write_config_files` 方法替换为：

```python
    def write_config_files(
        self,
        workspace_dir: Path,
        config: dict[str, Any],
        env_vars: dict[str, str] | None = None,
        nanobot_config: dict[str, Any] | None = None,
        init_git: bool = True,
    ) -> dict[str, Path]:
        """写入所有配置文件

        v0.32.0: 同时写入 config.json 和 nanobot_config.json。

        Args:
            workspace_dir: workspace 目录路径
            config: Runner 专有配置字典（写入 config.json）
            env_vars: 环境变量字典（可选，v0.32.0 后通常为空）
            nanobot_config: nanobot 配置字典（写入 nanobot_config.json）
            init_git: 是否初始化 Git 仓库

        Returns:
            dict[str, Path]: 写入的文件路径字典

        Raises:
            ConfigError: 写入失败时抛出
        """
        written: dict[str, Path] = {}

        try:
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # 1. 写 config.json（Runner 专有字段）
            config_path = workspace_dir / "config.json"
            config_path.write_text(self.generate_config_json(config), encoding="utf-8")
            written["config"] = config_path

            # 2. 写 nanobot_config.json（nanobot 原生格式）
            if nanobot_config:
                nano_path = workspace_dir / "nanobot_config.json"
                nano_path.write_text(
                    json.dumps(nanobot_config, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                written["nanobot_config"] = nano_path

            # 3. 写 .env.local（v0.32.0 后通常为空，仅保留兼容）
            if env_vars:
                env_path = workspace_dir / ".env.local"
                env_path.write_text(self.generate_env_local(env_vars), encoding="utf-8")
                written["env"] = env_path

            # 4. 更新 .gitignore，排除 nanobot_config.json（含敏感凭证）
            self._ensure_gitignore_excludes_nanobot_config(workspace_dir)

            for path in self._copy_template_files(workspace_dir):
                written[path.name] = path

            for path in self._create_memory_files(workspace_dir):
                written[f"memory/{path.name}"] = path

            for path in self._copy_skills_directory(workspace_dir):
                rel_path = path.relative_to(workspace_dir)
                written[str(rel_path)] = path

            if init_git:
                self._init_git_repo(workspace_dir)

            logger.info(f"配置文件已写入: {list(written.keys())}")
            return written

        except OSError as e:
            raise ConfigError(
                f"写入配置文件失败: {e}",
                recovery_suggestion="请检查目录权限和磁盘空间",
            ) from e

    @staticmethod
    def _ensure_gitignore_excludes_nanobot_config(workspace_dir: Path) -> None:
        """确保 .gitignore 排除 nanobot_config.json

        nanobot_config.json 包含 apiKey 等明文敏感凭证，
        必须加入 .gitignore 防止泄露。

        Args:
            workspace_dir: 工作区目录路径
        """
        gitignore_path = workspace_dir / ".gitignore"
        entry = "nanobot_config.json"

        existing_content = ""
        if gitignore_path.exists():
            existing_content = gitignore_path.read_text(encoding="utf-8")

        if entry not in existing_content:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n# 敏感凭证配置，禁止提交\n{entry}\n")
```

同时更新 `_TRACKED_FILES`，移除 `.env.local`（不再包含凭证）：

```python
_TRACKED_FILES = [
    "MEMORY.md",
    "history.jsonl",
    "AGENTS.md",
    "HEARTBEAT.md",
    "SOUL.md",
    "TOOLS.md",
    "USER.md",
    "config.json",
]
```

- [ ] **Step 6: 改造 InitWizard 适配双文件输出**

在 `src/core/init/wizard.py` 的 `run` 方法中，将配置生成部分替换为：

找到 `wizard_result = self.guide_config(...)` 及后续代码块，替换为：

```python
            wizard_result = self.guide_config(
                skip_optional=skip_optional,
                agent_mode=agent_mode,
            )
            runner_config = wizard_result.get("runner_config", {})
            nanobot_config = wizard_result.get("nanobot_config")

            runner_config["data_dir"] = str(target_dir / "data")

            validation = self.validate_config(runner_config)
            if not validation.is_valid:
                return InitResult(
                    success=False,
                    errors=validation.errors,
                    warnings=validation.warnings,
                )

            written = self.config_generator.write_config_files(
                target_dir,
                runner_config,
                nanobot_config=nanobot_config,
            )

            next_steps = [
                "导入数据: nanobotrun data import <FIT文件路径>",
                "查看统计: nanobotrun data stats",
            ]
            if agent_mode and nanobot_config:
                next_steps.append("Agent聊天: nanobotrun agent chat")

            return InitResult(
                success=True,
                config_path=written.get("config"),
                warnings=validation.warnings,
                next_steps=next_steps,
            )
```

同时更新 `validate_config` 方法，移除对 `llm_provider` 的检查：

```python
    def validate_config(self, config: dict[str, Any]) -> ValidationResult:
        """验证配置

        Args:
            config: Runner 专有配置字典

        Returns:
            ValidationResult: 验证结果
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not config.get("version"):
            errors.append("缺少版本号")

        if not config.get("data_dir"):
            errors.append("缺少数据目录配置")

        data_path = Path(config.get("data_dir", ""))
        if data_path.exists() and not data_path.is_dir():
            errors.append(f"数据路径已存在且不是目录: {data_path}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
```

- [ ] **Step 7: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/test_init_prompts.py tests/unit/core/test_init_wizard.py tests/unit/core/test_init_generator.py -v`
Expected: PASS — 可能需要更新旧测试以适配新接口

- [ ] **Step 8: 更新旧测试适配新接口**

更新 `tests/unit/core/test_init_wizard.py` 和 `tests/unit/core/test_init_generator.py` 中引用旧接口的测试：
- 将 `wizard_result.get("config", {})` 改为 `wizard_result.get("runner_config", {})`
- 将 `write_config_files(workspace_dir, config, env_vars)` 调用改为 `write_config_files(workspace_dir, config, nanobot_config=nano_cfg)`

- [ ] **Step 9: 提交**

```bash
git add src/core/init/prompts.py src/core/init/generator.py src/core/init/wizard.py tests/unit/core/test_init_prompts.py tests/unit/core/test_init_generator.py tests/unit/core/test_init_wizard.py
git commit -m "refactor(init): 向导生成 nanobot_config.json + config.json 双文件"
```

---

## Task 10: 迁移命令实现

**Files:**
- Modify: `src/core/init/migrate.py`
- Modify: `src/cli/commands/system.py`
- Test: `tests/unit/core/test_migrate_engine.py`

- [ ] **Step 1: 编写 migrate_config 的失败测试**

在 `tests/unit/core/test_migrate_engine.py` 中追加（如果文件不存在则创建）：

```python
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config.manager import ConfigManager
from src.core.init.migrate import build_nanobot_config_from_legacy


class TestMigrateConfigToNanobot:
    """测试旧版 config.json → nanobot_config.json 迁移"""

    def test_build_nanobot_config_from_legacy_full(self):
        """完整字段映射测试"""
        legacy_config = {
            "version": "0.31.0",
            "data_dir": "/data",
            "timezone": "Asia/Shanghai",
            "llm_provider": "custom",
            "llm_model": "agnes-2.0-flash",
            "llm_base_url": "https://api.test.com/v1",
            "fallback_models": ["nvidia-backup"],
            "model_presets": {
                "nvidia-backup": {
                    "provider": "nvidia",
                    "model": "deepseek-v4-flash",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                }
            },
            "tools": {
                "mcp_servers": {
                    "weather": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@dangahagan/weather-mcp"],
                    }
                }
            },
        }
        env_keys = {"NANOBOT_LLM_API_KEY": "sk-test-key"}

        result = build_nanobot_config_from_legacy(legacy_config, env_keys)

        # 验证 providers
        assert result["providers"]["default"] == "custom"
        assert result["providers"]["custom"]["apiKey"] == "sk-test-key"
        assert result["providers"]["custom"]["apiBase"] == "https://api.test.com/v1"

        # 验证 agents.defaults
        assert result["agents"]["defaults"]["model"] == "agnes-2.0-flash"
        assert result["agents"]["defaults"]["timezone"] == "Asia/Shanghai"
        assert result["agents"]["defaults"]["fallbackModels"] == [
            {"model": "deepseek-v4-flash", "provider": "nvidia"}
        ]

        # 验证 model_presets
        assert "nvidia-backup" in result["model_presets"]

        # 验证 tools.mcpServers
        assert "weather" in result["tools"]["mcpServers"]

    def test_build_nanobot_config_minimal(self):
        """最小配置（无 fallback、无 tools）"""
        legacy_config = {
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
        }
        env_keys = {}

        result = build_nanobot_config_from_legacy(legacy_config, env_keys)

        assert result["providers"]["default"] == "openai"
        assert result["agents"]["defaults"]["model"] == "gpt-4o-mini"

    def test_build_nanobot_config_no_llm(self):
        """无 LLM 配置时返回空 providers"""
        legacy_config = {"version": "0.31.0"}
        result = build_nanobot_config_from_legacy(legacy_config, {})
        assert "providers" in result
        assert result["providers"].get("default", "") == ""
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/test_migrate_engine.py::TestMigrateConfigToNanobot -v`
Expected: FAIL — `build_nanobot_config_from_legacy` 函数不存在

- [ ] **Step 3: 实现 build_nanobot_config_from_legacy()**

在 `src/core/init/migrate.py` 中添加以下函数（在 `ConfigMigrator` 类之前）：

```python
def build_nanobot_config_from_legacy(
    legacy_config: dict[str, Any],
    env_keys: dict[str, str],
) -> dict[str, Any]:
    """将旧版 config.json 的 nanobot 字段迁移为 nanobot_config.json 格式

    独立实现字段映射，不复用 RunnerProviderAdapter 私有方法。
    字段映射参考规格说明书第 3.8 节。

    Args:
        legacy_config: 旧版 config.json 字典
        env_keys: 从 .env.local 读取的环境变量字典

    Returns:
        dict[str, Any]: nanobot 原生格式配置字典
    """
    nanobot_config: dict[str, Any] = {}

    # --- providers ---
    provider_name = legacy_config.get("llm_provider", "")
    providers: dict[str, Any] = {}

    if provider_name:
        providers["default"] = provider_name
        provider_cfg: dict[str, Any] = {
            "apiKey": env_keys.get("NANOBOT_LLM_API_KEY", ""),
            "apiType": "auto",
        }
        base_url = legacy_config.get("llm_base_url")
        if base_url:
            provider_cfg["apiBase"] = base_url
        providers[provider_name] = provider_cfg

    # 备选供应商的 apiKey 和 apiBase
    presets = legacy_config.get("model_presets", {})
    fallback_names = legacy_config.get("fallback_models", [])
    for name in fallback_names:
        preset = presets.get(name, {})
        fb_provider = preset.get("provider", "")
        if not fb_provider or fb_provider in providers:
            continue
        fb_api_key = env_keys.get(f"NANOBOT_LLM_API_KEY_{fb_provider.upper()}", "")
        fb_base_url = preset.get("base_url")
        fb_cfg: dict[str, Any] = {"apiKey": fb_api_key, "apiType": "auto"}
        if fb_base_url:
            fb_cfg["apiBase"] = fb_base_url
        providers[fb_provider] = fb_cfg

    nanobot_config["providers"] = providers

    # --- agents.defaults ---
    agents_defaults: dict[str, Any] = {
        "model": legacy_config.get("llm_model", ""),
        "provider": "auto",
        "timezone": legacy_config.get("timezone", "UTC"),
        "workspace": "~/.nanobot-runner",
        "botName": "nanobot-runner",
        "botIcon": "🍀",
    }

    # fallbackModels
    fb_list: list[dict[str, Any]] = []
    for name in fallback_names:
        preset = presets.get(name, {})
        fb_provider = preset.get("provider", "")
        fb_model = preset.get("model", "")
        if fb_provider and fb_model:
            fb_list.append({"model": fb_model, "provider": fb_provider})
    if fb_list:
        agents_defaults["fallbackModels"] = fb_list

    nanobot_config["agents"] = {"defaults": agents_defaults}

    # --- model_presets ---
    nano_presets: dict[str, Any] = {}
    for name, preset in presets.items():
        if not isinstance(preset, dict):
            continue
        nano_presets[name] = {
            "model": preset.get("model", ""),
            "provider": preset.get("provider", "auto"),
        }
    nanobot_config["model_presets"] = nano_presets

    # --- tools.mcpServers ---
    tools_section = legacy_config.get("tools", {})
    mcp_servers = tools_section.get("mcp_servers", {})
    nanobot_config["tools"] = {"mcpServers": mcp_servers}

    # --- channels（从环境变量迁移飞书凭证）---
    channels: dict[str, Any] = {}
    feishu_app_id = env_keys.get("NANOBOT_FEISHU_APP_ID", "")
    feishu_app_secret = env_keys.get("NANOBOT_FEISHU_APP_SECRET", "")
    if feishu_app_id and feishu_app_secret:
        channels["feishu"] = {
            "enabled": True,
            "app_id": feishu_app_id,
            "app_secret": feishu_app_secret,
            "receive_id": env_keys.get("NANOBOT_FEISHU_RECEIVE_ID", ""),
            "receive_id_type": "user_id",
            "allowFrom": ["*"],
        }
    nanobot_config["channels"] = channels

    return nanobot_config


def migrate_config(
    config_manager: ConfigManager,
    auto: bool = False,
) -> MigrationResult:
    """将旧版 config.json 的 nanobot 字段迁移到 nanobot_config.json

    迁移流程：
    1. 读取旧 config.json
    2. 读取 .env.local 获取 API Key
    3. 构建 nanobot_config.json
    4. 备份旧 config.json 为 config.json.bak
    5. 写入 nanobot_config.json
    6. 精简 config.json（仅保留 Runner 专有字段）
    7. 更新 .gitignore 排除 nanobot_config.json

    Args:
        config_manager: 配置管理器实例
        auto: 是否自动模式（跳过确认）

    Returns:
        MigrationResult: 迁移结果
    """
    import shutil

    from src import __version__

    try:
        legacy_config = config_manager.load_config()
    except Exception as e:
        return MigrationResult(success=False, errors=[f"读取 config.json 失败: {e}"])

    # 检查是否含旧版字段
    has_legacy_fields = any(
        key in legacy_config
        for key in ("llm_provider", "llm_model", "llm_base_url", "fallback_models")
    )
    if not has_legacy_fields:
        return MigrationResult(
            success=False,
            errors=["config.json 不含旧版 nanobot 字段，无需迁移"],
        )

    # 读取 .env.local
    env_keys: dict[str, str] = {}
    env_path = config_manager.base_dir / ".env.local"
    if env_path.exists():
        from src.core.config.env_manager import EnvManager

        env_manager = EnvManager(env_file=env_path)
        env_keys = env_manager.load_env()

    # 构建 nanobot_config.json
    nanobot_config = build_nanobot_config_from_legacy(legacy_config, env_keys)

    # 备份旧 config.json
    config_path = config_manager.config_file
    backup_path = config_path.with_suffix(".json.bak")
    shutil.copy2(config_path, backup_path)
    logger.info(f"已备份旧配置: {backup_path}")

    # 写入 nanobot_config.json
    nano_path = config_manager.get_nanobot_config_path()
    nano_path.write_text(
        json.dumps(nanobot_config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 精简 config.json
    runner_config = {
        "version": __version__,
        "data_dir": legacy_config.get("data_dir", str(config_manager.data_dir)),
        "timezone": legacy_config.get("timezone", "Asia/Shanghai"),
        "auto_push_feishu": legacy_config.get("auto_push_feishu", False),
        "user_id": legacy_config.get("user_id", "default_user"),
    }
    config_manager.save_config(runner_config)

    # 更新 .gitignore
    from src.core.init.generator import ConfigGenerator

    ConfigGenerator._ensure_gitignore_excludes_nanobot_config(config_manager.base_dir)

    migrated_fields = [
        k for k in ("llm_provider", "llm_model", "llm_base_url") if k in legacy_config
    ]

    return MigrationResult(
        success=True,
        migrated_fields=migrated_fields,
        config_path=nano_path,
        warnings=[
            f"旧配置已备份至: {backup_path}",
            "nanobot_config.json 已加入 .gitignore",
        ],
    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/test_migrate_engine.py::TestMigrateConfigToNanobot -v`
Expected: PASS

- [ ] **Step 5: 在 system.py 中注册 migrate-config 命令**

在 `src/cli/commands/system.py` 中追加新命令：

```python
@app.command(name="migrate-config")
def migrate_config_cmd(
    auto: bool = typer.Option(False, "--auto", "-a", help="自动模式，跳过确认"),
) -> None:
    """将旧版 config.json 的 nanobot 字段迁移到 nanobot_config.json

    v0.32.0 配置物理分离迁移工具。将 config.json 中的 llm_provider、
    llm_model、model_presets、tools 等字段迁移到 nanobot_config.json，
    并精简 config.json 为仅含 Runner 专有字段。
    """
    from src.core.config.manager import ConfigManager
    from src.core.init.migrate import migrate_config

    config = ConfigManager(allow_default=True)

    if not auto:
        confirm = typer.confirm(
            "将迁移 config.json 中的 nanobot 字段到 nanobot_config.json，继续？"
        )
        if not confirm:
            console.print("[dim]迁移已取消[/dim]")
            return

    result = migrate_config(config, auto=auto)

    if result.success:
        console.print("\n[bold green]✓ 迁移完成[/bold green]")
        if result.config_path:
            console.print(f"  nanobot 配置: [cyan]{result.config_path}[/cyan]")
        console.print(f"  迁移字段: {', '.join(result.migrated_fields)}")
        for w in result.warnings:
            console.print(f"  [yellow]![/yellow] {w}")
    else:
        console.print("\n[bold red]✗ 迁移失败[/bold red]")
        for err in result.errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(code=1)
```

- [ ] **Step 6: 验证命令注册**

Run: `uv run nanobotrun system migrate-config --help`
Expected: 显示帮助信息，无报错

- [ ] **Step 7: 提交**

```bash
git add src/core/init/migrate.py src/cli/commands/system.py tests/unit/core/test_migrate_engine.py
git commit -m "feat(migrate): 新增 migrate-config 命令，迁移旧版 config.json 到 nanobot_config.json"
```

---

## Task 11: env_manager.py 简化

**Files:**
- Modify: `src/core/config/env_manager.py`

- [ ] **Step 1: 简化 .env.local 模板**

在 `src/core/config/env_manager.py` 中，将 `_ENV_TEMPLATE` 替换为：

```python
_ENV_TEMPLATE = """# Nanobot Runner 环境变量
# v0.32.0: LLM/飞书凭证已迁移至 nanobot_config.json，此文件保留用于自定义环境变量
"""
```

- [ ] **Step 2: 简化 generate_env_local 方法**

在 `src/core/init/generator.py` 中，将 `generate_env_local` 方法简化（凭证已写入 nanobot_config.json，.env.local 通常为空）：

```python
    def generate_env_local(self, env_vars: dict[str, str]) -> str:
        """生成 .env.local 文件内容

        v0.32.0: 凭证已写入 nanobot_config.json，.env.local 仅保留兼容性。

        Args:
            env_vars: 环境变量字典

        Returns:
            str: .env.local 文件内容
        """
        if not env_vars:
            return "# Nanobot Runner 环境变量\n# v0.32.0: 凭证已迁移至 nanobot_config.json\n"

        lines: list[str] = ["# Nanobot Runner 环境变量配置\n"]
        for k, v in env_vars.items():
            lines.append(f"{k}={v}\n")
        return "".join(lines)
```

- [ ] **Step 3: 验证语法正确**

Run: `uv run python -c "from src.core.config.env_manager import EnvManager; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 4: 提交**

```bash
git add src/core/config/env_manager.py src/core/init/generator.py
git commit -m "refactor(env): 简化 .env.local 模板，凭证已迁移至 nanobot_config.json"
```

---

## Task 12: 删除废弃测试 + 集成验证

**Files:**
- Delete: `tests/unit/core/test_config_injector.py`
- Delete: `tests/unit/core/config/test_webui_config.py`
- Delete: `tests/unit/config/test_websocket_config.py`
- Delete: `tests/integration/test_config_injection_flow.py`
- Delete: `tests/integration/module/test_config_injection.py`

- [ ] **Step 1: 删除废弃测试文件**

删除以下测试文件（被测方法/类已删除）：
- `tests/unit/core/config/test_webui_config.py`（`get_webui_config()` 已删除）
- `tests/unit/config/test_websocket_config.py`（`get_websocket_config()` 已删除）

注意：`tests/unit/core/test_config_injector.py` 和 `tests/integration/test_config_injection_flow.py` 已在 Task 3 中删除。如果 `tests/integration/module/test_config_injection.py` 存在且引用 ConfigInjector，也一并删除。

- [ ] **Step 2: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -v --tb=short 2>&1 | head -100`
Expected: 无 ImportError，可能有少量失败需修复

- [ ] **Step 3: 修复因接口变更导致的测试失败**

逐个检查失败的测试，根据新接口更新测试代码。常见修复：
- `config.get_llm_config()` → `config.load_nanobot_config()` + 手动解析
- `config.get_websocket_config()` → `config.load_nanobot_config().get("channels", {}).get("websocket", {})`
- `config.get_webui_config()` → 使用默认值 `{"host": "127.0.0.1", "port": 8766}`
- `adapter._get_or_create_nanobot_config()` → 已删除，移除相关测试
- `adapter.save_nanobot_config()` → 已删除，移除相关测试

- [ ] **Step 4: 运行 lint 检查**

Run: `uv run ruff check src/ tests/ --select F401`
Expected: 无未使用导入（F401）错误。如有，删除对应导入。

- [ ] **Step 5: 运行类型检查**

Run: `uv run mypy src/core/config/manager.py src/core/provider_adapter.py src/cli/commands/gateway.py --ignore-missing-imports`
Expected: 无类型错误

- [ ] **Step 6: 提交**

```bash
git add tests/
git rm tests/unit/core/config/test_webui_config.py tests/unit/config/test_websocket_config.py
git commit -m "test: 删除废弃测试，修复接口变更导致的测试失败"
```

---

## Task 13: 集成测试验证

**Files:**
- Test: 手动验证完整流程

- [ ] **Step 1: 验证迁移命令端到端**

```bash
# 准备旧版配置测试环境
uv run python -c "
import json, os
from pathlib import Path
test_dir = Path.home() / '.nanobot-runner-test'
test_dir.mkdir(exist_ok=True)
config = {
    'version': '0.31.0',
    'data_dir': str(test_dir / 'data'),
    'timezone': 'Asia/Shanghai',
    'llm_provider': 'custom',
    'llm_model': 'test-model',
    'llm_base_url': 'https://api.test.com/v1',
}
(test_dir / 'config.json').write_text(json.dumps(config))
(test_dir / '.env.local').write_text('NANOBOT_LLM_API_KEY=sk-test\n')
print('测试环境已准备')
"

# 运行迁移
NANOBOT_CONFIG_DIR=~/.nanobot-runner-test uv run nanobotrun system migrate-config --auto

# 验证结果
uv run python -c "
import json
from pathlib import Path
test_dir = Path.home() / '.nanobot-runner-test'
nano = json.loads((test_dir / 'nanobot_config.json').read_text())
cfg = json.loads((test_dir / 'config.json').read_text())
print('nanobot_config.json providers:', nano.get('providers', {}).get('default'))
print('config.json fields:', list(cfg.keys()))
assert 'llm_provider' not in cfg, 'config.json 不应含 llm_provider'
assert nano['providers']['custom']['apiKey'] == 'sk-test'
print('迁移验证通过')
"

# 清理
rm -rf ~/.nanobot-runner-test
```

- [ ] **Step 2: 验证 .gitignore 包含 nanobot_config.json**

```bash
uv run python -c "
from pathlib import Path
from src.core.init.generator import ConfigGenerator
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp)
    ConfigGenerator._ensure_gitignore_excludes_nanobot_config(p)
    content = (p / '.gitignore').read_text()
    assert 'nanobot_config.json' in content
    print('.gitignore 验证通过')
"
```

- [ ] **Step 3: 验证 gateway 启动不崩溃（无 LLM 场景）**

```bash
# 确保 nanobot_config.json 不存在时 gateway 提示配置缺失
NANOBOT_CONFIG_DIR=/tmp/test-no-config uv run nanobotrun gateway start 2>&1 | head -5
# Expected: 提示 LLM 配置缺失
```

- [ ] **Step 4: 提交最终状态**

```bash
git add -A
git commit -m "test: 集成验证配置物理分离完整流程"
```

---

## Task 14: 向后兼容警告与 init 旧版检测

**Files:**
- Modify: `src/core/config/manager.py`
- Modify: `src/core/init/wizard.py`
- Test: `tests/unit/core/config/test_manager.py`

**覆盖规格：** 第 7.1 节（init 检测旧版 config.json 提示迁移）、第 7.3 节（config.json 含旧字段打印 warning）

- [ ] **Step 1: 编写旧字段 warning 的失败测试**

在 `tests/unit/core/config/test_manager.py` 中追加：

```python
class TestLegacyFieldsWarning:
    """测试旧版 config.json 字段检测（规格 7.3 向后兼容）"""

    def test_check_legacy_fields_returns_list(self, tmp_path, caplog):
        """config.json 含 llm_provider 等旧字段时返回字段列表"""
        config_data = {
            "version": "0.32.0",
            "data_dir": str(tmp_path / "data"),
            "llm_provider": "openai",
            "llm_model": "gpt-4o-mini",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            legacy = cm.check_legacy_fields()

        assert "llm_provider" in legacy
        assert "llm_model" in legacy

    def test_check_legacy_fields_empty_when_clean(self, tmp_path):
        """config.json 无旧字段时返回空列表"""
        config_data = {
            "version": "0.32.0",
            "data_dir": str(tmp_path / "data"),
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            cm = ConfigManager(allow_default=True)
            assert cm.check_legacy_fields() == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/config/test_manager.py::TestLegacyFieldsWarning -v`
Expected: FAIL — `check_legacy_fields` 方法不存在

- [ ] **Step 3: 在 ConfigManager 新增 check_legacy_fields 方法**

在 `src/core/config/manager.py` 的 `load_nanobot_config` 方法之后添加：

```python
    # 旧版 config.json 中需提示迁移的字段（规格 7.3 向后兼容）
    _LEGACY_NANOBOT_FIELDS: ClassVar[list[str]] = [
        "llm_provider",
        "llm_model",
        "llm_base_url",
        "fallback_models",
        "model_presets",
    ]

    def check_legacy_fields(self) -> list[str]:
        """检测 config.json 是否含旧版 nanobot 字段

        迁移完成后 config.json 不应含这些字段。若存在则打印 warning
        并返回字段名列表，供调用方提示用户运行 migrate-config。

        Returns:
            list[str]: 存在的旧版字段名列表
        """
        config = self.load_config()
        found = [f for f in self._LEGACY_NANOBOT_FIELDS if f in config]
        if found:
            logger.warning(
                "检测到 config.json 含旧版 nanobot 字段 %s，"
                "建议运行 'nanobotrun system migrate-config' 迁移",
                found,
            )
        return found
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/config/test_manager.py::TestLegacyFieldsWarning -v`
Expected: PASS

- [ ] **Step 5: 在 InitWizard.run() 开头加旧版检测（规格 7.1）**

在 `src/core/init/wizard.py` 的 `run` 方法开头（环境检测之后、配置生成之前）插入旧版检测块：

```python
            # 规格 7.1: 检测旧版 config.json，提示迁移
            existing_config_path = target_dir / "config.json"
            if existing_config_path.exists():
                import json as _json

                try:
                    existing = _json.loads(
                        existing_config_path.read_text(encoding="utf-8")
                    )
                except (json.JSONDecodeError, OSError):
                    existing = {}

                has_legacy = any(
                    k in existing
                    for k in ("llm_provider", "llm_model", "llm_base_url")
                )
                nano_path = target_dir / "nanobot_config.json"

                if has_legacy and not nano_path.exists():
                    console.print(
                        "[yellow]检测到旧版配置格式（config.json 含 llm_provider 字段）。[/yellow]"
                    )
                    console.print(
                        "建议先运行 [cyan]nanobotrun system migrate-config[/cyan] 迁移到 nanobot_config.json。"
                    )
                    if not typer.confirm("是否跳过迁移继续初始化？", default=False):
                        return InitResult(
                            success=False,
                            errors=["请先运行 nanobotrun system migrate-config 完成迁移"],
                        )
```

> 注：需在 `wizard.py` 顶部确保已导入 `typer` 和 `console`（若未导入则补充 `import typer` 和 `from rich.console import Console; console = Console()`）。

- [ ] **Step 6: 验证语法正确**

Run: `uv run python -c "from src.core.init.wizard import InitWizard; print('OK')"`
Expected: 输出 `OK`

- [ ] **Step 7: 提交**

```bash
git add src/core/config/manager.py src/core/init/wizard.py tests/unit/core/config/test_manager.py
git commit -m "feat(compat): 旧版 config.json 字段检测警告 + init 旧版迁移提示"
```

---

## 验收清单

- [ ] `config.json` 仅含 `version`、`data_dir`、`timezone`、`auto_push_feishu`、`user_id`
- [ ] `nanobot_config.json` 包含 `providers`、`agents`、`channels`、`model_presets`、`tools`
- [ ] `nanobot_config.json` 已加入 `.gitignore`
- [ ] `ConfigInjector` 类已删除
- [ ] `RunnerProviderAdapter` 不再含转换方法，直接从 nanobot_config.json 读取
- [ ] `gateway start` 直接 `set_config_path(nanobot_config.json)`，不调用 `save_nanobot_config()`
- [ ] `ChannelManager` 从 `nanobot_config.json` 加载 Config 对象
- [ ] MCP 配置从 `nanobot_config.json` 的 `tools.mcpServers` 读取
- [ ] `nanobotrun system migrate-config` 命令可用
- [ ] 初始化向导同时生成 `config.json` 和 `nanobot_config.json`
- [ ] 所有单元测试通过
- [ ] `ruff check` 无 F401 错误

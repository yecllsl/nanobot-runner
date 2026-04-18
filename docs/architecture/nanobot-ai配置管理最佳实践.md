# nanobot-ai 官方配置管理最佳实践

> **文档版本**: v1.0.0  
> **调研日期**: 2026-04-17  
> **调研对象**: HKUDS/nanobot-ai 官方项目配置管理机制  
> **调研目标**: 总结nanobot-ai官方配置管理最佳实践，指导当前项目配置合并方案

---

## 1. 执行摘要

nanobot-ai官方提供了完善的配置管理机制，基于**Pydantic-Settings**构建，支持类型安全、环境变量覆盖、多优先级配置加载。本文档总结了官方推荐的配置管理最佳实践，并分析了与当前项目配置合并方案的适配性。

**核心发现**：
- ✅ **配置格式**：JSON（主配置） + Markdown（Agent配置）
- ✅ **配置管理**：基于Pydantic-Settings，支持类型安全、环境变量覆盖
- ✅ **敏感信息**：推荐环境变量管理，禁止硬编码
- ✅ **配置加载**：支持多优先级（环境变量 > 配置文件 > 默认值）
- ✅ **SDK模式**：支持直接实例化、配置文件加载、环境变量驱动

---

## 2. 配置文件结构

### 2.1 主配置文件（`~/.nanobot/config.json`）

nanobot-ai采用JSON格式作为主配置文件，包含以下核心配置项：

```json
{
  "providers": {
    "openai": {
      "apiKey": "sk-xxxxxxxx",
      "baseUrl": "https://api.openai.com/v1"
    },
    "anthropic": {
      "apiKey": "sk-ant-xxxxxxxx",
      "baseUrl": "https://api.anthropic.com"
    }
  },
  "channels": {
    "cli": {
      "enabled": true
    },
    "telegram": {
      "enabled": false,
      "token": "your-telegram-token"
    }
  },
  "agents": {
    "defaults": {
      "workspace": "~/.nanobot-runner",
      "model": "gpt-4",
      "temperature": 0.7
    }
  },
  "tools": {
    "allowedCommands": ["ls", "cat", "grep"],
    "workspaceRestrictions": {
      "readOnly": ["/etc"],
      "readWrite": ["~/.nanobot-runner"]
    }
  },
  "memory": {
    "maxHistoryItems": 100,
    "tokenLimit": 4000
  }
}
```

**配置项说明**：

| 配置项 | 说明 | 必填 | 默认值 |
|--------|------|------|--------|
| `providers` | LLM提供商配置（API密钥、Base URL等） | ✅ | - |
| `channels` | 通道配置（CLI、Telegram、Discord等） | ❌ | `{}` |
| `agents` | Agent默认配置（workspace、model等） | ✅ | - |
| `tools` | 工具行为配置（命令白名单、工作区限制） | ❌ | `{}` |
| `memory` | 记忆系统配置（历史记录条数、token限制） | ❌ | `{}` |

### 2.2 Workspace配置文件

nanobot-ai支持Markdown格式的Agent配置文件，位于workspace目录：

```
workspace/
├── AGENTS.md        # Agent行为准则
├── SOUL.md          # 人格设定
├── USER.md          # 用户画像
├── IDENTITY.md      # 身份标识
├── CAPABILITIES.md  # 能力说明
├── POLICY.md        # 策略规则
└── REPUTATION.md    # 信誉记录
```

**配置文件用途**：

| 文件 | 用途 | 必填 | 说明 |
|------|------|------|------|
| `AGENTS.md` | 子Agent行为说明、协作规则 | ❌ | 定义Agent的工作方式和行为规范 |
| `SOUL.md` | 角色个性、语气风格定义 | ❌ | 定义Agent的性格和交互风格 |
| `USER.md` | 用户画像、偏好设置 | ❌ | 存储用户的基本信息和偏好 |
| `IDENTITY.md` | Agent名称、标识 | ❌ | 定义Agent的身份标识 |
| `CAPABILITIES.md` | Agent能力说明 | ❌ | 描述Agent的能力范围 |
| `POLICY.md` | 策略规则、约束条件 | ❌ | 定义Agent的行为约束 |
| `REPUTATION.md` | 信誉记录、历史表现 | ❌ | 记录Agent的历史表现 |

**System Prompt组装顺序**：
```
AGENTS.md → SOUL.md → USER.md → IDENTITY.md → CAPABILITIES.md → POLICY.md → REPUTATION.md
```

---

## 3. 配置格式选择

### 3.1 JSON vs YAML vs INI

nanobot-ai官方选择JSON格式的原因：

| 格式 | 优点 | 缺点 | nanobot-ai选择 |
|------|------|------|---------------|
| **JSON** | ✅ 原生支持、类型明确、工具丰富 | ❌ 不支持注释、语法严格 | ✅ **官方选择** |
| **YAML** | ✅ 支持注释、可读性好 | ❌ 解析复杂、缩进敏感 | ❌ 未采用 |
| **INI** | ✅ 简单直观 | ❌ 不支持嵌套、类型不明确 | ❌ 未采用 |

**官方推荐JSON格式的原因**：
1. **Python原生支持**：使用`json`模块，无需额外依赖
2. **与Pydantic完美集成**：Pydantic原生支持JSON Schema验证
3. **类型安全**：JSON类型明确，支持Schema验证
4. **工具链成熟**：IDE支持、格式化工具、验证工具丰富

### 3.2 Markdown格式

Agent配置文件使用Markdown格式，原因：
- **可读性强**：便于人类编辑和维护
- **支持富文本格式**：标题、列表、代码块等
- **与LLM交互友好**：直接作为System Prompt使用

---

## 4. 环境特定配置管理

### 4.1 环境变量覆盖机制

nanobot-ai支持通过环境变量覆盖配置文件，优先级为：

**环境变量 > 配置文件 > 默认值**

#### 4.1.1 环境变量命名规范

- **前缀**：`NANOBOT_`
- **命名风格**：支持camelCase和snake_case
- **嵌套分隔符**：`_`（下划线）

**示例**：
```bash
# camelCase风格
NANOBOT_PROVIDERS_OPENAI_APIKEY=sk-xxxx
NANOBOT_AGENTS_DEFAULTS_WORKSPACE=~/.nanobot-runner

# snake_case风格
NANOBOT_PROVIDERS_OPENAI_API_KEY=sk-xxxx
NANOBOT_AGENTS_DEFAULTS_WORKSPACE=~/.nanobot-runner
```

**映射规则**：
```
NANOBOT_PROVIDERS_OPENAI_APIKEY → providers.openai.apiKey
NANOBOT_AGENTS_DEFAULTS_MODEL → agents.defaults.model
```

#### 4.1.2 实现机制（基于pydantic-settings）

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Config(BaseSettings):
    """nanobot-ai配置Schema"""
    
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    
    class Config:
        env_prefix = "NANOBOT_"
        env_nested_delimiter = "_"
        case_sensitive = False
```

**关键特性**：
- ✅ 自动解析嵌套配置（通过`env_nested_delimiter`）
- ✅ 支持camelCase和snake_case（通过`case_sensitive=False`）
- ✅ 环境变量优先级最高（通过pydantic-settings默认行为）

### 4.2 多环境配置策略

#### 4.2.1 环境变量驱动（推荐）

```bash
# 开发环境
export NANOBOT_AGENTS_DEFAULTS_WORKSPACE="~/.nanobot-runner-dev"
export NANOBOT_PROVIDERS_OPENAI_APIKEY="sk-dev-xxxx"

# 测试环境
export NANOBOT_AGENTS_DEFAULTS_WORKSPACE="~/.nanobot-runner-test"
export NANOBOT_PROVIDERS_OPENAI_APIKEY="sk-test-xxxx"

# 生产环境
export NANOBOT_AGENTS_DEFAULTS_WORKSPACE="~/.nanobot-runner-prod"
export NANOBOT_PROVIDERS_OPENAI_APIKEY="sk-prod-xxxx"
```

#### 4.2.2 配置文件分离

```
~/.nanobot/
├── config.json           # 主配置文件
├── config.dev.json       # 开发环境配置
├── config.test.json      # 测试环境配置
└── config.prod.json      # 生产环境配置
```

**加载逻辑**：
```python
import os
from pathlib import Path

def load_config_by_env() -> Config:
    """根据环境加载配置"""
    env = os.environ.get("NANOBOT_ENV", "dev")
    config_file = Path.home() / ".nanobot" / f"config.{env}.json"
    
    if config_file.exists():
        return load_config(config_file)
    else:
        return load_config(Path.home() / ".nanobot" / "config.json")
```

---

## 5. 敏感信息处理

### 5.1 官方推荐方案

#### 5.1.1 方案1：环境变量（推荐）

```bash
# .env.local（不纳入Git）
NANOBOT_PROVIDERS_OPENAI_APIKEY=sk-xxxxxxxx
NANOBOT_PROVIDERS_ANTHROPIC_APIKEY=sk-ant-xxxxxxxx
NANOBOT_CHANNELS_TELEGRAM_TOKEN=your-telegram-token
```

**优点**：
- ✅ 敏感信息不进入代码仓库
- ✅ 支持环境隔离
- ✅ 符合12-Factor App原则

#### 5.1.2 方案2：配置文件模板

```json
// config.example.json（纳入Git）
{
  "providers": {
    "openai": {
      "apiKey": "${OPENAI_API_KEY}",
      "baseUrl": "https://api.openai.com/v1"
    }
  }
}
```

**加载逻辑**：
```python
import os
import json
from pathlib import Path

def load_config_with_template(config_path: Path) -> dict:
    """加载配置文件并替换占位符"""
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 替换环境变量占位符
    for key, value in os.environ.items():
        placeholder = f"${{{key}}}"
        content = content.replace(placeholder, value)
    
    return json.loads(content)
```

#### 5.1.3 方案3：密钥管理服务（生产环境）

```python
# 从AWS Secrets Manager或HashiCorp Vault加载密钥
import boto3

def load_api_key_from_secrets_manager() -> str:
    """从AWS Secrets Manager加载API密钥"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='nanobot/openai-api-key')
    return response['SecretString']
```

### 5.2 安全最佳实践

#### 5.2.1 禁止硬编码密钥

```python
# ❌ 错误做法
api_key = "sk-xxxxxxxx"

# ✅ 正确做法
api_key = os.environ.get("NANOBOT_PROVIDERS_OPENAI_APIKEY")
```

#### 5.2.2 使用`.gitignore`排除敏感文件

```gitignore
# 环境变量文件
.env.local
.env.*.local

# 配置文件（包含密钥）
config.json
config.*.json
```

#### 5.2.3 配置文件权限控制

```bash
# 设置配置文件权限（仅所有者可读写）
chmod 600 ~/.nanobot/config.json
```

---

## 6. 配置加载机制

### 6.1 Pydantic-Settings集成

nanobot-ai使用Pydantic-Settings进行配置管理，核心特性：

```python
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Config(BaseSettings):
    """nanobot-ai配置Schema"""
    
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    
    class Config:
        env_prefix = "NANOBOT_"
        env_nested_delimiter = "_"
        case_sensitive = False
    
    @validator("providers")
    def validate_providers(cls, v):
        """验证providers配置"""
        if not v:
            raise ValueError("至少需要配置一个LLM提供商")
        return v
```

**关键特性**：
- ✅ **类型安全**：基于Pydantic，支持类型注解和验证
- ✅ **环境变量覆盖**：自动从环境变量加载配置
- ✅ **嵌套配置**：支持嵌套配置结构
- ✅ **验证机制**：支持自定义验证器

### 6.2 配置加载流程

```python
from pathlib import Path
import json
from nanobot.config.schema import Config

def load_config(config_path: Path = None) -> Config:
    """加载配置文件
    
    优先级：
    1. 环境变量（NANOBOT_*）
    2. 配置文件（~/.nanobot/config.json）
    3. 默认值
    """
    # 默认配置路径
    if config_path is None:
        config_path = Path.home() / ".nanobot" / "config.json"
    
    # 加载配置文件
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    
    # 创建配置实例（自动应用环境变量覆盖）
    config = Config(**data)
    
    return config
```

### 6.3 配置验证机制

```python
from pydantic import BaseModel, validator

class ProvidersConfig(BaseModel):
    """LLM提供商配置"""
    
    openai: OpenAIConfig | None = None
    anthropic: AnthropicConfig | None = None
    
    @validator("*")
    def validate_at_least_one_provider(cls, v, values):
        """验证至少配置一个提供商"""
        if not any(values.values()):
            raise ValueError("至少需要配置一个LLM提供商")
        return v

class OpenAIConfig(BaseModel):
    """OpenAI配置"""
    
    apiKey: str
    baseUrl: str = "https://api.openai.com/v1"
    
    @validator("apiKey")
    def validate_api_key(cls, v):
        """验证API密钥格式"""
        if not v.startswith("sk-"):
            raise ValueError("OpenAI API密钥应以'sk-'开头")
        return v
```

---

## 7. SDK特定的配置模式

### 7.1 作为Python SDK使用

当nanobot-ai作为Python SDK使用时，官方推荐以下配置模式：

#### 7.1.1 模式1：直接实例化配置

```python
from nanobot import Agent, Config
from nanobot.config.schema import ProvidersConfig, OpenAIConfig

# 直接创建配置实例
config = Config(
    providers=ProvidersConfig(
        openai=OpenAIConfig(
            apiKey=os.environ["OPENAI_API_KEY"],
            baseUrl="https://api.openai.com/v1"
        )
    ),
    agents=AgentsConfig(
        defaults=AgentDefaultsConfig(
            workspace="./workspace",
            model="gpt-4"
        )
    )
)

# 创建Agent实例
agent = Agent(config=config)
```

**适用场景**：
- ✅ 需要精细控制配置的场景
- ✅ 动态生成配置的场景
- ✅ 测试环境

#### 7.1.2 模式2：从配置文件加载

```python
from nanobot import Agent
from nanobot.config import load_config

# 从配置文件加载
config = load_config(Path("./config.json"))

# 创建Agent实例
agent = Agent(config=config)
```

**适用场景**：
- ✅ 生产环境
- ✅ 需要配置文件管理的场景

#### 7.1.3 模式3：环境变量驱动

```python
import os
from nanobot import Agent

# 设置环境变量
os.environ["NANOBOT_PROVIDERS_OPENAI_APIKEY"] = "sk-xxxx"
os.environ["NANOBOT_AGENTS_DEFAULTS_WORKSPACE"] = "./workspace"

# 创建Agent实例（自动从环境变量加载配置）
agent = Agent()
```

**适用场景**：
- ✅ 容器化部署
- ✅ CI/CD环境
- ✅ 敏感信息管理

### 7.2 配置继承与覆盖

```python
from nanobot.config.schema import Config

# 加载基础配置
base_config = load_config(Path("~/.nanobot/config.json"))

# 创建派生配置（覆盖特定字段）
derived_config = Config(
    **base_config.dict(),
    agents=AgentsConfig(
        defaults=AgentDefaultsConfig(
            **base_config.agents.defaults.dict(),
            workspace="./custom-workspace",  # 覆盖workspace
            model="gpt-4-turbo"              # 覆盖model
        )
    )
)
```

---

## 8. 官方提供的配置工具

### 8.1 配置Schema定义

nanobot-ai提供了完整的配置Schema定义（基于Pydantic）：

```python
# nanobot/config/schema.py

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from pydantic.alias_generators import to_camel

class Base(BaseModel):
    """基础模型，支持camelCase和snake_case"""
    
    class Config:
        alias_generator = to_camel
        populate_by_name = True

class Config(BaseSettings):
    """nanobot-ai主配置"""
    
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    
    class Config:
        env_prefix = "NANOBOT_"
        env_nested_delimiter = "_"
```

**关键特性**：
- ✅ **命名风格支持**：支持camelCase和snake_case
- ✅ **类型安全**：基于Pydantic，支持类型注解
- ✅ **环境变量集成**：基于pydantic-settings

### 8.2 配置验证工具

```python
from nanobot.config.schema import Config

def validate_config(config_path: Path) -> tuple[bool, list[str]]:
    """验证配置文件
    
    Returns:
        tuple[bool, list[str]]: (是否验证通过, 错误消息列表)
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 使用Pydantic验证
        Config(**data)
        return True, []
    except Exception as e:
        return False, [str(e)]
```

---

## 9. 最佳实践总结

### 9.1 配置管理原则

1. **类型安全**：使用Pydantic进行Schema验证
2. **环境变量优先**：敏感信息通过环境变量管理
3. **配置分层**：基础配置 → 环境配置 → 环境变量覆盖
4. **启动验证**：应用启动时验证配置完整性
5. **配置文档**：每个配置项都有注释和默认值

### 9.2 推荐目录结构

```
project/
├── .env.example              # 环境变量模板
├── .env.local                # 本地环境变量（不纳入Git）
├── config.example.json       # 配置文件模板
├── config.json               # 实际配置文件（不纳入Git）
├── workspace/                # Workspace目录
│   ├── AGENTS.md
│   ├── SOUL.md
│   ├── USER.md
│   ├── data/
│   └── memory/
└── scripts/
    ├── validate_config.py    # 配置验证脚本
    └── migrate_config.py     # 配置迁移脚本
```

### 9.3 配置加载最佳实践

```python
from pathlib import Path
from nanobot.config.schema import Config

def load_config_with_fallback() -> Config:
    """加载配置（带回退机制）"""
    
    # 优先级1：环境变量
    if os.environ.get("NANOBOT_CONFIG_PATH"):
        config_path = Path(os.environ["NANOBOT_CONFIG_PATH"])
    # 优先级2：项目目录
    elif Path("./config.json").exists():
        config_path = Path("./config.json")
    # 优先级3：全局配置
    elif Path.home().joinpath(".nanobot/config.json").exists():
        config_path = Path.home() / ".nanobot" / "config.json"
    else:
        # 使用默认配置
        return Config()
    
    # 加载配置文件
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 创建配置实例（自动应用环境变量覆盖）
    return Config(**data)
```

---

## 10. 与当前项目的适配建议

### 10.1 配置文件结构适配

**推荐结构**：

```
<project_root>/
├── .env.example              # 环境变量模板
├── .env.local                # 本地环境变量
├── config.example.json       # 配置文件模板
├── nanobot-runner/           # Workspace目录
│   ├── config.json           # 业务配置
│   ├── AGENTS.md             # Agent配置
│   ├── SOUL.md               # 人格配置
│   ├── USER.md               # 用户画像
│   ├── data/                 # 数据目录
│   └── memory/               # 记忆系统
└── .nanobot/                 # 框架配置（可选）
    └── config.json           # LLM Provider配置
```

### 10.2 配置加载机制适配

```python
# src/core/config.py

from pathlib import Path
from nanobot.config.schema import Config

class ConfigManager:
    """配置管理器（适配nanobot-ai最佳实践）"""
    
    def __init__(self) -> None:
        # 优先级：环境变量 > 项目配置 > 全局配置
        self.base_dir = self._resolve_config_dir()
        self.config_file = self.base_dir / "config.json"
    
    def _resolve_config_dir(self) -> Path:
        """解析配置目录（支持多优先级）"""
        # 优先级1：环境变量
        if os.environ.get("NANOBOT_CONFIG_DIR"):
            return Path(os.environ["NANOBOT_CONFIG_DIR"])
        
        # 优先级2：项目目录
        project_config = Path.cwd() / "nanobot-runner"
        if project_config.exists():
            return project_config
        
        # 优先级3：全局配置（兼容旧架构）
        return Path.home() / ".nanobot-runner"
```

### 10.3 环境变量管理适配

```bash
# .env.example

# nanobot-ai框架配置
NANOBOT_PROVIDERS_OPENAI_APIKEY=sk-xxxx
NANOBOT_AGENTS_DEFAULTS_MODEL=gpt-4

# 业务配置
NANOBOT_CONFIG_DIR=./nanobot-runner
NANOBOT_DATA_DIR=./nanobot-runner/data
NANOBOT_TIMEZONE=Asia/Shanghai

# 飞书配置
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 11. 参考资源

- [nanobot-ai GitHub仓库](https://github.com/HKUDS/nanobot)
- [nanobot-ai配置Schema源码](https://github.com/HKUDS/nanobot/blob/main/nanobot/config/schema.py)
- [Pydantic-Settings官方文档](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [12-Factor App配置管理](https://12factor.net/config)

---

**文档版本**: v1.0.0  
**最后更新**: 2026-04-17  
**作者**: 架构师智能体  
**审核状态**: 待评审

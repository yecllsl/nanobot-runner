# 配置迁移指南

## 概述

本文档提供 Nanobot Runner 项目中配置迁移的完整指南，包括版本间配置升级、配置格式转换和迁移验证。

## 配置版本历史

| 版本 | 配置变更 | 迁移需求 |
|------|----------|----------|
| v0.4.0 | 初始配置格式 | 基础配置 |
| v0.4.1 | 添加飞书配置字段 | 自动迁移 |
| v0.4.2 | 添加调试配置字段 | 自动迁移 |
| v0.5.0 | 配置Schema重构 | 手动迁移 |

## 迁移架构

```
┌─────────────────────────────────────────────────────────────┐
│                    配置迁移流程                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   检测版本    │ -> │   执行迁移    │ -> │   验证结果    │  │
│  │  (读取配置)   │    │  (转换数据)   │    │  (检查完整)   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                      错误处理                          │ │
│  │  • 版本未知 -> 使用默认配置                             │ │
│  │  • 迁移失败 -> 备份原配置 + 告警                        │ │
│  │  • 验证失败 -> 回滚迁移                                 │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 配置迁移实现

### 1. 迁移管理器

```python
# src/core/config_migration.py
"""配置迁移管理器

管理配置版本间的自动迁移。
"""

import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    """迁移记录"""
    migration_id: str
    source_version: str
    target_version: str
    status: str  # pending, in_progress, completed, failed, rolled_back
    timestamp: str
    backup_path: Optional[str] = None
    error: Optional[str] = None


class ConfigMigrationManager:
    """配置迁移管理器
    
    职责：
    1. 检测配置版本
    2. 执行版本迁移
    3. 记录迁移历史
    4. 支持迁移回滚
    """
    
    def __init__(self, status_file: Optional[Path] = None):
        self.status_file = status_file or (
            Path.home() / ".nanobot-runner" / "migration_status.json"
        )
        self._records: dict[str, MigrationRecord] = {}
        self._load_records()
    
    def _load_records(self):
        """加载迁移记录"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._records = {
                        k: MigrationRecord(**v) for k, v in data.items()
                    }
            except Exception as e:
                logger.warning(f"加载迁移记录失败: {e}")
                self._records = {}
    
    def _save_records(self):
        """保存迁移记录"""
        try:
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {k: asdict(v) for k, v in self._records.items()},
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"保存迁移记录失败: {e}")
    
    def detect_version(self, config: dict[str, Any]) -> str:
        """检测配置版本
        
        Args:
            config: 配置字典
            
        Returns:
            str: 版本号（如 "0.4.0"）
        """
        version = config.get("version", "0.4.0")
        
        # 根据配置字段推断版本
        if "feishu_receive_id_type" in config:
            return "0.4.1"
        elif "debug_mode" in config:
            return "0.4.2"
        
        return version
    
    def migrate(
        self,
        config: dict[str, Any],
        target_version: str = "0.4.2"
    ) -> tuple[bool, dict[str, Any], list[str]]:
        """执行配置迁移
        
        Args:
            config: 当前配置
            target_version: 目标版本
            
        Returns:
            tuple[bool, dict, list]: (是否成功, 新配置, 警告信息)
        """
        source_version = self.detect_version(config)
        migration_id = f"{source_version}_to_{target_version}"
        warnings = []
        
        # 检查是否已迁移
        if self.is_migrated(migration_id):
            logger.info(f"迁移已完成，跳过: {migration_id}")
            return True, config, []
        
        # 检查版本是否需要迁移
        if source_version == target_version:
            return True, config, []
        
        # 记录迁移开始
        self._record_migration(migration_id, source_version, target_version, "in_progress")
        
        try:
            # 备份原配置
            backup_path = self._backup_config(config, source_version)
            
            # 执行迁移转换
            new_config = self._transform_config(config, source_version, target_version)
            
            # 验证迁移结果
            if not self._verify_migration(config, new_config):
                raise ValueError("迁移结果验证失败")
            
            # 记录迁移完成
            self._record_migration(
                migration_id, 
                source_version, 
                target_version, 
                "completed",
                backup_path=str(backup_path) if backup_path else None
            )
            
            logger.info(f"配置迁移成功: {source_version} -> {target_version}")
            return True, new_config, warnings
            
        except Exception as e:
            # 记录迁移失败
            self._record_migration(
                migration_id, 
                source_version, 
                target_version, 
                "failed",
                error=str(e)
            )
            logger.error(f"配置迁移失败: {e}")
            return False, config, [str(e)]
    
    def _transform_config(
        self, 
        config: dict[str, Any], 
        source_version: str,
        target_version: str
    ) -> dict[str, Any]:
        """转换配置
        
        依次应用从source_version到target_version的所有转换。
        """
        new_config = config.copy()
        
        # 定义版本转换链
        transforms = [
            ("0.4.0", "0.4.1", self._v040_to_v041),
            ("0.4.1", "0.4.2", self._v041_to_v042),
        ]
        
        for from_ver, to_ver, transform_func in transforms:
            if source_version <= from_ver and to_ver <= target_version:
                logger.debug(f"应用迁移: {from_ver} -> {to_ver}")
                new_config = transform_func(new_config)
        
        return new_config
    
    def _v040_to_v041(self, config: dict[str, Any]) -> dict[str, Any]:
        """v0.4.0 到 v0.4.1 的迁移
        
        变更：
        - 添加 feishu_receive_id_type 字段
        - 更新版本号
        """
        if "feishu_receive_id_type" not in config:
            config["feishu_receive_id_type"] = "user_id"
        
        config["version"] = "0.4.1"
        return config
    
    def _v041_to_v042(self, config: dict[str, Any]) -> dict[str, Any]:
        """v0.4.1 到 v0.4.2 的迁移
        
        变更：
        - 添加 debug_mode 字段
        - 添加 log_level 字段
        - 更新版本号
        """
        if "debug_mode" not in config:
            config["debug_mode"] = False
        
        if "log_level" not in config:
            config["log_level"] = "INFO"
        
        config["version"] = "0.4.2"
        return config
    
    def _backup_config(
        self, 
        config: dict[str, Any], 
        version: str
    ) -> Optional[Path]:
        """备份配置"""
        try:
            backup_dir = Path.home() / ".nanobot-runner" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"config_v{version}_{timestamp}.json"
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已备份: {backup_path}")
            return backup_path
        except Exception as e:
            logger.warning(f"配置备份失败: {e}")
            return None
    
    def _verify_migration(
        self, 
        old_config: dict[str, Any], 
        new_config: dict[str, Any]
    ) -> bool:
        """验证迁移结果"""
        # 基本验证
        if not new_config:
            return False
        
        # 验证版本号已更新
        if "version" not in new_config:
            return False
        
        # 验证原有数据未丢失
        for key in old_config:
            if key not in new_config and key != "version":
                logger.warning(f"迁移可能丢失数据: {key}")
        
        return True
    
    def _record_migration(
        self,
        migration_id: str,
        source_version: str,
        target_version: str,
        status: str,
        backup_path: Optional[str] = None,
        error: Optional[str] = None
    ):
        """记录迁移状态"""
        self._records[migration_id] = MigrationRecord(
            migration_id=migration_id,
            source_version=source_version,
            target_version=target_version,
            status=status,
            timestamp=datetime.now().isoformat(),
            backup_path=backup_path,
            error=error
        )
        self._save_records()
    
    def is_migrated(self, migration_id: str) -> bool:
        """检查是否已完成迁移"""
        record = self._records.get(migration_id)
        return record is not None and record.status == "completed"
    
    def rollback(self, migration_id: str) -> bool:
        """回滚迁移
        
        Args:
            migration_id: 迁移ID
            
        Returns:
            bool: 回滚是否成功
        """
        record = self._records.get(migration_id)
        if not record:
            logger.warning(f"未找到迁移记录: {migration_id}")
            return False
        
        if not record.backup_path:
            logger.error(f"迁移记录中没有备份路径: {migration_id}")
            return False
        
        backup_path = Path(record.backup_path)
        if not backup_path.exists():
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        try:
            # 恢复备份
            config_path = Path.home() / ".nanobot-runner" / "config.json"
            shutil.copy2(backup_path, config_path)
            
            # 更新记录状态
            record.status = "rolled_back"
            record.timestamp = datetime.now().isoformat()
            self._save_records()
            
            logger.info(f"迁移已回滚: {migration_id}")
            return True
        except Exception as e:
            logger.error(f"回滚失败: {e}")
            return False
    
    def get_migration_history(self) -> list[MigrationRecord]:
        """获取迁移历史"""
        return sorted(
            self._records.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
```

### 2. 配置管理器集成

```python
# src/core/config_manager.py（迁移相关部分）
"""配置管理器 - 迁移集成"""

import json
import logging
from pathlib import Path
from typing import Optional, Any

from .config_schema import AppConfig
from .config_migration import ConfigMigrationManager

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器（支持自动迁移）"""
    
    # 当前支持的最新配置版本
    CURRENT_CONFIG_VERSION = "0.4.2"
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        auto_create: bool = True,
        validate: bool = True,
        auto_migrate: bool = True
    ):
        self.config_path = config_path or Path.home() / ".nanobot-runner" / "config.json"
        self._config: Optional[AppConfig] = None
        self._validate = validate
        self._auto_migrate = auto_migrate
        self._migration_manager = ConfigMigrationManager()
        
        # 加载配置
        if self.config_path.exists():
            self._load_config()
        elif auto_create:
            self._create_default_config()
    
    def _load_config(self):
        """加载配置（含自动迁移）"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # 检测并执行迁移
            if self._auto_migrate:
                config_dict = self._migrate_if_needed(config_dict)
            
            # 创建配置对象
            self._config = AppConfig.from_dict(config_dict)
            
            logger.info(f"配置加载成功: {self.config_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            self._handle_corrupted_config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self._create_default_config()
    
    def _migrate_if_needed(self, config: dict[str, Any]) -> dict[str, Any]:
        """根据需要执行迁移"""
        current_version = self._migration_manager.detect_version(config)
        
        if current_version == self.CURRENT_CONFIG_VERSION:
            return config
        
        logger.info(f"检测到配置版本 {current_version}，需要迁移到 {self.CURRENT_CONFIG_VERSION}")
        
        success, new_config, warnings = self._migration_manager.migrate(
            config,
            target_version=self.CURRENT_CONFIG_VERSION
        )
        
        if success:
            # 保存迁移后的配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            logger.info("迁移后的配置已保存")
            
            if warnings:
                for warning in warnings:
                    logger.warning(f"迁移警告: {warning}")
            
            return new_config
        else:
            logger.error("配置迁移失败，使用原配置")
            return config
    
    def _create_default_config(self):
        """创建默认配置"""
        self._config = AppConfig()
        self.save_config()
        logger.info(f"已创建默认配置: {self.config_path}")
```

## 手动迁移指南

### 场景1: v0.4.0 -> v0.4.1

**变更内容**:
- 新增 `feishu_receive_id_type` 字段，默认值为 `"user_id"`

**自动迁移**: 支持

**手动迁移步骤**:

```bash
# 1. 备份原配置
cp ~/.nanobot-runner/config.json ~/.nanobot-runner/config.json.backup

# 2. 编辑配置文件，添加新字段
# 在 feishu_receive_id 下方添加:
# "feishu_receive_id_type": "user_id"

# 3. 更新版本号
# "version": "0.4.1"
```

### 场景2: v0.4.1 -> v0.4.2

**变更内容**:
- 新增 `debug_mode` 字段，默认值为 `false`
- 新增 `log_level` 字段，默认值为 `"INFO"`

**自动迁移**: 支持

**手动迁移步骤**:

```bash
# 1. 备份原配置
cp ~/.nanobot-runner/config.json ~/.nanobot-runner/config.json.backup

# 2. 编辑配置文件，添加新字段
# 添加以下字段:
# "debug_mode": false
# "log_level": "INFO"

# 3. 更新版本号
# "version": "0.4.2"
```

### 场景3: 配置损坏恢复

**症状**: 配置文件格式错误，无法加载

**恢复步骤**:

```bash
# 1. 检查备份
cd ~/.nanobot-runner/backups
ls -la

# 2. 恢复最近的备份
cp config_v0.4.1_20260329_120000.json ../config.json

# 3. 验证配置
uv run python -c "from src.core.config_manager import ConfigManager; ConfigManager()"
```

## 迁移验证

### 验证脚本

```python
# scripts/verify_config_migration.py
"""配置迁移验证脚本"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config_manager import ConfigManager
from src.core.config_migration import ConfigMigrationManager


def verify_migration():
    """验证配置迁移"""
    print("=== 配置迁移验证 ===\n")
    
    # 1. 加载配置
    print("[1/4] 加载配置...")
    try:
        config_manager = ConfigManager()
        print("✓ 配置加载成功")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False
    
    # 2. 验证配置
    print("\n[2/4] 验证配置...")
    valid, errors = config_manager.validate()
    if valid:
        print("✓ 配置验证通过")
    else:
        print("✗ 配置验证失败:")
        for error in errors:
            print(f"  - {error}")
    
    # 3. 检查迁移历史
    print("\n[3/4] 检查迁移历史...")
    migration_manager = ConfigMigrationManager()
    history = migration_manager.get_migration_history()
    if history:
        print(f"发现 {len(history)} 条迁移记录:")
        for record in history[:5]:  # 显示最近5条
            print(f"  - {record.migration_id}: {record.status}")
    else:
        print("无迁移记录")
    
    # 4. 检查配置版本
    print("\n[4/4] 检查配置版本...")
    config = config_manager.config
    if config:
        print(f"当前配置版本: {config.version}")
        print(f"目标版本: {ConfigManager.CURRENT_CONFIG_VERSION}")
        if config.version == ConfigManager.CURRENT_CONFIG_VERSION:
            print("✓ 配置版本正确")
        else:
            print("⚠ 配置版本不匹配")
    
    print("\n=== 验证完成 ===")
    return valid


if __name__ == "__main__":
    success = verify_migration()
    sys.exit(0 if success else 1)
```

### 运行验证

```bash
# 运行迁移验证
uv run python scripts/verify_config_migration.py
```

## 迁移检查清单

- [ ] 迁移前备份原配置
- [ ] 了解版本间变更内容
- [ ] 执行迁移（自动或手动）
- [ ] 验证迁移结果
- [ ] 测试应用功能正常
- [ ] 保留备份直到确认稳定

## 常见问题

### Q1: 迁移失败怎么办？

```bash
# 1. 查看迁移记录
cat ~/.nanobot-runner/migration_status.json

# 2. 尝试回滚
uv run python -c "
from src.core.config_migration import ConfigMigrationManager
mgr = ConfigMigrationManager()
mgr.rollback('0.4.0_to_0.4.1')
"

# 3. 手动恢复备份
cp ~/.nanobot-runner/backups/config_v0.4.0_*.json ~/.nanobot-runner/config.json
```

### Q2: 如何禁用自动迁移？

```python
from src.core.config_manager import ConfigManager

# 禁用自动迁移
config = ConfigManager(auto_migrate=False)
```

### Q3: 迁移后配置不兼容？

1. 检查迁移记录中的错误信息
2. 查看备份文件是否完整
3. 手动编辑配置文件修复
4. 联系开发团队获取支持

---

*文档版本: 1.0*  
*适用版本: v0.4.1+*  
*最后更新: 2026-03-29*

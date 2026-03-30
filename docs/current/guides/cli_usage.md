# CLI 使用指南

## 1. 概述

Nanobot Runner 提供命令行界面（CLI），用于导入跑步数据、查看统计信息和与 Agent 交互。

## 2. 安装与配置

### 2.1 环境要求

- Python 3.11+
- uv 包管理器

### 2.2 安装步骤

```bash
# 克隆项目
git clone <repository-url>
cd nanobot-runner

# 创建虚拟环境
uv venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 同步依赖
uv sync --all-extras

# 验证安装
uv run nanobotrun --help
```

## 3. 命令参考

### 3.1 帮助命令

```bash
# 显示帮助信息
uv run nanobotrun --help

# 显示版本信息
uv run nanobotrun version
```

### 3.2 数据导入

```bash
# 导入单个FIT文件
uv run nanobotrun import path/to/activity.fit

# 导入目录下所有FIT文件
uv run nanobotrun import path/to/fit/files/

# 强制重新导入（跳过去重检查）
uv run nanobotrun import path/to/activity.fit --force
```

**导入流程**：
1. 解析FIT文件提取运动数据
2. 计算SHA256指纹进行去重
3. 保存到Parquet文件（按年分片）
4. 更新索引文件

### 3.3 统计查询

```bash
# 查看当前年份统计
uv run nanobotrun stats

# 查看指定年份统计
uv run nanobotrun stats --year 2024

# 查看日期范围统计
uv run nanobotrun stats --start 2024-01-01 --end 2024-12-31
```

**统计输出示例**：
```
📊 2024年跑步统计
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总里程: 1,234.56 km
总时长: 123:45:67
总次数: 45 次
平均配速: 5'34"/km
平均距离: 27.43 km
```

### 3.4 Agent 交互

```bash
# 启动交互式对话
uv run nanobotrun chat
```

**交互示例**：
```
> 最近一个月跑了多少？
📊 最近30天跑步统计：
- 总里程: 85.5 km
- 总时长: 8:15:30
- 总次数: 8 次

> 我的VDOT趋势怎么样？
📈 VDOT趋势分析：
- 当前VDOT: 45.2
- 30天前: 44.8
- 变化: +0.4 (↑ 改善中)
```

## 4. 输出格式

### 4.1 时长格式

- **CLI显示**: `HH:MM:SS` (如 1:23:45)
- **存储格式**: 秒数 (float)

### 4.2 配速格式

- **CLI显示**: `M'SS"/km` (如 5'30"/km)
- **存储格式**: 秒/公里 (float)

### 4.3 距离格式

- **CLI显示**: `X.XX km` (如 10.25 km)
- **存储格式**: 米 (float)

## 5. 数据存储

### 5.1 存储位置

```
~/.nanobot-runner/data/
├── activities_2023.parquet
├── activities_2024.parquet
└── index.json
```

### 5.2 数据格式

Parquet 文件 Schema：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `activity_id` | string | 活动唯一ID |
| `timestamp` | datetime | 活动时间 |
| `total_distance` | float | 总距离（米） |
| `total_timer_time` | float | 总时长（秒） |
| `avg_speed` | float | 平均速度 |
| `avg_heart_rate` | float | 平均心率 |
| `total_calories` | float | 消耗卡路里 |

## 6. 常见问题

### 6.1 导入失败

**问题**: 导入FIT文件时报错
**解决**:
1. 确认文件格式正确（.fit扩展名）
2. 检查文件是否损坏
3. 使用 `--force` 参数重试

### 6.2 数据查询为空

**问题**: 统计命令无数据返回
**解决**:
1. 确认数据已成功导入
2. 检查日期范围是否正确
3. 验证年份参数

### 6.3 环境问题

**问题**: Windows PowerShell 执行策略限制
**解决**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 7. 高级用法

### 7.1 批量导入

```bash
# 导入多个目录
uv run nanobotrun import dir1/ dir2/ dir3/
```

### 7.2 数据验证

```bash
# 导入后验证数据完整性
uv run nanobotrun stats --year 2024
```

### 7.3 性能优化

- 大量数据导入时使用 `--force` 跳过去重检查
- 定期清理旧数据文件
- 使用SSD存储提升查询性能

## 8. 配置文件

### 8.1 配置位置

`~/.nanobot-runner/config.json`

### 8.2 配置示例

```json
{
  "data_dir": "~/.nanobot-runner/data",
  "default_year": 2024,
  "timezone": "Asia/Shanghai"
}
```

---

**文档版本**: v0.4.1  
**最后更新**: 2026-03-30  
**关联文档**: [Agent配置指南](./agent_config_guide.md)

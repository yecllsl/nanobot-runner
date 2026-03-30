# 项目部署手册

## 📋 文档版本信息

| 项目 | 详细信息 |
|------|----------|
| **文档版本** | v3.1 |
| **更新日期** | 2026-03-17 |
| **适用版本** | v0.3.0+ |
| **更新内容** | 新增运维风险与应对、监控指标章节，更新风险复盘结果 |

## 1. 环境要求

### 1.1 系统要求
- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **Python版本**: 3.11+
- **内存**: 最低4GB，推荐8GB+
- **存储**: 至少1GB可用空间

### 1.2 依赖软件
- Git 2.0+
- Python包管理器: uv (推荐) 或 pip

## 2. 本地开发环境部署

### 2.1 环境准备
```bash
# 克隆项目
git clone https://github.com/yecllsl/nanobot-runner.git
cd nanobot-runner

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2.2 安装依赖
```bash
# 使用uv安装（推荐）
uv sync

# 或使用pip安装
pip install -e .
```

### 2.3 验证安装
```bash
# 检查版本
nanobotrun --version

# 查看帮助
nanobotrun --help

# 运行测试
pytest tests/
```

## 3. 生产环境部署

### 3.1 服务器准备
```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 安装Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev

# 安装Git
sudo apt install git
```

### 3.2 应用部署
```bash
# 创建应用目录
sudo mkdir -p /opt/nanobot-runner
sudo chown $USER:$USER /opt/nanobot-runner

# 克隆代码
cd /opt/nanobot-runner
git clone https://github.com/yecllsl/nanobot-runner.git .

# 安装依赖
python3.11 -m venv .venv
source .venv/bin/activate
uv sync
```

### 3.3 配置系统服务

创建systemd服务文件 `/etc/systemd/system/nanobot-runner.service`:
```ini
[Unit]
Description=Nanobot Runner AI跑步助理
After=network.target

[Service]
Type=simple
User=nanobot
WorkingDirectory=/opt/nanobot-runner
Environment=PATH=/opt/nanobot-runner/.venv/bin
ExecStart=/opt/nanobot-runner/.venv/bin/python -m nanobotrun
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3.4 启动服务
```bash
# 重新加载systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable nanobot-runner

# 启动服务
sudo systemctl start nanobot-runner

# 检查状态
sudo systemctl status nanobot-runner
```

## 4. 容器化部署

### 4.1 Docker部署

创建 `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install uv && uv sync

# 设置入口点
ENTRYPOINT ["python", "-m", "nanobotrun"]
```

构建和运行:
```bash
# 构建镜像
docker build -t nanobot-runner .

# 运行容器
docker run -d --name nanobot-runner -p 8000:8000 nanobot-runner
```

### 4.2 Docker Compose部署

创建 `docker-compose.yml`:
```yaml
version: '3.8'

services:
  nanobot-runner:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - PYTHONPATH=/app
```

启动服务:
```bash
docker-compose up -d
```

## 5. 配置管理

### 5.1 环境变量配置

创建 `.env` 文件:
```bash
# 数据库配置
DATABASE_URL=sqlite:///data/nanobot.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/nanobot-runner.log

# 应用配置
DEBUG=false
PORT=8000
```

### 5.2 配置文件

创建 `config/production.yaml`:
```yaml
app:
  name: "nanobot-runner"
  version: "1.0.0"
  debug: false

database:
  url: "sqlite:///data/nanobot.db"
  pool_size: 10

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 6. 监控与日志

### 6.1 日志配置
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/nanobot-runner.log'),
        logging.StreamHandler()
    ]
)
```

### 6.2 健康检查
```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查版本
curl http://localhost:8000/version
```

## 7. 备份与恢复

### 7.1 数据备份
```bash
# 备份数据库
sqlite3 data/nanobot.db ".backup backup/nanobot-$(date +%Y%m%d).db"

# 备份配置文件
tar -czf backup/config-$(date +%Y%m%d).tar.gz config/
```

### 7.2 恢复流程
```bash
# 恢复数据库
sqlite3 data/nanobot.db < backup/nanobot-20240302.db

# 恢复配置
tar -xzf backup/config-20240302.tar.gz -C ./
```

## 8. 故障排查

### 8.1 常见问题

**问题**: 服务无法启动
```bash
# 检查日志
journalctl -u nanobot-runner -f

# 检查端口占用
netstat -tulpn | grep 8000
```

**问题**: 依赖安装失败
```bash
# 清理缓存
uv cache clean

# 重新安装
uv sync --force-reinstall
```

### 8.2 性能优化

**内存优化**:
```python
# 使用Polars进行内存优化
import polars as pl

df = pl.read_parquet("data.parquet")
df = df.lazy().filter(pl.col("heart_rate") > 100).collect()
```

**磁盘优化**:
```bash
# 定期清理缓存
find /tmp -name "*.parquet" -mtime +7 -delete
```

## 9. 安全配置

### 9.1 网络安全
```bash
# 配置防火墙
sudo ufw allow 8000
sudo ufw enable
```

### 9.2 权限管理
```bash
# 创建专用用户
sudo useradd -r -s /bin/false nanobot
sudo chown -R nanobot:nanobot /opt/nanobot-runner
```

## 10. 更新与升级

### 10.1 版本升级
```bash
# 备份当前版本
git tag backup-$(date +%Y%m%d)

# 拉取最新代码
git pull origin main

# 更新依赖
uv sync

# 重启服务
sudo systemctl restart nanobot-runner
```

### 10.2 回滚流程
```bash
# 回滚到指定版本
git checkout v1.0.0

# 恢复依赖
uv sync

# 重启服务
sudo systemctl restart nanobot-runner
```

## 11. 运维风险与应对

### 11.1 风险识别与应对策略

基于风险复盘会议识别的关键风险，制定以下应对措施：

#### R-004: 网络不稳定导致Git推送失败

**风险描述**: 网络波动可能导致代码推送失败，影响CI/CD流程触发

**应对措施**:
```bash
# 1. 配置Git重试机制
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 1000
git config --global http.lowSpeedTime 300

# 2. 使用重试脚本推送
function git_push_with_retry() {
    local max_attempts=3
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        echo "推送尝试 $attempt/$max_attempts..."
        if git push "$@"; then
            echo "推送成功"
            return 0
        fi
        echo "推送失败，等待重试..."
        sleep 5
        ((attempt++))
    done
    echo "推送失败，已达到最大重试次数"
    return 1
}

# 3. 本地备份策略
# 推送前自动创建本地标签作为备份
git tag backup-$(date +%Y%m%d-%H%M%S)
```

**监控告警**:
- CI/CD流水线失败时发送告警通知
- 记录推送失败日志，分析网络稳定性

#### R-008: 依赖库版本冲突

**风险描述**: 第三方依赖版本更新可能导致兼容性问题或安全漏洞

**应对措施**:
```bash
# 1. 依赖版本锁定
# pyproject.toml中已使用精确版本约束
# 定期执行依赖检查
uv pip list --outdated

# 2. 虚拟环境隔离
# 每个版本使用独立的虚拟环境
python -m venv .venv-$(git describe --tags)

# 3. 依赖更新流程
# 步骤1: 在开发环境测试新版本
uv sync --upgrade-package <package-name>
# 步骤2: 运行完整测试套件
pytest tests/ -v
# 步骤3: 确认无误后提交uv.lock更新
```

**版本管理策略**:
| 依赖类型 | 版本策略 | 更新频率 |
|---------|---------|---------|
| 核心依赖(nanobot-ai, polars) | 固定主版本 | 每季度评估 |
| 开发依赖(black, isort) | 固定次版本 | 每月评估 |
| 安全相关(bandit, safety) | 及时更新 | 实时关注 |

#### R-009: 安全漏洞

**风险描述**: 第三方依赖或代码本身可能存在安全漏洞

**应对措施**:
```bash
# 1. 安全扫描集成到CI/CD
# 已在ci.yml中配置bandit扫描
# 本地执行安全扫描
uv run bandit -r src/ -f json -o security-report.json

# 2. 依赖漏洞检测
uv run safety check

# 3. 定期安全审计
# 每月执行一次全面安全扫描
# 生成安全报告并归档
date_str=$(date +%Y%m)
uv run bandit -r src/ -f html -o docs/security/audit-${date_str}.html
```

**安全响应流程**:
1. **发现**: CI/CD安全扫描或手动检测发现漏洞
2. **评估**: 评估漏洞严重程度和影响范围
3. **修复**: 更新受影响的依赖或修复代码
4. **验证**: 重新运行安全扫描确认修复
5. **发布**: 紧急发布安全补丁版本

### 11.2 应急预案

#### 服务不可用应急处理
```bash
# 1. 检查服务状态
sudo systemctl status nanobot-runner

# 2. 查看错误日志
journalctl -u nanobot-runner -n 100 --no-pager

# 3. 快速回滚到上一个稳定版本
git log --oneline -5  # 查看最近提交
git revert HEAD       # 回滚最后一次提交
uv sync
sudo systemctl restart nanobot-runner

# 4. 如果回滚无效，切换到备份版本
git checkout backup-YYYYMMDD
uv sync
sudo systemctl restart nanobot-runner
```

#### 数据损坏应急处理
```bash
# 1. 立即停止服务防止进一步损坏
sudo systemctl stop nanobot-runner

# 2. 从备份恢复数据
# 数据库恢复
sqlite3 data/nanobot.db < backup/nanobot-YYYYMMDD.db

# 3. 验证数据完整性
uv run pytest tests/integration/ -v

# 4. 重启服务
sudo systemctl start nanobot-runner
```

## 12. 监控指标

### 12.1 关键运维指标定义

#### 系统级指标

| 指标名称 | 指标说明 | 采集方式 | 采集频率 |
|---------|---------|---------|---------|
| CPU使用率 | 应用程序CPU占用百分比 | psutil | 60秒 |
| 内存使用率 | 应用程序内存占用(MB) | psutil | 60秒 |
| 磁盘使用率 | 数据目录磁盘占用百分比 | os.statvfs | 300秒 |
| 进程状态 | 应用程序运行状态 | systemctl | 60秒 |

#### 应用级指标

| 指标名称 | 指标说明 | 采集方式 | 采集频率 |
|---------|---------|---------|---------|
| FIT文件导入成功率 | 成功导入文件数/总文件数 | 应用日志 | 实时 |
| 数据处理耗时 | 单次导入处理时间(秒) | 应用日志 | 实时 |
| 查询响应时间 | 统计查询平均响应时间(ms) | 应用日志 | 实时 |
| 活跃用户数 | 每日活跃用户数量 | 应用统计 | 每日 |

#### CI/CD指标

| 指标名称 | 指标说明 | 采集方式 | 采集频率 |
|---------|---------|---------|---------|
| 流水线成功率 | 成功构建次数/总构建次数 | GitHub Actions API | 实时 |
| 构建耗时 | 单次流水线执行时间(分钟) | GitHub Actions API | 实时 |
| 测试覆盖率 | 代码测试覆盖率百分比 | pytest-cov | 每次构建 |
| 代码质量评分 | bandit安全扫描结果 | bandit | 每次构建 |

### 12.2 告警阈值设置

#### 系统告警阈值

| 告警级别 | 指标 | 阈值 | 持续时间 | 通知方式 |
|---------|------|------|---------|---------|
| 警告 | CPU使用率 | >70% | 5分钟 | 日志记录 |
| 严重 | CPU使用率 | >90% | 2分钟 | 邮件+短信 |
| 警告 | 内存使用率 | >80% | 5分钟 | 日志记录 |
| 严重 | 内存使用率 | >95% | 2分钟 | 邮件+短信 |
| 严重 | 磁盘使用率 | >90% | 立即 | 邮件+短信 |
| 紧急 | 服务状态 | 停止 | 立即 | 邮件+短信+电话 |

#### 应用告警阈值

| 告警级别 | 指标 | 阈值 | 持续时间 | 通知方式 |
|---------|------|------|---------|---------|
| 警告 | 导入成功率 | <95% | 单次 | 日志记录 |
| 严重 | 导入成功率 | <90% | 连续3次 | 邮件通知 |
| 警告 | 查询响应时间 | >1000ms | 5分钟 | 日志记录 |
| 严重 | 查询响应时间 | >3000ms | 2分钟 | 邮件通知 |

#### CI/CD告警阈值

| 告警级别 | 指标 | 阈值 | 通知方式 |
|---------|------|------|---------|
| 严重 | 流水线失败 | 失败 | 邮件通知 |
| 警告 | 构建耗时 | >15分钟 | 日志记录 |
| 严重 | 测试覆盖率 | <80% | 邮件通知 |
| 严重 | 安全扫描 | 发现高危漏洞 | 邮件+短信 |

### 12.3 监控工具配置

#### 日志监控脚本

创建 `scripts/monitor.sh`:
```bash
#!/bin/bash
# 系统监控脚本

LOG_FILE="/var/log/nanobot-monitor.log"
ALERT_EMAIL="ops@example.com"

# 检查服务状态
check_service() {
    if ! systemctl is-active --quiet nanobot-runner; then
        echo "$(date): 警告 - nanobot-runner服务未运行" >> $LOG_FILE
        # 尝试自动重启
        systemctl restart nanobot-runner
        sleep 5
        if ! systemctl is-active --quiet nanobot-runner; then
            echo "$(date): 严重 - 服务重启失败，发送告警" >> $LOG_FILE
            # 发送告警邮件
            echo "nanobot-runner服务异常，请立即处理" | mail -s "服务告警" $ALERT_EMAIL
        fi
    fi
}

# 检查磁盘空间
check_disk() {
    usage=$(df /opt/nanobot-runner | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $usage -gt 90 ]; then
        echo "$(date): 严重 - 磁盘使用率${usage}%，超过阈值" >> $LOG_FILE
    elif [ $usage -gt 80 ]; then
        echo "$(date): 警告 - 磁盘使用率${usage}%，接近阈值" >> $LOG_FILE
    fi
}

# 主循环
while true; do
    check_service
    check_disk
    sleep 60
done
```

#### CI/CD监控配置

在 `.github/workflows/monitor.yml` 中添加:
```yaml
name: Pipeline Monitor

on:
  workflow_run:
    workflows: ["CI Pipeline"]
    types: [completed]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
    - name: Check workflow status
      run: |
        if [ "${{ github.event.workflow_run.conclusion }}" == "failure" ]; then
          echo "CI流水线执行失败，请检查: ${{ github.event.workflow_run.html_url }}"
          # 发送告警通知
        fi
```

#### 应用性能监控

在应用中添加监控代码 `src/monitoring.py`:
```python
"""
应用性能监控模块
用于收集和上报关键性能指标
"""
import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_timing(self, operation: str, duration: float) -> None:
        """记录操作耗时"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
        
        # 超过阈值记录警告
        if duration > 3.0:  # 3秒阈值
            logger.warning(f"操作 {operation} 耗时过长: {duration:.2f}s")
    
    def get_stats(self, operation: str) -> dict:
        """获取操作统计信息"""
        if operation not in self.metrics:
            return {}
        times = self.metrics[operation]
        return {
            "count": len(times),
            "avg": sum(times) / len(times),
            "max": max(times),
            "min": min(times)
        }


def monitor_performance(operation: str):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start
                # 记录性能指标
                logger.info(f"{operation} 完成，耗时: {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(f"{operation} 失败，耗时: {duration:.3f}s, 错误: {e}")
                raise
        return wrapper
    return decorator


# 全局监控器实例
monitor = PerformanceMonitor()
```

### 12.4 监控数据收集

#### 日志收集配置

```python
# 配置结构化日志
import logging
import json
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(level)s %(name)s %(message)s'
)
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

#### 指标上报

```bash
# 使用curl定期上报指标到监控平台
# 每分钟上报一次
*/1 * * * * curl -X POST https://monitoring.example.com/metrics \
  -H "Content-Type: application/json" \
  -d @/var/log/nanobot-metrics.json
```

## 13. 变更历史

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|--------|
| v1.0 | 2026-03-01 | 初始版本，包含基础部署流程 | DevOps智能体 |
| v2.0 | 2026-03-10 | 新增容器化部署、备份恢复章节 | DevOps智能体 |
| v3.0 | 2026-03-17 | 适配v0.3.0版本，更新测试覆盖率与质量门禁要求 | DevOps智能体 |
| v3.1 | 2026-03-17 | **风险复盘更新**:<br>- 新增"运维风险与应对"章节(R-004网络不稳定、R-008依赖冲突、R-009安全漏洞)<br>- 新增"监控指标"章节(系统/应用/CI/CD指标、告警阈值、监控工具配置)<br>- 完善应急预案和回滚流程 | DevOps智能体 |

### 风险复盘记录

**会议日期**: 2026-03-17

**识别风险**:
- R-004: 网络不稳定导致Git推送失败 - 已制定重试机制和本地备份策略
- R-008: 依赖库版本冲突 - 已制定版本锁定和更新流程
- R-009: 安全漏洞 - 已制定安全扫描和响应流程

**应对措施状态**: 已全部文档化并纳入运维手册

---

**最后更新**: 2026-03-17  
**维护者**: DevOps智能体  
**审核状态**: 已审核
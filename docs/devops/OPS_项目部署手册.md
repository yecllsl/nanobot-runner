# 项目部署手册

## 📋 文档版本信息

| 项目 | 详细信息 |
|------|----------|
| **文档版本** | v3.0 |
| **更新日期** | 2026-03-17 |
| **适用版本** | v0.3.0+ |
| **更新内容** | 适配v0.3.0版本，更新测试覆盖率与质量门禁要求 |

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

---

**最后更新**: 2026-03-17  
**维护者**: DevOps智能体
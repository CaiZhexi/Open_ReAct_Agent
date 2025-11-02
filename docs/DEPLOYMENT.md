# 部署指南

> Agentic-RAG 系统部署完整指南

本文档提供 Agentic-RAG 系统在不同环境下的部署方案和最佳实践。

---

## 📋 目录

- [部署概述](#部署概述)
- [环境准备](#环境准备)
- [开发环境部署](#开发环境部署)
- [生产环境部署](#生产环境部署)
- [Docker 部署](#docker-部署)
- [性能优化](#性能优化)
- [监控与运维](#监控与运维)
- [故障排查](#故障排查)
- [安全加固](#安全加固)

---

## 部署概述

### 支持的部署方式

| 方式 | 适用场景 | 难度 | 推荐度 |
|------|----------|------|--------|
| 本地开发 | 开发测试 | ⭐ | ⭐⭐⭐⭐⭐ |
| 生产环境（裸机） | 小型部署 | ⭐⭐ | ⭐⭐⭐⭐ |
| Docker 容器 | 标准化部署 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Kubernetes | 大规模部署 | ⭐⭐⭐⭐ | ⭐⭐⭐ |

### 系统要求

#### 最低配置

- **CPU**: 2核
- **内存**: 4GB
- **磁盘**: 20GB SSD
- **操作系统**: Linux/macOS/Windows

#### 推荐配置

- **CPU**: 4核+
- **内存**: 8GB+
- **磁盘**: 50GB+ SSD
- **操作系统**: Linux (Ubuntu 20.04+ / CentOS 8+)

---

## 环境准备

### 1. 安装 Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip

# macOS (使用 Homebrew)
brew install python@3.10

# 验证安装
python3 --version  # 应显示 Python 3.10+
```

### 2. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git

# macOS
brew install openssl libffi git
```

### 3. 克隆项目

```bash
# 克隆仓库
git clone https://github.com/CaiZhexi/Open_ReAct_Agent.git
cd Open_ReAct_Agent
```

---

## 开发环境部署

### 快速开始

```bash
# 1. 创建虚拟环境
python3 -m venv venv

# 2. 激活虚拟环境
source venv/bin/activate          # Linux/macOS
# 或
venv\Scripts\activate             # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API 密钥
cp .env.example .env              # 复制环境变量模板
nano .env                         # 编辑配置，填入你的 API 密钥

# 5. 初始化数据目录
mkdir -p data/vectors logs

# 6. 运行服务
python app.py
```

### 开发环境配置

创建 `.env` 文件：

```bash
# API Keys
CHAT_API_KEY=your-chat-api-key
EMBED_API_KEY=your-embed-api-key
RERANK_API_KEY=your-rerank-api-key
SEARCH_API_KEY=your-search-api-key

# 开发环境配置
FLASK_DEBUG=true
PYTHON_EXECUTOR_TYPE=default
ENABLE_IO_LOGGING=true
```

### 访问服务

```
http://localhost:5004
```

---

## 生产环境部署

### 1. 系统用户创建

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash agentic-rag
sudo su - agentic-rag
```

### 2. 项目部署

```bash
# 克隆项目
git clone https://github.com/your-repo/Agentic-RAG.git
cd Agentic-RAG

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn  # 生产环境 WSGI 服务器
```

### 3. 生产环境配置

创建 `.env` 文件：

```bash
# API Keys（使用环境变量或密钥管理服务）
CHAT_API_KEY=${CHAT_API_KEY}
EMBED_API_KEY=${EMBED_API_KEY}
RERANK_API_KEY=${RERANK_API_KEY}
SEARCH_API_KEY=${SEARCH_API_KEY}

# 生产环境配置
FLASK_DEBUG=false
PYTHON_EXECUTOR_TYPE=process_isolated
ENABLE_IO_LOGGING=true

# 安全配置
PYTHON_EXECUTOR_ENABLE_MONITORING=true
PYTHON_EXECUTOR_ENABLE_AUDIT=true
PYTHON_EXECUTOR_ENABLE_RATE_LIMIT=true
```

### 4. 使用 Gunicorn 运行

```bash
# 创建 gunicorn 配置文件
cat > gunicorn_config.py << 'EOF'
import multiprocessing

# 绑定地址
bind = "0.0.0.0:5004"

# 工作进程数（通常是 CPU 核心数 * 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1

# 工作进程类型
worker_class = "sync"

# 超时时间
timeout = 300

# 日志
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# 最大请求数（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 守护进程
daemon = False

# PID 文件
pidfile = "gunicorn.pid"
EOF

# 运行 Gunicorn
gunicorn -c gunicorn_config.py app:app
```

### 5. 使用 Systemd 管理服务

创建服务文件 `/etc/systemd/system/agentic-rag.service`：

```ini
[Unit]
Description=Agentic-RAG Service
After=network.target

[Service]
Type=notify
User=agentic-rag
Group=agentic-rag
WorkingDirectory=/home/agentic-rag/Agentic-RAG
Environment="PATH=/home/agentic-rag/Agentic-RAG/venv/bin"
ExecStart=/home/agentic-rag/Agentic-RAG/venv/bin/gunicorn -c gunicorn_config.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用和启动服务：

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable agentic-rag

# 启动服务
sudo systemctl start agentic-rag

# 查看状态
sudo systemctl status agentic-rag

# 查看日志
sudo journalctl -u agentic-rag -f
```

### 6. Nginx 反向代理

安装 Nginx：

```bash
sudo apt install nginx
```

创建 Nginx 配置 `/etc/nginx/sites-available/agentic-rag`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 请求体大小限制（文件上传）
    client_max_body_size 20M;

    # 超时设置
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
    proxy_read_timeout 300;

    # 日志
    access_log /var/log/nginx/agentic-rag-access.log;
    error_log /var/log/nginx/agentic-rag-error.log;

    location / {
        proxy_pass http://127.0.0.1:5004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件缓存
    location /static {
        alias /home/agentic-rag/Agentic-RAG/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

启用配置：

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/agentic-rag /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 7. SSL/TLS 配置（推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书并自动配置 Nginx
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

---

## Docker 部署

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

# 创建数据目录
RUN mkdir -p data/vectors logs

# 暴露端口
EXPOSE 5004

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5004/api/health || exit 1

# 启动命令
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  agentic-rag:
    build: .
    ports:
      - "5004:5004"
    environment:
      - CHAT_API_KEY=${CHAT_API_KEY}
      - EMBED_API_KEY=${EMBED_API_KEY}
      - RERANK_API_KEY=${RERANK_API_KEY}
      - SEARCH_API_KEY=${SEARCH_API_KEY}
      - FLASK_DEBUG=false
      - PYTHON_EXECUTOR_TYPE=process_isolated
      - ENABLE_IO_LOGGING=true
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5004/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - agentic-rag
    restart: unless-stopped
```

### 3. 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

---

## 性能优化

### 1. Gunicorn 优化

```python
# gunicorn_config.py

import multiprocessing

# 根据 CPU 核心数调整
workers = multiprocessing.cpu_count() * 2 + 1

# 使用 gevent 异步工作模式（需要安装 gevent）
# worker_class = "gevent"
# worker_connections = 1000

# 预加载应用（减少内存占用）
preload_app = True

# 设置合理的超时
timeout = 300
graceful_timeout = 30
keepalive = 5
```

### 2. 数据库优化

```python
# config.py

# SQLite 优化
import sqlite3

def optimize_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 启用 WAL 模式（提高并发性能）
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # 增加缓存大小
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB
    
    # 优化同步模式
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    conn.commit()
    conn.close()
```

### 3. 向量检索优化

```python
# config.py

# 调整检索参数
INITIAL_RETRIEVAL_TOP_K = 30  # 减少初始检索数量
LIGHT_RERANK_TOP_K = 15
FINAL_RERANK_TOP_K = 5

# 使用更小的向量维度（如果可能）
EMBED_DIMENSIONS = 512  # 代替 1024
```

### 4. 缓存配置

```python
# 使用 Redis 缓存（可选）
# 安装: pip install redis

from redis import Redis

redis_client = Redis(host='localhost', port=6379, db=0)

# 缓存向量检索结果
def get_cached_vectors(query, kb_id):
    cache_key = f"vectors:{kb_id}:{hash(query)}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    # 执行检索...
    redis_client.setex(cache_key, 3600, json.dumps(result))
    return result
```

---

## 监控与运维

### 1. 日志管理

```bash
# 配置日志轮转
sudo nano /etc/logrotate.d/agentic-rag
```

```
/home/agentic-rag/Agentic-RAG/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 agentic-rag agentic-rag
    sharedscripts
    postrotate
        systemctl reload agentic-rag > /dev/null
    endscript
}
```

### 2. 监控指标

使用 Prometheus + Grafana 监控（可选）：

```python
# 安装: pip install prometheus-flask-exporter

from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# 自动收集 Flask 指标
# 访问 /metrics 端点查看指标
```

### 3. 健康检查

```bash
# 定期检查服务健康状态
*/5 * * * * curl -f http://localhost:5004/api/health || systemctl restart agentic-rag
```

### 4. 数据备份

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/backup/agentic-rag"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
cp data/knowledge_base.db "$BACKUP_DIR/knowledge_base_$DATE.db"

# 备份向量索引
tar -czf "$BACKUP_DIR/vectors_$DATE.tar.gz" data/vectors/

# 删除7天前的备份
find "$BACKUP_DIR" -name "*.db" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# 添加到 crontab（每天凌晨2点备份）
0 2 * * * /home/agentic-rag/backup.sh
```

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

**症状**：`systemctl start agentic-rag` 失败

**排查步骤**：
```bash
# 查看详细日志
sudo journalctl -u agentic-rag -n 50 --no-pager

# 检查端口占用
sudo lsof -i :5004

# 检查文件权限
ls -la /home/agentic-rag/Agentic-RAG

# 手动测试启动
sudo su - agentic-rag
cd Agentic-RAG
source venv/bin/activate
python app.py
```

#### 2. 内存占用过高

**症状**：系统内存不足，OOM Killer 杀死进程

**解决方案**：
```python
# gunicorn_config.py
# 减少 worker 数量
workers = 2

# 限制最大请求数
max_requests = 500
max_requests_jitter = 50

# 配置 Python 执行器内存限制
# config.py
PYTHON_EXECUTOR_MAX_MEMORY_MB = 128
```

#### 3. 向量检索慢

**症状**：检索响应时间长

**解决方案**：
```python
# 优化 Faiss 索引
# 使用 IVF 索引代替暴力搜索
import faiss

# 创建 IVF 索引
quantizer = faiss.IndexFlatL2(dimensions)
index = faiss.IndexIVFFlat(quantizer, dimensions, nlist=100)
index.train(vectors)
index.add(vectors)
```

#### 4. 文档处理队列堵塞

**症状**：上传的文档长时间处于 pending 状态

**排查步骤**：
```bash
# 查看队列状态
curl http://localhost:5004/api/docs/queue-status/{kb_id}

# 查看日志
tail -f logs/app.log

# 重启文档处理队列
sudo systemctl restart agentic-rag
```

---

## 安全加固

### 1. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# 仅允许 Nginx 访问应用端口
sudo ufw allow from 127.0.0.1 to any port 5004
```

### 2. 限制文件权限

```bash
# 设置正确的文件权限
chmod 700 /home/agentic-rag/Agentic-RAG
chmod 600 /home/agentic-rag/Agentic-RAG/.env
chmod 755 /home/agentic-rag/Agentic-RAG/app.py
```

### 3. 定期更新

```bash
# 创建更新脚本
cat > update.sh << 'EOF'
#!/bin/bash

cd /home/agentic-rag/Agentic-RAG
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart agentic-rag
EOF

chmod +x update.sh
```

### 4. 日志审计

定期检查审计日志：

```bash
# 查看执行器审计日志
tail -f logs/executor_audit.log

# 查看失败的代码执行
tail -f logs/executor_failures.log

# 分析异常模式
grep "SECURITY" logs/*.log
```

---

## 部署检查清单

### 部署前

- [ ] 系统要求满足
- [ ] Python 3.10+ 已安装
- [ ] 所有依赖已安装
- [ ] API 密钥已配置
- [ ] 数据目录已创建
- [ ] 执行器类型设置为 `process_isolated`
- [ ] 所有安全特性已启用

### 部署后

- [ ] 服务正常启动
- [ ] 健康检查通过
- [ ] API 端点可访问
- [ ] 文档上传测试成功
- [ ] 问答功能正常
- [ ] 日志正常记录
- [ ] 监控指标正常
- [ ] 备份脚本配置
- [ ] SSL 证书配置（生产环境）
- [ ] 防火墙规则配置

---

## 性能基准

### 测试环境

- CPU: 4核 2.5GHz
- 内存: 8GB
- 磁盘: SSD
- 网络: 100Mbps

### 基准结果

| 操作 | QPS | 平均响应时间 | P95响应时间 |
|------|-----|-------------|-------------|
| 简单问答 | 20 | 500ms | 800ms |
| Agentic 问答 | 10 | 2s | 4s |
| V2 问答（多任务） | 8 | 3s | 6s |
| 文档上传 | 50 | 200ms | 400ms |
| 向量检索 | 100 | 100ms | 200ms |

---

## 扩展部署

### 水平扩展

使用负载均衡器分发请求：

```nginx
upstream agentic_rag_backend {
    least_conn;
    server 127.0.0.1:5004 weight=1;
    server 127.0.0.1:5005 weight=1;
    server 127.0.0.1:5006 weight=1;
}

server {
    listen 80;
    location / {
        proxy_pass http://agentic_rag_backend;
    }
}
```

### 数据库分离

将 SQLite 迁移到 PostgreSQL（未来支持）：

```python
# 使用 PostgreSQL 代替 SQLite
DATABASE_URL = "postgresql://user:pass@localhost/agentic_rag"
```

---

## 总结

遵循本文档的部署步骤和最佳实践，可以确保 Agentic-RAG 系统稳定、安全、高效地运行。

**关键要点**：

1. ✅ 生产环境使用 Gunicorn + Nginx
2. ✅ 使用 Systemd 管理服务
3. ✅ 配置 SSL/TLS 证书
4. ✅ 定期备份数据
5. ✅ 监控系统性能和日志
6. ✅ 遵循安全最佳实践

---

**文档版本**：v1.0  
**最后更新**：2025年10月12日  
**维护者**：Agentic-RAG Team


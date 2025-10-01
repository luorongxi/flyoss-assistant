#!/bin/bash
set -e

# 设置UTF-8环境变量
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

echo "----- 启动环境检查 -----"

cd /app || { echo "进入/app目录失败"; exit 1; }

echo "检查依赖服务可用性..."

# 增强版服务检查 - 增加超时和重试
check_service() {
  local host=$1 port=$2 name=$3
  local counter=0
  local max_retries=60  # 增加到60次重试（约5分钟）

  echo "检查 $name 服务 ($host:$port)..."

  until nc -zw 1 "$host" "$port"; do
    echo "等待 $name... 尝试 #$((counter+1))/$max_retries"
    sleep 5  # 增加等待时间到5秒
    ((counter++))

    if [ $counter -ge $max_retries ]; then
      echo "错误: $name 服务不可达!" >&2
      exit 1
    fi
  done
  echo "$name 服务就绪!"
}

check_service redis 6379 "Redis"
check_service qdrant 6333 "Qdrant"

# 初始化知识库（仅执行一次）
echo "初始化知识库..."
python -m app.core.knowledge_base init || {
  echo "错误: 知识库初始化失败"
  exit 1
}

# 根据CPU核心数动态设置workers（优化逻辑）
CPU_CORES=$(nproc)
MAX_WORKERS=8  # 最大worker数
WORKERS=$((CPU_CORES * 2 + 1))

# 控制worker上限并确保最小值为1
[ $WORKERS -gt $MAX_WORKERS ] && WORKERS=$MAX_WORKERS
[ $WORKERS -lt 1 ] && WORKERS=1

# 解决Gunicorn worker启动重复日志问题
export WORKER_STARTUP_SILENCE=1

echo "使用 $WORKERS workers 启动FlyOSS Assistant..."
exec gunicorn -k uvicorn.workers.UvicornWorker \
  --workers $WORKERS \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --preload \
  app.main:app
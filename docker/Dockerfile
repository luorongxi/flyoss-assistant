# 第一阶段：构建环境
FROM python:3.12-slim AS builder

# 设置清华源（加速 apt 包安装）
RUN rm -f /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list && \
    rm -rf /etc/apt/sources.list.d/*

# 设置工作目录
WORKDIR /app

# 安装系统依赖（带重试机制）
RUN for i in {1..5}; do \
        apt-get update && \
        apt-get install -y --no-install-recommends \
            build-essential \
            curl \
            git \
        && break || \
        (sleep 15 && echo "尝试 #$i 失败，正在重试..."); \
    done && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 配置全局 pip 使用阿里云源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com && \
    pip config set global.timeout 120 && \
    pip config set global.retries 10

# 安装 Poetry
ENV POETRY_VERSION=2.1.3
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# 配置 Poetry 虚拟环境设置
RUN poetry config virtualenvs.create true && \
    poetry config virtualenvs.in-project true

# 复制依赖文件
COPY pyproject.toml poetry.lock ./

# 配置 Poetry 使用阿里云源（双源冗余）
RUN poetry config repositories.pypi https://mirrors.aliyun.com/pypi/simple/ && \
    poetry config repositories.aliyun https://mirrors.aliyun.com/pypi/simple/ && \
    poetry config --list

# 安装项目依赖（增强重试机制）
RUN poetry cache clear pypi --all -n && \
    for i in {1..5}; do \
        echo "====> Poetry 依赖安装尝试 #$i" && \
        poetry install -v --no-interaction --no-ansi --only main --no-root 2>&1 | tee /tmp/poetry_install.log && break || \
        { \
            echo "====> 尝试 #$i 失败，等待重试..." && \
            grep -i -E 'error|fail|timeout|retry' /tmp/poetry_install.log || true; \
            sleep 30; \
            [ $i -eq 5 ] && { echo "!!!!> 所有安装尝试均失败！查看日志:"; cat /tmp/poetry_install.log; exit 1; }; \
        }; \
    done

# 复制应用代码
COPY . .

# 安装应用（主模块）
RUN poetry install --only-root --no-interaction --no-ansi

# 第二阶段：生产环境
FROM python:3.12-slim AS runtime

# 设置清华源（加速运行时依赖安装）
RUN rm -f /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list && \
    rm -rf /etc/apt/sources.list.d/*

# 设置环境变量 - 添加 UTF-8 支持
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    FLASK_APP="app.main:app" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=utf-8 \
    PYTHONUTF8=1

# 安装最小系统依赖
RUN for i in {1..5}; do \
        apt-get update && \
        apt-get install -y --no-install-recommends curl netcat-openbsd && \
        break || (sleep 15 && echo "运行时依赖安装尝试 #$i 失败"); \
    done && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app

# 从构建阶段复制虚拟环境和应用代码
COPY --from=builder /app /app

# 设置权限
RUN chmod -R a+rwx /app && \
    mkdir -p logs && \
    chmod a+rwx logs

# 暴露端口
EXPOSE 8000

# 设置入口点
ENTRYPOINT ["/bin/bash", "/app/docker/entrypoint.sh"]
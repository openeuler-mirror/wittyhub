# ============================================================================
# SkillSpector + Jenkins 镜像 (自包含版本)
# ============================================================================
# 用法:
#   docker build -f deploy/skillspector/Dockerfile -t skillspector-jenkins:latest .
#   docker run -d --name skillspector-jenkins \
#     -p 8083:8083 -p 50000:50000 \
#     -v jenkins_home:/var/jenkins_home \
#     skillspector-jenkins:latest
#
# 环境变量 (可选):
#   JENKINS_ADMIN_PASS    admin 初始密码 (默认 admin@123456)
#   GIT_REPO_URL          SkillSpector 仓库地址
#   GIT_REF               分支/标签 (默认 main)
# ============================================================================

# ---- Stage 1: 构建 SkillSpector wheels ----
FROM python:3.13-slim AS skillspector-builder

ARG GIT_REPO_URL=https://github.com/JunchengDwain/SkillSpector.git
ARG GIT_REF=main

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "${GIT_REF}" "${GIT_REPO_URL}" /tmp/skillspector

WORKDIR /tmp/skillspector
RUN pip config set global.timeout 120 && \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install pip --upgrade && \
    pip wheel . -w /tmp/wheels

# ---- Stage 2: Jenkins 镜像 ----
FROM jenkins/jenkins:lts

USER root

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 从 Stage 1 复制预构建的 wheels
COPY --from=skillspector-builder /tmp/wheels /tmp/wheels

# 安装 SkillSpector
RUN pip config set global.timeout 120 && \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --break-system-packages --ignore-installed /tmp/wheels/*.whl && \
    rm -rf /tmp/wheels

# 验证 SkillSpector 安装
RUN skillspector --version

# Jenkins 插件
RUN jenkins-plugin-cli --plugins \
    "workflow-aggregator:latest" \
    "git:latest" \
    "credentials-binding:latest" \
    "pipeline-stage-view:latest" \
    "build-token-root:latest" \
    "timestamper:latest"

# .override 确保已有 Jenkins 数据卷也使用最新初始化脚本
COPY deploy/skillspector/init.groovy /usr/share/jenkins/ref/init.groovy.d/01-init.groovy.override
COPY deploy/skillspector/pipeline.groovy /usr/share/jenkins/ref/jenkins-pipeline.groovy

ENV SKILLSPECTOR_LOG_LEVEL=WARNING
ENV SKILLSPECTOR_PROVIDER=openai

USER jenkins

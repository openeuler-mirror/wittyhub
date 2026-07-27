#!/usr/bin/env bash
# ============================================================================
# SkillSpector + Jenkins 一键部署脚本 (自包含版本)
# ============================================================================
# 只需要这一个文件，复制到任意有 Docker 的 Linux 机器上运行即可。
# 脚本会自动:
#   1. 克隆 SkillSpector 仓库
#   2. 生成 Dockerfile / Jenkins Pipeline / 初始化脚本
#   3. 下载适配当前架构的 Docker CLI 静态二进制
#   4. 构建镜像并启动 Jenkins 容器
#   5. 自动创建 admin 用户 + skill-scanner Job
#
# 用法:
#   chmod +x deploy.sh && ./deploy.sh
#
# 环境变量 (可选):
#   JENKINS_HTTP_PORT     Jenkins Web 端口 (默认 8080)
#   JENKINS_AGENT_PORT    Jenkins Agent 端口 (默认 50000)
#   JENKINS_ADMIN_PASS    admin 密码 (默认 admin@123456)
#   JENKINS_HOME_DIR      Jenkins 数据目录 (默认 /var/jenkins_home)
#   CONTAINER_NAME        容器名 (默认 skillspector-jenkins)
#   IMAGE_NAME            镜像名 (默认 skillspector-jenkins:latest)
#   DOCKER_SOCKET         Docker socket 路径 (默认 /var/run/docker.sock)
#   GIT_REPO_URL          SkillSpector 仓库地址
#   GIT_REF               分支/标签 (默认 main)
# ============================================================================

set -euo pipefail

# ---- 颜色输出 ----
if [ -t 1 ] && command -v tput &>/dev/null && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "\n${CYAN}==>${NC} $*"; }

# ---- 配置 ----
JENKINS_HTTP_PORT="${JENKINS_HTTP_PORT:-8080}"
JENKINS_AGENT_PORT="${JENKINS_AGENT_PORT:-50000}"
JENKINS_ADMIN_PASS="${JENKINS_ADMIN_PASS:-admin@123456}"
JENKINS_HOME_DIR="${JENKINS_HOME_DIR:-/var/jenkins_home}"
CONTAINER_NAME="${CONTAINER_NAME:-skillspector-jenkins}"
IMAGE_NAME="${IMAGE_NAME:-skillspector-jenkins:latest}"
DOCKER_SOCKET="${DOCKER_SOCKET:-/var/run/docker.sock}"
GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/JunchengDwain/SkillSpector.git}"
GIT_REF="${GIT_REF:-main}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ---- 权限检查 ----
if [ "$(id -u)" -ne 0 ]; then
    log_error "此脚本需要 root 权限运行，请使用: sudo $0"
    exit 1
fi

# ---- 检测系统 ----
case "$(uname -s)" in
    Linux)  OS="linux" ;;
    Darwin) OS="macos" ;;
    *)      log_error "不支持的操作系统: $(uname -s)"; exit 1 ;;
esac

case "$(uname -m)" in
    x86_64|amd64)  ARCH="x86_64" ;;
    aarch64|arm64) ARCH="aarch64" ;;
    *)             log_error "不支持的架构: $(uname -m)"; exit 1 ;;
esac

log_info "系统: ${OS} / ${ARCH}"

# ---- 检查依赖 ----
for cmd in curl tar git; do
    if ! command -v "$cmd" &>/dev/null; then
        log_error "缺少命令: ${cmd}，请先安装 (apt install ${cmd} / dnf install ${cmd})"
        exit 1
    fi
done

# ---- 安装 Docker ----
if ! command -v docker &>/dev/null; then
    log_info "正在安装 Docker..."
    if command -v dnf &>/dev/null; then
        dnf install -y docker-ce docker-ce-cli 2>/dev/null || dnf install -y docker
    elif command -v yum &>/dev/null; then
        yum install -y docker-ce docker-ce-cli 2>/dev/null || yum install -y docker
    elif command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq docker.io
    else
        log_error "请手动安装 Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi
fi

if ! docker info &>/dev/null; then
    log_warn "正在启动 Docker 服务..."
    systemctl start docker 2>/dev/null || service docker start 2>/dev/null || true
    sleep 3
    if ! docker info &>/dev/null; then
        log_error "Docker 启动失败，请手动启动 Docker 服务"
        exit 1
    fi
fi

log_info "Docker: $(docker --version)"

# ---- 配置 Docker 镜像加速 (国内网络) ----
DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
MIRRORS=(
    "https://docker.m.daocloud.io"
    "https://dockerhub.timeweb.cloud"
    "https://hub.rat.dev"
    "https://mirror.ccs.tencentyun.com"
)

configure_docker_mirrors() {
    # 如果已有 registry-mirrors 配置，跳过
    if [ -f "$DOCKER_DAEMON_JSON" ] && grep -q "registry-mirrors" "$DOCKER_DAEMON_JSON" 2>/dev/null; then
        log_info "Docker 镜像加速已配置，跳过"
        return 0
    fi

    log_info "配置 Docker 镜像加速..."

    # 构建 mirrors JSON 数组
    local mirrors_json="["
    local first=true
    for m in "${MIRRORS[@]}"; do
        if $first; then first=false; else mirrors_json+=", "; fi
        mirrors_json+="\"$m\""
    done
    mirrors_json+="]"

    if [ -f "$DOCKER_DAEMON_JSON" ] && [ -s "$DOCKER_DAEMON_JSON" ]; then
        # 合并现有配置
        python3 -c "
import json
with open('$DOCKER_DAEMON_JSON') as f:
    cfg = json.load(f) if f.read().strip() else {}
cfg['registry-mirrors'] = $mirrors_json
with open('$DOCKER_DAEMON_JSON', 'w') as f:
    json.dump(cfg, f, indent=2)
" 2>/dev/null || {
            # python3 不可用时直接覆盖
            cat > "$DOCKER_DAEMON_JSON" <<JSONEOF
{
  "registry-mirrors": $mirrors_json
}
JSONEOF
        }
    else
        mkdir -p "$(dirname "$DOCKER_DAEMON_JSON")"
        cat > "$DOCKER_DAEMON_JSON" <<JSONEOF
{
  "registry-mirrors": $mirrors_json
}
JSONEOF
    fi

    # 重启 Docker
    systemctl restart docker 2>/dev/null || service docker restart 2>/dev/null || true
    sleep 3

    if ! docker info &>/dev/null; then
        log_error "Docker 重启失败，请检查 ${DOCKER_DAEMON_JSON}"
        return 1
    fi
    log_info "Docker 镜像加速配置完成"
}

configure_docker_mirrors

# ---- 下载 Docker CLI 静态二进制 ----
log_step "1/6 下载 Docker CLI 二进制 (${ARCH})"

DOCKER_CLI_VER="${DOCKER_CLI_VERSION:-27.5.1}"
mkdir -p "${WORK_DIR}/docker-bin"

for url in \
    "https://mirrors.aliyun.com/docker-ce/linux/static/stable/${ARCH}/docker-${DOCKER_CLI_VER}.tgz" \
    "https://download.docker.com/linux/static/stable/${ARCH}/docker-${DOCKER_CLI_VER}.tgz"; do
    log_info "尝试: ${url}"
    if curl -fsSL --connect-timeout 30 --max-time 120 "$url" -o "/tmp/docker-cli.tgz" 2>/dev/null; then
        tar xzf /tmp/docker-cli.tgz -C "${WORK_DIR}/docker-bin" --strip-components=1 docker/docker
        chmod +x "${WORK_DIR}/docker-bin/docker"
        rm -f /tmp/docker-cli.tgz
        log_info "Docker CLI 下载成功: $(${WORK_DIR}/docker-bin/docker --version)"
        break
    fi
done

if [ ! -x "${WORK_DIR}/docker-bin/docker" ]; then
    log_error "Docker CLI 下载失败，请设置 DOCKER_CLI_VERSION 重试"
    exit 1
fi

# ---- 克隆仓库 ----
log_step "2/6 克隆 SkillSpector 仓库"

git clone --depth 1 --branch "${GIT_REF}" "${GIT_REPO_URL}" "${WORK_DIR}/repo" 2>&1 | tail -3
log_info "仓库已克隆到: ${WORK_DIR}/repo"

# ---- 生成 Dockerfile ----
log_step "3/6 生成构建文件"

cat > "${WORK_DIR}/repo/Dockerfile.jenkins" <<'DOCKERFILE_EOF'
FROM jenkins/jenkins:lts

USER root

# 系统包 - 使用阿里云镜像加速
RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://deb.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-venv python3-dev python3-pip python3-full \
        gcc make git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 config set global.trusted-host mirrors.aliyun.com

# Docker CLI 静态二进制
COPY docker-bin/docker /usr/local/bin/docker
RUN chmod +x /usr/local/bin/docker && docker --version

# 安装 SkillSpector
COPY pyproject.toml README.md /tmp/skillspector/
COPY src/ /tmp/skillspector/src/
RUN cd /tmp/skillspector && \
    pip3 install --no-cache-dir . && \
    rm -rf /tmp/skillspector && \
    skillspector --version

# Jenkins 插件
ENV JENKINS_HOME=/var/jenkins_home
RUN jenkins-plugin-cli --plugins \
    "workflow-aggregator:latest" \
    "git:latest" \
    "credentials-binding:latest" \
    "pipeline-stage-view:latest" \
    "build-token-root:latest" \
    "timestamper:latest"

# 初始化脚本
COPY jenkins-init.groovy /usr/share/jenkins/ref/init.groovy.d/01-init.groovy
COPY jenkins-pipeline.groovy /usr/share/jenkins/ref/jenkins-pipeline.groovy

ENV SKILLSPECTOR_LOG_LEVEL=WARNING
ENV SKILLSPECTOR_PROVIDER=openai

USER jenkins
DOCKERFILE_EOF

# ---- 生成 Jenkins Pipeline ----
cat > "${WORK_DIR}/repo/jenkins-pipeline.groovy" <<'PIPELINE_EOF'
pipeline {
    agent any

    options {
        timestamps()
        skipDefaultCheckout()
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }

    environment {
        PATH = "/usr/local/bin:${env.PATH}"
        SRC_DIR = "${WORKSPACE}/src"
        REPORT_DIR = "${WORKSPACE}/reports"
    }

    parameters {
        string(name: 'GIT_URL', defaultValue: 'https://github.com/JunchengDwain/SkillSpector.git',
               description: 'Git Repository URL to clone')
        string(name: 'REF', defaultValue: 'main',
               description: 'Branch / Tag / Commit SHA')
        string(name: 'SKILL_PATH', defaultValue: '',
               description: 'Relative Skill Path (leave empty for repo root)')
        string(name: 'SCANNERS', defaultValue: 'skillspector',
               description: 'Comma separated scanners')
    }

    stages {
        stage("Checkout") {
            steps {
                git url: "${params.GIT_URL}",
                    branch: "${params.REF}"
            }
        }

        stage("Detect Skill") {
            steps {
                script {
                    if (params.SKILL_PATH?.trim()) {
                        SKILL_DIR = "${WORKSPACE}/${params.SKILL_PATH}"
                    } else {
                        SKILL_DIR = "${WORKSPACE}"
                    }
                    sh "ls -la \$(realpath '${SKILL_DIR}')/"

                    SCANNER_LIST = params.SCANNERS.split(",").collect { it.trim() }.findAll { it }
                    echo "Scan dir  : ${SKILL_DIR}"
                    echo "Scanners  : ${SCANNER_LIST}"
                }
            }
        }

        stage("Parallel Scan") {
            steps {
                script {
                    def jobs = [:]
                    SCANNER_LIST.each { scanner ->
                        jobs[scanner] = {
                            switch(scanner) {
                                case "skillspector":
                                    sh """
                                        set -ux

                                        mkdir -p "${REPORT_DIR}/${scanner}"

                                        docker run --rm \\
                                            -v "${SKILL_DIR}:/skill:ro" \\
                                            -v "${REPORT_DIR}/${scanner}:/reports" \\
                                            skillspector:latest \\
                                            skillspector scan \\
                                                /skill \\
                                                --no-llm \\
                                                --format json -o /reports/report.json \\
                                                --format markdown -o /reports/report.md || true
                                    """
                                    break
                                default:
                                    error("Unknown scanner: ${scanner}")
                            }
                        }
                    }
                    parallel jobs
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**/*', fingerprint: true, allowEmptyArchive: true
            deleteDir()
        }
    }
}
PIPELINE_EOF

# ---- 生成 Jenkins 初始化脚本 (密码替换在下方) ----
cat > "${WORK_DIR}/repo/jenkins-init.groovy" <<'INIT_EOF'
import jenkins.model.*
import hudson.security.*
import jenkins.install.InstallState
import org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition
import hudson.model.ParametersDefinitionProperty
import hudson.model.StringParameterDefinition

def instance = Jenkins.get()

// 0. 跳过 setup wizard
instance.installState = InstallState.INITIAL_SETUP_COMPLETED
println "[init] Setup wizard disabled"

// 1. 创建/重置 admin 用户
def hudsonRealm = new HudsonPrivateSecurityRealm(false)
def adminUser = hudsonRealm.getUser("admin")
if (adminUser == null) {
    hudsonRealm.createAccount("admin", "ADMIN_PASS_PLACEHOLDER")
    println "[init] admin user created"
} else {
    hudsonRealm.createAccount("admin", "ADMIN_PASS_PLACEHOLDER")
    println "[init] admin password reset"
}
instance.setSecurityRealm(hudsonRealm)

// 2. 设置授权策略
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(strategy)
instance.save()

// 3. 创建 skill-scanner Pipeline Job
def jobName = "skill-scanner"
def job = instance.getItem(jobName)

if (job == null) {
    try {
        job = instance.createProjectFromXML(jobName, new java.io.ByteArrayInputStream(
            '<?xml version="1.1" encoding="UTF-8"?><flow-definition plugin="workflow-job@2.42"/></flow-definition>'.bytes
        ))
        println "[init] ${jobName} job created"
    } catch (Exception e) {
        println "[init] createProjectFromXML failed: ${e.message}"
        // 回退方案: 手动创建 job 目录和 config.xml，然后 reload
        def jobsDir = new File(instance.getRootDir(), "jobs/${jobName}")
        jobsDir.mkdirs()
        def configFile = new File(jobsDir, "config.xml")
        configFile.text = '<?xml version="1.1" encoding="UTF-8"?><flow-definition plugin="workflow-job@2.42"><actions/><description></description><keepDependencies>false</keepDependencies><properties><hudson.model.ParametersDefinitionProperty><parameterDefinitions><hudson.model.StringParameterDefinition><name>GIT_URL</name><description>Git Repository URL to clone</description><defaultValue>https://github.com/JunchengDwain/SkillSpector.git</defaultValue><trim>false</trim></hudson.model.StringParameterDefinition><hudson.model.StringParameterDefinition><name>REF</name><description>Branch / Tag / Commit SHA</description><defaultValue>main</defaultValue><trim>false</trim></hudson.model.StringParameterDefinition><hudson.model.StringParameterDefinition><name>SKILL_PATH</name><description>Relative Skill Path</description><defaultValue></defaultValue><trim>false</trim></hudson.model.StringParameterDefinition><hudson.model.StringParameterDefinition><name>SCANNERS</name><description>Comma separated scanners</description><defaultValue>skillspector</defaultValue><trim>false</trim></hudson.model.StringParameterDefinition></parameterDefinitions></hudson.model.ParametersDefinitionProperty></properties><definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps@2.94"><script/><sandbox>true</sandbox></definition><triggers/><disabled>false</disabled></flow-definition>'
        instance.reload()
        println "[init] ${jobName} job created via fallback, reloaded"
        job = instance.getItem(jobName)
    }
} else {
    println "[init] ${jobName} job already exists, updating definition"
}

// 读取 Pipeline 脚本
def pipelineFile = new File("/usr/share/jenkins/ref/jenkins-pipeline.groovy")
def pipelineScript = pipelineFile.text
job.definition = new CpsFlowDefinition(pipelineScript, true)

// 添加参数
def params = new ParametersDefinitionProperty([
    new StringParameterDefinition("GIT_URL", "https://github.com/JunchengDwain/SkillSpector.git", "Git Repository URL to clone"),
    new StringParameterDefinition("REF", "main", "Branch / Tag / Commit SHA"),
    new StringParameterDefinition("SKILL_PATH", "", "Relative Skill Path"),
    new StringParameterDefinition("SCANNERS", "skillspector", "Comma separated scanners")
])
job.addProperty(params)
job.save()
instance.save()

println "[init] Initialization complete: admin user and skill-scanner job ready"
INIT_EOF

# 替换密码占位符
if [ "$(uname -s)" = "Darwin" ]; then
    sed -i '' "s/ADMIN_PASS_PLACEHOLDER/${JENKINS_ADMIN_PASS}/g" "${WORK_DIR}/repo/jenkins-init.groovy"
else
    sed -i "s/ADMIN_PASS_PLACEHOLDER/${JENKINS_ADMIN_PASS}/g" "${WORK_DIR}/repo/jenkins-init.groovy"
fi

# 复制 Docker CLI 二进制到仓库目录
cp -r "${WORK_DIR}/docker-bin" "${WORK_DIR}/repo/docker-bin"

log_info "构建文件已生成: Dockerfile.jenkins, jenkins-pipeline.groovy, jenkins-init.groovy"

# ---- 构建镜像 ----
log_step "4/6 构建 Docker 镜像"

cd "${WORK_DIR}/repo"

# 4a. 构建 Jenkins 镜像
docker build -f Dockerfile.jenkins -t "${IMAGE_NAME}" . 2>&1 | tail -40

if ! docker image inspect "${IMAGE_NAME}" &>/dev/null; then
    log_error "Jenkins 镜像构建失败"
    exit 1
fi
log_info "Jenkins 镜像构建成功: ${IMAGE_NAME}"

# 4b. 构建 skillspector 镜像 (Pipeline 中 docker run 需要)
log_info "构建 skillspector:latest 镜像..."
# 使用仓库中的 Dockerfile，添加 apt 镜像加速
cat > "${WORK_DIR}/repo/Dockerfile.skillspector" <<'SKILLSPECTOR_DOCKERFILE'
FROM python:3.12-slim AS builder

RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/

RUN python -m venv .venv \
    && .venv/bin/pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ \
    && .venv/bin/pip config set global.trusted-host mirrors.aliyun.com \
    && .venv/bin/pip config set global.timeout 120 \
    && .venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim

RUN sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /scan

CMD ["/bin/bash"]
SKILLSPECTOR_DOCKERFILE

docker build -f Dockerfile.skillspector -t skillspector:latest "${WORK_DIR}/repo" 2>&1 | tail -20

if ! docker image inspect skillspector:latest &>/dev/null; then
    log_error "skillspector 镜像构建失败"
    exit 1
fi
log_info "skillspector:latest 镜像构建成功"

# ---- 启动容器 ----
log_step "5/6 启动 Jenkins 容器"

# 清理旧容器
docker stop "${CONTAINER_NAME}" 2>/dev/null || true
docker rm "${CONTAINER_NAME}" 2>/dev/null || true

mkdir -p "${JENKINS_HOME_DIR}"
chown -R 1000:1000 "${JENKINS_HOME_DIR}"
log_info "Jenkins 数据目录权限已设置: ${JENKINS_HOME_DIR}"

DOCKER_GID=$(stat -c '%g' "$DOCKER_SOCKET" 2>/dev/null || stat -f '%g' "$DOCKER_SOCKET" 2>/dev/null || echo "0")

if [ "$OS" = "macos" ]; then
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${JENKINS_HTTP_PORT}:8080" \
        -p "${JENKINS_AGENT_PORT}:50000" \
        -v "${JENKINS_HOME_DIR}:/var/jenkins_home" \
        -v "${DOCKER_SOCKET}:${DOCKER_SOCKET}" \
        "${IMAGE_NAME}"
else
    docker run -d \
        --name "${CONTAINER_NAME}" \
        --restart unless-stopped \
        -p "${JENKINS_HTTP_PORT}:8080" \
        -p "${JENKINS_AGENT_PORT}:50000" \
        -v "${JENKINS_HOME_DIR}:/var/jenkins_home" \
        -v "${DOCKER_SOCKET}:${DOCKER_SOCKET}" \
        --group-add "${DOCKER_GID}" \
        "${IMAGE_NAME}"
fi

log_info "容器已启动: ${CONTAINER_NAME}"

# ---- 等待 Jenkins 就绪 ----
log_step "6/6 等待 Jenkins 就绪"

MAX_WAIT=300
WAITED=0
JENKINS_URL="http://127.0.0.1:${JENKINS_HTTP_PORT}"

log_info "等待 Jenkins 启动 (最多 ${MAX_WAIT}s)..."

while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s -m 3 -o /dev/null -w "%{http_code}" "${JENKINS_URL}/login" 2>/dev/null | grep -q "200"; then
        log_info "Jenkins 已就绪 (耗时 ${WAITED}s)"
        break
    fi
    sleep 5
    WAITED=$((WAITED + 5))
    [ $((WAITED % 30)) -eq 0 ] && log_info "  已等待 ${WAITED}s..."
done

if [ $WAITED -ge $MAX_WAIT ]; then
    log_error "Jenkins 启动超时，检查日志: docker logs ${CONTAINER_NAME}"
    exit 1
fi

sleep 10

# ---- 等待 init groovy 执行完成 ----
log_info "等待 init 脚本执行..."
sleep 10

# 检查 init 脚本是否执行成功
INIT_OK=false
for i in $(seq 1 6); do
    if docker logs "${CONTAINER_NAME}" 2>&1 | grep -q "Initialization complete"; then
        log_info "init 脚本执行成功"
        INIT_OK=true
        break
    fi
    if [ $i -lt 6 ]; then
        log_info "  等待 init 脚本... (${i}/6)"
        sleep 10
    fi
done
if ! $INIT_OK; then
    log_warn "未检测到 init 脚本成功日志，检查 Jenkins 日志:"
    docker logs "${CONTAINER_NAME}" 2>&1 | grep -i "init\|error\|exception" | grep -v "Picked up\|UpdateCenter\|NodeMonitors\|ComputerSet\|AtomicFile" | tail -10
fi

# ---- 验证 ----
log_info "验证 admin 登录..."
HTTP_CODE=$(curl -s -m 5 -u "admin:${JENKINS_ADMIN_PASS}" -o /dev/null -w "%{http_code}" "${JENKINS_URL}/" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    log_info "admin 登录验证通过"
else
    log_warn "admin 登录返回 HTTP ${HTTP_CODE}，再等 15s..."
    sleep 15
    HTTP_CODE=$(curl -s -m 5 -u "admin:${JENKINS_ADMIN_PASS}" -o /dev/null -w "%{http_code}" "${JENKINS_URL}/" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        log_info "admin 登录验证通过 (重试)"
    else
        log_warn "admin 登录仍然失败 (HTTP ${HTTP_CODE})"
        log_warn "如果 Jenkins 显示 setup wizard，请手动完成初始化后重新部署"
        log_warn "提示: 删除 ${JENKINS_HOME_DIR} 后重新执行此脚本可清除旧状态"
    fi
fi

log_info "验证 skill-scanner Job..."
JOB_CHECK=$(curl -s -m 5 -u "admin:${JENKINS_ADMIN_PASS}" "${JENKINS_URL}/job/skill-scanner/api/json" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('name','NOT_FOUND'))" 2>/dev/null || echo "NOT_FOUND")
if [ "$JOB_CHECK" = "skill-scanner" ]; then
    log_info "skill-scanner Job 已创建"
else
    log_warn "skill-scanner Job 未创建 (检测到: ${JOB_CHECK})"
    log_warn "如果 Jenkins 是新版 LTS，可能需要手动完成 setup wizard 后，init 脚本才会执行"
    log_warn "提示: 删除 ${JENKINS_HOME_DIR} 后重新执行此脚本可清除旧状态"
fi

# ---- 获取 IP ----
if [ "$OS" = "macos" ]; then
    SERVER_IP=$(ifconfig 2>/dev/null | awk '/inet / && !/127.0.0.1/{print $2}' | head -1)
else
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' | head -1)
    [ -z "$SERVER_IP" ] && SERVER_IP=$(ip -4 addr show 2>/dev/null | awk '/inet / && !/127.0.0.1/{print $2}' | cut -d/ -f1 | head -1)
fi
[ -z "$SERVER_IP" ] && SERVER_IP="<服务器IP>"

# ---- 输出 ----
echo ""
echo "======================================================================"
echo -e "  ${GREEN}SkillSpector + Jenkins 部署完成!${NC}"
echo "======================================================================"
echo ""
echo "  Jenkins:  http://${SERVER_IP}:${JENKINS_HTTP_PORT}/"
echo "  Job:      http://${SERVER_IP}:${JENKINS_HTTP_PORT}/job/skill-scanner/"
echo "  账号:     admin"
echo "  密码:     ${JENKINS_ADMIN_PASS}"
echo ""
echo "----------------------------------------------------------------------"
echo "  触发扫描:"
echo "----------------------------------------------------------------------"
echo ""
echo "  COOKIE_JAR=\$(mktemp)"
echo "  CRUMB=\$(curl -s -c \"\$COOKIE_JAR\" \\"
echo "    -u \"admin:${JENKINS_ADMIN_PASS}\" \\"
echo "    \"${JENKINS_URL}/crumbIssuer/api/json\" \\"
echo "    | python3 -c \"import sys,json; print(json.load(sys.stdin)['crumb'])\")"
echo ""
echo "  curl -s -b \"\$COOKIE_JAR\" \\"
echo "    -u \"admin:${JENKINS_ADMIN_PASS}\" \\"
echo "    -H \"Jenkins-Crumb:\$CRUMB\" \\"
echo "    -X POST \"${JENKINS_URL}/job/skill-scanner/buildWithParameters\" \\"
echo "    --data-urlencode 'GIT_URL=https://github.com/JunchengDwain/SkillSpector.git' \\"
echo "    --data-urlencode 'REF=main' \\"
echo "    --data-urlencode 'SKILL_PATH=' \\"
echo "    --data-urlencode 'SCANNERS=skillspector'"
echo ""
echo "----------------------------------------------------------------------"
echo "  查询状态 / 下载报告:"
echo "----------------------------------------------------------------------"
echo ""
echo "  curl -s -u \"admin:${JENKINS_ADMIN_PASS}\" \\"
echo "    \"${JENKINS_URL}/job/skill-scanner/lastBuild/api/json\""
echo ""
echo "  curl -s -u \"admin:${JENKINS_ADMIN_PASS}\" -o report.json \\"
echo "    \"${JENKINS_URL}/job/skill-scanner/lastBuild/artifact/reports/skillspector/report.json\""
echo ""
echo "  curl -s -u \"admin:${JENKINS_ADMIN_PASS}\" -o report.md \\"
echo "    \"${JENKINS_URL}/job/skill-scanner/lastBuild/artifact/reports/skillspector/report.md\""
echo ""
echo "======================================================================"
echo "  管理: docker logs -f ${CONTAINER_NAME}"
echo "======================================================================"
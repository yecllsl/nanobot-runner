#!/usr/bin/env bash
# =============================================================================
# Nanobot Runner 安装脚本
# 桌面端私人AI跑步助理 - 一键安装
#
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash
#   或指定版本和目录:
#   curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash -s -- --version v0.9.3 --dir ~/my-runner
#   或先下载再执行:
#   bash install.sh [--version TAG] [--dir PATH] [--skip-uv] [--verbose]
# =============================================================================

set -euo pipefail

# ---- 配置 ----
REPO_OWNER="yecllsl"
REPO_NAME="nanobot-runner"
REPO_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}.git"
DEFAULT_VERSION="main"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11
DATA_DIR="${HOME}/.nanobot-runner"

# ---- 颜色 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ---- 工具函数 ----
info()    { echo -e "${BLUE}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

separator() {
    echo -e "${CYAN}──────────────────────────────────────────────────${RESET}"
}

banner() {
    echo ""
    separator
    echo -e "${BOLD}${CYAN}  _   _                  _   _           _             ${RESET}"
    echo -e "${BOLD}${CYAN} | \\ | | __ _ _ __   __| | | |__   __ _| |_ ___ _ __  ${RESET}"
    echo -e "${BOLD}${CYAN} |  \\| |/ _\` | '_ \\ / _\` | | '_ \\ / _\` | __/ _ \\ '__| ${RESET}"
    echo -e "${BOLD}${CYAN} | |\\  | (_| | | | | (_| | | |_) | (_| | ||  __/ |    ${RESET}"
    echo -e "${BOLD}${CYAN} |_| \\_|\\__,_|_| |_|\\__,_| |_.__/ \\__,_|\\__\\___|_|    ${RESET}"
    echo -e "${BOLD}${CYAN}  Runner - 桌面端私人AI跑步助理${RESET}"
    separator
    echo ""
}

# ---- 版本比较 ----
version_ge() {
    local major="$1" minor="$2" req_major="$3" req_minor="$4"
    if [ "$major" -gt "$req_major" ]; then
        return 0
    elif [ "$major" -eq "$req_major" ] && [ "$minor" -ge "$req_minor" ]; then
        return 0
    fi
    return 1
}

# ---- 检测 Python ----
detect_python() {
    local py_cmd=""
    local py_version=""

    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            py_version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
            local major minor
            major=$(echo "$py_version" | cut -d. -f1)
            minor=$(echo "$py_version" | cut -d. -f2)

            if version_ge "$major" "$minor" "$MIN_PYTHON_MAJOR" "$MIN_PYTHON_MINOR"; then
                py_cmd="$cmd"
                break
            fi
        fi
    done

    echo "$py_cmd"
}

# ---- 安装 uv ----
install_uv() {
    if [ "$SKIP_UV" = true ]; then
        warn "跳过 uv 安装 (--skip-uv)"
        return 0
    fi

    if command -v uv &>/dev/null; then
        local uv_version
        uv_version=$(uv --version 2>/dev/null || echo "unknown")
        success "uv 已安装: $uv_version"
        return 0
    fi

    info "正在安装 uv 包管理器..."

    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh 2>/dev/null
    else
        error "需要 curl 或 wget 来安装 uv"
        error "请手动安装 uv: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    if command -v uv &>/dev/null; then
        success "uv 安装成功: $(uv --version)"
    else
        export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"
        if command -v uv &>/dev/null; then
            success "uv 安装成功: $(uv --version)"
        else
            error "uv 安装失败，请手动安装: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
        fi
    fi
}

# ---- 克隆仓库 ----
clone_repo() {
    local target_dir="$1"
    local version="$2"

    if [ -d "${target_dir}/.git" ]; then
        info "检测到已有仓库: ${target_dir}"
        cd "$target_dir"
        git fetch --tags 2>/dev/null || true
        git checkout "$version" 2>/dev/null || true
        success "已切换到 ${version}"
        return 0
    fi

    if [ -d "$target_dir" ]; then
        warn "目录已存在但非 Git 仓库: ${target_dir}"
        warn "将备份后重新克隆"
        mv "$target_dir" "${target_dir}.bak.$(date +%Y%m%d%H%M%S)"
    fi

    info "正在克隆仓库 [${version}]..."
    if [ "$version" = "main" ] || [ "$version" = "master" ]; then
        git clone --depth 1 "$REPO_URL" "$target_dir" 2>/dev/null
    else
        git clone --depth 1 --branch "$version" "$REPO_URL" "$target_dir" 2>/dev/null
    fi

    if [ $? -ne 0 ]; then
        error "克隆仓库失败，请检查网络连接或版本号: ${version}"
        exit 1
    fi

    success "仓库克隆完成"
}

# ---- 安装依赖 ----
install_dependencies() {
    local target_dir="$1"

    cd "$target_dir"

    info "正在创建虚拟环境..."
    uv venv 2>/dev/null
    success "虚拟环境创建完成"

    info "正在安装依赖 (可能需要几分钟)..."
    uv sync --all-extras 2>/dev/null
    success "依赖安装完成"
}

# ---- 初始化配置目录 ----
init_config_dirs() {
    info "正在初始化配置目录..."

    mkdir -p "${DATA_DIR}/data"
    mkdir -p "${DATA_DIR}/memory"
    mkdir -p "${DATA_DIR}/sessions"

    if [ ! -f "${DATA_DIR}/config.json" ]; then
        if [ -f "config.example.json" ]; then
            cp config.example.json "${DATA_DIR}/config.json"
            info "已创建默认配置: ${DATA_DIR}/config.json"
        fi
    fi

    success "配置目录初始化完成: ${DATA_DIR}"
}

# ---- 生成启动脚本 ----
generate_run_script() {
    local target_dir="$1"
    local script_path="${target_dir}/run.sh"

    cat > "$script_path" << 'RUNSCRIPT'
#!/usr/bin/env bash
# Nanobot Runner 启动脚本
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || . .venv/bin/activate
uv run nanobotrun "$@"
RUNSCRIPT
    chmod +x "$script_path"
    success "启动脚本已生成: ${script_path}"
}

# ---- 打印安装结果 ----
print_result() {
    local target_dir="$1"

    echo ""
    separator
    success "Nanobot Runner 安装完成！"
    separator
    echo ""
    echo -e "${BOLD}项目目录:${RESET}   ${target_dir}"
    echo -e "${BOLD}数据目录:${RESET}   ${DATA_DIR}"
    echo -e "${BOLD}配置文件:${RESET}   ${DATA_DIR}/config.json"
    echo ""
    echo -e "${BOLD}快速开始:${RESET}"
    echo ""
    echo -e "  ${CYAN}cd ${target_dir}${RESET}"
    echo ""
    echo -e "  ${CYAN}# 导入跑步数据${RESET}"
    echo -e "  uv run nanobotrun data import /path/to/activity.fit"
    echo ""
    echo -e "  ${CYAN}# 查看统计${RESET}"
    echo -e "  uv run nanobotrun data stats"
    echo ""
    echo -e "  ${CYAN}# VDOT 分析${RESET}"
    echo -e "  uv run nanobotrun analysis vdot"
    echo ""
    echo -e "  ${CYAN}# AI 助手${RESET}"
    echo -e "  uv run nanobotrun agent chat"
    echo ""
    echo -e "  ${CYAN}# 或使用启动脚本${RESET}"
    echo -e "  ./run.sh data stats"
    echo ""
    echo -e "${YELLOW}提示: 请编辑 ${DATA_DIR}/config.json 配置 LLM 和飞书通道${RESET}"
    echo ""
    separator
}

# ---- 参数解析 ----
INSTALL_VERSION="$DEFAULT_VERSION"
INSTALL_DIR=""
SKIP_UV=false
VERBOSE=false

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --version)
                INSTALL_VERSION="$2"
                shift 2
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --skip-uv)
                SKIP_UV=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                echo "Nanobot Runner 安装脚本"
                echo ""
                echo "用法: bash install.sh [选项]"
                echo ""
                echo "选项:"
                echo "  --version TAG    安装指定版本 (默认: main)"
                echo "  --dir PATH       安装到指定目录 (默认: ~/.nanobot-runner-app)"
                echo "  --skip-uv        跳过 uv 安装"
                echo "  --verbose        详细输出"
                echo "  --help           显示帮助"
                echo ""
                echo "示例:"
                echo "  bash install.sh"
                echo "  bash install.sh --version v0.9.3"
                echo "  bash install.sh --dir ~/apps/nanobot-runner"
                echo "  curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash -s -- --version v0.9.3"
                exit 0
                ;;
            *)
                error "未知参数: $1"
                error "使用 --help 查看帮助"
                exit 1
                ;;
        esac
    done

    if [ -z "$INSTALL_DIR" ]; then
        INSTALL_DIR="${HOME}/.nanobot-runner-app"
    fi
}

# ---- 主函数 ----
main() {
    parse_args "$@"

    if [ "$VERBOSE" = true ]; then
        set -x
    fi

    banner

    info "安装版本: ${INSTALL_VERSION}"
    info "安装目录: ${INSTALL_DIR}"
    echo ""

    # 1. 检测 Python
    info "正在检测 Python 环境..."
    local py_cmd
    py_cmd=$(detect_python)

    if [ -z "$py_cmd" ]; then
        error "未找到 Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+"
        error "请安装 Python: https://www.python.org/downloads/"
        exit 1
    fi

    local py_version
    py_version=$("$py_cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    success "Python: ${py_version} (${py_cmd})"
    echo ""

    # 2. 检测/安装 Git
    if ! command -v git &>/dev/null; then
        error "未找到 git，请先安装 Git"
        exit 1
    fi
    success "Git: $(git --version)"
    echo ""

    # 3. 安装 uv
    install_uv
    echo ""

    # 4. 克隆仓库
    clone_repo "$INSTALL_DIR" "$INSTALL_VERSION"
    echo ""

    # 5. 安装依赖
    install_dependencies "$INSTALL_DIR"
    echo ""

    # 6. 初始化配置
    init_config_dirs
    echo ""

    # 7. 生成启动脚本
    generate_run_script "$INSTALL_DIR"
    echo ""

    # 8. 打印结果
    print_result "$INSTALL_DIR"
}

# ---- 入口 ----
# 脚本主体放在函数内，防止管道执行时部分下载导致异常
main "$@"

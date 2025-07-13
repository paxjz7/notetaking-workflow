#!/bin/bash

# AI研究工作流快速启动脚本
# 作者: AI Research Team
# 版本: 1.0.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_msg() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查Python版本
check_python() {
    print_step "检查Python版本..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装，请先安装Python 3.8+"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.8"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        print_error "Python版本 $python_version 不符合要求，需要 $required_version 或更高版本"
        exit 1
    fi
    
    print_msg "Python版本 $python_version 符合要求"
}

# 检查pip
check_pip() {
    print_step "检查pip..."
    
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 未安装，请先安装pip"
        exit 1
    fi
    
    print_msg "pip3 已安装"
}

# 创建虚拟环境
create_venv() {
    print_step "创建虚拟环境..."
    
    if [ -d "venv" ]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        python3 -m venv venv
        print_msg "虚拟环境创建成功"
    fi
}

# 激活虚拟环境
activate_venv() {
    print_step "激活虚拟环境..."
    source venv/bin/activate
    print_msg "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    print_step "安装依赖包..."
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_msg "依赖包安装完成"
    else
        print_error "requirements.txt 文件不存在"
        exit 1
    fi
}

# 配置环境变量
configure_env() {
    print_step "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_msg "已创建 .env 文件"
            print_warning "请编辑 .env 文件，配置必要的API密钥"
            print_warning "至少需要配置以下之一："
            print_warning "  - OPENAI_API_KEY (OpenAI API密钥)"
            print_warning "  - LOCAL_LLM_URL (本地LLM服务地址)"
            print_warning "  - PUBMED_EMAIL (PubMed搜索邮箱)"
        else
            print_error ".env.example 文件不存在"
            exit 1
        fi
    else
        print_msg ".env 文件已存在"
    fi
}

# 测试配置
test_config() {
    print_step "测试配置..."
    
    if python3 main.py --config-check "test" 2>/dev/null; then
        print_msg "配置验证通过"
    else
        print_error "配置验证失败，请检查 .env 文件"
        print_warning "运行以下命令查看详细错误信息："
        print_warning "  python3 main.py --config-check test"
        exit 1
    fi
}

# 显示使用说明
show_usage() {
    print_step "使用说明"
    echo ""
    echo "程序已准备就绪！使用方法："
    echo ""
    echo "1. 激活虚拟环境："
    echo "   source venv/bin/activate"
    echo ""
    echo "2. 运行程序："
    echo "   python3 main.py \"研究关键词\""
    echo ""
    echo "3. 查看帮助："
    echo "   python3 main.py --help"
    echo ""
    echo "4. 示例命令："
    echo "   python3 main.py \"人工智能\""
    echo "   python3 main.py \"机器学习\" --details"
    echo "   python3 main.py \"深度学习\" --no-save"
    echo ""
    echo "5. 结果文件："
    echo "   - JSON数据: results/research_关键词_时间戳.json"
    echo "   - 研究报告: results/report_关键词_时间戳.md"
    echo ""
}

# 主函数
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    AI研究工作流快速启动脚本${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_python
    check_pip
    create_venv
    activate_venv
    install_dependencies
    configure_env
    
    echo ""
    print_msg "安装完成！"
    
    # 询问是否测试配置
    echo ""
    read -p "是否测试配置? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        test_config
    else
        print_warning "跳过配置测试，请确保 .env 文件配置正确"
    fi
    
    echo ""
    show_usage
}

# 检查是否为bash
if [ -z "$BASH_VERSION" ]; then
    echo "此脚本需要bash运行"
    exit 1
fi

# 运行主函数
main "$@"
#!/bin/bash
# WSL环境部署脚本

echo "🐧 开始WSL环境部署..."

# 1. 检查conda环境
if ! command -v conda &> /dev/null; then
    echo "❌ Conda未安装，请先安装miniconda"
    exit 1
fi

# 2. 创建conda环境
echo "📦 创建conda环境..."
conda create -n youtube-summary python=3.11 -y

# 3. 激活环境并安装依赖
echo "📥 安装Python依赖..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate youtube-summary

# 安装基础包
pip install loguru python-dotenv

# 如果需要完整功能，安装额外依赖
read -p "是否安装完整依赖包（包括YouTube和Gemini API）？(y/n): " install_full

if [[ $install_full == "y" || $install_full == "Y" ]]; then
    pip install -r requirements.txt
    echo "✅ 完整依赖安装完成"
else
    echo "✅ 基础依赖安装完成，仅可运行事件驱动架构测试"
fi

# 4. 创建配置文件
echo "⚙️ 创建配置文件..."
cat > .env << EOL
# WSL环境配置
GEMINI_API_KEY=your_gemini_api_key_here
OBSIDIAN_VAULT_PATH=~/Documents/ObsidianVault
MAX_SEARCH_RESULTS=3
GEMINI_RPM_LIMIT=5

# 事件系统配置
EVENT_STORE_TYPE=file
EVENT_STORE_PATH=./data/events
CIRCUIT_BREAKER_ENABLED=true
API_FAILURE_THRESHOLD=5
API_RECOVERY_TIMEOUT=300
EOL

# 5. 创建Obsidian vault目录
echo "📁 创建Obsidian vault目录..."
mkdir -p ~/Documents/ObsidianVault
mkdir -p ./data/events
mkdir -p ./logs

# 6. 创建启动脚本
cat > run_system.sh << 'EOL'
#!/bin/bash
# 启动脚本

# 激活conda环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate youtube-summary

# 检查参数
if [ $# -eq 0 ]; then
    echo "使用方法: ./run_system.sh <搜索关键词>"
    echo "示例: ./run_system.sh '人工智能教程'"
    exit 1
fi

# 运行事件驱动系统（测试版本）
echo "🚀 启动事件驱动系统..."
python test_event_system.py "$1"
EOL

chmod +x run_system.sh

echo "✅ WSL环境部署完成！"
echo ""
echo "📝 接下来的步骤："
echo "1. 编辑 .env 文件，添加您的Gemini API密钥"
echo "2. 运行测试: ./run_system.sh '人工智能教程'"
echo "3. 查看生成的文档: ls -la ~/Documents/ObsidianVault/"
echo ""
echo "🔧 激活环境命令:"
echo "conda activate youtube-summary"
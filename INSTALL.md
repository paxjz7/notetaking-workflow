# 安装指南

## 快速开始

### 方法1: 使用快速启动脚本 (推荐)

```bash
# 1. 运行快速启动脚本
./quick_start.sh

# 2. 根据提示编辑配置文件
nano .env

# 3. 运行程序
source venv/bin/activate
python3 main.py "人工智能"
```

### 方法2: 手动安装

```bash
# 1. 检查Python版本 (需要3.8+)
python3 --version

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
nano .env

# 5. 测试配置
python3 main.py --config-check test

# 6. 运行程序
python3 main.py "研究关键词"
```

## 配置说明

### 必须配置项

**LLM服务** (至少选择一个)：
- `GEMINI_API_KEY`: Google Gemini API密钥 (推荐)
- `OPENAI_API_KEY`: OpenAI API密钥
- `LOCAL_LLM_URL`: 本地LLM服务地址

**搜索服务**：
- `PUBMED_EMAIL`: PubMed搜索需要的邮箱地址

### 可选配置项

- `GEMINI_MODEL`: Gemini模型名称 (默认: gemini-1.5-flash)
- `OPENAI_MODEL`: OpenAI模型名称 (默认: gpt-4o-mini)
- `SEARCH_DELAY`: 搜索间隔秒数 (默认: 1)
- `MAX_SEARCH_RESULTS`: 每个查询的最大结果数 (默认: 10)

## 常见问题

### Q: 如何获取Gemini API密钥？
A: 访问 https://makersuite.google.com/app/apikey 注册并获取API密钥

### Q: 如何获取OpenAI API密钥？
A: 访问 https://platform.openai.com/api-keys 注册并获取API密钥

### Q: 如何使用本地LLM？
A: 安装Ollama或类似工具，启动本地LLM服务，然后在.env中配置LOCAL_LLM_URL

### Q: PubMed搜索需要什么？
A: 只需要提供一个有效的邮箱地址，PubMed API是免费的

### Q: 程序运行失败怎么办？
A: 
1. 检查Python版本是否为3.8+
2. 确认所有依赖都已安装
3. 验证.env文件配置正确
4. 查看错误日志中的具体信息

## 测试

运行测试脚本验证安装：
```bash
python3 test_workflow.py
```

运行配置检查：
```bash
python3 main.py --config-check test
```

## 下一步

安装完成后，请参考 [README.md](README.md) 了解详细使用方法。
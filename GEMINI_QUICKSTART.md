# 🚀 Gemini快速开始指南

本指南将帮助您快速配置和使用Google Gemini API。

## 1. 获取API密钥

### 步骤1：访问Google AI Studio
打开 [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)

### 步骤2：登录Google账号
使用您的Google账号登录

### 步骤3：创建API密钥
1. 点击 "Create API Key" 按钮
2. 选择现有项目或创建新项目
3. 复制生成的API密钥 (以 `AI...` 开头)

## 2. 配置程序

### 步骤1：创建配置文件
```bash
cp .env.example .env
```

### 步骤2：编辑配置文件
```bash
nano .env
```

### 步骤3：配置Gemini API
```bash
# Google Gemini API配置
GEMINI_API_KEY=AIzaSyA...your_actual_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# 注释掉其他LLM配置
# OPENAI_API_KEY=...
# LOCAL_LLM_URL=...

# 搜索配置
PUBMED_EMAIL=your_email@example.com
```

## 3. 运行程序

### 步骤1：安装依赖
```bash
pip install -r requirements.txt
```

### 步骤2：测试配置
```bash
python3 main.py --config-check test
```

### 步骤3：运行第一个研究
```bash
python3 main.py "人工智能"
```

## 4. 验证输出

程序应该显示：
```
✅ 使用Gemini模型: gemini-1.5-flash
🚀 启动AI驱动的研究工作流
📌 关键词: 人工智能
```

## 5. 推荐模型

| 模型 | 用途 | 特点 |
|------|------|------|
| `gemini-1.5-flash` | 日常使用 | 快速、经济 |
| `gemini-1.5-pro` | 复杂研究 | 高质量、全功能 |
| `gemini-1.0-pro` | 基础使用 | 稳定、可靠 |

## 6. 常见问题

### Q: API密钥无效
**错误**：`Invalid API key`
**解决**：
1. 检查API密钥是否完整复制
2. 确保API密钥没有多余的空格
3. 验证API密钥是否已激活

### Q: 配额超限
**错误**：`Quota exceeded`
**解决**：
1. 等待配额重置（通常是每分钟）
2. 检查免费配额使用情况
3. 考虑升级到付费计划

### Q: 网络连接问题
**错误**：`Connection timeout`
**解决**：
1. 检查网络连接
2. 尝试使用VPN
3. 确认防火墙没有阻止连接

## 7. 完整示例

```bash
# 1. 快速安装
./quick_start.sh

# 2. 配置Gemini API
echo "GEMINI_API_KEY=your_api_key_here" >> .env
echo "GEMINI_MODEL=gemini-1.5-flash" >> .env

# 3. 运行测试
python3 main.py --config-check test

# 4. 开始研究
python3 main.py "机器学习"
```

## 8. 高级配置

### 调整模型参数
编辑 `llm_client.py` 中的 `_gemini_chat_completion` 方法：

```python
generation_config = genai.types.GenerationConfig(
    temperature=0.7,        # 创造性 (0.0-1.0)
    max_output_tokens=4000, # 最大输出
    top_p=0.8,             # 核采样
    top_k=40,              # Top-K采样
)
```

### 监控API使用
访问 [Google Cloud Console](https://console.cloud.google.com/) 监控API使用情况。

## 9. 获取帮助

如果遇到问题：
1. 查看程序日志输出
2. 运行 `python3 test_workflow.py` 测试
3. 查看 [Gemini API文档](https://ai.google.dev/docs)
4. 访问 [GEMINI_SETUP.md](GEMINI_SETUP.md) 了解详细配置

---

**🎉 配置完成！现在您可以享受Gemini强大的AI研究能力了！**
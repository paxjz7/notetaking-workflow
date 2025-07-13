# Google Gemini API 配置指南

## 🚀 快速开始

### 1. 获取Gemini API密钥

1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 使用Google账号登录
3. 点击 "Create API Key" 按钮
4. 选择现有项目或创建新项目
5. 复制生成的API密钥

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# Google Gemini API配置
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# 注释掉或删除其他LLM配置
# OPENAI_API_KEY=...
# LOCAL_LLM_URL=...
```

### 3. 测试配置

```bash
# 测试配置
python3 main.py --config-check test

# 运行程序
python3 main.py "人工智能"
```

## 📋 支持的Gemini模型

| 模型名称 | 描述 | 推荐用途 |
|----------|------|----------|
| `gemini-1.5-flash` | 快速响应模型 | 日常使用 (推荐) |
| `gemini-1.5-pro` | 高质量模型 | 复杂研究任务 |
| `gemini-1.0-pro` | 标准模型 | 基础使用 |

## ⚙️ 配置选项

### 基础配置

```bash
# 必需配置
GEMINI_API_KEY=your_api_key_here

# 可选配置
GEMINI_MODEL=gemini-1.5-flash  # 默认模型
```

### 高级配置

如果需要更精细的控制，可以在代码中调整：

```python
# 在llm_client.py中的_gemini_chat_completion方法
generation_config = genai.types.GenerationConfig(
    temperature=0.7,        # 创造性 (0.0-1.0)
    max_output_tokens=4000, # 最大输出长度
    top_p=0.8,             # 核采样参数
    top_k=40,              # Top-K采样参数
)
```

## 💡 使用建议

### 1. 模型选择

- **日常使用**: `gemini-1.5-flash` (速度快，成本低)
- **重要研究**: `gemini-1.5-pro` (质量高，功能完整)
- **测试开发**: `gemini-1.0-pro` (稳定可靠)

### 2. 性能优化

```bash
# 在.env中调整参数
GEMINI_MODEL=gemini-1.5-flash  # 更快的响应
SEARCH_DELAY=0.5               # 更短的搜索延迟
MAX_SEARCH_RESULTS=15          # 更多搜索结果
```

### 3. 成本控制

- 选择合适的模型 (Flash < Pro)
- 合理设置 `max_output_tokens`
- 监控API使用量

## 🔧 故障排除

### 常见错误

1. **API密钥无效**
   ```
   错误: Invalid API key
   解决: 检查API密钥是否正确复制
   ```

2. **配额超限**
   ```
   错误: Quota exceeded
   解决: 等待配额重置或升级计划
   ```

3. **模型不存在**
   ```
   错误: Model not found
   解决: 检查模型名称是否正确
   ```

### 调试步骤

1. 验证API密钥
   ```bash
   python3 main.py --config-check test
   ```

2. 检查网络连接
   ```bash
   curl -H "x-goog-api-key: YOUR_API_KEY" \
   https://generativelanguage.googleapis.com/v1/models
   ```

3. 查看详细错误
   ```bash
   python3 main.py "测试" --details
   ```

## 📊 性能对比

| 功能 | OpenAI GPT-4 | Gemini 1.5 Flash | Gemini 1.5 Pro |
|------|--------------|-------------------|-----------------|
| 响应速度 | 中等 | 快 | 慢 |
| 输出质量 | 高 | 中高 | 高 |
| 成本 | 高 | 低 | 中 |
| 中文支持 | 良好 | 优秀 | 优秀 |
| 长文本处理 | 32K tokens | 1M tokens | 1M tokens |

## 🎯 最佳实践

### 1. 提示词优化

Gemini对中文提示词响应很好，可以直接使用中文：

```python
# config.py中的提示词已经优化适配Gemini
PROMPTS = {
    "association": "你是一位富有逻辑思维的联想大师...",
    # 其他提示词...
}
```

### 2. 并发处理

程序已经支持并发处理，Gemini可以很好地处理并行请求：

```python
# 双重评审会并行调用Gemini
review1, review2 = await asyncio.gather(
    self.llm_client.chat_completion(prompt, temperature=1.0),
    self.llm_client.chat_completion(prompt, temperature=1.0)
)
```

### 3. 错误处理

程序已包含完善的错误处理机制：

```python
# 自动重试和故障恢复
try:
    response = await self._gemini_chat_completion(prompt, temperature, max_tokens)
except Exception as e:
    print(f"Gemini API错误: {e}")
    return f"API调用失败: {str(e)}"
```

## 🌟 Gemini的优势

1. **多语言支持优秀** - 对中文理解和生成能力强
2. **长文本处理** - 支持最大1M token的输入
3. **成本效益** - 相比GPT-4更经济
4. **响应速度** - Flash模型响应速度快
5. **免费额度** - 提供慷慨的免费使用配额

## 📞 获取帮助

如果遇到问题：

1. 检查 [Google AI Studio](https://makersuite.google.com/)
2. 查看 [Gemini API文档](https://ai.google.dev/docs)
3. 运行程序的配置检查功能
4. 查看程序日志和错误信息

---

**🎉 配置完成后，享受Gemini强大的AI能力吧！**
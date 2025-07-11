# YouTube视频总结系统

一个基于YouTube搜索、Gemini AI总结和Obsidian文档生成的自动化系统，能够根据关键词搜索相关YouTube视频，下载字幕内容，使用Gemini 2.5 Pro进行智能总结，并在Obsidian中生成互相连接的文档。

## 功能特性

- 🔍 **智能搜索**: 根据关键词搜索相关YouTube视频
- 📥 **内容提取**: 自动下载视频字幕或使用视频描述
- 🤖 **AI总结**: 使用Gemini 2.5 Pro生成高质量的内容总结
- 📝 **文档生成**: 在Obsidian中创建格式化的Markdown文档
- 🔗 **智能连接**: 基于标签自动创建文档间的双向链接
- 📊 **索引管理**: 自动生成视频总结索引

## 系统架构

```
搜索查询 → YouTube搜索 → 视频信息提取 → 字幕下载 → Gemini总结 → Obsidian文档生成
```

## 安装步骤

### 1. 克隆仓库
```bash
git clone <repository-url>
cd youtube-summary-system
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
复制 `.env.example` 到 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
# Google Gemini API Key (必需)
GEMINI_API_KEY=your_gemini_api_key_here

# Obsidian Vault Path (必需 - 绝对路径)
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# YouTube搜索设置 (可选)
MAX_SEARCH_RESULTS=3
VIDEO_QUALITY=best[height<=720]

# 速率限制 (可选)
GEMINI_RPM_LIMIT=5
```

### 4. 获取Gemini API Key
1. 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 创建新的API密钥
3. 将密钥复制到 `.env` 文件中

## 使用方法

### 基本使用
```bash
python -m src.main "人工智能教程"
```

### 示例命令
```bash
# 搜索编程相关视频
python -m src.main "Python编程入门"

# 搜索技术讲座
python -m src.main "机器学习算法讲解"

# 搜索教程视频
python -m src.main "数据科学实战案例"
```

## 输出结果

系统会在您的Obsidian vault中创建以下内容：

### 1. 视频总结文档
每个视频会生成一个包含以下内容的Markdown文档：
- 视频基本信息（标题、频道、时长等）
- AI生成的内容总结
- 关键要点列表
- 相关标签
- 与其他视频的链接

### 2. 索引文档
自动生成的索引文档包含：
- 所有视频的链接列表
- 按频道分组的视频
- 汇总的所有标签

### 3. 文件结构
```
Obsidian Vault/
└── YouTube视频总结/
    ├── 视频标题1.md
    ├── 视频标题2.md  
    ├── 视频标题3.md
    └── YouTube视频总结索引_20240101_120000.md
```

## 配置选项

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| `MAX_SEARCH_RESULTS` | 最大搜索结果数量 | 3 |
| `VIDEO_QUALITY` | 视频质量设置 | `best[height<=720]` |
| `GEMINI_RPM_LIMIT` | Gemini API每分钟请求限制 | 5 |

## 技术细节

### 核心组件

1. **YouTubeProcessor**: 负责搜索和下载YouTube视频信息
2. **GeminiSummarizer**: 使用Gemini API进行内容总结
3. **ObsidianWriter**: 生成Obsidian格式的Markdown文档

### API限制处理

- 内置速率限制器确保不超出Gemini API限制
- 支持免费层级（5 RPM）和付费层级
- 自动处理API错误和重试

### 文档链接策略

- 基于共同标签自动创建文档间的链接
- 使用Obsidian的双向链接语法 `[[文档名]]`
- 自动清理文件名中的非法字符

## 故障排除

### 常见问题

1. **API密钥错误**
   ```
   错误: 缺少必要的配置项: GEMINI_API_KEY
   ```
   解决: 检查 `.env` 文件中的 `GEMINI_API_KEY` 设置

2. **Obsidian路径错误**
   ```
   错误: Obsidian vault路径不存在
   ```
   解决: 确保 `OBSIDIAN_VAULT_PATH` 指向正确的Obsidian vault目录

3. **依赖安装失败**
   ```bash
   # 尝试升级pip
   pip install --upgrade pip
   
   # 重新安装依赖
   pip install -r requirements.txt
   ```

4. **字幕下载失败**
   - 系统会自动fallback到视频描述
   - 检查网络连接
   - 某些视频可能没有可用字幕

### 日志文件

系统会在 `logs/` 目录下生成详细的日志文件：
- `app.log`: 完整的系统日志
- 日志自动轮换（每天轮换，保留7天）

## 开发指南

### 项目结构
```
src/
├── __init__.py          # 包初始化
├── config.py            # 配置管理
├── youtube_processor.py # YouTube处理器
├── gemini_summarizer.py # Gemini总结器
├── obsidian_writer.py   # Obsidian写入器
└── main.py             # 主程序入口
```

### 扩展功能

1. **添加新的内容源**: 在 `youtube_processor.py` 中扩展
2. **自定义总结模板**: 修改 `gemini_summarizer.py` 中的提示词
3. **定制文档格式**: 调整 `obsidian_writer.py` 中的模板

## 许可证

本项目基于 MIT 许可证开源。

## 贡献

欢迎提交Issue和Pull Request来改进本项目！

## 免责声明

- 请遵守YouTube服务条款和相关法律法规
- 本工具仅用于学习和研究目的
- 使用时请尊重内容创作者的版权
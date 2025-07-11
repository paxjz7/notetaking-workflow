# WSL环境配置指南

## 🔧 WSL特定配置

### 1. 文件路径配置
```bash
# WSL中的路径配置
export OBSIDIAN_VAULT_PATH="/mnt/c/Users/你的用户名/Documents/ObsidianVault"
# 或者使用WSL内部路径
export OBSIDIAN_VAULT_PATH="~/Documents/ObsidianVault"
```

### 2. 访问Windows文件系统
```bash
# 访问Windows C盘
cd /mnt/c/

# 访问Windows文档文件夹
cd /mnt/c/Users/你的用户名/Documents/

# 创建Obsidian vault在Windows侧
mkdir -p /mnt/c/Users/你的用户名/Documents/ObsidianVault
```

### 3. VSCode集成
```bash
# 在WSL中安装VSCode服务器
code .

# 安装Python扩展
# Ctrl+Shift+P -> Python: Select Interpreter -> 选择conda环境
```

### 4. 性能优化
```bash
# 在.bashrc或.zshrc中添加
echo 'export PYTHONPATH="${PYTHONPATH}:${PWD}"' >> ~/.bashrc
echo 'conda activate youtube-summary' >> ~/.bashrc

# 设置WSL内存限制（可选）
# 创建 %UserProfile%\.wslconfig 文件
[wsl2]
memory=4GB
processors=2
```

## 🚀 快速部署命令

### 一键部署
```bash
# 1. 下载项目
git clone <项目地址>
cd youtube-summary-system

# 2. 运行部署脚本
chmod +x wsl_setup.sh
./wsl_setup.sh

# 3. 配置API密钥
nano .env
# 修改 GEMINI_API_KEY=你的实际密钥

# 4. 测试运行
./run_system.sh "人工智能教程"
```

## 📁 目录结构
```
~/youtube-summary-system/
├── src/                    # 源代码
│   ├── core/              # 事件系统核心
│   ├── processors/        # 业务处理器
│   └── integration/       # 集成层
├── test_event_system.py   # 独立测试脚本
├── wsl_setup.sh          # 部署脚本
├── run_system.sh         # 启动脚本
├── .env                  # 环境配置
└── requirements.txt      # 依赖列表
```

## 🐧 WSL优势

### 为什么选择WSL？
1. **Linux环境**: 原生Linux工具和包管理
2. **Windows集成**: 无缝访问Windows文件系统
3. **性能好**: 接近原生Linux性能
4. **开发友好**: VSCode、Git等工具完美集成
5. **conda支持**: 完整的Python数据科学生态

### WSL vs 其他方案
| 方案 | 优势 | 缺点 |
|------|------|------|
| **WSL** | 性能好、集成度高、工具丰富 | 需要Windows 10+ |
| Docker | 隔离性好、部署一致 | 资源占用大、复杂度高 |
| 原生Windows | 简单直接 | 包管理复杂、兼容性问题 |
| 虚拟机 | 完全隔离 | 性能损失、资源占用大 |

## 🔧 故障排除

### 常见问题
1. **conda命令未找到**
   ```bash
   # 重新加载shell配置
   source ~/.bashrc
   # 或重启WSL
   wsl --shutdown
   ```

2. **权限问题**
   ```bash
   # 确保脚本有执行权限
   chmod +x *.sh
   ```

3. **文件路径问题**
   ```bash
   # 使用绝对路径
   realpath ~/Documents/ObsidianVault
   ```

4. **Python包导入错误**
   ```bash
   # 确保在正确的conda环境中
   conda activate youtube-summary
   which python
   ```

## 📱 移动端访问
WSL生成的文档可以通过以下方式在移动端访问：
- Obsidian mobile app (同步到手机)
- OneDrive/Dropbox 同步
- Git仓库同步
- 网络共享文件夹
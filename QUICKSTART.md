# Sys-Mentor 快速开始指南

## 🚀 第一步：安装依赖

```bash
# 激活虚拟环境（如果使用）
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 🔑 第二步：配置 API 密钥

1. 复制 `.env.example` 为 `.env`：
   ```bash
   copy .env.example .env
   ```

2. 编辑 `.env` 文件，填入你的 DeepSeek API 密钥：
   ```
   DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   DEEPSEEK_API_BASE_URL=https://api.deepseek.com/v1
   ```

## ▶️ 第三步：运行 Sys-Mentor

```bash
# 使用批处理文件（推荐）
run.bat

# 或直接运行
python main.py
```

## 💡 使用指南

### 基本用法
- 直接输入问题或命令
- Sys-Mentor 会自动判断是终端命令还是需要 AI 分析的问题

### 内置指令
- `/clear` - 清空对话历史
- `/probe` - 探测当前系统状态
- `/exit` 或 `/quit` - 退出程序

### 示例对话
```
(Sys-Mentor) > 我的 Python 环境变量有问题，pip 命令找不到

[AI 会自动:]
1. 调用 probe_system_state() 探测 PATH 变量
2. 分析问题原因
3. 给出修复建议

(Sys-Mentor) > 请帮我安装 PyTorch

[AI 会:]
1. 探测系统状态（Python 版本、CUDA 状态）
2. 推荐合适的安装命令
3. 询问你是否授权执行安装
```

## 🔍 测试工具函数

运行测试脚本验证所有工具是否正常工作：

```bash
python test_local.py
```

## 🛠️ 故障排除

### 问题：API 调用失败
- 检查 `.env` 文件中的 API 密钥是否正确
- 确认网络连接正常

### 问题：nvidia-smi not found
- 这是正常的，如果你没有 NVIDIA GPU 或驱动未安装
- 不影响 Sys-Mentor 的核心功能

### 问题：虚拟环境问题
- 删除 `venv` 文件夹
- 重新运行 `python -m venv venv`
- 重新安装依赖

## 📚 更多信息

- 查看 `ARCHITECTURE.md` 了解系统架构
- 查看 `BUGFIX_LOG.md` 了解已知问题和修复
- 查看 `PROJECT_STATUS.md` 了解项目进度

---

**作者**: Decent898  
**GitHub**: https://github.com/Decent898/Sys-Mentor

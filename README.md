# Sys-Mentor 🧠

> 一个本地终端伴随工具，像老中医一样治疗你的电脑"慢性病"

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-orange.svg)

## 🎯 核心理念

Sys-Mentor 不是一个盲目替用户敲回车、黑盒装软件的"急救包"。它像一个治疗电脑"慢性病"的老中医，或者一个循循善诱的极客导师。

**当你遇到环境配置、工业软件安装（MATLAB/SolidWorks）或系统报错时，Sys-Mentor 会：**

1. **带领你探索底层细节** - DLL 加载顺序、PATH 遍历机制、内核日志、C++ 运行库原理
2. **解释原理** - 告诉你为什么会报错，而不是直接给出安装命令
3. **循序渐进** - 像导师一样引导你理解计算机体系结构

## ✨ 核心功能

### 🔍 系统探针
自动探测系统状态：
- OS 架构、PATH 变量
- Python 解释器实际路径
- NVIDIA/CUDA 状态
- Windows 注册表信息（MSVC 运行库等）

### 🌐 联网搜索
使用 DuckDuckGo 实时检索最新解决方案：
- 社区讨论
- 技术博客
- GitHub issues

### ⚡ 命令执行（需授权）
在真实终端中执行命令：
- 必须用户明确授权 `[Y/n]`
- 捕获 stdout/stderr
- 不使用虚拟沙盒

## 📦 安装

### 方法 1：使用自动脚本（推荐）

```bash
# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh
```

### 方法 2：手动安装

```bash
# 克隆或下载项目
cd env_project

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 API 密钥
# 复制 .env.example 为 .env 并填写你的 DeepSeek API 密钥
copy .env.example .env
# 编辑 .env 文件
```

## 🚀 使用方法

### 启动

```bash
python main.py
```

### 基本用法

```
(Sys-Mentor) > 我的 Python 环境变量有问题，pip 命令找不到
```

AI 会自动：
1. 调用探针工具探测系统状态
2. 分析问题原因
3. 给出修复建议

### 内置指令

| 指令 | 说明 |
|------|------|
| `/clear` | 清空对话历史 |
| `/probe` | 探测当前系统状态 |
| `/exit` / `/quit` | 退出程序 |

## 🔧 技术栈

- **语言**: Python 3.10+
- **UI 框架**: [Rich](https://github.com/Textualize/rich) - 终端富文本
- **大模型**: DeepSeek API (支持 Tool Calling)
- **底层交互**: subprocess (真实 Shell)
- **搜索**: DuckDuckGo Search

## 📁 项目结构

```
env_project/
├── main.py              # 主程序 - REPL 循环
├── tools.py             # 核心工具函数
├── requirements.txt     # 依赖列表
├── .env.example         # 环境变量示例
├── .gitignore          # Git 忽略文件
├── run.bat             # Windows 启动脚本
├── run.sh              # Linux/Mac 启动脚本
├── test_local.py       # 本地测试脚本
├── QUICKSTART.md       # 快速开始指南
├── ARCHITECTURE.md     # 系统架构文档
├── PROJECT_STATUS.md   # 项目进度
└── venv/               # 虚拟环境（已忽略）
```

## 🛠️ 开发

### 运行测试

```bash
python test_local.py
```

### 工具函数

#### `probe_system_state()`
```python
from tools import probe_system_state

state = probe_system_state()
print(json.dumps(state, indent=2))
```

#### `search_web_for_issue(query)`
```python
from tools import search_web_for_issue

results = search_web_for_issue("Python PATH not working", max_results=3)
for r in results:
    print(r['title'])
```

#### `execute_real_command(command)`
```python
from tools import execute_real_command

result = execute_real_command("python --version")
print(result['stdout'])
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 👨‍💻 作者

**Decent898**

- GitHub: [@Decent898](https://github.com/Decent898)
- Email: decent898@gmail.com

## ⭐ 星标历史

[![Star History Chart](https://api.star-history.com/svg?repos=Decent898/Sys-Mentor&type=Date)](https://star-history.com/#Decent898/Sys-Mentor&Date)

---

**最后更新**: 2026年3月22日

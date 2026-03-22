# START HERE - Sys-Mentor 入门指南

## 🎯 你正在查看的文件

这是项目的入口点文档。如果你是第一次使用 Sys-Mentor，请按顺序阅读以下文件：

## 📚 推荐阅读顺序

### 1️⃣ 本文件 (START_HERE.md)
**目的**: 快速了解项目结构和下一步操作

### 2️⃣ README.md
**目的**: 了解 Sys-Mentor 的核心理念和功能介绍

### 3️⃣ QUICKSTART.md
**目的**: 跟随步骤安装和配置 Sys-Mentor

### 4️⃣ ARCHITECTURE.md (可选)
**目的**: 深入了解系统架构和实现细节

### 5️⃣ PROJECT_STATUS.md
**目的**: 了解当前版本的功能和已知问题

## 🚀 快速开始

### 方法 1: 使用自动脚本 (推荐)

```bash
# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh
```

### 方法 2: 手动运行

```bash
# 1. 激活虚拟环境
venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API 密钥
# 复制 .env.example 为 .env 并填写你的 DeepSeek API 密钥

# 4. 运行
python main.py
```

## 🧪 测试安装

运行测试脚本验证所有功能是否正常：

```bash
python test_local.py
```

预期输出:
```
测试 1: probe_system_state() - 系统探针
✓ 探针执行成功

测试 2: search_web_for_issue() - 网络搜索
✓ 搜索执行成功

测试 3: execute_real_command() - 命令执行
✓ 执行成功

测试 4: API 密钥配置
✓ DEEPSEEK_API_KEY 已配置

总计: 4/4 个测试通过
```

## 📖 常见问题

### Q: 什么是 Sys-Mentor？
A: Sys-Mentor 是一个本地终端伴随工具，像老中医一样治疗你的电脑"慢性病"。它不会直接给你黑盒命令，而是带你理解底层原理。

### Q: 我需要 DeepSeek API 密钥吗？
A: 是的，核心功能需要 DeepSeek API。你可以从 https://platform.deepseek.com 获取。

### Q: 支持哪些操作系统？
A: Windows、Linux 和 macOS

### Q: 会修改我的系统吗？
A: 只有在你明确授权的情况下才会执行可能修改系统的命令。

### Q: 有图形界面吗？
A: 没有。Sys-Mentor 是纯终端工具，使用 Rich 库实现漂亮的终端 UI。

## 🤝 需要帮助？

- 查看 [QUICKSTART.md](QUICKSTART.md) 获取详细安装指南
- 查看 [README.md](README.md) 了解项目 overview
- 提交 Issue: https://github.com/Decent898/Sys-Mentor/issues

## 📦 项目结构

```
env_project/
├── main.py              # 主程序
├── tools.py             # 工具函数
├── requirements.txt     # 依赖
├── .env.example         # 环境变量示例
├── run.bat             # Windows 启动脚本
├── run.sh              # Linux/Mac 启动脚本
├── test_local.py       # 测试脚本
├── README.md           # 项目介绍
├── QUICKSTART.md       # 快速开始
├── ARCHITECTURE.md     # 系统架构
├── PROJECT_STATUS.md   # 项目状态
└── BUGFIX_LOG.md       # 修复日志
```

## 🎓 学习路径

### 初学者
1. 阅读 README.md
2. 阅读 QUICKSTART.md
3. 运行测试脚本
4. 开始使用！

### 进阶用户
1. 阅读 ARCHITECTURE.md
2. 查看 tools.py 源码
3. 尝试添加自定义 Tool
4. 贡献代码！

### 开发者
1. 阅读所有文档
2. 运行测试
3. 提交 Issue 或 PR
4. 成为贡献者！

## 🌟 核心理念

> "这不是一个盲目替用户敲回车的'急救包'。它像一个治疗电脑'慢性病'的老中医，或者一个循循善诱的极客导师。"

**Sys-Mentor 的目标**:
1. 带你理解计算机底层原理
2. 教你如何诊断系统问题
3. 培养你的系统思维

## 📞 联系作者

- GitHub: [@Decent898](https://github.com/Decent898)
- Email: decent898@gmail.com

---

**祝你使用愉快！** 🎉

**最后更新**: 2026年3月22日

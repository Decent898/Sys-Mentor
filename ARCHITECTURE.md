# Sys-Mentor 系统架构文档

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户终端 (Terminal)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    main.py (REPL Loop)                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Read: 读取用户输入                                  │   │
│  │  Eval: 评估输入 (命令/问题/指令)                     │   │
│  │  Print: 打印结果 (Markdown 格式)                     │   │
│  │  Loop: 重复                                           │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
    ┌──────────────┐      ┌──────────────┐
    │ 终端命令     │      │ AI 问题      │
    └──────┬───────┘      └──────┬───────┘
           │                     │
           │                     ▼
           │              ┌──────────────┐
           │              │ tools.py     │
           │              │ ┌──────────┐ │
           │              │ │ probe_   │ │
           │              │ │ system_  │ │
           │              │ │ state()  │ │
           │              │ └──────────┘ │
           │              │ ┌──────────┐ │
           │              │ │ search_  │ │
           │              │ │ web_     │ │
           │              │ │ for_     │ │
           │              │ │ issue()  │ │
           │              │ └──────────┘ │
           │              │ ┌──────────┐ │
           │              │ │ execute_ │ │
           │              │ │ real_    │ │
           │              │ │ command()│ │
           │              │ └──────────┘ │
           │              └──────┬───────┘
           │                     │
           │                     ▼
    ┌──────┴──────┐    ┌──────────────┐
    │ subprocess  │    │ DeepSeek API │
    │ (真实 Shell)│    │ (Tool Call)  │
    └─────────────┘    └──────────────┘
```

## 📦 核心模块

### 1. main.py - 主程序模块

**职责**:
- 实现 REPL (Read-Eval-Print Loop) 循环
- 管理对话历史
- 与 DeepSeek API 交互
- 处理 Tool Call 回调
- 格式化输出结果

**关键类**:
```python
class SysMentor:
    - __init__(): 初始化 OpenAI 客户端
    - add_message(): 添加消息到历史
    - display_welcome(): 显示欢迎信息
    - display_system_state(): 探测并显示系统状态
    - execute_user_command(): 执行终端命令
    - handle_tool_call(): 处理 Tool Call
    - chat_with_deepseek(): 与 API 交互
    - print_response(): 优雅地打印回复
```

**核心流程**:
1. 用户输入 → Read
2. 判断是命令还是问题 → Eval
3. 如果是命令 → 直接执行
4. 如果是问题 → 调用 DeepSeek API
5. 如果有 Tool Call → 执行工具并回调
6. 打印结果 → Print

### 2. tools.py - 工具函数模块

**职责**:
- 实现三个核心 Tool Calling 函数
- 提供系统探测、网络搜索、命令执行功能

**核心函数**:

#### `probe_system_state() -> Dict[str, Any]`
```python
{
    "system": {
        "platform": "Windows",
        "machine": "AMD64",
        "python_version": "3.12.1",
        "python_executable": "C:\\Python312\\python.exe"
    },
    "path": ["C:\\Python312\\", "C:\\Windows\\System32\\", ...],
    "python": {
        "real_path": "C:\\Python312\\python.exe",
        "prefix": "C:\\Python312"
    },
    "gpu": {
        "nvidia_smi": {...},
        "torch_available": True,
        "cuda_available": True
    },
    "windows_specific": {
        "msvc_runtime": [...],
        "visual_studio": [...],
        "windows_sdk": [...]
    }
}
```

**实现细节**:
- 使用 `platform` 模块获取系统信息
- 使用 `sys` 模块获取 Python 信息
- 使用 `subprocess.run()` 执行 `nvidia-smi`
- 使用 `winreg` 模块读取 Windows 注册表
- 尝试导入 `torch` 检查 CUDA 支持

#### `search_web_for_issue(query: str, max_results: int = 3) -> List[Dict]`
```python
[
    {
        "title": "Result Title",
        "url": "https://example.com",
        "snippet": "Result description..."
    }
]
```

**实现细节**:
- 使用 `duckduckgo_search.DDGS` 进行搜索
- 返回前 N 条结果的标题、URL 和摘要
- 异常处理：如果库未安装，返回错误信息

#### `execute_real_command(command: str, working_dir: Optional[str] = None) -> Dict[str, str]`
```python
{
    "success": True,
    "returncode": 0,
    "stdout": "command output...",
    "stderr": "",
    "command": "python --version"
}
```

**实现细节**:
- 使用 `subprocess.run(shell=True)` 在真实 Shell 中执行
- 捕获 stdout 和 stderr
- 设置 60 秒超时
- **安全警告**: 这是一个危险工具，必须在 main.py 中询问用户授权

### 3. Tool Schema 定义

**定义位置**: `main.py` - `TOOLS` 列表

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "probe_system_state",
            "description": "...",
            "parameters": {...}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web_for_issue",
            "description": "...",
            "parameters": {...}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_real_command",
            "description": "...",
            "parameters": {...}
        }
    }
]
```

**用途**: 发送给 DeepSeek API，告诉它我们可以调用哪些工具

## 🔄 数据流

### 用户提问流程

```
用户输入 "pip 命令找不到"
    ↓
main.py: add_message("user", "pip 命令找不到")
    ↓
main.py: chat_with_deepseek()
    ↓
DeepSeek API: 返回 Tool Call (probe_system_state)
    ↓
main.py: handle_tool_call("probe_system_state", {})
    ↓
tools.py: probe_system_state() → 返回系统状态 JSON
    ↓
main.py: add_message("tool", <result>)
    ↓
DeepSeek API: 分析系统状态，返回修复建议
    ↓
main.py: print_response(Markdown 格式)
    ↓
用户看到优雅的 Markdown 输出
```

### 命令执行流程

```
AI 请求 execute_real_command("pip install torch")
    ↓
main.py: handle_tool_call("execute_real_command", {...})
    ↓
main.py: 显示命令，询问用户授权 [Y/n]
    ↓
用户输入 Y
    ↓
tools.py: execute_real_command("pip install torch")
    ↓
subprocess.run(shell=True) → 执行命令
    ↓
返回 stdout/stderr
    ↓
main.py: add_message("tool", <result>)
    ↓
DeepSeek API: 分析执行结果
    ↓
main.py: print_response()
```

## 🔐 安全机制

### 1. 用户授权
所有危险命令（`execute_real_command`）必须经过用户明确授权：

```python
if not Confirm.ask("\n[bold]授权执行? [y/N][/bold]", default=False):
    return "用户拒绝执行此命令。"
```

### 2. 超时保护
命令执行设置 60 秒超时，防止无限挂起：

```python
proc = subprocess.run(
    command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=60  # 60秒超时
)
```

### 3. 异常处理
所有工具函数都有完善的异常处理：

```python
try:
    result = some_operation()
except Exception as e:
    return {"error": str(e)}
```

## 🎨 UI 设计

### Rich 库使用

#### 1. Markdown 输出
```python
from rich.markdown import Markdown
from rich.panel import Panel

console.print(Panel(Markdown(response), title="[bold green]Sys-Mentor[/bold green]"))
```

#### 2. 交互式确认
```python
from rich.prompt import Confirm

if Confirm.ask("授权执行?"):
    # 执行命令
```

#### 3. 表格展示
```python
from rich.table import Table

table = Table(title="系统状态")
table.add_column("类别", style="cyan")
table.add_column("信息", style="green")
```

## 📝 系统提示词 (System Prompt)

**位置**: `main.py` - `SYSTEM_PROMPT` 变量

**核心要求**:
1. **不要直接给出黑盒命令**
2. **像诊断慢性病一样**：先探针，再分析
3. **解释原理 (Socratic Method)**：告诉用户为什么会报错
4. **语气**：专业、硬核、循循善诱、直击痛点

**示例对话**:

用户: "我的 Python 环境变量有问题"

❌ 黑盒回答: "运行这个命令: set PATH=%PATH%;C:\Python312"

✅ Sys-Mentor 回答:
```
我来帮你诊断这个问题。首先让我看看当前的 PATH 变量...

[探针执行中...]

我发现问题了！你的 PATH 变量中有 23 个路径，但没有 Python 的安装目录。

**原理分析**:
Windows 查找可执行文件的顺序是：
1. 当前目录
2. Windows System32 目录
3. PATH 环境变量中的每个目录

因为 Python 不在 PATH 中，所以 Windows 找不到 pip。

**修复方案**:
我将执行以下命令添加 Python 到 PATH:
  setx PATH "%PATH%;C:\Python312"

这会修改你的用户环境变量，重启终端后生效。
```

## 🚀 扩展性

### 添加新工具

1. 在 `tools.py` 中实现函数
2. 在 `TOOLS` 列表中添加 Schema
3. 在 `TOOL_MAP` 中添加映射

### 添加新指令

在 `main.py` 的 `main()` 函数中添加：

```python
if user_input.startswith('/'):
    if command == '/new_command':
        # 处理逻辑
        continue
```

## 📊 性能考虑

### 1. 缓存
- 暂无缓存机制（未来可考虑）

### 2. 超时
- 命令执行: 60 秒
- 网络搜索: 由 DDGS 库处理

### 3. 并发
- 暂无并发（未来可考虑异步）

## 🔮 未来规划

### v1.1
- [ ] 添加命令历史记录
- [ ] 支持多轮对话上下文
- [ ] 添加配置文件

### v1.2
- [ ] 支持更多大模型（OpenAI, Claude）
- [ ] 添加插件系统
- [ ] 支持自定义 Tool

### v2.0
- [ ] 异步支持
- [ ] 缓存机制
- [ ] 性能优化

---

**最后更新**: 2026年3月22日

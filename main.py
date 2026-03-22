"""
main.py - Sys-Mentor 终端交互主循环

本文件实现了 REPL (Read-Eval-Print Loop) 主循环，负责：
1. 初始化 Rich 控制台
2. 处理用户输入
3. 与 DeepSeek API 交互（携带 Tool Schema）
4. 处理 Tool Call 回调（用户授权后执行系统命令）
5. 使用 Markdown 优雅地输出 AI 的分析和指导

作者: Decent898
"""

import os
import sys
import json
import subprocess
import logging
import re
from typing import List, Dict, Any, Optional

# 导入第三方库
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box

# 加载环境变量（从 .env 文件）
from dotenv import load_dotenv
load_dotenv()

# 配置日志
# 通过环境变量 SYS_MENTOR_LOG 控制日志输出：
# - SYS_MENTOR_LOG=debug   : 输出详细调试日志
# - SYS_MENTOR_LOG=info    : 输出信息级别日志
# - SYS_MENTOR_LOG=warning : 仅输出警告和错误
# - SYS_MENTOR_LOG=off     : 完全关闭日志输出
# 默认值：off（关闭）
import os
log_level_str = os.environ.get('SYS_MENTOR_LOG', 'off').upper()
if log_level_str == 'OFF':
    log_level = logging.CRITICAL + 1  # 完全关闭日志
elif log_level_str == 'DEBUG':
    log_level = logging.DEBUG
elif log_level_str == 'INFO':
    log_level = logging.INFO
elif log_level_str == 'WARNING':
    log_level = logging.WARNING
elif log_level_str == 'ERROR':
    log_level = logging.ERROR
else:
    log_level = logging.CRITICAL + 1  # 默认关闭

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sys_mentor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 导入自定义工具
from tools import (
    probe_system_state,
    search_web_for_issue,
    execute_real_command,
    get_api_key,
    get_api_base_url
)

# 导入 OpenAI 库
try:
    from openai import OpenAI
except ImportError:
    print("错误: 请先安装 openai 库: pip install openai")
    sys.exit(1)


# =============================================================================
# 全局配置
# =============================================================================
console = Console()

# 系统提示词 (System Prompt)
# 这是注入到 DeepSeek API 的核心指令，定义了 Agent 的角色和行为准则
SYSTEM_PROMPT = """你是一个精通操作系统底层、编译原理和计算机架构的极客导师。用户正在真实终端里与你对话。

遇到问题时：
1. **不要直接给出一个黑盒的安装命令。**
2. 像诊断慢性病一样，先调用探针或执行测试命令，收集系统情报。如果遇到没见过的工业软件报错，调用联网搜索工具。
3. **解释原理 (Socratic Method)：** 告诉用户为什么会报错。比如是操作系统的链接器找不到动态库？还是环境变量的权重被覆盖了？带用户去理解底层发生了什么。
4. 给出修复建议，并向用户解释将要执行的命令会修改系统的哪一部分。

**输出格式要求：**
- 使用 Markdown 格式输出
- 优先使用中文
- 不要使用 XML 格式
- 工具调用后，基于工具结果给出最终的分析和建议

**🚨 极其重要：调用 execute_real_command 工具前的要求**
- 在调用 execute_real_command 工具之前，你必须先用一段文字向用户解释：
  1. 你将要执行什么命令
  2. 这个命令的作用和目的是什么
  3. 这个命令是否安全，会不会修改系统
  4. 预期会得到什么结果
- 格式示例：
  ```
  我来帮你检查 Git 的安装路径。

  我将执行以下命令：
  ```
  where git
  ```
  这会在 PATH 环境变量中搜索 git.exe 的位置，不会修改系统任何配置。

  [然后才调用 execute_real_command 工具]
  ```
- **不要直接调用工具而不解释！**

**重要：分析错误时的规则**
- 当用户报告命令执行失败时，不要调用 execute_real_command 工具
- 只分析错误原因并给出修复建议
- 如果需要执行命令，请明确告诉用户将要执行什么命令

**重要：Linux 命令在 Windows 上的处理**
- 如果用户输入了 Linux 命令（如 ls, grep, find 等），直接告诉用户这是 Linux 命令
- 建议使用 Windows 替代命令（如 dir, findstr, where 等）
- 不要调用工具执行这些命令

语气：专业、硬核、循循善诱、直击痛点。"""

# Tool Schema 定义
# 这些 Schema 会发送给 DeepSeek API，告诉它我们可以调用哪些工具
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "probe_system_state",
            "description": "探针工具：读取当前真实的 OS 架构、PATH 变量、Python 软链接实际指向、NVIDIA/CUDA 状态、以及关键的注册表路径（如 MSVC 运行库）。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web_for_issue",
            "description": "搜索工具：使用 duckduckgo-search 进行现场联网检索，获取最新的社区讨论和报错解决方案。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询字符串"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_real_command",
            "description": "执行工具：在真实终端环境中执行命令。这是一个极度危险且强大的工具，必须先征得用户同意。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的命令字符串"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "工作目录（可选）"
                    }
                },
                "required": ["command"]
            }
        }
    }
]

# 工具名称到函数的映射
TOOL_MAP = {
    "probe_system_state": probe_system_state,
    "search_web_for_issue": search_web_for_issue,
    "execute_real_command": execute_real_command
}


# =============================================================================
# 辅助函数：命令解释
# =============================================================================
def explain_command(command: str, cmd_lower: str) -> str:
    """
    解释命令的作用
    
    参数:
        command: 原始命令
        cmd_lower: 小写命令
    
    返回:
        命令解释字符串
    """
    # PowerShell 命令解释
    if cmd_lower.startswith('powershell') or cmd_lower.startswith('pwsh'):
        if 'get-audiodevice' in cmd_lower:
            return "获取当前系统的音频设备信息（播放/录制设备）"
        elif 'get-service' in cmd_lower:
            if 'audiosrv' in cmd_lower or 'audio' in cmd_lower:
                return "查询音频相关服务的状态（如 Windows Audio 服务）"
            return "查询 Windows 服务的状态信息"
        elif 'get-pnpdevice' in cmd_lower:
            if 'audio' in cmd_lower:
                return "查询系统中所有音频相关的即插即用设备（包括声卡、麦克风、扬声器等）"
            return "查询系统中的即插即用设备信息"
        elif 'get-winevent' in cmd_lower:
            if 'application' in cmd_lower and ('error' in cmd_lower or 'crash' in cmd_lower):
                return "查询应用程序日志中的错误、崩溃和异常事件（最近 24 小时）"
            elif 'system' in cmd_lower:
                return "查询系统日志中的事件"
            return "查询 Windows 事件日志"
        elif 'get-process' in cmd_lower:
            return "列出当前运行的进程信息"
        elif 'get-childitem' in cmd_lower or cmd_lower.startswith('gci') or 'dir' in cmd_lower:
            return "列出目录中的文件和子目录"
        elif 'get-content' in cmd_lower or 'cat' in cmd_lower:
            return "读取文件内容"
        elif 'select-object' in cmd_lower:
            return "从输出中选择特定属性进行显示"
        elif 'where-object' in cmd_lower:
            return "根据条件筛选对象"
        elif 'format-table' in cmd_lower or 'format-list' in cmd_lower:
            return "将结果格式化为表格或列表显示"
        elif 'sort-object' in cmd_lower:
            return "对结果进行排序"
        elif 'measure-object' in cmd_lower:
            return "统计对象数量或计算数值属性"
        elif 'get-eventlog' in cmd_lower:
            return "查询 Windows 事件日志"
        elif 'get-hotfix' in cmd_lower:
            return "查询已安装的 Windows 更新补丁"
        elif 'get-disk' in cmd_lower:
            return "查询磁盘信息"
        elif 'get-volume' in cmd_lower:
            return "查询卷（分区）信息"
        elif 'get-netipaddress' in cmd_lower:
            return "查询网络 IP 地址配置"
        elif 'test-netconnection' in cmd_lower:
            return "测试网络连接"
        elif 'get-scheduledtask' in cmd_lower:
            return "查询计划任务"
        elif 'get-wmiobject' in cmd_lower or 'gwmi' in cmd_lower:
            return "查询 WMI（Windows 管理规范）对象信息"
        elif 'invoke-command' in cmd_lower:
            return "在本地或远程计算机上执行命令"
        elif 'start-process' in cmd_lower:
            return "启动新进程"
        elif 'stop-process' in cmd_lower:
            return "停止进程"
        elif 'get-service' in cmd_lower:
            return "查询服务状态"
        elif 'start-service' in cmd_lower:
            return "启动服务"
        elif 'stop-service' in cmd_lower:
            return "停止服务"
        elif 'restart-service' in cmd_lower:
            return "重启服务"
        elif 'get-itemproperty' in cmd_lower:
            return "获取注册表或文件属性"
        elif 'set-itemproperty' in cmd_lower:
            return "设置注册表或文件属性"
        elif 'new-item' in cmd_lower:
            return "创建新文件或注册表项"
        elif 'remove-item' in cmd_lower:
            return "删除文件或注册表项"
        elif 'copy-item' in cmd_lower:
            return "复制文件或注册表项"
        elif 'move-item' in cmd_lower:
            return "移动文件或注册表项"
        elif 'get-acl' in cmd_lower:
            return "获取文件或注册表项的安全权限"
        elif 'set-acl' in cmd_lower:
            return "设置文件或注册表项的安全权限"
        elif 'get-alias' in cmd_lower:
            return "获取 PowerShell 别名"
        elif 'get-module' in cmd_lower:
            return "获取已加载的 PowerShell 模块"
        elif 'import-module' in cmd_lower:
            return "导入 PowerShell 模块"
        elif 'get-command' in cmd_lower:
            return "查询可用的命令"
        elif 'get-help' in cmd_lower:
            return "获取命令帮助文档"
    
    # CMD 命令解释
    elif 'sc query' in cmd_lower:
        if 'audio' in cmd_lower:
            return "查询音频相关服务的状态"
        return "查询 Windows 服务的状态"
    elif 'net start' in cmd_lower:
        return "启动 Windows 服务"
    elif 'net stop' in cmd_lower:
        return "停止 Windows 服务"
    elif 'tasklist' in cmd_lower:
        return "列出当前运行的进程"
    elif 'taskkill' in cmd_lower:
        return "终止指定的进程"
    elif 'sfc /scannow' in cmd_lower:
        return "扫描并修复系统文件（系统文件检查器）"
    elif 'chkdsk' in cmd_lower:
        return "检查磁盘错误"
    elif 'dism' in cmd_lower:
        return "部署映像服务和管理工具（用于修复系统映像）"
    elif 'reg query' in cmd_lower:
        return "查询注册表项"
    elif 'reg add' in cmd_lower:
        return "添加注册表项"
    elif 'reg delete' in cmd_lower:
        return "删除注册表项"
    elif 'ipconfig' in cmd_lower:
        return "显示网络配置信息"
    elif 'ping' in cmd_lower:
        return "测试网络连接"
    elif 'tracert' in cmd_lower:
        return "跟踪网络路由"
    elif 'netstat' in cmd_lower:
        return "显示网络连接和端口状态"
    elif 'systeminfo' in cmd_lower:
        return "显示系统配置信息"
    elif 'driverquery' in cmd_lower:
        return "列出已安装的设备驱动程序"
    elif 'bcdedit' in cmd_lower:
        return "修改启动配置数据（引导管理器）"
    elif 'wmic' in cmd_lower:
        return "查询 WMI（Windows 管理规范）信息"
    elif 'shutdown' in cmd_lower:
        return "关机或重启系统"
    elif 'format' in cmd_lower:
        return "格式化磁盘分区（危险操作！）"
    elif 'diskpart' in cmd_lower:
        return "磁盘分区管理工具"
    elif 'attrib' in cmd_lower:
        return "修改文件属性（只读/隐藏/系统等）"
    elif 'takeown' in cmd_lower:
        return "获取文件所有权"
    elif 'icacls' in cmd_lower:
        return "修改文件访问控制列表（ACL）"
    elif 'cacls' in cmd_lower:
        return "修改文件访问控制列表（旧版本）"
    elif 'robocopy' in cmd_lower:
        return "高级文件复制工具"
    elif 'xcopy' in cmd_lower:
        return "复制文件和目录"
    elif 'del' in cmd_lower or 'erase' in cmd_lower:
        return "删除文件"
    elif 'rmdir' in cmd_lower or 'rd ' in cmd_lower:
        return "删除目录"
    elif 'mkdir' in cmd_lower or 'md ' in cmd_lower:
        return "创建目录"
    elif 'copy' in cmd_lower:
        return "复制文件"
    elif 'move' in cmd_lower:
        return "移动文件"
    elif 'ren' in cmd_lower or 'rename' in cmd_lower:
        return "重命名文件"
    elif 'findstr' in cmd_lower:
        return "在文件中搜索字符串"
    elif 'type' in cmd_lower:
        return "显示文件内容"
    elif 'more' in cmd_lower:
        return "分页显示文件内容"
    elif 'echo' in cmd_lower:
        return "显示消息或变量"
    elif 'set ' in cmd_lower:
        return "设置或显示环境变量"
    
    return ""  # 没有匹配的解释时返回空字符串


# =============================================================================
# 核心类：SysMentor
# =============================================================================
class SysMentor:
    """
    Sys-Mentor 主类，负责：
    1. 管理对话历史
    2. 与 DeepSeek API 交互
    3. 处理 Tool Call 回调
    4. 格式化输出结果
    """
    
    def __init__(self):
        """初始化 Sys-Mentor 实例"""
        self.conversation_history: List[Dict[str, str]] = []
        self.api_key = get_api_key("deepseek")
        self.api_base_url = get_api_base_url("deepseek")
        self.client: Optional[OpenAI] = None
        
        # 尝试初始化 OpenAI 客户端
        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base_url
                )
                console.print("[green]✓ DeepSeek API 客户端初始化成功[/green]")
            except Exception as e:
                console.print(f"[red]✗ DeepSeek API 客户端初始化失败: {str(e)}[/red]")
        else:
            console.print("[yellow]⚠ 未设置 DEEPSEEK_API_KEY，部分功能将不可用[/yellow]")
    
    def add_message(self, role: str, content: str):
        """
        向对话历史添加消息
        
        参数:
            role: 消息角色 ("user", "assistant", "tool")
            content: 消息内容
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def display_welcome(self):
        """显示欢迎信息"""
        welcome_text = """
# Sys-Mentor v1.0 - 系统导师

欢迎来到 Sys-Mentor，一个本地终端伴随工具。

**核心理念：** 这不是一个盲目替用户敲回车的"急救包"。它像一个治疗电脑"慢性病"的老中医，或者一个循循善诱的极客导师。

**使用指南：**
- **直接输入终端命令** - 例如："python --version", "pip list", "dir"
- **PowerShell 命令** - 例如："powershell Get-Process", "gci", "Get-Service"
- **直接输入问题** - 例如："我的 Python 环境变量有问题"
- 输入 `/clear` 清空对话历史
- 输入 `/probe` 探测系统状态
- 输入 `/ask <问题>` 强制让 AI 分析（即使看起来像命令）
- 输入 `/exit` 或 `/quit` 退出

**智能判断：**
- 常见命令 (python, pip, git, dir 等) → 直接执行
- PowerShell 命令 (powershell, gci, Get-Process 等) → 直接执行
- 问题/对话 → 调用 AI 分析
- 命令失败 → 自动询问是否让 AI 分析

**提示符格式：** `当前路径 >`
**注意：** 如果需要执行危险命令，系统会询问你的授权。
"""
        console.print(Panel(Markdown(welcome_text), title="[bold blue]Sys-Mentor[/bold blue]", border_style="blue"))
    
    def display_system_state(self):
        """显示当前系统状态"""
        console.print("\n[bold]正在探测系统状态...[/bold]")
        
        try:
            state = probe_system_state()
            
            # 使用表格展示
            table = Table(title="系统状态探针结果", box=box.ROUNDED)
            table.add_column("类别", style="cyan")
            table.add_column("信息", style="green")
            
            # 系统信息
            system = state.get("system", {})
            table.add_row("平台", system.get("platform", "N/A"))
            table.add_row("架构", system.get("machine", "N/A"))
            table.add_row("Python 版本", system.get("python_version", "N/A").split('\n')[0])
            table.add_row("Python 路径", system.get("python_executable", "N/A"))
            
            # GPU 信息
            gpu = state.get("gpu", {})
            if gpu.get("nvidia_smi", {}).get("success"):
                table.add_row("GPU", "NVIDIA 可用")
            else:
                table.add_row("GPU", "未检测到 NVIDIA 驱动")
            
            if gpu.get("torch_available"):
                table.add_row("PyTorch", f"v{gpu.get('torch_version', 'N/A')}")
                if gpu.get("cuda_available"):
                    table.add_row("CUDA", "可用")
                else:
                    table.add_row("CUDA", "不可用")
            
            console.print(table)
            
            # 添加到对话历史
            self.add_message("user", "请分析当前系统状态。")
            self.add_message("assistant", f"系统状态探针结果:\n{json.dumps(state, indent=2, ensure_ascii=False, default=str)}")
            
        except Exception as e:
            console.print(f"[red]探测系统状态时发生错误: {str(e)}[/red]")
    
    def execute_user_command(self, command: str) -> bool:
        """
        尝试执行用户输入的普通终端命令
        
        只执行已知的终端命令，其他情况返回 False
        注意：现在只有 /ask 前缀才会发送给 AI，所以这里不需要智能判断

        参数:
            command: 用户输入的命令

        返回:
            bool: 命令是否被识别为终端命令并执行
        """
        cmd_stripped = command.strip()
        
        # 检查是否是内置指令
        if cmd_stripped.lower() in ['/clear', '/probe', '/exit', '/quit', '/help', '/ask']:
            return False
        
        # 只执行常见的终端命令
        terminal_commands = [
            'python', 'pip', 'git', 'node', 'npm', 'yarn',
            'dir', 'cd', 'ls', 'pwd', 'cat', 'echo', 'type',
            'ipconfig', 'ping', 'tracert', 'netstat',
            'tasklist', 'taskkill', 'sc', 'services.msc',
            'nvidia-smi', 'nvcc', 'cl', 'ml',
            'make', 'cmake', 'gcc', 'g++', 'clang',
            'docker', 'kubectl', 'aws', 'az',
            'whoami', 'hostname', 'systeminfo',
            'where', 'which', 'find', 'grep',
            'copy', 'move', 'del', 'rd', 'mkdir',
            'type', 'more', 'sort', 'tree',
            'help',
            # PowerShell 命令
            'powershell', 'pwsh',
            'Get-Process', 'Stop-Process', 'Get-Service', 'Start-Service', 'Stop-Service',
            'Get-ChildItem', 'Get-Content', 'Set-Location', 'Get-Location',
            'Write-Host', 'Write-Output', 'Select-Object', 'Where-Object',
            'Sort-Object', 'Measure-Object', 'Format-Table', 'Format-List',
            'Test-Path', 'New-Item', 'Remove-Item', 'Copy-Item', 'Move-Item',
            'Invoke-WebRequest', 'Invoke-RestMethod',
            'Get-Command', 'Get-Help', 'Get-Variable', 'Set-Variable',
            'Export-Csv', 'Import-Csv', 'ConvertTo-Json', 'ConvertFrom-Json',
            'Start-Sleep', 'Read-Host', 'Write-Verbose', 'Write-Warning',
            'Get-Date', 'Get-Random', 'Get-Unique',
            'Clear-Host', 'Pause', 'Exit'
        ]

        cmd_lower = cmd_stripped.lower().split()[0] if cmd_stripped else ''
        
        # 检查是否是已知的终端命令
        is_terminal = False
        for tc in terminal_commands:
            if cmd_lower.startswith(tc):
                is_terminal = True
                break

        # 特殊处理：如果包含路径分隔符，可能是文件路径
        if '\\' in cmd_stripped or '/' in cmd_stripped:
            is_terminal = True

        # 如果不是终端命令，返回 False
        if not is_terminal:
            logger.debug(f"不是终端命令: {command}")
            return False

        logger.debug(f"执行终端命令: {command}")

        # 检查是否是交互式命令（会卡死）
        interactive_commands = [
            'python', 'powershell', 'pwsh', 'node', 'npm', 'yarn',
            'mysql', 'psql', 'redis-cli', 'mongo', 'mongosh',
            'ftp', 'telnet', 'ssh'
        ]

        # 如果命令是交互式的，提示用户
        for ic in interactive_commands:
            if cmd_lower.startswith(ic):
                # 检查是否有参数
                args = cmd_stripped.split()[1:] if len(cmd_stripped.split()) > 1 else []
                if not args:
                    console.print(f"\n[yellow]警告: 单独输入 '{command}' 会启动交互式 shell，可能导致卡死[/yellow]")
                    console.print("[yellow]建议: 使用命令参数，例如:")
                    if cmd_lower == 'python':
                        console.print("  python --version")
                        console.print("  python -c 'print(\"hello\")'")
                    elif cmd_lower == 'powershell' or cmd_lower == 'pwsh':
                        console.print("  powershell Get-Process")
                        console.print("  powershell Get-Date")
                        console.print("  gci  (列出目录)")
                        console.print("  pwd  (显示当前路径)")
                    console.print("[yellow]是否继续执行？[/yellow]")
                    if not Confirm.ask("[bold]继续执行? [y/N][/bold]", default=False):
                        console.print("[yellow]已取消执行[/yellow]")
                        logger.debug(f"用户取消执行交互式命令: {command}")
                        return True  # 返回 True 表示已处理
                    break

        # 尝试执行终端命令
        try:
            logger.debug(f"执行命令: {command}")
            result = execute_real_command(command)
            logger.debug(f"命令执行结果: returncode={result['returncode']}, stdout长度={len(result['stdout'])}, stderr长度={len(result['stderr'])}")

            if result["returncode"] == 0:
                console.print(f"\n[bold green]✓ 命令执行成功[/bold green]")
                if result["stdout"]:
                    console.print(f"[dim]{result['stdout']}[/dim]")
                # 将成功结果添加到对话历史
                self.add_message("user", f"执行命令: {command}")
                self.add_message("assistant", f"命令执行成功:\n{result['stdout']}")
            else:
                console.print(f"\n[bold red]✗ 命令执行失败 (返回码: {result['returncode']})[/bold red]")
                if result["stderr"]:
                    console.print(f"[dim red]{result['stderr']}[/dim red]")
                # 将失败结果添加到对话历史
                self.add_message("user", f"执行命令: {command}")
                self.add_message("assistant", f"命令执行失败 (返回码: {result['returncode']}):\n{result['stderr']}")

                # 询问是否让 AI 分析错误
                console.print("\n[yellow]命令执行失败，是否让 AI 帮你分析错误原因？[/yellow]")
                if Confirm.ask("[bold]分析错误? [y/N][/bold]", default=False):
                    # 将错误信息发送给 AI
                    error_context = f"执行命令 '{command}' 失败，错误信息如下：\n\n{result['stderr']}"
                    console.print("\n[bold cyan]正在让 AI 分析...[/bold cyan]")
                    response = self.chat_with_deepseek(error_context)
                    self.print_response(response)

            return True

        except Exception as e:
            console.print(f"[yellow]无法执行命令: {str(e)}[/yellow]")
            return False
    
    def handle_tool_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        处理 Tool Call 回调
        
        参数:
            tool_name: 工具名称
            tool_args: 工具参数
        
        返回:
            str: 工具执行结果（字符串格式）
        """
        console.print(f"\n[bold yellow]AI 请求调用工具: {tool_name}[/bold yellow]")
        logger.debug(f"AI 请求调用工具: {tool_name}, 参数: {tool_args}")

        # 特殊处理：execute_real_command 需要用户授权
        if tool_name == "execute_real_command":
            command = tool_args.get("command", "")
            working_dir = tool_args.get("working_dir")

            # 先让 AI 解释命令的作用
            try:
                explanation_response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个简洁的技术助手。请用 1-2 句话解释以下命令的作用和安全性。"},
                        {"role": "user", "content": f"请解释这个命令的作用、是否安全、预期结果是什么：\n\n```bash\n{command}\n```"}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )
                explanation = explanation_response.choices[0].message.content or ""
                explanation = re.sub(r'<｜DSML｜[^>]+>', '', explanation).strip()

                if explanation:
                    console.print(Panel(
                        f"[cyan]{explanation}[/cyan]",
                        title="[bold cyan]📖 命令说明[/bold cyan]",
                        border_style="cyan"
                    ))
                else:
                    console.print("[dim]命令解释为空，跳过显示[/dim]")
            except Exception as e:
                console.print(f"[dim]获取命令解释失败：{str(e)}[/dim]")
                logger.error(f"获取命令解释失败：{str(e)}")

            # 显示将要执行的命令
            console.print(Panel(
                f"[bold]{command}[/bold]",
                title="[red]⚠️  命令执行[/red]",
                border_style="red"
            ))

            if working_dir:
                console.print(f"[dim]工作目录: {working_dir}[/dim]")

            # 询问用户授权
            console.print("\n[yellow]AI 想要执行上述命令。是否授权？[/yellow]")
            console.print("[yellow]这将直接在你的终端中执行，可能修改系统状态。[/yellow]")

            if not Confirm.ask("\n[bold]授权执行? [y/N][/bold]", default=False):
                logger.debug("用户拒绝执行命令")
                return "用户拒绝执行此命令。"

            console.print("\n[green]✓ 执行授权[/green]")
            logger.debug("用户授权执行命令")

        # 调用工具函数
        try:
            tool_func = TOOL_MAP.get(tool_name)
            if not tool_func:
                logger.error(f"未知工具: {tool_name}")
                return f"错误: 未知工具 {tool_name}"

            # 特殊处理：execute_real_command 需要检测 PowerShell 命令
            if tool_name == "execute_real_command":
                command = tool_args.get("command", "")
                # 检查是否是 PowerShell 命令
                cmd_lower = command.lower().strip()
                is_powershell = (
                    cmd_lower.startswith('powershell') or 
                    cmd_lower.startswith('pwsh') or
                    cmd_lower.startswith('get-') or
                    cmd_lower.startswith('set-') or
                    cmd_lower.startswith('start-') or
                    cmd_lower.startswith('stop-') or
                    cmd_lower.startswith('new-') or
                    cmd_lower.startswith('remove-') or
                    cmd_lower.startswith('invoke-') or
                    cmd_lower.startswith('gci') or
                    cmd_lower.startswith('gci ') or
                    cmd_lower.startswith('pwd') or
                    cmd_lower.startswith('pwd ')
                )
                
                if is_powershell:
                    logger.debug(f"检测到 PowerShell 命令: {command}")
                    tool_args["use_powershell"] = True
            
            # 调用工具
            logger.debug(f"调用工具函数: {tool_name}(**{tool_args})")
            result = tool_func(**tool_args)
            logger.debug(f"工具执行结果类型: {type(result)}, 长度: {len(str(result)) if isinstance(result, (str, list, dict)) else 'N/A'}")

            # 格式化结果
            if isinstance(result, (dict, list)):
                try:
                    logger.debug(f"尝试 JSON 序列化，类型: {type(result)}")
                    result_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                    logger.debug(f"JSON 序列化成功")
                except Exception as e:
                    logger.error(f"JSON 序列化失败: {str(e)}")
                    # 尝试递归转换为字符串
                    def convert_to_str(obj):
                        if isinstance(obj, dict):
                            return {str(k): convert_to_str(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_to_str(item) for item in obj]
                        elif isinstance(obj, bytes):
                            return obj.decode('utf-8', errors='ignore')
                        else:
                            return str(obj)
                    converted_result = convert_to_str(result)
                    logger.debug(f"递归转换完成")
                    result_str = json.dumps(converted_result, indent=2, ensure_ascii=False)
                    logger.debug(f"JSON 序列化成功（递归转换后）")
            else:
                result_str = str(result)

            logger.debug(f"工具执行结果长度: {len(result_str)}")
            logger.debug(f"工具执行结果: {result_str[:200]}...")
            return result_str

        except Exception as e:
            logger.error(f"工具执行失败: {str(e)}", exc_info=True)
            return f"工具执行失败: {str(e)}"
    
    def chat_with_deepseek(self, user_input: str) -> str:
        """
        与 DeepSeek API 交互，处理用户输入

        参数:
            user_input: 用户输入的文本

        返回:
            str: AI 的回复
        """
        logger.debug(f"=== chat_with_deepseek 开始 ===")
        logger.debug(f"用户输入: {user_input}")
        
        if not self.client:
            logger.error("未配置 DeepSeek API 密钥")
            return "错误: 未配置 DeepSeek API 密钥。请设置 DEEPSEEK_API_KEY 环境变量。"

        # 构建上下文消息
        context_messages = []

        # 添加系统提示词
        context_messages.append({
            "role": "system",
            "content": SYSTEM_PROMPT
        })

        # 添加之前的对话历史（最多保留 10 条）
        history_limit = 10
        for msg in self.conversation_history[-history_limit:]:
            context_messages.append(msg)
            logger.debug(f"添加历史消息: {msg.get('role', 'unknown')}")

        # 添加当前用户输入
        context_messages.append({
            "role": "user",
            "content": user_input
        })
        logger.debug(f"总消息数: {len(context_messages)}")

        try:
            # 去掉原来的最大循环限制，交由内部逻辑控制
            round_count = 0
            current_messages = context_messages.copy()

            while True:  # 无限循环，直到达成结论或触发阶段总结
                round_count += 1
                logger.debug(f"=== 第 {round_count} 轮 Tool Call ===")

                # 调用 DeepSeek API
                logger.debug(f"调用 DeepSeek API...")
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=current_messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.7
                )

                message = response.choices[0].message
                
                # 检查是否有 Tool Call
                if message.tool_calls:
                    tool_results = []
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)

                        # 执行工具 (依然会正常询问用户授权)
                        tool_result = self.handle_tool_call(tool_name, tool_args)

                        # 记录工具调用和结果
                        current_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }]
                        })
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        })
                        tool_results.append({"name": tool_name, "result": tool_result})

                    # ======== 核心：三步汇报机制 ========
                    if tool_results:
                        logger.debug(f"Tool Call 结果: {tool_results}")
                        
                        if round_count >= 3:
                            logger.info("触发阶段性汇报机制")
                            # 👇 1. 把 role 从 'system' 改成 'user'，大模型对 user 的指令更敏感
                            current_messages.append({
                                "role": "user",
                                "content": "【系统控制拦截】排查已达 3 步，系统暂时收回了你的工具调用权限。\n\n**严格指令**：\n1. 绝对不要直接输出任何代码或命令。\n2. 使用自然语言向用户汇报你刚才查了什么（比如音频服务状态如何），排除了什么原因。\n3. 告诉用户你下一步想要查什么（比如 PnP 音频设备），并询问用户是否继续。"
                            })
                            
                            # 不传 tools 参数，逼迫 AI 只能输出总结文本
                            summary_response = self.client.chat.completions.create(
                                model="deepseek-chat",
                                messages=current_messages,
                                temperature=0.7
                            )
                            content = summary_response.choices[0].message.content or ""
                            
                            import re
                            cleaned = re.sub(r'<｜DSML｜[^>]+>', '', content).strip()
                            
                            # 👇【记忆修复】把探索过程存入历史，确保输入"继续"时 AI 能接上思路
                            self.conversation_history.append({"role": "user", "content": user_input})
                            self.conversation_history.extend(current_messages[len(context_messages):])
                            self.conversation_history.append({"role": "assistant", "content": cleaned})
                            
                            return cleaned

                        # 还没到 3 步，继续静默探索
                        continue

                # ==========================================
                # 正常找到答案出口：AI 决定停止调用工具，直接回复
                # ==========================================
                content = message.content or ""
                import re
                cleaned = re.sub(r'<｜DSML｜[^>]+>', '', content).strip()

                # 👇【记忆修复】同样保存成功找到答案的历史记录
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.extend(current_messages[len(context_messages):])
                self.conversation_history.append({"role": "assistant", "content": cleaned})

                return cleaned

        except Exception as e:
            logger.error(f"API 调用失败: {str(e)}", exc_info=True)
            return f"API 调用失败: {str(e)}"
    
    def print_response(self, response: str):
        """
        优雅地打印 AI 的回复（使用 Markdown）
        
        清理 XML 格式的函数调用标记，只保留文本内容

        参数:
            response: AI 的回复文本
        """
        # 清理 XML 格式的函数调用标记
        import re
        # 移除 <｜DSML｜function_calls> 等标记
        cleaned = re.sub(r'<｜DSML｜[^>]+>', '', response)
        cleaned = re.sub(r'</｜DSML｜[^>]+>', '', cleaned)
        cleaned = cleaned.strip()
        
        console.print("\n" + "=" * 60)
        console.print(Panel(Markdown(cleaned), title="[bold green]Sys-Mentor[/bold green]", border_style="green"))
        console.print("=" * 60 + "\n")


# =============================================================================
# 主循环 (REPL)
# =============================================================================
def main():
    """
    主函数：启动 REPL 循环

    REPL (Read-Eval-Print Loop) 流程：
    1. Read: 读取用户输入
    2. Eval: 评估输入（是命令？是问题？是内置指令？）
    3. Print: 打印结果
    4. Loop: 重复
    
    提示符格式：当前路径 >
    例如：d:\\Programming2\\env_project >
    """
    # 初始化 Sys-Mentor
    mentor = SysMentor()

    # 显示欢迎信息
    mentor.display_welcome()

    # REPL 循环
    while True:
        try:
            # Read: 读取用户输入
            # 显示当前工作目录作为提示符
            current_dir = os.getcwd()
            console.print("\n" + "-" * 40)
            user_input = Prompt.ask(
                f"{current_dir} >",
                default="",
                console=console
            ).strip()

            # 检查空输入
            if not user_input:
                continue

            # Eval: 处理内置指令
            if user_input.startswith('/'):
                command = user_input.lower()

                if command in ['/exit', '/quit']:
                    console.print("\n[bold yellow]再见！祝你有个美好的一天。[/bold yellow]")
                    break

                elif command == '/clear':
                    mentor.conversation_history = []
                    console.print("[green]对话历史已清空[/green]")
                    continue

                elif command == '/probe':
                    mentor.display_system_state()
                    continue

                elif command == '/help':
                    console.print("\n" + "=" * 60)
                    console.print("[bold]Sys-Mentor 帮助[/bold]")
                    console.print("=" * 60)
                    console.print("\n[bold]内置指令:[/bold]")
                    console.print("  /clear    - 清空对话历史")
                    console.print("  /probe    - 探测系统状态")
                    console.print("  /help     - 显示此帮助信息")
                    console.print("  /ask <问题> - 强制让 AI 分析")
                    console.print("  /exit     - 退出程序")
                    console.print("\n[bold]使用说明:[/bold]")
                    console.print("  - 直接输入终端命令即可执行（如 python, pip, dir, powershell 等）")
                    console.print("  - 命令执行失败时会自动询问是否让 AI 分析")
                    console.print("  - 直接输入问题或未知命令会自动让 AI 分析")
                    console.print("  - 使用 /ask <问题> 强制让 AI 分析")
                    console.print("=" * 60 + "\n")
                    continue

                elif command.startswith('/ask'):
                    # /ask 前缀：强制让 AI 处理
                    question = user_input[5:].strip()  # 去掉 '/ask ' 前缀
                    if question:
                        console.print("\n[bold cyan]正在让 AI 分析...[/bold cyan]")
                        response = mentor.chat_with_deepseek(question)
                        mentor.print_response(response)
                    else:
                        console.print("[yellow]用法: /ask <你的问题>[/yellow]")
                    continue

                else:
                    console.print(f"[yellow]未知指令: {user_input}[/yellow]")
                    console.print("可用指令: /clear, /probe, /help, /exit, /quit, /ask <问题>")
                    continue

            # Eval: 直接执行终端命令
            console.print("\n[bold cyan]正在执行命令...[/bold cyan]")
            command_executed = mentor.execute_user_command(user_input)
            
            # 如果命令没有被执行（不是已知命令），询问是否让 AI 分析
            if not command_executed:
                console.print("\n[yellow]无法识别为终端命令，是否让 AI 帮你分析？[/yellow]")
                if Confirm.ask("[bold]分析? [y/N][/bold]", default=False):
                    console.print("\n[bold cyan]正在让 AI 分析...[/bold cyan]")
                    response = mentor.chat_with_deepseek(user_input)
                    mentor.print_response(response)
                else:
                    console.print("[yellow]如果要让 AI 分析，请使用 /ask 前缀，例如: /ask <你的问题>[/yellow]")

        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]检测到 Ctrl+C，正在退出...[/bold yellow]")
            break

        except EOFError:
            console.print("\n\n[bold yellow]检测到 EOF，正在退出...[/bold yellow]")
            break

        except Exception as e:
            console.print(f"\n[bold red]发生未预期的错误: {str(e)}[/bold red]")
            console.print("[yellow]请尝试重新输入或联系开发者。[/yellow]")


if __name__ == "__main__":
    main()

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
- **直接输入问题** - 例如："我的 Python 环境变量有问题"
- **输入终端命令** - 例如："python --version", "pip list", "dir"
- 输入 `/clear` 清空对话历史
- 输入 `/probe` 探测系统状态
- 输入 `/exit` 或 `/quit` 退出

**智能判断：**
- 问题/对话 → 调用 AI 分析
- 常见命令 (python, pip, git, dir 等) → 直接执行
- 其他输入 → AI 辅助

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
        
        智能判断：只有当命令看起来像是真正的终端命令时才执行
        - 以 / 开头的是内置指令（不执行）
        - 以 python, pip, git, dir, cd 等常见命令开头的才执行
        - 其他情况（如问题、对话）不执行，返回 False 让 AI 处理
        
        参数:
            command: 用户输入的命令

        返回:
            bool: 命令是否被识别为终端命令并执行
        """
        cmd_stripped = command.strip()
        
        # 检查是否是内置指令
        if cmd_stripped.lower() in ['/clear', '/probe', '/exit', '/quit']:
            return False
        
        # 检查是否是问题或对话（以疑问词开头）
        question_words = ['什么', '如何', '为什么', '怎么', '能', '会', '有', '请', '帮忙', '谢谢']
        if any(cmd_stripped.startswith(w) for w in question_words):
            return False
        
        # 检查是否包含问号（中文或英文）
        if '?' in cmd_stripped or '？' in cmd_stripped:
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
            'type', 'more', 'sort', 'tree'
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
        
        # 如果不是终端命令，返回 False 让 AI 处理
        if not is_terminal:
            return False
        
        # 尝试执行终端命令
        try:
            result = execute_real_command(command)

            if result["returncode"] == 0:
                console.print(f"\n[bold green]✓ 命令执行成功[/bold green]")
                if result["stdout"]:
                    console.print(f"[dim]{result['stdout']}[/dim]")
            else:
                console.print(f"\n[bold red]✗ 命令执行失败 (返回码: {result['returncode']})[/bold red]")
                if result["stderr"]:
                    console.print(f"[dim red]{result['stderr']}[/dim red]")

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
        
        # 特殊处理：execute_real_command 需要用户授权
        if tool_name == "execute_real_command":
            command = tool_args.get("command", "")
            working_dir = tool_args.get("working_dir")
            
            # 显示将要执行的命令
            console.print(Panel(
                f"[bold]{command}[/bold]",
                title="[red]危险命令[/red]",
                border_style="red"
            ))
            
            if working_dir:
                console.print(f"[dim]工作目录: {working_dir}[/dim]")
            
            # 询问用户授权
            console.print("\n[yellow]AI 想要执行上述命令。是否授权？[/yellow]")
            console.print("[yellow]这将直接在你的终端中执行，可能修改系统状态。[/yellow]")
            
            if not Confirm.ask("\n[bold]授权执行? [y/N][/bold]", default=False):
                return "用户拒绝执行此命令。"
            
            console.print("\n[green]✓ 执行授权[/green]")
        
        # 调用工具函数
        try:
            tool_func = TOOL_MAP.get(tool_name)
            if not tool_func:
                return f"错误: 未知工具 {tool_name}"
            
            # 调用工具
            result = tool_func(**tool_args)
            
            # 格式化结果
            if isinstance(result, (dict, list)):
                result_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            else:
                result_str = str(result)
            
            return result_str
            
        except Exception as e:
            return f"工具执行失败: {str(e)}"
    
    def chat_with_deepseek(self, user_input: str) -> str:
        """
        与 DeepSeek API 交互，处理用户输入
        
        参数:
            user_input: 用户输入的文本
        
        返回:
            str: AI 的回复
        """
        if not self.client:
            return "错误: 未配置 DeepSeek API 密钥。请设置 DEEPSEEK_API_KEY 环境变量。"
        
        # 添加用户消息到历史
        self.add_message("user", user_input)
        
        try:
            # 调用 DeepSeek API
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=self.conversation_history,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.7
            )
            
            # 获取响应
            message = response.choices[0].message
            
            # 检查是否有 Tool Call
            if message.tool_calls:
                # 处理所有 Tool Call
                tool_results = []
                
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # 执行工具
                    tool_result = self.handle_tool_call(tool_name, tool_args)
                    
                    # 添加工具调用和结果到历史
                    self.conversation_history.append({
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
                    
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                    
                    tool_results.append({
                        "name": tool_name,
                        "result": tool_result
                    })
                
                # 发送工具结果，获取最终回复
                final_response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=self.conversation_history,
                    temperature=0.7
                )
                
                final_message = final_response.choices[0].message.content
                return final_message
            
            else:
                # 没有 Tool Call，直接返回内容
                return message.content
                
        except Exception as e:
            return f"API 调用失败: {str(e)}"
    
    def print_response(self, response: str):
        """
        优雅地打印 AI 的回复（使用 Markdown）
        
        参数:
            response: AI 的回复文本
        """
        console.print("\n" + "=" * 60)
        console.print(Panel(Markdown(response), title="[bold green]Sys-Mentor[/bold green]", border_style="green"))
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
    """
    # 初始化 Sys-Mentor
    mentor = SysMentor()
    
    # 显示欢迎信息
    mentor.display_welcome()
    
    # REPL 循环
    while True:
        try:
            # Read: 读取用户输入
            console.print("\n" + "-" * 40)
            user_input = Prompt.ask(
                "(Sys-Mentor) >",
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
                
                else:
                    console.print(f"[yellow]未知指令: {user_input}[/yellow]")
                    console.print("可用指令: /clear, /probe, /exit, /quit")
                    continue
            
            # Eval: 尝试执行终端命令
            if mentor.execute_user_command(user_input):
                continue
            
            # Eval: 作为问题处理，调用 DeepSeek
            console.print("\n[bold cyan]正在思考...[/bold cyan]")
            response = mentor.chat_with_deepseek(user_input)
            
            # Print: 打印 AI 的回复
            mentor.print_response(response)
            
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

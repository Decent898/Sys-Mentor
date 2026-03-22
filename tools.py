"""
tools.py - Sys-Mentor 核心工具函数封装

本文件实现了三个核心 Tool Calling 函数，用于与 DeepSeek 大模型交互：
1. probe_system_state() - 探针工具：读取系统底层状态
2. search_web_for_issue() - 搜索工具：联网检索问题解决方案
3. execute_real_command() - 执行工具：在真实终端执行命令（需用户授权）

作者: Decent898
"""

import os
import json
import subprocess
import platform
import sys
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


# =============================================================================
# 工具 1: probe_system_state() - 系统探针
# =============================================================================
def probe_system_state() -> Dict[str, Any]:
    """
    探针工具：读取当前真实的 OS 架构、PATH 变量、Python 软链接实际指向、
    NVIDIA/CUDA 状态、以及关键的注册表路径（如 MSVC 运行库）。
    
    返回 JSON 结构，包含：
    - system: 系统基本信息（平台、架构、Python 版本）
    - path: 环境变量 PATH 的内容
    - python: Python 解释器信息（包括实际路径）
    - gpu: GPU 和 CUDA 状态
    - windows_specific: Windows 特定信息（注册表、MSVC 运行库）
    
    返回值示例:
    {
        "system": {...},
        "path": [...],
        "python": {...},
        "gpu": {...},
        "windows_specific": {...}
    }
    """
    state = {
        "system": {},
        "path": [],
        "python": {},
        "gpu": {},
        "windows_specific": {}
    }
    
    # --- 系统基本信息 ---
    state["system"]["platform"] = platform.system()  # Windows, Linux, Darwin
    state["system"]["platform_release"] = platform.release()
    state["system"]["platform_version"] = platform.version()
    state["system"]["machine"] = platform.machine()  # x86_64, AMD64, arm64
    state["system"]["processor"] = platform.processor()
    state["system"]["python_version"] = sys.version
    state["system"]["python_executable"] = sys.executable
    
    # --- PATH 环境变量 ---
    path_str = os.environ.get("PATH", "")
    state["path"] = path_str.split(os.pathsep)  # 分割成列表
    
    # --- Python 解释器信息 ---
    # 获取 Python 实际路径（处理软链接/符号链接）
    try:
        if platform.system() == "Windows":
            # Windows: 使用 os.readlink 检查是否为符号链接
            python_path = os.path.realpath(sys.executable)
        else:
            python_path = os.path.realpath(sys.executable)
        state["python"]["real_path"] = python_path
        state["python"]["prefix"] = sys.prefix
        state["python"]["base_prefix"] = getattr(sys, 'base_prefix', sys.prefix)
    except Exception as e:
        state["python"]["error"] = str(e)
    
    # --- GPU 和 CUDA 状态 ---
    state["gpu"]["nvidia_smi"] = None
    state["gpu"]["cuda_available"] = False
    state["gpu"]["torch_cuda_available"] = False
    
    # 尝试执行 nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            state["gpu"]["nvidia_smi"] = {
                "success": True,
                "output": result.stdout,
                "error": result.stderr
            }
            state["gpu"]["nvidia_driver_version"] = "Available"
    except FileNotFoundError:
        state["gpu"]["nvidia_smi"] = {
            "success": False,
            "error": "nvidia-smi not found in PATH"
        }
    except subprocess.TimeoutExpired:
        state["gpu"]["nvidia_smi"] = {
            "success": False,
            "error": "nvidia-smi timeout"
        }
    except Exception as e:
        state["gpu"]["nvidia_smi"] = {
            "success": False,
            "error": str(e)
        }
    
    # 检查 CUDA 是否可用（通过 torch）
    try:
        import torch
        state["gpu"]["torch_available"] = True
        state["gpu"]["torch_version"] = torch.__version__
        state["gpu"]["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            state["gpu"]["cuda_version"] = torch.version.cuda
            state["gpu"]["gpu_count"] = torch.cuda.device_count()
            state["gpu"]["gpu_names"] = [
                torch.cuda.get_device_name(i) 
                for i in range(torch.cuda.device_count())
            ]
    except ImportError:
        state["gpu"]["torch_available"] = False
    except Exception as e:
        state["gpu"]["torch_error"] = str(e)
    
    # --- Windows 特定信息（注册表、MSVC 运行库）---
    if platform.system() == "Windows":
        state["windows_specific"] = probe_windows_registry()
    
    return state


def probe_windows_registry() -> Dict[str, Any]:
    """
    Windows 特定：探测注册表中的关键信息
    - MSVC 运行库版本
    - Visual Studio 安装路径
    - Windows SDK 版本
    
    注意：此函数使用 winreg 模块读取注册表，仅在 Windows 下调用。
    """
    registry_info = {
        "msvc_runtime": [],
        "visual_studio": [],
        "windows_sdk": [],
        "error": []
    }
    
    try:
        import winreg
        
        # 尝试读取 MSVC 运行库信息
        # MSVC 运行库通常注册在：
        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VisualStudio\<Version>\Setup\VC\ProductDir
        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\VCCompiler\Default\ProductDir
        
        # 方法 1: 尝试通过 vcvarsall.bat 推断 MSVC 位置
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        
        # 常见的 MSVC 安装路径
        msvc_paths = [
            os.path.join(program_files, "Microsoft Visual Studio"),
            os.path.join(program_files_x86, "Microsoft Visual Studio"),
        ]
        
        for msvc_path in msvc_paths:
            if os.path.exists(msvc_path):
                registry_info["visual_studio"].append({
                    "path": msvc_path,
                    "exists": True
                })
                # 尝试查找 vcvarsall.bat
                for root, dirs, files in os.walk(msvc_path, topdown=True, maxdepth=3):
                    if "vcvarsall.bat" in files:
                        registry_info["visual_studio"][-1]["vcvarsall"] = os.path.join(root, "vcvarsall.bat")
                        break
        
        # 方法 2: 尝试读取注册表（需要管理员权限）
        try:
            # 尝试读取 VC++ 编译器信息
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\VCCompiler\Default"
            ) as key:
                try:
                    product_dir, _ = winreg.QueryValueEx(key, "ProductDir")
                    registry_info["msvc_runtime"].append({
                        "source": "registry",
                        "product_dir": product_dir
                    })
                except FileNotFoundError:
                    registry_info["error"].append("VCCompiler registry key not found")
        except FileNotFoundError:
            registry_info["error"].append("VCCompiler registry key not found")
        except PermissionError:
            registry_info["error"].append("Permission denied reading VCCompiler registry")
        
        # 尝试读取 Windows SDK
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows Kits\Installed Roots"
            ) as key:
                try:
                    kit_root, _ = winreg.QueryValueEx(key, "KitsRoot10")
                    registry_info["windows_sdk"].append({
                        "source": "registry",
                        "kits_root": kit_root
                    })
                except FileNotFoundError:
                    registry_info["error"].append("Windows Kits registry key not found")
        except FileNotFoundError:
            registry_info["error"].append("Windows Kits registry key not found")
        except PermissionError:
            registry_info["error"].append("Permission denied reading Windows Kits registry")
            
    except ImportError:
        registry_info["error"].append("winreg module not available (not on Windows?)")
    except Exception as e:
        registry_info["error"].append(f"Unexpected error: {str(e)}")
    
    return registry_info


# =============================================================================
# 工具 2: search_web_for_issue() - 网络搜索工具
# =============================================================================
def search_web_for_issue(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    搜索工具：使用 duckduckgo-search (DDGS) 进行现场联网检索，
    获取最新的社区讨论和报错解决方案。
    
    参数:
        query: 搜索查询字符串
        max_results: 返回结果数量（默认 3 条）
    
    返回:
        列表，每项包含:
        - title: 结果标题
        - url: 原始 URL
        - snippet: 摘要/描述
    
    异常:
        ImportError: 如果 duckduckgo-search 未安装
        Exception: 搜索过程中的其他错误
    """
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return [{
                "title": "Error",
                "url": "",
                "snippet": "请先安装 ddgs: pip install ddgs"
            }]
    
    results = []

    try:
        with DDGS() as ddgs:
            # 执行搜索
            search_results = ddgs.text(query, max_results=max_results)

            for i, result in enumerate(search_results):
                # 确保所有值都是字符串
                title = result.get("title", f"Result {i+1}")
                url = result.get("href", "")
                body = result.get("body", "")
                
                # 转换为字符串
                if isinstance(title, bytes):
                    title = title.decode('utf-8', errors='ignore')
                if isinstance(url, bytes):
                    url = url.decode('utf-8', errors='ignore')
                if isinstance(body, bytes):
                    body = body.decode('utf-8', errors='ignore')
                
                results.append({
                    "title": str(title),
                    "url": str(url),
                    "snippet": str(body)
                })

                if len(results) >= max_results:
                    break

    except Exception as e:
        results.append({
            "title": "Search Error",
            "url": "",
            "snippet": f"搜索过程中发生错误: {str(e)}"
        })

    return results


# =============================================================================
# 工具 3: execute_real_command() - 真实命令执行工具
# =============================================================================
def execute_real_command(command: str, working_dir: Optional[str] = None, use_powershell: bool = False) -> Dict[str, str]:
    """
    执行工具：在真实终端环境中执行命令。
    
    **警告**: 这是一个极度危险且强大的工具。Agent 可以生成探测性命令，
    但必须在控制台中明确询问用户 [Y/n]，用户同意后才能执行。

    参数:
        command: 要执行的命令字符串
        working_dir: 工作目录（可选，默认为当前目录）
        use_powershell: 是否使用 PowerShell 执行（默认 False，使用 CMD）

    返回:
        字典，包含:
        - success: bool - 命令是否成功执行
        - returncode: int - 返回码
        - stdout: str - 标准输出
        - stderr: str - 标准错误
        - command: str - 原始命令

    注意:
        - 使用 subprocess.run(shell=True) 在真实 Shell 中执行
        - 捕获 stdout 和 stderr 流
        - 不使用虚拟沙盒，直接操作真实系统
    """
    result = {
        "success": False,
        "returncode": -1,
        "stdout": "",
        "stderr": "",
        "command": command
    }

    try:
        # 确定工作目录
        cwd = working_dir if working_dir else os.getcwd()

        # 如果使用 PowerShell，添加 powershell -Command 前缀
        # 但避免重复添加
        if use_powershell:
            cmd_lower = command.lower().strip()
            # 检查是否已经包含 powershell 前缀（包括 powershell, pwsh, powershell -Command 等）
            is_powershell_cmd = (
                cmd_lower.startswith('powershell') or 
                cmd_lower.startswith('pwsh') or
                cmd_lower.startswith('powershell -command') or
                cmd_lower.startswith('pwsh -command')
            )
            if not is_powershell_cmd:
                # 使用单引号包裹命令，避免特殊字符被解释
                command = f"powershell -Command '{command}'"
            # 如果已经有 powershell 前缀，则不需要再添加

        # 在真实 Shell 中执行命令
        # 使用 powershell -Command 来执行，确保管道等特殊字符被正确处理
        if use_powershell:
            # 如果命令已经包含 powershell 前缀，直接执行
            if cmd_lower.startswith('powershell') or cmd_lower.startswith('pwsh'):
                final_cmd = command
            else:
                # 使用单引号包裹命令，避免特殊字符被解释
                final_cmd = f"powershell -Command '{command}'"
            proc = subprocess.run(
                final_cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60  # 60秒超时
            )
        else:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60  # 60秒超时
            )

        result["returncode"] = proc.returncode
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr

        if proc.returncode == 0:
            result["success"] = True

    except subprocess.TimeoutExpired:
        result["stderr"] = "命令执行超时（超过 60 秒）"
    except FileNotFoundError:
        result["stderr"] = "无法执行命令：找不到可执行文件"
    except Exception as e:
        result["stderr"] = f"执行命令时发生异常: {str(e)}"

    return result


# =============================================================================
# 工具 3b: execute_powershell_command() - PowerShell 专用执行工具
# =============================================================================
def execute_powershell_command(script: str, working_dir: Optional[str] = None) -> Dict[str, str]:
    """
    PowerShell 专用执行工具：在真实 PowerShell 环境中执行脚本。
    
    这是 execute_real_command 的 PowerShell 专用版本，自动添加 powershell 前缀。

    参数:
        script: PowerShell 脚本内容
        working_dir: 工作目录（可选，默认为当前目录）

    返回:
        字典，包含:
        - success: bool - 命令是否成功执行
        - returncode: int - 返回码
        - stdout: str - 标准输出
        - stderr: str - 标准错误
        - command: str - 原始命令
    """
    return execute_real_command(script, working_dir=working_dir, use_powershell=True)


# =============================================================================
# 辅助函数：获取环境变量
# =============================================================================
def get_api_key(provider: str = "deepseek") -> Optional[str]:
    """
    从环境变量中获取 API 密钥。
    
    参数:
        provider: 提供商名称 ("deepseek" 或其他)
    
    返回:
        API 密钥字符串，如果未设置则返回 None
    """
    if provider.lower() == "deepseek":
        return os.environ.get("DEEPSEEK_API_KEY")
    return os.environ.get(f"{provider.upper()}_API_KEY")


def get_api_base_url(provider: str = "deepseek") -> Optional[str]:
    """
    从环境变量中获取 API 基础 URL。
    
    参数:
        provider: 提供商名称 ("deepseek" 或其他)
    
    返回:
        API 基础 URL 字符串，如果未设置则返回 None
    """
    if provider.lower() == "deepseek":
        return os.environ.get("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com/v1")
    return os.environ.get(f"{provider.upper()}_API_BASE_URL")


if __name__ == "__main__":
    # 测试工具函数
    print("=" * 60)
    print("Sys-Mentor 工具测试")
    print("=" * 60)
    
    # 测试探针
    print("\n[1] 测试 probe_system_state()...")
    state = probe_system_state()
    print(json.dumps(state, indent=2, ensure_ascii=False, default=str)[:500] + "...")
    
    # 测试搜索
    print("\n[2] 测试 search_web_for_issue()...")
    results = search_web_for_issue("Python PATH environment variable", max_results=2)
    for r in results:
        print(f"  - {r['title']}")
    
    # 测试执行命令
    print("\n[3] 测试 execute_real_command()...")
    result = execute_real_command("python --version")
    print(f"  Return code: {result['returncode']}")
    print(f"  Output: {result['stdout'].strip()}")

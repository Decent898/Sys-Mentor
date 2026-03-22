"""
test_local.py - Sys-Mentor 本地测试脚本

本脚本用于测试 tools.py 中的三个核心工具函数是否正常工作。
运行此脚本可以验证：
1. probe_system_state() 能否正确探测系统状态
2. search_web_for_issue() 能否正常联网搜索
3. execute_real_command() 能否正确执行命令

作者: Decent898
"""

import sys
import json

# 添加当前目录到路径
sys.path.insert(0, '.')

from tools import (
    probe_system_state,
    search_web_for_issue,
    execute_real_command,
    get_api_key
)


def test_probe_system_state():
    """测试系统探针功能"""
    print("=" * 60)
    print("测试 1: probe_system_state() - 系统探针")
    print("=" * 60)
    
    try:
        state = probe_system_state()
        
        print("\n✓ 探针执行成功")
        print("\n系统基本信息:")
        print(f"  平台: {state['system'].get('platform', 'N/A')}")
        print(f"  架构: {state['system'].get('machine', 'N/A')}")
        print(f"  Python: {state['system'].get('python_version', 'N/A').split(chr(10))[0]}")
        
        print("\nGPU 信息:")
        gpu = state.get('gpu', {})
        if gpu.get('nvidia_smi', {}).get('success'):
            print("  ✓ NVIDIA 驱动可用")
        else:
            print("  ✗ 未检测到 NVIDIA 驱动")
        
        if gpu.get('torch_available'):
            print(f"  ✓ PyTorch v{gpu.get('torch_version', 'N/A')}")
            if gpu.get('cuda_available'):
                print("  ✓ CUDA 可用")
            else:
                print("  ✗ CUDA 不可用")
        else:
            print("  ✗ PyTorch 未安装")
        
        print("\nWindows 特定信息:")
        ws = state.get('windows_specific', {})
        if ws:
            if ws.get('visual_studio'):
                print(f"  ✓ 检测到 {len(ws['visual_studio'])} 个 VS 安装")
            if ws.get('msvc_runtime'):
                print("  ✓ 检测到 MSVC 运行库")
        else:
            print("  - 非 Windows 系统或未检测到特定信息")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 探针执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_search_web_for_issue():
    """测试网络搜索功能"""
    print("\n" + "=" * 60)
    print("测试 2: search_web_for_issue() - 网络搜索")
    print("=" * 60)
    
    query = "Python PATH environment variable not working"
    
    try:
        results = search_web_for_issue(query, max_results=3)
        
        print(f"\n✓ 搜索执行成功 (查询: {query})")
        print(f"\n返回 {len(results)} 条结果:")
        
        for i, result in enumerate(results, 1):
            print(f"\n  [{i}] {result['title']}")
            print(f"      URL: {result['url'][:60]}...")
            snippet = result['snippet'][:100]
            print(f"      摘要: {snippet}...")
        
        return True
        
    except ImportError as e:
        print(f"\n✗ 依赖缺失: {str(e)}")
        print("  请运行: pip install duckduckgo-search")
        return False
        
    except Exception as e:
        print(f"\n✗ 搜索执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_execute_real_command():
    """测试命令执行功能"""
    print("\n" + "=" * 60)
    print("测试 3: execute_real_command() - 命令执行")
    print("=" * 60)
    
    # 测试 1: 简单命令
    print("\n测试 3.1: 执行 'python --version'")
    try:
        result = execute_real_command("python --version")
        
        if result['returncode'] == 0:
            print(f"  ✓ 执行成功")
            print(f"  输出: {result['stdout'].strip()}")
        else:
            print(f"  ✗ 执行失败 (返回码: {result['returncode']})")
            if result['stderr']:
                print(f"  错误: {result['stderr'].strip()}")
        
        test1_pass = result['returncode'] == 0
        
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        test1_pass = False
    
    # 测试 2: 列出目录
    print("\n测试 3.2: 执行 'dir' (Windows) 或 'ls' (Linux/Mac)")
    try:
        import platform
        cmd = "dir" if platform.system() == "Windows" else "ls"
        result = execute_real_command(cmd)
        
        if result['returncode'] == 0:
            print(f"  ✓ 执行成功")
            output_lines = result['stdout'].strip().split('\n')[:5]
            print(f"  前 5 行输出:")
            for line in output_lines:
                print(f"    {line[:60]}")
        else:
            print(f"  ✗ 执行失败 (返回码: {result['returncode']})")
        
        test2_pass = result['returncode'] == 0
        
    except Exception as e:
        print(f"  ✗ 异常: {str(e)}")
        test2_pass = False
    
    return test1_pass and test2_pass


def test_api_key():
    """测试 API 密钥配置"""
    print("\n" + "=" * 60)
    print("测试 4: API 密钥配置")
    print("=" * 60)
    
    api_key = get_api_key("deepseek")
    
    if api_key:
        print(f"\n✓ DEEPSEEK_API_KEY 已配置")
        print(f"  密钥前缀: {api_key[:10]}...")
        return True
    else:
        print(f"\n✗ DEEPSEEK_API_KEY 未配置")
        print("  请创建 .env 文件并设置 DEEPSEEK_API_KEY")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Sys-Mentor 本地测试")
    print("=" * 60)
    
    results = {}
    
    # 运行测试
    results['probe'] = test_probe_system_state()
    results['search'] = test_search_web_for_issue()
    results['execute'] = test_execute_real_command()
    results['api_key'] = test_api_key()
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {test_name:15} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    print(f"\n总计: {total_passed}/{total_tests} 个测试通过")
    
    if total_passed == total_tests:
        print("\n[绿色]所有测试通过！你可以开始使用 Sys-Mentor 了。[/绿色]")
        print("提示: 请确保已设置 DEEPSEEK_API_KEY 环境变量。")
    else:
        print("\n[黄色]部分测试失败，请检查上述错误信息。[/黄色]")
    
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())

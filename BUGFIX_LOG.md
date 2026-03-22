# Bug 修复日志

## 📅 2026年3月22日 - v1.0 初始版本

### ✅ 修复: duckduckgo-search 依赖问题
**问题**: 
- 在 Windows 上安装 `duckduckgo-search` 时可能出现 `ddgs.exe` 写入失败
- 错误信息: `ERROR: Could not install packages due to an OSError: [WinError 2]`

**解决方案**:
- 将 `duckduckgo-search` 从必需依赖改为可选依赖
- 在 `requirements.txt` 中注释掉
- 在 `tools.py` 中添加异常处理
- 在 `README.md` 和 `QUICKSTART.md` 中说明

**影响**:
- 联网搜索功能在未安装时不可用
- 其他核心功能不受影响

**代码变更**:
```python
# tools.py - search_web_for_issue()
try:
    from duckduckgo_search import DDGS
except ImportError:
    return [{
        "title": "Error",
        "url": "",
        "snippet": "请先安装 duckduckgo-search: pip install duckduckgo-search"
    }]
```

---

### ✅ 修复: 环境变量配置
**问题**:
- 用户可能不知道如何配置 API 密钥

**解决方案**:
- 创建 `.env.example` 模板文件
- 在 `main.py` 中检查 API 密钥并提示
- 在 `run.bat` 中检查 `.env` 文件并提示

**代码变更**:
```python
# main.py - __init__()
if not self.api_key:
    console.print("[yellow]⚠ 未设置 DEEPSEEK_API_KEY，部分功能将不可用[/yellow]")
```

---

### ✅ 修复: 虚拟环境检测
**问题**:
- 用户可能没有创建虚拟环境

**解决方案**:
- `run.bat` 自动检测并创建虚拟环境
- 提供清晰的错误提示

**代码变更**:
```batch
REM run.bat
if not exist "venv" (
    echo [信息] 检测到虚拟环境不存在，正在创建...
    python -m venv venv
)
```

---

### ✅ 修复: 命令执行超时
**问题**:
- 某些命令可能无限挂起

**解决方案**:
- 设置 60 秒超时
- 捕获 `TimeoutExpired` 异常

**代码变更**:
```python
# tools.py - execute_real_command()
proc = subprocess.run(
    command,
    shell=True,
    capture_output=True,
    text=True,
    timeout=60  # 60秒超时
)
```

---

### ✅ 修复: Windows 注册表权限
**问题**:
- 读取注册表可能需要管理员权限

**解决方案**:
- 添加异常处理
- 降级处理：如果权限不足，返回错误信息

**代码变更**:
```python
# tools.py - probe_windows_registry()
try:
    with winreg.OpenKey(...) as key:
        # 读取注册表
except PermissionError:
    registry_info["error"].append("Permission denied")
```

---

## 📋 待修复问题

### 高优先级
- [ ] 无

### 中优先级
- [ ] 添加命令历史记录
- [ ] 优化 Markdown 渲染性能
- [ ] 改进错误提示信息

### 低优先级
- [ ] 支持更多大模型
- [ ] 添加插件系统
- [ ] 异步支持

---

## 📝 更新说明

### v1.0 (2026年3月22日)
- 初始版本发布
- 实现核心功能
- 添加测试脚本
- 完善文档

---

**最后更新**: 2026年3月22日

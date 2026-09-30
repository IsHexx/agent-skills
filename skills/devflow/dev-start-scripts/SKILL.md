---
name: dev-start-scripts
description: >-
  为项目编写跨平台一键启动/停止脚本：Windows（PowerShell）、Linux（Bash）、macOS（Bash）三版
  平台脚本 + start.sh / start.ps1 统一入口（自动识别操作系统分发）+ 对应停止脚本。
  核心要求：端口被占用时先杀掉占用进程再启动；先侦察项目真实启动方式（入口、端口、依赖、
  是否需要 Docker/迁移），不许凭空猜。
  当用户说"写启动脚本"、"一键启动"、"写三版启动脚本 windows/linux/macos"、
  "写个总启动脚本自动判断系统"、"整理启动流程成脚本"时使用。
  不用于：给单个服务写 systemd/supervisor 守护配置、写 Dockerfile/compose。
metadata:
  version: "1.0.0"
  category: tooling
---

你现在的任务是为当前项目产出一套可直接使用的跨平台启动/停止脚本。

## 阶段一：侦察项目（必须先做，用证据不用猜测）

在写任何脚本前，用 Read/Grep/Glob 确认以下事实，并在最终汇报中说明依据：

1. **后端怎么起**：入口命令、监听端口。线索位置：README、入口文件头部注释、
   `grep -rn "uvicorn\|--port\|listen" --include="*.py"`、配置文件。
2. **前端怎么起**：`package.json` 的 scripts、dev server 端口（vite/webpack 配置）、
   proxy 指向哪个后端端口、构建产物（如 `dist/`）是否由后端静态托管（托管则需在启动前保证产物存在）。
3. **依赖准备动作**：Python 虚拟环境（`.venv` + `requirements.txt`）、`node_modules`、
   构建步骤。Windows 的 venv 解释器在 `.venv/Scripts/python.exe`，Linux/macOS 在 `.venv/bin/python`。
4. **是否有 Docker / 数据库迁移**：找 `docker-compose.yml`、`Dockerfile`、alembic、
  迁移脚本。有则纳入启动流程（启动容器 → 等 healthy → 迁移 → 再起服务）；没有就不要写。

## 阶段二：产出文件清单

统一放在 `scripts/` 目录：

```
scripts/
├── start.sh            # 统一入口（Bash）：uname -s 识别系统后分发
├── start.ps1           # 统一入口（PowerShell）：$IsWindows/$IsLinux/$IsMacOS 分发
├── start-windows.ps1   # Windows 平台实现
├── start-linux.sh      # Linux 平台实现
├── start-macos.sh      # macOS 平台实现
├── stop.sh / stop.ps1  # 统一停止入口（结构同 start）
└── stop-windows.ps1 / stop-linux.sh / stop-macos.sh
```

`.sh` 文件写完后 `chmod +x`。把 `scripts/.pids/` 加进项目 `.gitignore`。

## 阶段三：每个启动脚本的标准流程

1. **释放端口**（核心需求）：对服务用到的每个端口，先杀占用进程。
2. **准备依赖**：缺 venv 就创建并装 requirements；缺 node_modules 就 `npm install`；
   后端托管静态产物且产物缺失就 `npm run build`。
3. **启动服务**：Windows 用 `Start-Process powershell -PassThru` 开独立窗口（方便看日志，
   `-PassThru` 拿到的 PID 写入 `scripts/.pids/*-window.pid`）；
   Linux/macOS 用 `nohup ... &` 后台运行，日志写 `logs/`，PID 写 `scripts/.pids/`。
4. **等端口就绪**：轮询直到可连接或超时（默认 60s），超时要打印去哪里看日志。
5. **收尾**：打印各服务地址和对应的停止命令。

### 端口占用处理（各平台实现要点）

Windows PowerShell（精确、不误杀）：

```powershell
function Stop-PortProcess([int]$Port) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return }
    foreach ($p in ($conns | Select-Object -ExpandProperty OwningProcess -Unique)) {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -ne "System") {
            Write-Host "端口 $Port 被 $($proc.ProcessName) (PID $p) 占用，结束该进程"
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Milliseconds 500
}
```

Linux（lsof 优先，fuser 兜底）/ macOS（自带 lsof）：

```bash
kill_port() {
    local port=$1 pids=""
    pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "端口 $port 被 PID $pids 占用，结束该进程"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    elif command -v fuser >/dev/null 2>&1; then   # Linux 无 lsof 时
        fuser -k "$port"/tcp 2>/dev/null || true
    fi
}
```

### 等端口就绪

- Bash：优先 `curl -sf http://127.0.0.1:$port/`，退回 `bash` 的 `/dev/tcp`（注意 zsh 不支持）。
- PowerShell：`[System.Net.Sockets.TcpClient]::Connect("127.0.0.1", $Port)` try/catch。

### 统一入口的分发逻辑

- `start.sh`：`uname -s` → `Linux*` 跑 linux 脚本，`Darwin*` 跑 macos 脚本，
  `MINGW*|MSYS*|CYGWIN*|Windows_NT`（Git Bash）转调
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...\start-windows.ps1`。
- `start.ps1`：`$IsWindows -or $env:OS -eq "Windows_NT"` → windows.ps1；
  `$IsLinux` / `$IsMacOS` → `bash start-linux.sh` / `bash start-macos.sh`。

## 阶段四：停止脚本

- **按端口杀实际服务进程**（复用上面的 Stop-PortProcess / kill_port），不管服务是不是脚本起的都能停掉。
- 再按 `scripts/.pids/` 里的 PID 文件清理窗口/后台进程，删 PID 文件。
- Linux/macOS 停止脚本最后以端口检查兜底。

## 已踩过的坑（务必遵守）

1. **PS1 含中文必须存成 UTF-8 带 BOM**。Windows PowerShell 5.1 对无 BOM 的 .ps1 按系统
   代码页（GBK）解码，中文里的字节会被误解析成引号/反斜杠导致语法错误。Write/Edit 工具
   写文件不带 BOM，写完或改完要补：
   `printf '\xEF\xBB\xBF' | cat - file.ps1 > tmp && mv tmp file.ps1`，然后重新验证。
2. **禁止按 CommandLine 模糊匹配杀进程**（如 `-match 'uvicorn'`）：任何命令行里出现过该
   字符串的 bash/powershell 进程都会被误杀。一律按端口定位进程。
3. **macOS 等待端口别用 `/dev/tcp`**：默认 shell 是 zsh，不支持，用 curl。
4. **Git Bash 不是 cmd**：统一入口必须把 MINGW/MSYS/CYGWIN 识别为 Windows 并转调 PowerShell。
5. Windows 上 `Start-Process` 要加 `-PassThru` 才能拿到新窗口的 PID 供停止脚本使用。

## 阶段五：验证纪律

1. 每个 `.sh` 跑 `bash -n`；每个 `.ps1` 用 PowerShell Parser 做语法解析：
   `[System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$t, [ref]$errs)`。
2. 端口检测逻辑在真机上实测（只检测、不杀）。
3. **如果目标服务正在被用户使用，不要完整执行启动脚本做验证**——它会杀掉正在用的进程、
   还会在用户桌面弹新窗口。只做局部验证（语法、端口检测），把完整运行留给用户，并在汇报中说明。

## 汇报格式

用表格列出：类型（启动/停止）× 入口（Bash/PowerShell）× 平台实现文件；
简述每个脚本的流程、端口占用处理方式和平台差异；明确说明哪些验证做过、哪些留给用户做。

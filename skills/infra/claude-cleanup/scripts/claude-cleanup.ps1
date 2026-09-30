param(
  [switch]$AuditOnly,
  [switch]$Clean,
  [string[]]$PreserveWorkspace = @()
)

$ErrorActionPreference = "Stop"

if (-not $AuditOnly -and -not $Clean) {
  $AuditOnly = $true
}

function Resolve-FullPath {
  param([string]$Path)
  try { [System.IO.Path]::GetFullPath($Path) } catch { $Path }
}

function Test-IsUnderPreservedWorkspace {
  param([string]$Path)
  $full = Resolve-FullPath $Path
  foreach ($workspace in $PreserveWorkspace) {
    if (-not $workspace) { continue }
    $preserve = Resolve-FullPath $workspace
    if ($full.StartsWith($preserve, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }
  return $false
}

function Get-DirectoryStats {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) { return $null }
  $item = Get-Item -LiteralPath $Path -Force
  if ($item.PSIsContainer) {
    $files = Get-ChildItem -LiteralPath $Path -Recurse -Force -File -ErrorAction SilentlyContinue
    return [pscustomobject]@{
      Path = $Path
      Type = "Directory"
      Files = ($files | Measure-Object).Count
      SizeMB = [math]::Round((($files | Measure-Object Length -Sum).Sum / 1MB), 2)
      LastWriteTime = $item.LastWriteTime
    }
  }
  [pscustomobject]@{
    Path = $Path
    Type = "File"
    Files = 1
    SizeMB = [math]::Round($item.Length / 1MB, 2)
    LastWriteTime = $item.LastWriteTime
  }
}

function Add-IfExists {
  param(
    [System.Collections.Generic.List[string]]$List,
    [string]$Path
  )
  if ($Path -and (Test-Path -LiteralPath $Path) -and -not (Test-IsUnderPreservedWorkspace $Path)) {
    [void]$List.Add((Resolve-FullPath $Path))
  }
}

$targets = [System.Collections.Generic.List[string]]::new()

$user = $env:USERPROFILE
$appData = $env:APPDATA
$localAppData = $env:LOCALAPPDATA
$temp = $env:TEMP
$npmPrefix = $null
try { $npmPrefix = (npm config get prefix 2>$null).Trim() } catch {}
if (-not $npmPrefix) { $npmPrefix = Join-Path $appData "npm" }

$staticTargets = @(
  (Join-Path $user ".claude"),
  (Join-Path $user ".claude.json"),
  (Join-Path $user ".claude.json.backup"),
  (Join-Path $localAppData "claude-cli-nodejs"),
  (Join-Path $appData "clawdhub"),
  (Join-Path $user ".config\ccstatusline"),
  (Join-Path $npmPrefix "node_modules\@anthropic-ai")
)

foreach ($path in $staticTargets) { Add-IfExists -List $targets -Path $path }

Get-ChildItem -LiteralPath $user -Force -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match "(?i)^anthropic-ai-claude-code-.*\.tgz$" } |
  ForEach-Object { Add-IfExists -List $targets -Path $_.FullName }

Get-ChildItem -LiteralPath $temp -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match "(?i)^claude" } |
  ForEach-Object { Add-IfExists -List $targets -Path $_.FullName }

Get-ChildItem -LiteralPath $npmPrefix -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match "(?i)^(claude|claude-code|ccusage|ccstatusline|clawdhub)(\.cmd|\.ps1)?$" } |
  ForEach-Object { Add-IfExists -List $targets -Path $_.FullName }

$vscodeExt = Join-Path $user ".vscode\extensions"
if (Test-Path -LiteralPath $vscodeExt) {
  Get-ChildItem -LiteralPath $vscodeExt -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "(?i)^anthropic\.claude-code" } |
    ForEach-Object { Add-IfExists -List $targets -Path $_.FullName }
}

$vsixCache = Join-Path $appData "Code\CachedExtensionVSIXs"
if (Test-Path -LiteralPath $vsixCache) {
  Get-ChildItem -LiteralPath $vsixCache -Force -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match "(?i)anthropic\.claude-code|claude|anthropic" } |
    ForEach-Object { Add-IfExists -List $targets -Path $_.FullName }
}

$codeLogs = Join-Path $appData "Code\logs"
if (Test-Path -LiteralPath $codeLogs) {
  Get-ChildItem -LiteralPath $codeLogs -Recurse -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match "(?i)Anthropic\.claude-code" } |
    ForEach-Object { Add-IfExists -List $targets -Path $_.FullName }
}

$npxRoot = Join-Path $localAppData "npm-cache\_npx"
if (Test-Path -LiteralPath $npxRoot) {
  Get-ChildItem -LiteralPath $npxRoot -Force -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $hit = Get-ChildItem -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue |
      Where-Object { $_.FullName -match "(?i)ccusage|ccstatusline|clawdhub|claude-agent-acp|@anthropic-ai" } |
      Select-Object -First 1
    if ($hit) { Add-IfExists -List $targets -Path $_.FullName }
  }
}

$commands = foreach ($name in @("claude", "claude-code", "ccusage", "ccstatusline", "clawdhub")) {
  Get-Command $name -ErrorAction SilentlyContinue | Select-Object Name, CommandType, Source, Path
}

$npmMatches = @()
try {
  $npmMatches = npm list -g --depth=0 2>$null | Select-String -Pattern "claude|anthropic|ccusage|ccstatusline|clawdhub" -CaseSensitive:$false
} catch {}

$targetStats = $targets |
  Select-Object -Unique |
  ForEach-Object { Get-DirectoryStats -Path $_ } |
  Where-Object { $_ }

[pscustomobject]@{
  Mode = if ($Clean) { "Clean" } else { "AuditOnly" }
  CommandMatches = @($commands).Count
  NpmMatches = @($npmMatches).Count
  TargetCount = @($targetStats).Count
} | ConvertTo-Json -Depth 4

if ($commands) {
  "COMMAND_MATCHES"
  $commands | Format-Table -AutoSize | Out-String
}

if ($npmMatches) {
  "NPM_MATCHES"
  $npmMatches | ForEach-Object { $_.Line }
}

if ($targetStats) {
  "TARGETS"
  $targetStats | Sort-Object Path | Format-Table -AutoSize | Out-String
} else {
  "No cleanable Claude Code remnants found."
}

if ($Clean) {
  foreach ($pkg in @("@anthropic-ai/claude-code", "ccusage", "ccstatusline", "clawdhub")) {
    try { npm uninstall -g $pkg 2>$null | Out-Null } catch {}
  }

  $allowedPrefixes = @($user, $appData, $localAppData, $temp, $npmPrefix) |
    Where-Object { $_ } |
    ForEach-Object { Resolve-FullPath $_ }

  foreach ($target in ($targets | Select-Object -Unique)) {
    $full = Resolve-FullPath $target
    if (Test-IsUnderPreservedWorkspace $full) {
      Write-Output "SKIP preserved workspace: $full"
      continue
    }
    $allowed = $false
    foreach ($prefix in $allowedPrefixes) {
      if ($full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        $allowed = $true
        break
      }
    }
    if (-not $allowed) { throw "Refusing to delete outside allowed prefixes: $full" }
    if (Test-Path -LiteralPath $full) {
      Remove-Item -LiteralPath $full -Recurse -Force
      Write-Output "Deleted: $full"
    }
  }
}

[CmdletBinding(DefaultParameterSetName = 'Check')]
param(
    [Parameter(ParameterSetName = 'Check')]
    [switch]$Check,

    [Parameter(ParameterSetName = 'Plan')]
    [switch]$Plan,

    [Parameter(ParameterSetName = 'Apply')]
    [switch]$Apply,

    [Parameter(ParameterSetName = 'Apply', Mandatory = $true)]
    [switch]$Confirmed,

    [string]$StateRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:SkillRoot = Split-Path -Parent $PSScriptRoot
$script:ExampleConfig = Join-Path $script:SkillRoot 'config.example.json'

function Write-JsonAtomic {
    param([Parameter(Mandatory = $true)]$Value, [Parameter(Mandatory = $true)][string]$Destination)

    $folder = Split-Path -Parent $Destination
    [System.IO.Directory]::CreateDirectory($folder) | Out-Null
    $temporary = Join-Path $folder ('.' + [System.IO.Path]::GetFileName($Destination) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        $json = $Value | ConvertTo-Json -Depth 20
        [System.IO.File]::WriteAllText($temporary, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Destination -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
    }
}

function Resolve-ConfiguredPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [regex]::Replace($Path, '\$\{([A-Za-z_][A-Za-z0-9_]*)\}', {
        param($match)
        $value = [Environment]::GetEnvironmentVariable($match.Groups[1].Value)
        if ([string]::IsNullOrWhiteSpace($value) -and $match.Groups[1].Value -eq 'CODEX_HOME') {
            $value = Join-Path $env:USERPROFILE '.codex'
        }
        if ([string]::IsNullOrWhiteSpace($value)) { throw "环境变量未设置：$($match.Groups[1].Value)" }
        return $value
    })
}

function Initialize-State {
    param([string]$RequestedRoot)

    if ([string]::IsNullOrWhiteSpace($RequestedRoot)) {
        $base = $env:LOCALAPPDATA
        if ([string]::IsNullOrWhiteSpace($base)) { $base = Join-Path $env:USERPROFILE 'AppData\Local' }
        $RequestedRoot = Join-Path $base 'skill-catalog'
    }
    [System.IO.Directory]::CreateDirectory($RequestedRoot) | Out-Null
    $paths = [pscustomobject]@{
        state = $RequestedRoot
        config = Join-Path $RequestedRoot 'config.json'
        health = Join-Path $RequestedRoot 'platform-health.json'
        plan = Join-Path $RequestedRoot 'platform-plan.json'
    }
    if (-not (Test-Path -LiteralPath $paths.config)) { Copy-Item -LiteralPath $script:ExampleConfig -Destination $paths.config }
    return $paths
}

function Read-PlatformConfig {
    param([Parameter(Mandatory = $true)][string]$ConfigPath)

    try {
        $config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $config.canonical -or [string]::IsNullOrWhiteSpace([string]$config.canonical.path)) { throw '缺少 canonical.path。' }
        if ($null -eq $config.platforms) { throw '缺少 platforms。' }
        $seen = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
        foreach ($platform in @($config.platforms)) {
            if ([string]::IsNullOrWhiteSpace([string]$platform.platform_id) -or [string]$platform.platform_id -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') { throw 'platform_id 必须为小写连字符格式。' }
            if (-not $seen.Add([string]$platform.platform_id)) { throw "platform_id 重复：$($platform.platform_id)" }
            if (@('native', 'junction', 'manual') -notcontains [string]$platform.mode) { throw "平台 mode 无效：$($platform.platform_id)" }
            if ([string]::IsNullOrWhiteSpace([string]$platform.path)) { throw "平台缺少 path：$($platform.platform_id)" }
        }
        return $config
    }
    catch { throw "平台配置无效：$($_.Exception.Message)" }
}

function Get-CanonicalSkills {
    param([Parameter(Mandatory = $true)][string]$CanonicalPath)

    if (-not (Test-Path -LiteralPath $CanonicalPath -PathType Container)) { throw "中央 Skill 目录不可用：$CanonicalPath" }
    return @(
        Get-ChildItem -LiteralPath $CanonicalPath -Directory -Force |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') -PathType Leaf } |
            Sort-Object -Property Name |
            ForEach-Object { [pscustomobject]@{ name = $_.Name; path = $_.FullName } }
    )
}

function Resolve-FullPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
}

function Test-JunctionTarget {
    param(
        [Parameter(Mandatory = $true)][string]$LinkPath,
        [Parameter(Mandatory = $true)][string]$ExpectedTarget
    )

    $item = Get-Item -LiteralPath $LinkPath -Force
    if ([string]::IsNullOrWhiteSpace([string]$item.LinkType) -or $item.LinkType -notin @('Junction', 'SymbolicLink')) { return $false }
    $targets = @($item.Target)
    if ($targets.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$targets[0])) { return $false }
    $target = [string]$targets[0]
    if (-not [System.IO.Path]::IsPathRooted($target)) { $target = Join-Path (Split-Path -Parent $LinkPath) $target }
    return [string]::Equals((Resolve-FullPath $target), (Resolve-FullPath $ExpectedTarget), [System.StringComparison]::OrdinalIgnoreCase)
}

function New-PlatformPlan {
    param([Parameter(Mandatory = $true)]$Config)

    $canonicalPath = Resolve-ConfiguredPath -Path ([string]$Config.canonical.path)
    $skills = Get-CanonicalSkills -CanonicalPath $canonicalPath
    $platformPlans = New-Object System.Collections.Generic.List[object]

    foreach ($platform in @($Config.platforms)) {
        if (-not [bool]$platform.enabled) { continue }
        $destinationRoot = Resolve-ConfiguredPath -Path ([string]$platform.path)
        $actions = New-Object System.Collections.Generic.List[object]
        $status = 'healthy'
        $message = $null
        $mode = [string]$platform.mode

        if ($mode -eq 'native') {
            if (-not [string]::Equals((Resolve-FullPath $canonicalPath), (Resolve-FullPath $destinationRoot), [System.StringComparison]::OrdinalIgnoreCase)) {
                $status = 'misconfigured'
                $message = 'native 模式的平台路径必须等于中央目录。'
            }
            else {
                foreach ($skill in $skills) { $actions.Add([pscustomobject]@{ action = 'native'; skill = $skill.name; source = $skill.path; destination = $destinationRoot }) }
            }
        }
        elseif ($mode -eq 'manual') {
            $status = 'pending-manual'
            $message = if ($platform.note) { [string]$platform.note } else { '需要先确认该终端的 Skill 发现入口。' }
        }
        else {
            if (-not (Test-Path -LiteralPath $destinationRoot -PathType Container)) {
                if ([bool]$platform.create_root) {
                    $actions.Add([pscustomobject]@{ action = 'create-root'; skill = $null; source = $null; destination = $destinationRoot })
                    $status = 'needs-apply'
                }
                else {
                    $status = 'unavailable'
                    $message = '目标目录不存在，且配置不允许自动创建。'
                }
            }
            foreach ($skill in $skills) {
                $destination = Join-Path $destinationRoot $skill.name
                if (-not (Test-Path -LiteralPath $destination)) {
                    $actions.Add([pscustomobject]@{ action = 'create-junction'; skill = $skill.name; source = $skill.path; destination = $destination })
                    if ($status -eq 'healthy') { $status = 'needs-apply' }
                    continue
                }
                if (Test-JunctionTarget -LinkPath $destination -ExpectedTarget $skill.path) {
                    $actions.Add([pscustomobject]@{ action = 'current'; skill = $skill.name; source = $skill.path; destination = $destination })
                }
                else {
                    $actions.Add([pscustomobject]@{ action = 'conflict'; skill = $skill.name; source = $skill.path; destination = $destination })
                    $status = 'conflict'
                }
            }
        }

        $platformPlans.Add([pscustomobject]@{
            platform_id = [string]$platform.platform_id
            mode = $mode
            destination_root = $destinationRoot
            status = $status
            message = $message
            actions = $actions.ToArray()
        })
    }

    return [pscustomobject]@{
        schema_version = 1
        generated_at = (Get-Date).ToUniversalTime().ToString('o')
        canonical = [pscustomobject]@{ path = $canonicalPath; skills = $skills.Count }
        platforms = $platformPlans.ToArray()
    }
}

function Write-PlatformState {
    param([Parameter(Mandatory = $true)]$PlatformPlan, [Parameter(Mandatory = $true)]$Paths)

    $hasConflict = @($PlatformPlan.platforms | Where-Object { $_.status -in @('conflict', 'misconfigured', 'unavailable') }).Count -gt 0
    $needsApply = @($PlatformPlan.platforms | Where-Object { $_.status -eq 'needs-apply' }).Count -gt 0
    $health = [pscustomobject]@{
        schema_version = 1
        checked_at = (Get-Date).ToUniversalTime().ToString('o')
        status = if ($hasConflict) { 'attention' } elseif ($needsApply) { 'needs-apply' } else { 'healthy' }
        canonical = $PlatformPlan.canonical
        platforms = $PlatformPlan.platforms
    }
    Write-JsonAtomic -Value $PlatformPlan -Destination $Paths.plan
    Write-JsonAtomic -Value $health -Destination $Paths.health
    return $health
}

function Invoke-Apply {
    param([Parameter(Mandatory = $true)]$PlatformPlan)

    $misconfigured = @($PlatformPlan.platforms | Where-Object { $_.status -eq 'misconfigured' })
    if ($misconfigured.Count -gt 0) { throw '存在配置错误的平台，未创建任何链接。请先处理 platform-plan.json。' }
    foreach ($platform in @($PlatformPlan.platforms | Where-Object { $_.mode -eq 'junction' })) {
        if ($platform.status -eq 'unavailable') { continue }
        foreach ($action in @($platform.actions | Where-Object { $_.action -eq 'create-root' })) {
            if (-not (Test-Path -LiteralPath $action.destination)) { [System.IO.Directory]::CreateDirectory($action.destination) | Out-Null }
        }
        foreach ($action in @($platform.actions | Where-Object { $_.action -eq 'create-junction' })) {
            if (Test-Path -LiteralPath $action.destination) { throw "目标在执行前发生变化，已停止：$($action.destination)" }
            New-Item -ItemType Junction -Path $action.destination -Target $action.source | Out-Null
        }
    }
}

$paths = Initialize-State -RequestedRoot $StateRoot
$mutex = $null
$lockTaken = $false
try {
    if ($PSCmdlet.ParameterSetName -eq 'Apply') {
        $mutex = New-Object System.Threading.Mutex($false, 'Local\SkillCatalogPlatformLock')
        $lockTaken = $mutex.WaitOne([TimeSpan]::FromSeconds(30))
        if (-not $lockTaken) { throw '平台适配正在由其他操作更新，请稍后重试。' }
    }
    $config = Read-PlatformConfig -ConfigPath $paths.config
    $platformPlan = New-PlatformPlan -Config $config
    if ($PSCmdlet.ParameterSetName -eq 'Apply') {
        Invoke-Apply -PlatformPlan $platformPlan
        $platformPlan = New-PlatformPlan -Config $config
    }
    $health = Write-PlatformState -PlatformPlan $platformPlan -Paths $paths
    [pscustomobject]@{ status = $health.status; canonical_skills = $platformPlan.canonical.skills; platforms = @($platformPlan.platforms | ForEach-Object { [pscustomobject]@{ platform_id = $_.platform_id; status = $_.status; actions = @($_.actions).Count } }); state_root = $paths.state } | ConvertTo-Json -Compress
    if ($PSCmdlet.ParameterSetName -eq 'Check') { if ($health.status -eq 'healthy') { exit 0 } else { exit 2 } }
    exit 0
}
catch {
    [pscustomobject]@{ status = 'error'; message = $_.Exception.Message } | ConvertTo-Json -Compress
    exit 1
}
finally {
    if ($lockTaken -and $null -ne $mutex) { $mutex.ReleaseMutex() }
    if ($null -ne $mutex) { $mutex.Dispose() }
}

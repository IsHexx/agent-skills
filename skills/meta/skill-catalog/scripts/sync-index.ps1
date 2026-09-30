[CmdletBinding(DefaultParameterSetName = 'Check')]
param(
    [Parameter(ParameterSetName = 'Check')]
    [switch]$Check,

    [Parameter(ParameterSetName = 'Rebuild')]
    [switch]$Rebuild,

    [Parameter(ParameterSetName = 'Export')]
    [switch]$ExportPreferences,

    [Parameter(ParameterSetName = 'Import')]
    [switch]$ImportPreferences,

    [Parameter(ParameterSetName = 'Export', Mandatory = $true)]
    [Parameter(ParameterSetName = 'Import', Mandatory = $true)]
    [string]$Path,

    [Parameter(ParameterSetName = 'AdoptPlan', Mandatory = $true)]
    [string]$AdoptPlan,

    [Parameter(ParameterSetName = 'AdoptCommit', Mandatory = $true)]
    [string]$AdoptCommit,

    [Parameter(ParameterSetName = 'AdoptCommit')]
    [switch]$Confirmed,

    [string]$StateRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:SchemaVersion = 2
$script:SkillRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$script:HubRoot = Split-Path -Parent $script:SkillRoot
$script:ExampleConfig = Join-Path $script:SkillRoot 'config.example.json'
$script:RegistryPath = Join-Path (Split-Path -Parent $script:HubRoot) 'skills-registry.md'

function Write-JsonAtomic {
    param(
        [Parameter(Mandatory = $true)]$Value,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $folder = Split-Path -Parent $Destination
    [System.IO.Directory]::CreateDirectory($folder) | Out-Null
    $temporary = Join-Path $folder ('.' + [System.IO.Path]::GetRandomFileName())
    $json = $Value | ConvertTo-Json -Depth 32
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    try {
        [System.IO.File]::WriteAllText($temporary, $json + [Environment]::NewLine, $utf8)
        Move-Item -LiteralPath $temporary -Destination $Destination -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
        }
    }
}

function Write-TextAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $folder = Split-Path -Parent $Destination
    [System.IO.Directory]::CreateDirectory($folder) | Out-Null
    $temporary = Join-Path $folder ('.' + [System.IO.Path]::GetRandomFileName())
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    try {
        [System.IO.File]::WriteAllText($temporary, $Text, $utf8)
        Move-Item -LiteralPath $temporary -Destination $Destination -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
        }
    }
}

function Get-Utf8Text {
    param([Parameter(Mandatory = $true)][string]$LiteralPath)

    $bytes = [System.IO.File]::ReadAllBytes($LiteralPath)
    $encoding = [System.Text.UTF8Encoding]::new($true)
    try {
        $text = $encoding.GetString($bytes)
    }
    catch {
        throw "文件不是有效 UTF-8：$LiteralPath"
    }
    if ($text.Length -gt 0 -and [int][char]$text[0] -eq 0xFEFF) {
        $text = $text.Substring(1)
    }
    return $text -replace "`r`n", "`n"
}

function ConvertTo-PlainMetadataValue {
    param([string]$Value)

    $trimmed = $Value.Trim()
    if ($trimmed.Length -ge 2 -and (($trimmed.StartsWith('"') -and $trimmed.EndsWith('"')) -or ($trimmed.StartsWith("'") -and $trimmed.EndsWith("'")))) {
        $trimmed = $trimmed.Substring(1, $trimmed.Length - 2)
    }
    return ($trimmed -replace '\s+', ' ').Trim()
}

function Read-SkillMetadata {
    param([Parameter(Mandatory = $true)][string]$SkillFile)

    $text = Get-Utf8Text -LiteralPath $SkillFile
    $lines = $text -split "`n"
    if ($lines.Count -lt 3 -or $lines[0].Trim() -ne '---') {
        throw '缺少开头 frontmatter 分隔符。'
    }

    $end = -1
    for ($index = 1; $index -lt $lines.Count; $index++) {
        if ($lines[$index].Trim() -eq '---') {
            $end = $index
            break
        }
    }
    if ($end -lt 1) {
        throw '缺少结束 frontmatter 分隔符。'
    }

    $metadata = @{}
    $index = 1
    while ($index -lt $end) {
        $line = $lines[$index]
        if ($line.Trim().Length -eq 0 -or $line.TrimStart().StartsWith('#')) {
            $index++
            continue
        }
        $match = [regex]::Match($line, '^(?<key>[A-Za-z][A-Za-z0-9_-]*):\s*(?<value>.*)$')
        if (-not $match.Success) {
            $index++
            continue
        }
        $key = $match.Groups['key'].Value
        $value = $match.Groups['value'].Value
        if ($value.Trim() -match '^[>|][+-]?$') {
            $block = New-Object System.Collections.Generic.List[string]
            $index++
            while ($index -lt $end -and ($lines[$index] -match '^\s+' -or $lines[$index].Trim().Length -eq 0)) {
                $block.Add($lines[$index].Trim())
                $index++
            }
            $metadata[$key] = ($block -join ' ' -replace '\s+', ' ').Trim()
            continue
        }
        $metadata[$key] = ConvertTo-PlainMetadataValue -Value $value
        $index++
    }

    if (-not $metadata.ContainsKey('name') -or [string]::IsNullOrWhiteSpace($metadata['name'])) {
        throw 'frontmatter 缺少 name。'
    }
    if ($metadata['name'] -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') {
        throw "name 不符合小写连字符规范：$($metadata['name'])"
    }
    if (-not $metadata.ContainsKey('description') -or [string]::IsNullOrWhiteSpace($metadata['description'])) {
        throw 'frontmatter 缺少 description。'
    }

    return [pscustomobject]@{
        name = $metadata['name']
        description = ($metadata['description'] -replace '\s+', ' ').Trim()
    }
}

function Resolve-ConfiguredPath {
    param([Parameter(Mandatory = $true)][string]$ConfiguredPath)

    $profilePath = $env:USERPROFILE
    if ([string]::IsNullOrWhiteSpace($profilePath)) {
        throw 'USERPROFILE 环境变量不可用。'
    }
    $localAppData = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($localAppData)) {
        $localAppData = Join-Path $profilePath 'AppData\Local'
    }
    $codexBase = $env:CODEX_HOME
    if ([string]::IsNullOrWhiteSpace($codexBase)) {
        $codexBase = Join-Path $profilePath '.codex'
    }

    $variables = @{
        'USERPROFILE' = $profilePath
        'LOCALAPPDATA' = $localAppData
        'CODEX_HOME' = $codexBase
        'SKILL_HUB_ROOT' = $script:HubRoot
    }
    $resolved = $ConfiguredPath
    foreach ($key in $variables.Keys) {
        $resolved = $resolved.Replace(('${' + $key + '}'), $variables[$key])
    }
    return [Environment]::ExpandEnvironmentVariables($resolved)
}

function Get-Sha256Text {
    param([Parameter(Mandatory = $true)][string]$Text)

    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return ([System.BitConverter]::ToString($algorithm.ComputeHash($bytes)) -replace '-', '').ToLowerInvariant()
    }
    finally {
        $algorithm.Dispose()
    }
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Child
    )

    $rootPath = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $childPath = [System.IO.Path]::GetFullPath($Child)
    if (-not $childPath.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "路径不在扫描根目录内：$Child"
    }
    return $childPath.Substring($rootPath.Length).Replace('\', '/')
}

function Get-SkillId {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$RootId,
        [Parameter(Mandatory = $true)][string]$RelativePath
    )

    $digest = Get-Sha256Text -Text ($RootId + '/' + $RelativePath.ToLowerInvariant())
    return $Name + '_' + $digest.Substring(0, 12)
}

function Test-IsExcludedPath {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][object[]]$ExcludedNames
    )

    $parts = $RelativePath.Replace('\', '/').Split('/')
    foreach ($part in $parts) {
        if ($ExcludedNames -contains $part) {
            return $true
        }
    }
    return $false
}

function Get-DirectoryContentHash {
    param(
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)][object[]]$ExcludedNames
    )

    $entries = New-Object System.Collections.Generic.List[string]
    $files = Get-ChildItem -LiteralPath $Directory -Recurse -File -Force
    foreach ($file in $files) {
        $relative = Get-RelativePath -Root $Directory -Child $file.FullName
        if (Test-IsExcludedPath -RelativePath $relative -ExcludedNames $ExcludedNames) { continue }
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $entries.Add($relative.ToLowerInvariant() + '|' + $hash)
    }
    return Get-Sha256Text -Text (($entries | Sort-Object) -join "`n")
}

function Get-RegisteredLocalNames {
    $names = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
    if (-not (Test-Path -LiteralPath $script:RegistryPath)) { return ,$names }
    foreach ($line in Get-Content -LiteralPath $script:RegistryPath -Encoding utf8) {
        $columns = @($line.Split('|') | ForEach-Object { $_.Trim() })
        if ($columns.Count -lt 4 -or $columns[3] -ne '本地自建') { continue }
        $candidateName = $columns[1].Trim('`')
        if ($candidateName -match '^[a-z0-9][a-z0-9-]*$') { [void]$names.Add($candidateName) }
    }
    return ,$names
}

function Get-SourceKind {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Directory,
        [Parameter(Mandatory = $true)]$RegisteredNames
    )

    if ($RegisteredNames.Contains($Name)) { return 'local-authored' }
    if ($Directory -match '[\\/]plugins[\\/]') { return 'plugin-generated' }
    $provenance = Join-Path $Directory 'provenance.json'
    if (Test-Path -LiteralPath $provenance -PathType Leaf) {
        try {
            $evidence = Get-Content -LiteralPath $provenance -Raw -Encoding utf8 | ConvertFrom-Json
            if ($evidence.source_kind -eq 'external' -and -not [string]::IsNullOrWhiteSpace([string]$evidence.source_url)) {
                return 'external'
            }
            if ($evidence.source_kind -eq 'local-authored' -and -not [string]::IsNullOrWhiteSpace([string]$evidence.author)) {
                return 'local-authored'
            }
        }
        catch { }
    }
    return 'unknown'
}

function Scan-Root {
    param(
        [Parameter(Mandatory = $true)]$RootConfig,
        [Parameter(Mandatory = $true)][object[]]$ExcludedNames,
        [Parameter(Mandatory = $true)]$RegisteredNames,
        [switch]$IncludeContentHash
    )

    $resolvedPath = Resolve-ConfiguredPath -ConfiguredPath ([string]$RootConfig.path)
    $rootState = [ordered]@{
        root_id = [string]$RootConfig.root_id
        source_type = [string]$RootConfig.source_type
        configured_path = [string]$RootConfig.path
        resolved_path = $resolvedPath
        required = [bool]$RootConfig.required
        available = $false
        status = 'unavailable'
        error = $null
        available_in = @($RootConfig.available_in)
    }
    $items = New-Object System.Collections.Generic.List[object]
    $anomalies = New-Object System.Collections.Generic.List[object]

    if (-not (Test-Path -LiteralPath $resolvedPath -PathType Container)) {
        $rootState.error = '扫描根目录不存在。'
        return [pscustomobject]@{ root = [pscustomobject]$rootState; items = $items.ToArray(); anomalies = $anomalies.ToArray() }
    }

    try {
        $rootState.available = $true
        $rootState.status = 'current'
        $maxDepth = [int]$RootConfig.max_depth
        # PowerShell 不会递归进入 Junction/Symlink；一级 Skill 目录链接必须显式补入，
        # 否则已安装到用户目录的 Hub Skill 会被错误标记为 source-only。
        $skillFiles = @(Get-ChildItem -LiteralPath $resolvedPath -Recurse -File -Filter 'SKILL.md' -Force)
        if (Test-Path -LiteralPath (Join-Path $resolvedPath 'SKILL.md') -PathType Leaf) {
            $skillFiles += Get-Item -LiteralPath (Join-Path $resolvedPath 'SKILL.md')
        }
        foreach ($topDirectory in @(Get-ChildItem -LiteralPath $resolvedPath -Directory -Force)) {
            $linkedSkillFile = Join-Path $topDirectory.FullName 'SKILL.md'
            if (Test-Path -LiteralPath $linkedSkillFile -PathType Leaf) {
                $skillFiles += Get-Item -LiteralPath $linkedSkillFile
            }
        }
        $skillFiles = @($skillFiles | Sort-Object FullName -Unique)
        foreach ($skillFile in $skillFiles) {
            $directory = $skillFile.Directory.FullName
            $relativeDirectory = Get-RelativePath -Root $resolvedPath -Child $directory
            if (Test-IsExcludedPath -RelativePath $relativeDirectory -ExcludedNames $ExcludedNames) { continue }
            $depth = @($relativeDirectory.Split('/', [System.StringSplitOptions]::RemoveEmptyEntries)).Count
            if ($depth -gt $maxDepth) { continue }
            try {
                $metadata = Read-SkillMetadata -SkillFile $skillFile.FullName
                $metadataHash = (Get-FileHash -LiteralPath $skillFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                $contentHash = if ($IncludeContentHash) { Get-DirectoryContentHash -Directory $directory -ExcludedNames $ExcludedNames } else { $null }
                $isActive = ([string]$RootConfig.source_type -ne 'hub')
                $sourceKind = Get-SourceKind -Name $metadata.name -Directory $directory -RegisteredNames $RegisteredNames
                $items.Add([pscustomobject]@{
                    skill_id = Get-SkillId -Name $metadata.name -RootId ([string]$RootConfig.root_id) -RelativePath $relativeDirectory
                    name = $metadata.name
                    description = $metadata.description
                    root_id = [string]$RootConfig.root_id
                    source_type = [string]$RootConfig.source_type
                    directory = $directory
                    relative_path = $relativeDirectory
                    metadata_hash = $metadataHash
                    content_hash = $contentHash
                    availability = if ($isActive) { 'active' } else { 'source-only' }
                    available_in = @($RootConfig.available_in)
                    source_kind = $sourceKind
                })
            }
            catch {
                $anomalies.Add([pscustomobject]@{
                    root_id = [string]$RootConfig.root_id
                    path = $skillFile.FullName
                    severity = 'warning'
                    message = $_.Exception.Message
                })
            }
        }
    }
    catch {
        $rootState.status = 'error'
        $rootState.error = $_.Exception.Message
    }

    return [pscustomobject]@{ root = [pscustomobject]$rootState; items = $items.ToArray(); anomalies = $anomalies.ToArray() }
}

function Get-DefaultFrequency {
    param([Parameter(Mandatory = $true)][string]$Name)

    $high = @('lark-base', 'lark-wiki', 'lark-doc', 'lark-sheets', 'lark-im', 'task-scheduler', 'codebase-reader', 'officecli')
    $low = @('neat-freak', 'storage-analyzer', 'aihot', 'khazix-writer', 'hv-analysis', 'leader', 'kami', 'lark-workflow-meeting-summary', 'lark-workflow-standup-report')
    if ($high -contains $Name) { return 'high' }
    if ($low -contains $Name) { return 'low' }
    if ($Name -like 'lark-*') { return 'low' }
    return 'unclassified'
}

function Get-DefaultCategory {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (@('dws', 'agent-reach', 'awesome-design-md', 'remotion-best-practices') -contains $Name) {
        return 'observe'
    }
    return 'general'
}

function New-EmptyOverrides {
    return [pscustomobject]@{
        schema_version = $script:SchemaVersion
        updated_at = (Get-Date).ToUniversalTime().ToString('o')
        skills = [pscustomobject]@{}
    }
}

function Write-OverridesAtomic {
    param(
        [Parameter(Mandatory = $true)]$Overrides,
        [Parameter(Mandatory = $true)][string]$OverridesPath
    )

    if (Test-Path -LiteralPath $OverridesPath) {
        Copy-Item -LiteralPath $OverridesPath -Destination ($OverridesPath + '.bak') -Force
    }
    Write-JsonAtomic -Value $Overrides -Destination $OverridesPath
}

function Get-Overrides {
    param([Parameter(Mandatory = $true)][string]$OverridesPath)

    if (-not (Test-Path -LiteralPath $OverridesPath)) {
        $newOverrides = New-EmptyOverrides
        Write-OverridesAtomic -Overrides $newOverrides -OverridesPath $OverridesPath
        return $newOverrides
    }
    try {
        $overrides = Get-Content -LiteralPath $OverridesPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $overrides.skills) { throw '缺少 skills 节点。' }
        return $overrides
    }
    catch {
        throw "偏好文件无效：$($_.Exception.Message)"
    }
}

function Get-OverrideForSkill {
    param(
        [Parameter(Mandatory = $true)]$Overrides,
        [Parameter(Mandatory = $true)][string]$SkillId
    )

    $property = $Overrides.skills.PSObject.Properties[$SkillId]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Ensure-InitialFrequencyLabels {
    param(
        [Parameter(Mandatory = $true)]$Overrides,
        [Parameter(Mandatory = $true)][object[]]$Skills,
        [Parameter(Mandatory = $true)][string]$OverridesPath
    )

    $changed = $false
    foreach ($skill in $Skills) {
        if ($null -ne (Get-OverrideForSkill -Overrides $Overrides -SkillId $skill.skill_id)) { continue }
        $frequency = Get-DefaultFrequency -Name $skill.name
        $category = Get-DefaultCategory -Name $skill.name
        if ($frequency -eq 'unclassified' -and $category -eq 'general') { continue }
        $entry = [pscustomobject]@{ frequency = $frequency; category = $category; tags = @(); note = ''; pinned = $false }
        $Overrides.skills | Add-Member -NotePropertyName $skill.skill_id -NotePropertyValue $entry
        $changed = $true
    }
    if ($changed) {
        $Overrides.updated_at = (Get-Date).ToUniversalTime().ToString('o')
        Write-OverridesAtomic -Overrides $Overrides -OverridesPath $OverridesPath
    }
}

function Migrate-LegacyOverrideIds {
    param(
        [Parameter(Mandatory = $true)][object[]]$Items,
        [Parameter(Mandatory = $true)]$Overrides,
        [Parameter(Mandatory = $true)][string]$OverridesPath
    )

    # 早期试运行曾以 "目录/SKILL.md" 参与哈希；正式规则以 Skill 目录为相对路径。
    # 仅迁移可被精确反推的旧键，避免丢失人工偏好或误合并同名项。
    $changed = $false
    foreach ($item in $Items) {
        $legacyId = Get-SkillId -Name $item.name -RootId $item.root_id -RelativePath ($item.relative_path + '/SKILL.md')
        if ($legacyId -eq $item.skill_id) { continue }
        $legacy = $Overrides.skills.PSObject.Properties[$legacyId]
        if ($null -eq $legacy) { continue }
        $current = $Overrides.skills.PSObject.Properties[$item.skill_id]
        if ($null -ne $current) { $current.Value = $legacy.Value } else { $Overrides.skills | Add-Member -NotePropertyName $item.skill_id -NotePropertyValue $legacy.Value }
        [void]$Overrides.skills.PSObject.Properties.Remove($legacyId)
        $changed = $true
    }
    if ($changed) {
        $Overrides.updated_at = (Get-Date).ToUniversalTime().ToString('o')
        Write-OverridesAtomic -Overrides $Overrides -OverridesPath $OverridesPath
    }
}

function Get-GroupedSkills {
    param([Parameter(Mandatory = $true)][object[]]$Items)

    $result = New-Object System.Collections.Generic.List[object]
    foreach ($nameGroup in ($Items | Group-Object -Property name | Sort-Object Name)) {
        # 同名但内容不同是两个独立条目，不能共享 skill_id 或人工标签；只有内容完全相同的来源才合并。
        $contentGroups = @($nameGroup.Group | Group-Object -Property content_hash)
        foreach ($contentGroup in $contentGroups) {
            $ranked = @($contentGroup.Group | Sort-Object @{ Expression = {
                switch ($_.root_id) {
                    'agents-user' { 0; break }
                    'codex-user' { 1; break }
                    'hub-origin' { 2; break }
                    default { 3; break }
                }
            } }, root_id, relative_path)
            $primary = $ranked[0]
            $active = @($ranked | Where-Object { $_.availability -eq 'active' })
            $sourceOnly = @($ranked | Where-Object { $_.availability -eq 'source-only' })
            $availability = if ($active.Count -gt 0) { 'active' } elseif ($sourceOnly.Count -gt 0) { 'source-only' } else { 'unavailable' }
            $sameNameOtherContent = @($nameGroup.Group | Where-Object { $_.content_hash -ne $primary.content_hash })
            $hasHubVariant = @($nameGroup.Group | Where-Object { $_.root_id -eq 'hub-origin' }).Count -gt 0
            $integrity = if ($sameNameOtherContent.Count -eq 0) { 'ok' } elseif ($hasHubVariant -and $active.Count -gt 0) { 'drift' } else { 'conflict' }
            $sourceKinds = @($ranked | Select-Object -ExpandProperty source_kind -Unique)
            $sourceKind = if ($sourceKinds -contains 'local-authored') { 'local-authored' } elseif ($sourceKinds -contains 'plugin-generated') { 'plugin-generated' } elseif ($sourceKinds -contains 'external') { 'external' } else { 'unknown' }
            $managed = @($ranked | Where-Object { $_.root_id -eq 'hub-origin' }).Count -gt 0
            $adoptability = if ($sourceKind -eq 'plugin-generated') { 'blocked' } elseif ($sourceKind -eq 'local-authored' -and -not $managed) { 'eligible' } elseif ($managed) { 'not-applicable' } else { 'review-required' }
            $sources = @($ranked | ForEach-Object {
                [pscustomobject]@{
                    skill_id = $_.skill_id
                    root_id = $_.root_id
                    source_type = $_.source_type
                    path = $_.directory
                    relative_path = $_.relative_path
                    availability = $_.availability
                    available_in = $_.available_in
                    metadata_hash = $_.metadata_hash
                    content_hash = $_.content_hash
                    source_kind = $_.source_kind
                }
            })
            $aliases = @($ranked | Where-Object { $_.skill_id -ne $primary.skill_id } | Select-Object -ExpandProperty skill_id)
            $result.Add([pscustomobject]@{
                skill_id = $primary.skill_id
                logical_name = $primary.name
                name = $primary.name
                description = $primary.description
                managed = $managed
                availability = $availability
                integrity = $integrity
                source_kind = $sourceKind
                adoptability = $adoptability
                aliases = $aliases
                sources = $sources
            })
        }
    }
    return $result.ToArray()
}

function Add-StaleItemsFromCatalog {
    param(
        [Parameter(Mandatory = $true)]$PreviousCatalog,
        [Parameter(Mandatory = $true)][string]$RootId,
        [Parameter(Mandatory = $true)]$Destination
    )

    if ($null -eq $PreviousCatalog -or $null -eq $PreviousCatalog.skills) { return }
    foreach ($previousSkill in @($PreviousCatalog.skills)) {
        foreach ($previousSource in @($previousSkill.sources | Where-Object { $_.root_id -eq $RootId })) {
            $Destination.Add([pscustomobject]@{
                skill_id = $previousSource.skill_id
                name = if ($previousSkill.logical_name) { $previousSkill.logical_name } else { $previousSkill.name }
                description = $previousSkill.description
                root_id = $previousSource.root_id
                source_type = $previousSource.source_type
                directory = $previousSource.path
                relative_path = $previousSource.relative_path
                metadata_hash = $previousSource.metadata_hash
                content_hash = $previousSource.content_hash
                availability = 'unavailable'
                available_in = @($previousSource.available_in)
                source_kind = if ($previousSource.source_kind) { $previousSource.source_kind } else { $previousSkill.source_kind }
            })
        }
    }
}

function Get-Manifest {
    param(
        [Parameter(Mandatory = $true)][object[]]$Items,
        [Parameter(Mandatory = $true)][object[]]$ExcludedNames,
        [Parameter(Mandatory = $true)]$Config
    )

    $entries = New-Object System.Collections.Generic.List[string]
    $configJson = $Config | ConvertTo-Json -Depth 32 -Compress
    $entries.Add(('config|' + (Get-Sha256Text -Text $configJson)))
    foreach ($item in @($Items | Where-Object { $_.availability -ne 'unavailable' })) {
        $files = Get-ChildItem -LiteralPath $item.directory -Recurse -File -Force
        foreach ($file in $files) {
            $relative = Get-RelativePath -Root $item.directory -Child $file.FullName
            if (Test-IsExcludedPath -RelativePath $relative -ExcludedNames $ExcludedNames) { continue }
            $entries.Add(($item.root_id + '|' + $item.relative_path.ToLowerInvariant() + '|' + $relative.ToLowerInvariant() + '|' + $file.Length + '|' + $file.LastWriteTimeUtc.Ticks))
        }
    }
    foreach ($root in @($Config.roots | Where-Object { $_.enabled })) {
        $path = Resolve-ConfiguredPath -ConfiguredPath ([string]$root.path)
        $entries.Add(('root|' + $root.root_id + '|' + $path.ToLowerInvariant() + '|' + (Test-Path -LiteralPath $path)))
    }
    return @($entries | Sort-Object)
}

function New-IndexMarkdown {
    param(
        [Parameter(Mandatory = $true)][object[]]$Skills,
        [Parameter(Mandatory = $true)]$Overrides,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Anomalies,
        [Parameter(Mandatory = $true)]$Health,
        [Parameter(Mandatory = $true)]$Config
    )

    $maxLength = [int]$Config.index.max_description_length
    $rows = foreach ($skill in $Skills) {
        $preference = Get-OverrideForSkill -Overrides $Overrides -SkillId $skill.skill_id
        $frequencyProperty = if ($null -ne $preference) { $preference.PSObject.Properties['frequency'] } else { $null }
        $categoryProperty = if ($null -ne $preference) { $preference.PSObject.Properties['category'] } else { $null }
        $frequency = if ($null -ne $frequencyProperty -and $frequencyProperty.Value) { [string]$frequencyProperty.Value } else { 'unclassified' }
        $category = if ($null -ne $categoryProperty -and $categoryProperty.Value) { [string]$categoryProperty.Value } else { 'general' }
        [pscustomobject]@{ skill = $skill; frequency = $frequency; category = $category }
    }
    $builder = New-Object System.Text.StringBuilder
    [void]$builder.AppendLine('# Skill 目录')
    [void]$builder.AppendLine()
    [void]$builder.AppendLine("- 最近成功构建：$($Health.last_success_at)")
    [void]$builder.AppendLine("- Skill 数量：$($Skills.Count)；异常数量：$($Anomalies.Count)")
    [void]$builder.AppendLine('- 频率仅为个人偏好；可用性和完整性来自扫描。')
    foreach ($frequency in @('high', 'unclassified', 'low')) {
        $title = switch ($frequency) { 'high' { '高频' } 'low' { '低频' } default { '未分类' } }
        [void]$builder.AppendLine()
        [void]$builder.AppendLine("## $title")
        [void]$builder.AppendLine()
        [void]$builder.AppendLine('| Skill | 描述 | 可用性 | 完整性 | 来源 |')
        [void]$builder.AppendLine('|---|---|---|---|---|')
        foreach ($row in @($rows | Where-Object { $_.frequency -eq $frequency -and $_.category -ne 'observe' } | Sort-Object { $_.skill.name })) {
            $description = $row.skill.description.Replace('|', '\|').Replace("`n", ' ')
            if ($description.Length -gt $maxLength) { $description = $description.Substring(0, $maxLength) + '…' }
            $source = (@($row.skill.sources | Select-Object -ExpandProperty root_id -Unique) -join ', ')
            [void]$builder.AppendLine("| ``$($row.skill.name)`` | $description | $($row.skill.availability) | $($row.skill.integrity) | $source |")
        }
    }
    $observed = @($rows | Where-Object { $_.category -eq 'observe' } | Sort-Object { $_.skill.name })
    if ($observed.Count -gt 0) {
        [void]$builder.AppendLine()
        [void]$builder.AppendLine('## 观察')
        [void]$builder.AppendLine()
        [void]$builder.AppendLine('| Skill | 描述 | 可用性 | 完整性 | 来源 |')
        [void]$builder.AppendLine('|---|---|---|---|---|')
        foreach ($row in $observed) {
            $description = $row.skill.description.Replace('|', '\|').Replace("`n", ' ')
            if ($description.Length -gt $maxLength) { $description = $description.Substring(0, $maxLength) + '…' }
            $source = (@($row.skill.sources | Select-Object -ExpandProperty root_id -Unique) -join ', ')
            [void]$builder.AppendLine("| ``$($row.skill.name)`` | $description | $($row.skill.availability) | $($row.skill.integrity) | $source |")
        }
    }
    $unmanagedGroups = @(
        [pscustomobject]@{ key = 'eligible'; title = '可直接收编' },
        [pscustomobject]@{ key = 'review-required'; title = '需评估来源' },
        [pscustomobject]@{ key = 'blocked'; title = '保持外部管理' }
    )
    $hasUnmanaged = @($rows | Where-Object { -not $_.skill.managed }).Count -gt 0
    if ($hasUnmanaged) {
        [void]$builder.AppendLine()
        [void]$builder.AppendLine('## 未纳管')
        foreach ($group in $unmanagedGroups) {
            $groupRows = @($rows | Where-Object { -not $_.skill.managed -and $_.skill.adoptability -eq $group.key } | Sort-Object { $_.skill.name })
            if ($groupRows.Count -eq 0) { continue }
            [void]$builder.AppendLine()
            [void]$builder.AppendLine("### $($group.title)")
            [void]$builder.AppendLine()
            [void]$builder.AppendLine('| Skill | 来源证据 | 可用性 | 完整性 |')
            [void]$builder.AppendLine('|---|---|---|---|')
            foreach ($row in $groupRows) {
                [void]$builder.AppendLine("| ``$($row.skill.name)`` | $($row.skill.source_kind) | $($row.skill.availability) | $($row.skill.integrity) |")
            }
        }
    }
    if ($Anomalies.Count -gt 0) {
        [void]$builder.AppendLine()
        [void]$builder.AppendLine('## 待处理异常')
        [void]$builder.AppendLine()
        foreach ($anomaly in $Anomalies) {
            [void]$builder.AppendLine("- [$($anomaly.root_id)] $($anomaly.path)：$($anomaly.message)")
        }
    }
    return $builder.ToString()
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
        catalog = Join-Path $RequestedRoot 'catalog.json'
        health = Join-Path $RequestedRoot 'health.json'
        index = Join-Path $RequestedRoot 'INDEX.md'
        overrides = Join-Path $RequestedRoot 'overrides.json'
    }
    if (-not (Test-Path -LiteralPath $paths.config)) { Copy-Item -LiteralPath $script:ExampleConfig -Destination $paths.config }
    return $paths
}

function Read-Config {
    param([Parameter(Mandatory = $true)][string]$ConfigPath)
    try {
        $config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $config.roots -or $null -eq $config.index) { throw '缺少 roots 或 index 节点。' }
        $seenRootIds = New-Object System.Collections.Generic.HashSet[string]([System.StringComparer]::OrdinalIgnoreCase)
        foreach ($root in @($config.roots)) {
            if ([string]::IsNullOrWhiteSpace([string]$root.root_id) -or [string]$root.root_id -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') {
                throw 'root_id 必须为小写连字符格式。'
            }
            if (-not $seenRootIds.Add([string]$root.root_id)) { throw "root_id 重复：$($root.root_id)" }
            if ([string]::IsNullOrWhiteSpace([string]$root.path)) { throw "扫描根缺少 path：$($root.root_id)" }
            if (@('direct-children', 'nested', 'recursive') -notcontains [string]$root.layout) { throw "扫描根 layout 无效：$($root.root_id)" }
            if ([int]$root.max_depth -lt 0) { throw "扫描根 max_depth 无效：$($root.root_id)" }
        }
        if ($null -eq $config.PSObject.Properties['allowed_categories']) { $config | Add-Member -NotePropertyName allowed_categories -NotePropertyValue @('general', 'observe') }
        if ($null -eq $config.PSObject.Properties['panel']) { $config | Add-Member -NotePropertyName panel -NotePropertyValue ([pscustomobject]@{ host = '127.0.0.1'; port = 8765 }) }
        return $config
    }
    catch { throw "目录配置无效：$($_.Exception.Message)" }
}

function Get-CanonicalRoot {
    param([Parameter(Mandatory = $true)]$Config)

    if ($null -ne $Config.canonical -and -not [string]::IsNullOrWhiteSpace([string]$Config.canonical.path)) {
        return Resolve-ConfiguredPath -ConfiguredPath ([string]$Config.canonical.path)
    }
    $legacy = @($Config.roots | Where-Object { $_.root_id -eq 'agents-user' } | Select-Object -First 1)
    if ($legacy.Count -ne 1) { throw '未配置中央 Skill 目录。' }
    return Resolve-ConfiguredPath -ConfiguredPath ([string]$legacy[0].path)
}

function Write-HealthFailure {
    param(
        [Parameter(Mandatory = $true)][string]$HealthPath,
        [Parameter(Mandatory = $true)][string]$Message
    )
    $previous = $null
    if (Test-Path -LiteralPath $HealthPath) {
        try { $previous = Get-Content -LiteralPath $HealthPath -Raw -Encoding utf8 | ConvertFrom-Json } catch { }
    }
    $health = [pscustomobject]@{
        schema_version = $script:SchemaVersion
        status = 'error'
        checked_at = (Get-Date).ToUniversalTime().ToString('o')
        last_success_at = if ($null -ne $previous) { $previous.last_success_at } else { $null }
        message = $Message
    }
    Write-JsonAtomic -Value $health -Destination $HealthPath
}

function Invoke-Rebuild {
    param([Parameter(Mandatory = $true)]$Paths)

    $config = Read-Config -ConfigPath $Paths.config
    $previousCatalog = $null
    if (Test-Path -LiteralPath $Paths.catalog) {
        try { $previousCatalog = Get-Content -LiteralPath $Paths.catalog -Raw -Encoding utf8 | ConvertFrom-Json } catch { }
    }
    $excluded = @($config.exclude_directory_names)
    $registeredNames = Get-RegisteredLocalNames
    $allItems = New-Object System.Collections.Generic.List[object]
    $allAnomalies = New-Object System.Collections.Generic.List[object]
    $rootStates = New-Object System.Collections.Generic.List[object]
    foreach ($root in @($config.roots | Where-Object { $_.enabled })) {
        $scan = Scan-Root -RootConfig $root -ExcludedNames $excluded -RegisteredNames $registeredNames -IncludeContentHash
        $rootStates.Add($scan.root)
        foreach ($item in $scan.items) { $allItems.Add($item) }
        foreach ($anomaly in $scan.anomalies) { $allAnomalies.Add($anomaly) }
        if ($root.required -and -not $scan.root.available) {
            throw "必需扫描根不可用 [$($root.root_id)]：$($scan.root.error)"
        }
        if (-not $root.required -and -not $scan.root.available) {
            $scan.root.status = 'stale'
            Add-StaleItemsFromCatalog -PreviousCatalog $previousCatalog -RootId ([string]$root.root_id) -Destination $allItems
            $allAnomalies.Add([pscustomobject]@{
                root_id = [string]$root.root_id
                path = $scan.root.resolved_path
                severity = 'warning'
                message = '可选扫描根不可用，已保留上次成功索引中的数据。'
            })
        }
    }
    $skills = Get-GroupedSkills -Items $allItems.ToArray()
    $overrides = Get-Overrides -OverridesPath $Paths.overrides
    Migrate-LegacyOverrideIds -Items $allItems.ToArray() -Overrides $overrides -OverridesPath $Paths.overrides
    Ensure-InitialFrequencyLabels -Overrides $overrides -Skills $skills -OverridesPath $Paths.overrides
    $manifest = Get-Manifest -Items $allItems.ToArray() -ExcludedNames $excluded -Config $config
    $now = (Get-Date).ToUniversalTime().ToString('o')
    $health = [pscustomobject]@{
        schema_version = $script:SchemaVersion
        status = if (@($rootStates | Where-Object { $_.status -eq 'stale' }).Count -gt 0) { 'partial' } else { 'healthy' }
        checked_at = $now
        last_success_at = $now
        message = $null
        roots = $rootStates.ToArray()
        anomalies = $allAnomalies.Count
    }
    $catalog = [pscustomobject]@{
        schema_version = $script:SchemaVersion
        generated_at = $now
        manifest = $manifest
        roots = $rootStates.ToArray()
        skills = $skills
        anomalies = $allAnomalies.ToArray()
    }
    Write-JsonAtomic -Value $catalog -Destination $Paths.catalog
    Write-JsonAtomic -Value $health -Destination $Paths.health
    Write-TextAtomic -Text (New-IndexMarkdown -Skills $skills -Overrides $overrides -Anomalies $allAnomalies.ToArray() -Health $health -Config $config) -Destination $Paths.index
    [pscustomobject]@{ status = 'rebuilt'; skills = $skills.Count; anomalies = $allAnomalies.Count; state_root = $Paths.state } | ConvertTo-Json -Compress
}

function Invoke-Check {
    param([Parameter(Mandatory = $true)]$Paths)

    if (-not (Test-Path -LiteralPath $Paths.catalog) -or -not (Test-Path -LiteralPath $Paths.health)) {
        Write-Output '{"status":"stale","reason":"目录尚未建立"}'
        exit 2
    }
    try {
        $config = Read-Config -ConfigPath $Paths.config
        $catalog = Get-Content -LiteralPath $Paths.catalog -Raw -Encoding utf8 | ConvertFrom-Json
        $registeredNames = Get-RegisteredLocalNames
        $items = New-Object System.Collections.Generic.List[object]
        foreach ($root in @($config.roots | Where-Object { $_.enabled })) {
            $scan = Scan-Root -RootConfig $root -ExcludedNames @($config.exclude_directory_names) -RegisteredNames $registeredNames
            if (-not $scan.root.available) { throw "扫描根不可用 [$($root.root_id)]：$($scan.root.error)" }
            foreach ($item in $scan.items) { $items.Add($item) }
        }
        $current = Get-Manifest -Items $items.ToArray() -ExcludedNames @($config.exclude_directory_names) -Config $config
        $stored = @($catalog.manifest)
        $difference = Compare-Object -ReferenceObject $stored -DifferenceObject $current
        if ($null -ne $difference) {
            Write-Output '{"status":"stale","reason":"检测到 Skill 或配置变化"}'
            exit 2
        }
        Write-Output '{"status":"current"}'
        exit 0
    }
    catch {
        Write-HealthFailure -HealthPath $Paths.health -Message $_.Exception.Message
        Write-Output (([pscustomobject]@{ status = 'error'; message = $_.Exception.Message }) | ConvertTo-Json -Compress)
        exit 1
    }
}

function Test-PreferenceEntry {
    param($Entry)
    if ($null -eq $Entry -or [string]::IsNullOrWhiteSpace([string]$Entry.frequency)) { return $false }
    return @('high', 'low', 'unclassified') -contains [string]$Entry.frequency
}

function Export-Preferences {
    param([Parameter(Mandatory = $true)]$Paths, [Parameter(Mandatory = $true)][string]$Destination)
    $overrides = Get-Overrides -OverridesPath $Paths.overrides
    Write-JsonAtomic -Value $overrides -Destination ([System.IO.Path]::GetFullPath($Destination))
    Write-Output (([pscustomobject]@{ status = 'exported'; path = [System.IO.Path]::GetFullPath($Destination) }) | ConvertTo-Json -Compress)
}

function Import-Preferences {
    param([Parameter(Mandatory = $true)]$Paths, [Parameter(Mandatory = $true)][string]$Source)
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "偏好导入文件不存在：$Source" }
    $incoming = Get-Content -LiteralPath $Source -Raw -Encoding utf8 | ConvertFrom-Json
    if ($null -eq $incoming.skills) { throw '偏好导入文件缺少 skills 节点。' }
    $current = Get-Overrides -OverridesPath $Paths.overrides
    $invalid = New-Object System.Collections.Generic.List[string]
    foreach ($property in $incoming.skills.PSObject.Properties) {
        if (-not (Test-PreferenceEntry -Entry $property.Value)) { $invalid.Add($property.Name); continue }
        $existing = $current.skills.PSObject.Properties[$property.Name]
        if ($null -ne $existing) { $existing.Value = $property.Value } else { $current.skills | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value }
    }
    if ($invalid.Count -gt 0) { throw ('偏好导入文件包含无效条目：' + ($invalid -join ', ')) }
    $current.updated_at = (Get-Date).ToUniversalTime().ToString('o')
    Write-OverridesAtomic -Overrides $current -OverridesPath $Paths.overrides
    Write-Output (([pscustomobject]@{ status = 'imported'; entries = @($incoming.skills.PSObject.Properties).Count }) | ConvertTo-Json -Compress)
}

function Get-AdoptionManifest {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDirectory,
        [Parameter(Mandatory = $true)][object[]]$ExcludedNames
    )

    $blocked = New-Object System.Collections.Generic.List[string]
    $risks = New-Object System.Collections.Generic.List[object]
    $entries = New-Object System.Collections.Generic.List[object]
    $allItems = @(Get-ChildItem -LiteralPath $SourceDirectory -Force -Recurse)
    foreach ($item in $allItems) {
        $relative = Get-RelativePath -Root $SourceDirectory -Child $item.FullName
        if (Test-IsExcludedPath -RelativePath $relative -ExcludedNames $ExcludedNames) { continue }
        if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            $blocked.Add("检测到指向 Skill 目录外风险的链接：$relative")
            continue
        }
        if ($item.PSIsContainer) { continue }
        $leaf = $item.Name.ToLowerInvariant()
        if ($leaf -match '^(\.env|.*\.pem|.*\.key|id_rsa|.*token.*|.*secret.*|.*cookie.*|.*credential.*)$') {
            $blocked.Add("检测到敏感文件：$relative")
            continue
        }
        if ($item.Length -gt 5MB) {
            $risks.Add([pscustomobject]@{ type = 'large-file'; path = $relative; bytes = $item.Length; message = '大文件将在提交确认时一并复制。' })
        }
        $entries.Add([pscustomobject]@{
            path = $relative.Replace('\', '/')
            bytes = $item.Length
            sha256 = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
    if ($blocked.Count -gt 0) { throw ('收编预检被阻断：' + ($blocked -join '；')) }
    if ($entries.Count -eq 0) { throw '收编预检失败：没有可复制文件。' }
    $fingerprint = @($entries | Sort-Object path | ForEach-Object { $_.path.ToLowerInvariant() + '|' + $_.sha256 }) -join "`n"
    return [pscustomobject]@{
        copy_manifest = $entries.ToArray()
        expected_content_hash = Get-Sha256Text -Text $fingerprint
        risk_findings = $risks.ToArray()
    }
}

function Get-AdoptionCandidate {
    param([Parameter(Mandatory = $true)]$Paths)

    if (-not (Test-Path -LiteralPath $Paths.catalog)) { throw '尚未建立 Skill 目录，请先执行 Rebuild。' }
    $catalog = Get-Content -LiteralPath $Paths.catalog -Raw -Encoding utf8 | ConvertFrom-Json
    $match = @($catalog.skills | Where-Object { $_.skill_id -eq $AdoptPlan })
    if ($match.Count -ne 1) { throw '未找到待收编 Skill。' }
    $skill = $match[0]
    if ($skill.adoptability -ne 'eligible') { throw "该 Skill 当前不可直接收编：$($skill.adoptability)。" }
    $source = @($skill.sources | Where-Object { $_.availability -eq 'active' } | Select-Object -First 1)
    if ($source.Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$source[0].path)) { throw '没有可收编的本机安装来源。' }
    if ($source[0].source_type -eq 'project') { throw '项目级 Skill 一期仅报告，不执行收编。' }
    if (-not (Test-Path -LiteralPath $source[0].path -PathType Container)) { throw '本机安装来源已变化，请先 Rebuild。' }
    return [pscustomobject]@{ skill = $skill; source = $source[0] }
}

function Invoke-AdoptPlan {
    param([Parameter(Mandatory = $true)]$Paths)

    if ($AdoptPlan -notmatch '^[a-z0-9][a-z0-9-]*_[0-9a-f]{12}$') { throw 'Skill 标识无效。' }
    $config = Read-Config -ConfigPath $Paths.config
    $candidate = Get-AdoptionCandidate -Paths $Paths
    $name = [string]$candidate.skill.name
    $canonicalRoot = Get-CanonicalRoot -Config $config
    if (-not (Test-Path -LiteralPath $canonicalRoot -PathType Container)) { throw "中央 Skill 目录不可用：$canonicalRoot" }
    $target = Join-Path $canonicalRoot $name
    if (Test-Path -LiteralPath $target) { throw '中央目录已存在同名 Skill，不能自动覆盖。' }
    $manifest = Get-AdoptionManifest -SourceDirectory ([string]$candidate.source.path) -ExcludedNames @($config.exclude_directory_names)
    $planId = [guid]::NewGuid().ToString('N')
    $planFolder = Join-Path $Paths.state 'transactions\plans'
    $planPath = Join-Path $planFolder ($planId + '.json')
    $now = (Get-Date).ToUniversalTime()
    $plan = [pscustomobject]@{
        schema_version = $script:SchemaVersion
        plan_id = $planId
        status = 'pending'
        created_at = $now.ToString('o')
        expires_at = $now.AddHours(24).ToString('o')
        skill_id = $candidate.skill.skill_id
        logical_name = $name
        source_root_id = $candidate.source.root_id
        source_path = $candidate.source.path
        expected_content_hash = $manifest.expected_content_hash
        copy_manifest = $manifest.copy_manifest
        risk_findings = $manifest.risk_findings
        planned_paths = @{
            canonical_target = $target
            backup_target = Join-Path (Join-Path $Paths.state 'adopt-backups') $planId
        }
        registry_change_preview = "新增 $name 的收编资产台账记录"
    }
    Write-JsonAtomic -Value $plan -Destination $planPath
    Write-Output ($plan | ConvertTo-Json -Depth 16)
}

function Get-PlanPath {
    param(
        [Parameter(Mandatory = $true)]$Paths,
        [Parameter(Mandatory = $true)][string]$PlanId
    )
    if ($PlanId -notmatch '^[0-9a-f]{32}$') { throw '收编计划标识无效。' }
    return Join-Path (Join-Path $Paths.state 'transactions\plans') ($PlanId + '.json')
}

function Update-AdoptionJournal {
    param([Parameter(Mandatory = $true)]$Journal, [Parameter(Mandatory = $true)][string]$JournalPath)
    $Journal.updated_at = (Get-Date).ToUniversalTime().ToString('o')
    Write-JsonAtomic -Value $Journal -Destination $JournalPath
}

function Invoke-AdoptCommit {
    param([Parameter(Mandatory = $true)]$Paths)

    if (-not $Confirmed) { throw '收编提交需要显式 -Confirmed 确认。' }
    $planPath = Get-PlanPath -Paths $Paths -PlanId $AdoptCommit
    if (-not (Test-Path -LiteralPath $planPath)) { throw '收编计划不存在。' }
    $plan = Get-Content -LiteralPath $planPath -Raw -Encoding utf8 | ConvertFrom-Json
    if ($plan.status -ne 'pending') { throw "收编计划已终结：$($plan.status)。" }
    if ((Get-Date).ToUniversalTime() -gt [DateTime]::Parse($plan.expires_at).ToUniversalTime()) {
        $plan.status = 'expired'; Write-JsonAtomic -Value $plan -Destination $planPath; throw '收编计划已过期，请重新预检。'
    }
    $config = Read-Config -ConfigPath $Paths.config
    if (-not (Test-Path -LiteralPath $plan.source_path -PathType Container)) { throw '来源目录已变化，请重新预检。' }
    $currentManifest = Get-AdoptionManifest -SourceDirectory $plan.source_path -ExcludedNames @($config.exclude_directory_names)
    if ($currentManifest.expected_content_hash -ne $plan.expected_content_hash) { throw '来源内容已变化，请重新预检。' }
    $target = [string]$plan.planned_paths.canonical_target
    $backupBase = [string]$plan.planned_paths.backup_target
    if (Test-Path -LiteralPath $target) { throw '中央目录目标已存在，不能覆盖。' }
    $transactionId = [guid]::NewGuid().ToString('N')
    $canonicalRoot = Get-CanonicalRoot -Config $config
    $tmpRoot = Join-Path $canonicalRoot '.adopt_tmp'
    $tmpTarget = Join-Path $tmpRoot $transactionId
    $journalPath = Join-Path (Join-Path $Paths.state 'transactions\journals') ($transactionId + '.json')
    $registryBackup = Join-Path $backupBase 'skills-registry.md'
    $sourceBackup = Join-Path $backupBase ([string]$plan.logical_name)
    $journal = [pscustomobject]@{
        schema_version = $script:SchemaVersion
        transaction_id = $transactionId
        plan_id = $plan.plan_id
        status = 'running'
        source_path = $plan.source_path
        canonical_target = $target
        source_backup = $sourceBackup
        steps = @()
    }
    Update-AdoptionJournal -Journal $journal -JournalPath $journalPath
    $targetCreated = $false; $sourceMoved = $false; $junctionCreated = $false; $registryChanged = $false
    try {
        [System.IO.Directory]::CreateDirectory($tmpRoot) | Out-Null
        foreach ($entry in @($plan.copy_manifest)) {
            $sourceFile = Join-Path $plan.source_path $entry.path
            $targetFile = Join-Path $tmpTarget $entry.path
            [System.IO.Directory]::CreateDirectory((Split-Path -Parent $targetFile)) | Out-Null
            Copy-Item -LiteralPath $sourceFile -Destination $targetFile
        }
        $copied = Get-AdoptionManifest -SourceDirectory $tmpTarget -ExcludedNames @($config.exclude_directory_names)
        if ($copied.expected_content_hash -ne $plan.expected_content_hash) { throw '复制后的内容校验失败。' }
        [System.IO.Directory]::CreateDirectory($backupBase) | Out-Null
        Copy-Item -LiteralPath $script:RegistryPath -Destination $registryBackup -Force
        Move-Item -LiteralPath $tmpTarget -Destination $target
        $targetCreated = $true
        Move-Item -LiteralPath $plan.source_path -Destination $sourceBackup
        $sourceMoved = $true
        New-Item -ItemType Junction -Path $plan.source_path -Target $target | Out-Null
        $junctionCreated = $true
        if (-not (Test-Path -LiteralPath (Join-Path $plan.source_path 'SKILL.md') -PathType Leaf)) { throw '新入口校验失败。' }
        $registryText = Get-Content -LiteralPath $script:RegistryPath -Raw -Encoding utf8
        $registryText = $registryText.TrimEnd() + [Environment]::NewLine + "| $($plan.logical_name) | 收编 Skill | 本地自建 | ``~/.agents/skills/$($plan.logical_name)`` | Kimi/Codex | 已纳管 | 收编至中央目录；计划 $($plan.plan_id) |" + [Environment]::NewLine
        Write-TextAtomic -Text $registryText -Destination $script:RegistryPath
        $registryChanged = $true
        $plan.status = 'committed'; $plan.transaction_id = $transactionId; $plan.committed_at = (Get-Date).ToUniversalTime().ToString('o')
        Write-JsonAtomic -Value $plan -Destination $planPath
        $journal.status = 'committed'; $journal.steps = @('copied', 'verified', 'moved-to-canonical', 'backed-up-source', 'created-junction', 'updated-registry')
        Update-AdoptionJournal -Journal $journal -JournalPath $journalPath
        Invoke-Rebuild -Paths $Paths | Out-Null
        Write-Output (([pscustomobject]@{ status = 'committed'; plan_id = $plan.plan_id; transaction_id = $transactionId; logical_name = $plan.logical_name }) | ConvertTo-Json -Compress)
    }
    catch {
        $failure = $_.Exception.Message
        if ($junctionCreated -and (Test-Path -LiteralPath $plan.source_path)) { Remove-Item -LiteralPath $plan.source_path -Force -ErrorAction SilentlyContinue }
        if ($sourceMoved -and (Test-Path -LiteralPath $sourceBackup) -and -not (Test-Path -LiteralPath $plan.source_path)) { Move-Item -LiteralPath $sourceBackup -Destination $plan.source_path -ErrorAction SilentlyContinue }
        if ($registryChanged -and (Test-Path -LiteralPath $registryBackup)) { Copy-Item -LiteralPath $registryBackup -Destination $script:RegistryPath -Force }
        if ($targetCreated -and (Test-Path -LiteralPath $target)) { Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $tmpTarget) { Remove-Item -LiteralPath $tmpTarget -Recurse -Force -ErrorAction SilentlyContinue }
        $journal.status = 'failed'; $journal.failure = $failure; Update-AdoptionJournal -Journal $journal -JournalPath $journalPath
        throw "收编失败，已执行事务回滚：$failure"
    }
}

$paths = Initialize-State -RequestedRoot $StateRoot
$mutex = $null
$lockTaken = $false
try {
    if ($PSCmdlet.ParameterSetName -in @('Rebuild', 'Import', 'AdoptPlan', 'AdoptCommit')) {
        $mutex = New-Object System.Threading.Mutex($false, 'Local\SkillCatalogStateLock')
        $lockTaken = $mutex.WaitOne([TimeSpan]::FromSeconds(30))
        if (-not $lockTaken) { throw '目录正在由其他操作更新，请稍后重试。' }
    }
    switch ($PSCmdlet.ParameterSetName) {
        'Rebuild' { Invoke-Rebuild -Paths $paths; exit 0 }
        'Export' { Export-Preferences -Paths $paths -Destination $Path; exit 0 }
        'Import' { Import-Preferences -Paths $paths -Source $Path; exit 0 }
        'AdoptPlan' { Invoke-AdoptPlan -Paths $paths; exit 0 }
        'AdoptCommit' { Invoke-AdoptCommit -Paths $paths; exit 0 }
        default { Invoke-Check -Paths $paths }
    }
}
catch {
    Write-HealthFailure -HealthPath $paths.health -Message $_.Exception.Message
    Write-Output (([pscustomobject]@{ status = 'error'; message = $_.Exception.Message }) | ConvertTo-Json -Compress)
    exit 1
}
finally {
    if ($lockTaken -and $null -ne $mutex) { $mutex.ReleaseMutex() }
    if ($null -ne $mutex) { $mutex.Dispose() }
}

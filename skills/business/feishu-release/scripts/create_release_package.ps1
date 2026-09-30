[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{8}$')]
    [string]$ReleaseDate,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^(?:[01]\d|2[0-3]):[0-5]\d$')]
    [string]$ReleaseTime,

    [ValidateSet('blueGreen', 'majorDowntime')]
    [string]$Mode = 'blueGreen',

    [switch]$IncludePdf,
    [switch]$Notify,
    [switch]$AtAll,
    [string]$NotificationText = '',
    [string[]]$MentionOpenIds = @(),
    [string]$ChatId = '',
    [string]$ItemsJson = '',
    [string]$ConfigPath = 'D:\财宝\AgentWorkspace\_workspace\发版通知\release_notifier_config.json',
    [switch]$LocalOnly,
    [switch]$DryRun,
    [switch]$OverwriteLocal
)

$ErrorActionPreference = 'Stop'

function ConvertFrom-LarkOutput {
    param([string]$RawText, [int]$ExitCode, [string]$Operation)

    $start = $RawText.IndexOf('{')
    $end = $RawText.LastIndexOf('}')
    if ($start -lt 0 -or $end -le $start) {
        throw "$Operation returned no JSON: $RawText"
    }

    $payload = $RawText.Substring($start, $end - $start + 1) | ConvertFrom-Json
    if ($ExitCode -ne 0 -or ($payload.PSObject.Properties.Name -contains 'ok' -and -not $payload.ok)) {
        throw "$Operation failed: $RawText"
    }
    return $payload
}

function Invoke-Lark {
    param([string[]]$Arguments, [string]$Operation)

    $lark = Get-Command 'lark-cli' -ErrorAction SilentlyContinue
    if (-not $lark) {
        $lark = Get-Command 'lark-cli.cmd' -ErrorAction SilentlyContinue
    }
    if (-not $lark) {
        throw 'lark-cli is not installed or not available on PATH.'
    }

    $raw = (& $lark.Source @Arguments 2>&1 | Out-String)
    return ConvertFrom-LarkOutput -RawText $raw -ExitCode $LASTEXITCODE -Operation $Operation
}

function Get-Worksheet {
    param($Workbook, [string]$Name)
    foreach ($sheet in $Workbook.Worksheets) {
        if ($sheet.Name -eq $Name) {
            return $sheet
        }
    }
    return $null
}

function Get-ItemValue {
    param($Item, [string]$Name)
    $property = $Item.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) {
        return ''
    }
    return [string]$property.Value
}

function Write-ReleaseItems {
    param($Workbook, [object[]]$Items)

    if (-not $Items -or $Items.Count -eq 0) {
        return
    }

    $targetSheet = $null
    $headerRow = 0
    $columnMap = @{}
    foreach ($sheet in $Workbook.Worksheets) {
        for ($row = 1; $row -le 20; $row++) {
            $candidateMap = @{}
            for ($column = 1; $column -le 20; $column++) {
                $header = [string]$sheet.Cells.Item($row, $column).Text
                if ($header) {
                    $candidateMap[$header.Trim()] = $column
                }
            }
            if ($candidateMap.ContainsKey('需求/BUG描述')) {
                $targetSheet = $sheet
                $headerRow = $row
                $columnMap = $candidateMap
                break
            }
        }
        if ($targetSheet) { break }
    }

    if (-not $targetSheet) {
        throw 'Release items were provided, but no sheet contains the 需求/BUG描述 header.'
    }

    $fieldByHeader = @{
        '编号' = 'number'
        '模块' = 'module'
        '子模块' = 'submodule'
        '需求/BUG描述' = 'description'
        '参与人' = 'participants'
        '验证结果' = 'validation'
        '备注' = 'notes'
    }

    $dataRow = $headerRow + 1
    foreach ($item in $Items) {
        foreach ($entry in $fieldByHeader.GetEnumerator()) {
            if ($columnMap.ContainsKey($entry.Key)) {
                $targetSheet.Cells.Item($dataRow, $columnMap[$entry.Key]).Value2 = Get-ItemValue -Item $item -Name $entry.Value
            }
        }
        $targetSheet.Rows.Item($dataRow).WrapText = $true
        if ($targetSheet.Rows.Item($dataRow).RowHeight -lt 40) {
            $targetSheet.Rows.Item($dataRow).RowHeight = 40
        }
        $dataRow++
    }
}

function New-ReleaseWorkbook {
    param(
        [string]$TemplatePath,
        [string]$OutputPath,
        [datetime]$DateValue,
        [string]$DateText,
        [string]$TimeText,
        [string]$ReleaseMode,
        [object[]]$Items,
        [bool]$AllowOverwrite
    )

    if (-not (Test-Path -LiteralPath $TemplatePath)) {
        throw "Template does not exist: $TemplatePath"
    }
    if ((Test-Path -LiteralPath $OutputPath) -and -not $AllowOverwrite) {
        throw "Output already exists: $OutputPath. Inspect and reuse it, or pass -OverwriteLocal intentionally."
    }

    $outputDirectory = Split-Path -Parent $OutputPath
    New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
    Copy-Item -LiteralPath $TemplatePath -Destination $OutputPath -Force

    $excel = $null
    $workbook = $null
    try {
        $excel = New-Object -ComObject Excel.Application
        $excel.Visible = $false
        $excel.DisplayAlerts = $false
        $workbook = $excel.Workbooks.Open($OutputPath)

        $displayDate = $DateValue.ToString('yyyy年MM月dd日')
        $isoDate = $DateValue.ToString('yyyy-MM-dd')
        $replacementPairs = [ordered]@{
            'YYYY年MM月DD日 HH:mm' = "$displayDate $TimeText"
            'YYYY年MM月DD日' = $displayDate
            '{YYYY-MM-DD}' = $isoDate
            '{YYYYMMDD}' = $DateText
            '{HH:MM}' = $TimeText
            '202605XX' = $DateText
        }
        foreach ($sheet in $workbook.Worksheets) {
            foreach ($pair in $replacementPairs.GetEnumerator()) {
                [void]$sheet.UsedRange.Replace($pair.Key, $pair.Value, 2, 1, $false, $false, $false, $false)
            }
        }

        if ($ReleaseMode -eq 'blueGreen') {
            $sheet = Get-Worksheet -Workbook $workbook -Name '蓝绿发布申请单'
            if (-not $sheet) { throw 'Blue-green template is missing sheet 蓝绿发布申请单.' }
            $sheet.Range('A1').Value2 = "$DateText $TimeText 蓝绿发布申请单"
            $sheet.Range('B3').Value2 = $isoDate
            $sheet.Range('D3').Value2 = $TimeText
            $sheet.Range('F3').Value2 = '蓝 → 绿'
            $sheet.Range('F4').Value2 = '待发布'
        }
        else {
            $plan = Get-Worksheet -Workbook $workbook -Name '版本发布计划'
            if ($plan) {
                $plan.Range('A1').Value2 = "$DateText 版本发布计划"
                $plan.Range('B2').Value2 = $displayDate
                $plan.Range('E2').Value2 = $DateText
            }

            $application = Get-Worksheet -Workbook $workbook -Name '版本发布申请单'
            if ($application) {
                $application.Range('A1').Value2 = "$DateText 版本发布申请单"
                $application.Range('B3').Value2 = "${DateText}上线"
                $application.Range('B4').Value2 = "$displayDate $TimeText"
            }

            $simpleApplication = Get-Worksheet -Workbook $workbook -Name '发版申请单'
            if ($simpleApplication) {
                $simpleApplication.Range('A1').Value2 = "$DateText $TimeText 版本发布申请单"
                $simpleApplication.Range('B3').Value2 = $DateText
                $simpleApplication.Range('D3').Value2 = $TimeText
                $simpleApplication.Range('F3').Value2 = '待发布'
            }

            $report = Get-Worksheet -Workbook $workbook -Name '版本发布测试报告'
            if ($report) {
                $report.Range('A1').Value2 = "$DateText 版本测试报告"
                $report.Range('B2').Value2 = $displayDate
                $report.Range('D2').Value2 = $DateText
            }
        }

        Write-ReleaseItems -Workbook $workbook -Items $Items
        $workbook.Save()
    }
    finally {
        if ($workbook) { $workbook.Close($true) }
        if ($excel) { $excel.Quit() }
        if ($workbook) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) }
        if ($excel) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel) }
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Release config does not exist: $ConfigPath"
}

$config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$dateValue = [datetime]::ParseExact($ReleaseDate, 'yyyyMMdd', [Globalization.CultureInfo]::InvariantCulture)
$timeCompact = $ReleaseTime.Replace(':', '')
$modeLabel = if ($Mode -eq 'majorDowntime') { '停服发布' } else { '蓝绿发布' }
$templatePath = if ($Mode -eq 'majorDowntime') { $config.releaseTemplates.majorDowntime } else { $config.releaseTemplates.blueGreen }
$fileLabel = if ($Mode -eq 'majorDowntime') { '版本发布相关表单' } else { '蓝绿发布申请单' }
$fileName = "$ReleaseDate$timeCompact$fileLabel.xlsx"
$localPath = Join-Path $config.outputDir $fileName
$items = @()
if ($ItemsJson) {
    $parsedItems = $ItemsJson | ConvertFrom-Json
    $items = @($parsedItems)
}

$plan = [ordered]@{
    releaseDate = $ReleaseDate
    releaseTime = $ReleaseTime
    mode = $Mode
    localPath = $localPath
    includePdf = [bool]$IncludePdf
    notify = [bool]$Notify
    chatId = if ($ChatId) { $ChatId } else { $config.releaseChat.chatId }
    itemCount = $items.Count
}

if ($DryRun) {
    [pscustomobject]@{ ok = $true; dryRun = $true; plan = $plan } | ConvertTo-Json -Depth 8
    exit 0
}

New-ReleaseWorkbook -TemplatePath $templatePath -OutputPath $localPath -DateValue $dateValue -DateText $ReleaseDate -TimeText $ReleaseTime -ReleaseMode $Mode -Items $items -AllowOverwrite ([bool]$OverwriteLocal)

$result = [ordered]@{
    ok = $true
    releaseDate = $ReleaseDate
    releaseTime = $ReleaseTime
    mode = $Mode
    sheet = [ordered]@{ localPath = $localPath; token = ''; wikiToken = ''; wikiUrl = '' }
    pdf = $null
    notification = $null
}

if ($LocalOnly) {
    $result.localOnly = $true
    [pscustomobject]$result | ConvertTo-Json -Depth 8
    exit 0
}

$workspaceRoot = [string]$config.workspaceRoot
Push-Location $workspaceRoot
try {
    $relativeFile = ".\output\$fileName"
    $sheetImport = Invoke-Lark -Operation 'Import release spreadsheet' -Arguments @(
        'drive', '+import', '--as', 'user', '--file', $relativeFile,
        '--type', 'sheet', '--name', ([IO.Path]::GetFileNameWithoutExtension($fileName)), '--format', 'json'
    )
    $sheetMove = Invoke-Lark -Operation 'Move release spreadsheet to Wiki' -Arguments @(
        'wiki', '+move', '--as', 'user', '--obj-type', 'sheet', '--obj-token', [string]$sheetImport.data.token,
        '--target-space-id', [string]$config.wikiSpaceId,
        '--target-parent-token', [string]$config.wikiParentToken, '--format', 'json'
    )

    $sheetWikiToken = [string]$sheetMove.data.wiki_token
    $sheetWikiUrl = "https://pcnt0al1urx3.feishu.cn/wiki/$sheetWikiToken"
    $result.sheet.token = [string]$sheetImport.data.token
    $result.sheet.wikiToken = $sheetWikiToken
    $result.sheet.wikiUrl = $sheetWikiUrl

    $pdfWikiUrl = ''
    if ($IncludePdf) {
        $pdfName = "【$ReleaseDate$timeCompact" + '缺陷发版】PDF缺陷目标文件'
        $copyParams = @{ file_token = [string]$config.pdfTemplateDocToken } | ConvertTo-Json -Compress
        $copyData = @{ folder_token = ''; name = $pdfName; type = 'docx' } | ConvertTo-Json -Compress
        $pdfCopy = Invoke-Lark -Operation 'Copy PDF defect template' -Arguments @(
            'drive', 'files', 'copy', '--as', 'user', '--params', $copyParams, '--data', $copyData, '--format', 'json'
        )
        $pdfToken = [string]$pdfCopy.data.file.token
        $displayDate = $dateValue.ToString('yyyy年MM月dd日')
        [void](Invoke-Lark -Operation 'Set PDF release datetime' -Arguments @(
            'docs', '+update', '--as', 'user', '--doc', $pdfToken, '--command', 'str_replace',
            '--pattern', 'YYYY年MM月DD日 HH:mm', '--content', "$displayDate $ReleaseTime", '--format', 'json'
        ))
        [void](Invoke-Lark -Operation 'Set PDF creation date' -Arguments @(
            'docs', '+update', '--as', 'user', '--doc', $pdfToken, '--command', 'str_replace',
            '--pattern', 'YYYY年MM月DD日', '--content', $displayDate, '--format', 'json'
        ))
        $pdfCheck = Invoke-Lark -Operation 'Verify PDF defect document' -Arguments @(
            'docs', '+fetch', '--as', 'user', '--doc', $pdfToken, '--detail', 'full', '--format', 'json'
        )
        $pdfContent = [string]$pdfCheck.data.document.content
        if (-not $pdfContent.Contains($displayDate) -or -not $pdfContent.Contains($ReleaseTime) -or -not $pdfContent.Contains('缺陷清单')) {
            throw 'PDF defect document verification failed after placeholder replacement.'
        }
        $pdfMove = Invoke-Lark -Operation 'Move PDF defect document under release sheet' -Arguments @(
            'wiki', '+move', '--as', 'user', '--obj-type', 'docx', '--obj-token', $pdfToken,
            '--target-space-id', [string]$config.wikiSpaceId,
            '--target-parent-token', $sheetWikiToken, '--format', 'json'
        )
        $pdfWikiToken = [string]$pdfMove.data.wiki_token
        $pdfWikiUrl = "https://pcnt0al1urx3.feishu.cn/wiki/$pdfWikiToken"
        $result.pdf = [ordered]@{ token = $pdfToken; wikiToken = $pdfWikiToken; wikiUrl = $pdfWikiUrl }
    }

    if ($Notify) {
        $targetChatId = if ($ChatId) { $ChatId } else { [string]$config.releaseChat.chatId }
        if (-not $targetChatId) { throw 'Notification requested but no chat_id is configured.' }

        $message = $NotificationText
        if (-not $message) {
            $message = "今天$ReleaseTime 进行$modeLabel，请相关人员及时补充发版申请单。`n`n发版申请单：`n{sheetUrl}"
        }
        $message = $message.Replace('{sheetUrl}', $sheetWikiUrl).Replace('{pdfUrl}', $pdfWikiUrl).Replace('{date}', $ReleaseDate).Replace('{time}', $ReleaseTime)
        if ($AtAll -and -not $message.Contains('user_id="all"')) {
            $message = '<at user_id="all"></at>' + "`n" + $message
        }
        foreach ($openId in $MentionOpenIds) {
            if ($openId) { $message += ("`n<at user_id=`"{0}`"></at>" -f $openId) }
        }

        $content = @{ text = $message } | ConvertTo-Json -Compress
        $sha = [Security.Cryptography.SHA256]::Create()
        try {
            $hashBytes = $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($message))
            $messageHash = ([BitConverter]::ToString($hashBytes)).Replace('-', '').Substring(0, 12).ToLowerInvariant()
        }
        finally {
            $sha.Dispose()
        }
        $idempotencyKey = "release-$ReleaseDate-$timeCompact-$Mode-$messageHash"
        $messageResult = Invoke-Lark -Operation 'Send release notification' -Arguments @(
            'im', '+messages-send', '--as', 'bot', '--chat-id', $targetChatId,
            '--content', $content, '--msg-type', 'text', '--idempotency-key', $idempotencyKey, '--format', 'json'
        )
        if (-not $messageResult.data.message_id) { throw 'Message send returned no message_id.' }
        $result.notification = [ordered]@{
            chatId = $targetChatId
            messageId = [string]$messageResult.data.message_id
            mentionedAll = [bool]$AtAll
            mentionOpenIds = $MentionOpenIds
        }
    }
}
finally {
    Pop-Location
}

[pscustomobject]$result | ConvertTo-Json -Depth 8

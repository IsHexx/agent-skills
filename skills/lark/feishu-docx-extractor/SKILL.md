---
name: feishu-docx-extractor
description: Extract authorized Feishu/Lark wiki or DocX documents whose browser page cannot be copied, including text blocks, tables, and embedded images. Use when the user provides a feishu.cn/larksuite.com wiki/docx URL and asks to copy, export, scrape, pull down, preserve, or convert its content to local Markdown/TXT/JSON; requires legitimate document access and, when necessary, an interactive login via agent-browser.
---

# Feishu DocX Extractor

## Guardrails

Use only with documents the user is authorized to access. Do not bypass login, paywalls, tenant permissions, DLP controls, or access restrictions. If the unauthenticated request redirects to login, ask the user to complete login in a visible browser window or provide an exported file/screenshot.

Delete temporary cookie files after use. Avoid printing cookie values or access tokens in final output.

## Workflow

1. Check availability:
   - `agent-browser --help`
   - `Get-Command agent-browser -ErrorAction SilentlyContinue`
2. Open the URL:
   - Headless first: `agent-browser --session feishu-doc open '<url>'`
   - If redirected to login, use a visible persistent session:
     `agent-browser --session feishu-doc-login --session-name feishu-doc-login --headed open '<url>'`
   - Wait for the user to log in, then confirm `agent-browser --session feishu-doc-login get url` is back on the wiki/docx URL.
3. Capture all DocX client vars from the authorized page with `agent-browser eval`.
4. Render the merged client vars JSON with `scripts/render_clientvars.js`.
5. Download images using the authorized browser cookies and the generated image manifest.
6. Remove cookie temp files and report output paths.

## Capture Full Client Vars

Run this from the target workspace after the authorized page is open. Use the active session name.

```powershell
$js = @'
(async () => {
  const source = window.DATA?.clientVars?.data;
  if (!source?.block_map || !window.DATA?.meta?.token) {
    throw new Error("window.DATA.clientVars.data not found; open the Feishu DocX page first");
  }
  const base = JSON.parse(JSON.stringify(source));
  const token = window.DATA.meta.token;
  const mode = String(window.DATA.clientVars.mode || 7);
  for (const k of ["block_map","user_map","editor_map","meta_map","external_mention_url","mention_page_title"]) {
    base[k] = base[k] || {};
  }
  const seen = new Set();
  const queue = [...(base.next_cursors || [])];
  if (!base.concurrent && base.has_more && base.cursor) queue.push(base.cursor);
  const merge = (dst, src) => {
    for (const k of ["block_map","user_map","editor_map","meta_map","external_mention_url","mention_page_title"]) {
      dst[k] = dst[k] || {};
      Object.assign(dst[k], src?.[k] || {});
    }
  };
  while (queue.length) {
    const cursor = queue.shift();
    if (!cursor || seen.has(cursor)) continue;
    seen.add(cursor);
    const params = new URLSearchParams({ id: token, mode, limit: "1500", cursor });
    const res = await fetch("/space/api/docx/pages/client_vars?" + params.toString(), { credentials: "include" });
    const json = await res.json();
    if (json.code !== 0) throw new Error(json.msg || "client_vars fetch failed");
    const data = json.data || {};
    merge(base, data);
    if (data.concurrent) {
      for (const c of data.next_cursors || []) if (!seen.has(c)) queue.push(c);
    } else if (data.has_more && data.cursor && !seen.has(data.cursor)) {
      queue.push(data.cursor);
    }
  }
  base._fetch_meta = {
    url: location.href,
    title: window.DATA.meta.title,
    token,
    fetched_cursors: Array.from(seen),
    block_count: Object.keys(base.block_map || {}).length
  };
  return base;
})()
'@
agent-browser --session feishu-doc-login eval $js | Set-Content -LiteralPath '.\feishu_clientvars_full.json' -Encoding UTF8
```

Verify it is non-empty:

```powershell
$d = Get-Content -Raw '.\feishu_clientvars_full.json' | ConvertFrom-Json
$d._fetch_meta | ConvertTo-Json
```

## Render Markdown And TXT

Use the bundled renderer:

```powershell
node 'C:\Users\win10\.codex\skills\feishu-docx-extractor\scripts\render_clientvars.js' `
  '.\feishu_clientvars_full.json' `
  '.\feishu_doc_export' `
  'feishu_images'
```

The renderer writes:

- `feishu_doc_export.md`
- `feishu_doc_export.txt`
- `feishu_doc_export.images.json`

## Download Images

The image manifest contains DocX image block IDs and file tokens. Download image covers with the authorized browser cookies.

```powershell
agent-browser --session feishu-doc-login cookies get --json --max-output 200000 |
  Set-Content -LiteralPath '.\feishu_cookies.json' -Encoding UTF8

$cookieData = Get-Content -Raw -LiteralPath '.\feishu_cookies.json' | ConvertFrom-Json
$cookie = ($cookieData.data.cookies | ForEach-Object { "$($_.name)=$($_.value)" }) -join '; '
$manifest = Get-Content -Raw -LiteralPath '.\feishu_doc_export.images.json' | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $manifest.imageDir | Out-Null
$headers = @{
  Cookie = $cookie
  Referer = '<original-feishu-url>'
  'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

foreach ($img in $manifest.images) {
  $out = Join-Path $manifest.imageDir ($img.id + '.png')
  if (Test-Path $out) { continue }
  $url = "https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/v2/cover/$($img.token)/?fallback_source=1&height=1280&mount_node_token=$($img.id)&mount_point=docx_image&policy=equal&width=1280"
  Invoke-WebRequest -Uri $url -Headers $headers -OutFile $out -TimeoutSec 30 | Out-Null
}

Remove-Item -LiteralPath '.\feishu_cookies.json' -Force -ErrorAction SilentlyContinue
```

## Validation

Check coverage:

```powershell
$d = Get-Content -Raw '.\feishu_clientvars_full.json' | ConvertFrom-Json
($d.block_map.PSObject.Properties).Count
$d.block_map.PSObject.Properties.Value | ForEach-Object { $_.data.type } |
  Group-Object | Sort-Object Count -Descending | Format-Table Count,Name
Get-ChildItem '.\feishu_images' -Filter '*.png' | Measure-Object
```

Inspect the end of the Markdown to ensure later sections are present:

```powershell
Get-Content -LiteralPath '.\feishu_doc_export.md' -Tail 80
```

If the Markdown is missing later content, check `_fetch_meta.fetched_cursors` and rerun the client-vars capture after reloading the page.

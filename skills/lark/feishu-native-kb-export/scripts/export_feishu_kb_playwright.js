const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const { chromium } = require('playwright');

const cdpUrl = process.env.FEISHU_CDP_URL;
const sessionManifest = process.env.FEISHU_NODE_MANIFEST || path.resolve('kb_nodes_detailed.json');
const outputRoot = process.env.FEISHU_OUTPUT_ROOT || path.resolve('企业知识库_Word导出');

if (!cdpUrl) {
  throw new Error('FEISHU_CDP_URL is required');
}

function sanitizeName(name) {
  const value = String(name || '')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .trim();
  return value || '_';
}

async function ensureDir(dir) {
  await fsp.mkdir(dir, { recursive: true });
}

function buildNodeMap(nodes) {
  const map = new Map();
  for (const node of nodes) {
    map.set(node.wiki_token, node);
  }
  return map;
}

function getSegments(node, map) {
  const segments = [];
  let current = node;
  let guard = 0;
  while (current && guard < 64) {
    segments.unshift(sanitizeName(current.title));
    if (!current.parent_wiki_token || !map.has(current.parent_wiki_token)) {
      break;
    }
    current = map.get(current.parent_wiki_token);
    guard += 1;
  }
  return segments;
}

async function writeJson(file, data) {
  await fsp.writeFile(file, JSON.stringify(data, null, 2), 'utf8');
}

async function exportDocAsWord(page, node, nodeDir) {
  await page.goto(node.url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);

  const more = page.locator('button[data-selector="more-menu"]').last();
  await more.click();

  const downloadAs = page.getByText('下载为', { exact: true }).last();
  await downloadAs.hover();
  await page.waitForTimeout(1000);

  const word = page.getByText('Word', { exact: true }).last();
  await word.click();
  await page.waitForTimeout(800);

  const exportBtn = page.getByRole('button', { name: '导出' }).last();
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 45000 }),
    exportBtn.click()
  ]);

  const suggested = sanitizeName(download.suggestedFilename() || `${node.title}.docx`);
  const ext = path.extname(suggested) || '.docx';
  const out = path.join(nodeDir, `${sanitizeName(node.title)}${ext}`);
  await download.saveAs(out);

  return {
    export_mode: 'playwright_word_export',
    saved_file: path.basename(out)
  };
}

async function exportSheetAsXlsx(page, node, nodeDir) {
  await page.goto(node.url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);

  const more = page.locator('button[data-selector="more-menu"]').last();
  await more.click();
  await page.waitForTimeout(800);

  const downloadAs = page.getByText('下载为', { exact: true }).last();
  await downloadAs.hover({ force: true });
  await page.waitForTimeout(1000);

  const xlsx = page.getByText('本地 Excel 表格(.xlsx)', { exact: true }).last();
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 45000 }),
    xlsx.click({ force: true })
  ]);

  const suggested = sanitizeName(download.suggestedFilename() || `${node.title}.xlsx`);
  const ext = path.extname(suggested) || '.xlsx';
  const out = path.join(nodeDir, `${sanitizeName(node.title)}${ext}`);
  await download.saveAs(out);

  return {
    export_mode: 'playwright_sheet_xlsx_export',
    saved_file: path.basename(out)
  };
}

async function exportBitableAsXlsx(page, node, nodeDir) {
  await page.goto(node.url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3500);

  const more = page.locator('button[data-selector="more-menu"]').last();
  await more.click();
  await page.waitForTimeout(800);

  const exportMenu = page.getByText('导出', { exact: true }).last();
  await exportMenu.hover({ force: true });
  await page.waitForTimeout(1000);

  const excelCsv = page.getByText('Excel/CSV 文件', { exact: true }).last();
  await excelCsv.click({ force: true });
  await page.waitForTimeout(1200);

  const downloadBtn = page.getByRole('button', { name: '下载' }).last();
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 45000 }),
    downloadBtn.click({ force: true })
  ]);

  const suggested = sanitizeName(download.suggestedFilename() || `${node.title}.xlsx`);
  const ext = path.extname(suggested) || '.xlsx';
  const out = path.join(nodeDir, `${sanitizeName(node.title)}${ext}`);
  await download.saveAs(out);

  return {
    export_mode: 'playwright_bitable_xlsx_export',
    saved_file: path.basename(out)
  };
}

async function downloadFileNode(page, node, nodeDir) {
  await page.goto(node.url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);

  let download = null;
  const directBtn = page.getByRole('button', { name: '下载' });
  if (await directBtn.count()) {
    [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 45000 }),
      directBtn.last().click()
    ]);
  } else {
    const more = page.locator('button[data-selector="more-menu"]').last();
    await more.click();
    await page.waitForTimeout(800);
    const menuDownload = page.getByText('下载', { exact: true }).last();
    [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 45000 }),
      menuDownload.click({ force: true })
    ]);
  }

  const suggested = sanitizeName(download.suggestedFilename() || node.title);
  const out = path.join(nodeDir, suggested);
  await download.saveAs(out);
  return {
    export_mode: 'playwright_file_download',
    saved_file: path.basename(out)
  };
}

async function exportSpecialAsPdf(page, node, nodeDir) {
  await page.goto(node.url, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  const out = path.join(nodeDir, 'page.pdf');
  await page.pdf({ path: out, printBackground: true });
  return {
    export_mode: 'playwright_page_pdf',
    saved_file: path.basename(out)
  };
}

async function main() {
  const nodes = JSON.parse(await fsp.readFile(sessionManifest, 'utf8'));
  const nodeMap = buildNodeMap(nodes);
  await ensureDir(outputRoot);

  const browser = await chromium.connectOverCDP(cdpUrl);
  const context = browser.contexts()[0];
  const page = context.pages()[0] || await context.newPage();
  await page.bringToFront();

  const manifest = [];
  for (let i = 0; i < nodes.length; i += 1) {
    const node = nodes[i];
    const nodeDir = path.join(outputRoot, ...getSegments(node, nodeMap));
    await ensureDir(nodeDir);

    const meta = {
      title: node.title,
      wiki_token: node.wiki_token,
      obj_type: node.obj_type,
      obj_token: node.obj_token,
      source_url: node.url,
      level: node.level,
      has_child: node.has_child,
      parent_wiki_token: node.parent_wiki_token,
      exported_at: new Date().toISOString()
    };

    console.log(`[${i + 1}/${nodes.length}] ${node.title} (type=${node.obj_type})`);

    try {
      let result;
      if (node.obj_type === 22) {
        result = await exportDocAsWord(page, node, nodeDir);
      } else if (node.obj_type === 12) {
        result = await downloadFileNode(page, node, nodeDir);
      } else if (node.obj_type === 3) {
        result = await exportSheetAsXlsx(page, node, nodeDir);
      } else if (node.obj_type === 8) {
        result = await exportBitableAsXlsx(page, node, nodeDir);
      } else {
        result = await exportSpecialAsPdf(page, node, nodeDir);
      }
      Object.assign(meta, result);
    } catch (error) {
      meta.export_mode = 'failed';
      meta.export_error = String(error && error.message ? error.message : error);
    }

    await writeJson(path.join(nodeDir, 'meta.json'), meta);
    manifest.push(meta);
  }

  await writeJson(path.join(outputRoot, 'manifest.json'), manifest);
  await browser.close();
  console.log(`Done: ${outputRoot}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

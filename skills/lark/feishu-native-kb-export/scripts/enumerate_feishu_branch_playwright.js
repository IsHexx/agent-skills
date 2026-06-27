const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const cdpUrl = process.env.FEISHU_CDP_URL;
const rootWikiToken = process.env.FEISHU_ROOT_WIKI_TOKEN;
const rootUrl = process.env.FEISHU_ROOT_URL || (rootWikiToken ? `https://pcnt0al1urx3.feishu.cn/wiki/${rootWikiToken}` : null);
const outputFile = process.env.FEISHU_ENUM_OUTPUT || path.resolve(`branch_${rootWikiToken || 'root'}_nodes.json`);

if (!cdpUrl) throw new Error('FEISHU_CDP_URL is required');
if (!rootWikiToken) throw new Error('FEISHU_ROOT_WIKI_TOKEN is required');

function parseUid(uid) {
  const out = {};
  for (const part of String(uid || '').split('&')) {
    const [k, v] = part.split('=', 2);
    if (k && v !== undefined) out[k] = v;
  }
  return out;
}

async function waitForTree(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(3000);
  await page.waitForFunction(() => document.querySelectorAll('[data-node-uid]').length > 0, null, { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1000);
}

async function collectVisibleNodes(page) {
  return page.evaluate(() => Array.from(document.querySelectorAll('[data-node-uid]')).map(el => ({
    uid: el.getAttribute('data-node-uid'),
    level: Number(el.getAttribute('data-node-level') || 0),
    text: (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' '),
    expanded: String(el.className || '').includes('workspace-tree-view-node--expanded'),
    hasArrow: !!el.querySelector('.workspace-tree-view-node-expand-arrow .universe-icon[role="button"]'),
    className: String(el.className || '')
  })));
}

async function expandAllVisible(page) {
  let changed = true;
  let guard = 0;
  while (changed && guard < 20) {
    changed = false;
    guard += 1;
    const clicked = await page.evaluate(() => {
      const nodes = Array.from(document.querySelectorAll('[data-node-uid]'));
      let count = 0;
      for (const node of nodes) {
        const expanded = String(node.className || '').includes('workspace-tree-view-node--expanded');
        const arrow = node.querySelector('.workspace-tree-view-node-expand-arrow .universe-icon[role="button"]');
        if (arrow && !expanded) {
          arrow.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
          count += 1;
        }
      }
      return count;
    });
    if (clicked > 0) {
      changed = true;
      await page.waitForTimeout(800);
    }
  }
}

async function scrollSidebarAndCollect(page) {
  const seen = new Map();
  for (let pass = 0; pass < 8; pass += 1) {
    const nodes = await collectVisibleNodes(page);
    for (const node of nodes) {
      if (!seen.has(node.uid)) seen.set(node.uid, node);
    }
    const moved = await page.evaluate(() => {
      const el = document.querySelector('.sidebar-styled__ScrollableContainer-czoANO');
      if (!el) return false;
      const before = el.scrollTop;
      el.scrollTop = Math.min(el.scrollTop + Math.max(200, el.clientHeight - 60), el.scrollHeight);
      return el.scrollTop !== before;
    });
    if (!moved) break;
    await page.waitForTimeout(500);
    await expandAllVisible(page);
  }
  return Array.from(seen.values());
}

async function getNodeDetail(page, wikiToken) {
  return page.evaluate(async ({ wikiToken }) => {
    const spaceId = window.current_space_wiki?.space_id || window.wiki_info_map?.[wikiToken]?.spaceId;
    const res = await fetch(`/space/api/wiki/v2/tree/get_node/?wiki_token=${wikiToken}&space_id=${spaceId}&expand_shortcut=true&with_deleted=true`, { credentials: 'include' });
    const json = await res.json();
    return json.data;
  }, { wikiToken });
}

async function main() {
  const browser = await chromium.connectOverCDP(cdpUrl);
  const context = browser.contexts()[0];
  const page = context.pages()[0] || await context.newPage();
  const queue = [rootWikiToken];
  const visited = new Set();
  const results = new Map();

  while (queue.length) {
    const token = queue.shift();
    if (visited.has(token)) continue;
    visited.add(token);

    const url = `https://pcnt0al1urx3.feishu.cn/wiki/${token}`;
    console.log(`visit ${token}`);
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    await waitForTree(page);
    await expandAllVisible(page);
    const visible = await scrollSidebarAndCollect(page);

    for (const node of visible) {
      const parsed = parseUid(node.uid);
      const wikiToken = parsed.wikiToken;
      if (!wikiToken) continue;
      if (!results.has(wikiToken)) {
        const detail = await getNodeDetail(page, wikiToken);
        results.set(wikiToken, {
          wiki_token: wikiToken,
          level: node.level,
          text: node.text,
          obj_type: detail.obj_type,
          obj_token: detail.obj_token,
          title: detail.title,
          url: detail.url,
          has_child: detail.has_child,
          node_type: detail.wiki_node_type,
          parent_wiki_token: detail.parent_wiki_token
        });
      }
    }

    for (const item of results.values()) {
      if (item.parent_wiki_token === token && item.has_child && !visited.has(item.wiki_token)) {
        queue.push(item.wiki_token);
      }
    }
  }

  const all = Array.from(results.values())
    .filter(item => item.wiki_token === rootWikiToken || visited.has(item.parent_wiki_token) || item.parent_wiki_token === rootWikiToken)
    .sort((a, b) => String(a.url).localeCompare(String(b.url), 'zh-CN'));

  fs.writeFileSync(outputFile, JSON.stringify(all, null, 2), 'utf8');
  console.log(`saved ${outputFile} count=${all.length}`);
  await browser.close();
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});

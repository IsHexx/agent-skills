#!/usr/bin/env node
// Extract raw design data from a live website using Playwright (headless Chromium).
// Output is consumed by the `web-to-design-md` skill to synthesize a spec-compliant
// DESIGN.md (Google Stitch design.md format).
//
// Token-name semantic classification, type-role inference, breakpoint mining and the
// dual light/dark capture are adapted from getdesign (MIT, (c) 2026 getdesign /
// Mohtasham Murshid Madani — https://github.com/MohtashamMurshid/getdesign). That
// project parses authored CSS; here the same heuristics are layered on top of our
// computed-style + CSS-variable capture.
//
// Usage:
//   node extract-design-data.mjs <url> [--out <dir>] [--wait <ms>] [--name <name>]
//
// Produces in <dir> (default ./design-md-output):
//   design-data.json  — ranked colors, type scale, spacing, radii, shadows, CSS
//                        variables (role-classified), breakpoints, dark-mode colors, meta
//   screenshot.png        — full-page screenshot, light mode (for judging atmosphere)
//   screenshot-dark.png   — full-page screenshot, dark mode (only if the site differs)

import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

// Playwright may live locally, globally, or in the npx cache — try them all.
function loadChromium() {
  const candidates = ['playwright', 'playwright-core'];
  try {
    const groot = execSync('npm root -g', { encoding: 'utf8' }).trim();
    candidates.push(join(groot, 'playwright'), join(groot, 'playwright-core'));
  } catch { /* npm not on PATH — fall through */ }
  for (const c of candidates) {
    try {
      const m = require(c);
      if (m && m.chromium) return m.chromium;
    } catch { /* try next */ }
  }
  throw new Error(
    'Playwright not found. Install it once with:\n' +
    '  npm install -g playwright && npx playwright install chromium'
  );
}

// ---- borrowed heuristics (getdesign, MIT) ----------------------------------
// Bucket a color token by what its CSS variable name / selector implies.
function classifyColorRole(nameAndSelector) {
  const h = (nameAndSelector || '').toLowerCase();
  if (/(success|positive)/.test(h)) return 'success';
  if (/(warning|caution)/.test(h)) return 'warning';
  if (/(error|danger|destructive)/.test(h)) return 'error';
  if (/(info|notice|highlight)/.test(h)) return 'info';
  if (/(border|stroke|divider|outline)/.test(h)) return 'border';
  if (/(background|surface|canvas|panel|card|overlay|bg)/.test(h)) return 'surface';
  if (/(accent|brand|primary|cta|focus|link|interactive)/.test(h)) return 'primary';
  if (/(text|foreground|neutral|muted|gray|grey|ink)/.test(h)) return 'neutral';
  return 'unclassified';
}

// Map a px size to a typographic role; for clamp()/multi-value, the largest px wins.
function inferTypeRole(fontSizeStr) {
  const pxs = [...String(fontSizeStr).matchAll(/(\d+(?:\.\d+)?)px/g)].map((m) => Number(m[1]));
  if (pxs.length === 0) return 'body';
  const size = Math.max(...pxs);
  if (size >= 48) return 'display';
  if (size >= 36) return 'headline';
  if (size >= 28) return 'title';
  if (size >= 20) return 'subtitle';
  if (size <= 13) return 'caption';
  if (size <= 15) return 'small';
  return 'body';
}

const COLORISH = /(#[0-9a-f]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(|\boklab\(|\blab\(|\blch\(|\bcolor-mix\()/i;

const args = process.argv.slice(2);
const url = args.find((a) => !a.startsWith('--'));
if (!url) {
  console.error('Usage: node extract-design-data.mjs <url> [--out <dir>] [--wait <ms>] [--name <name>]');
  process.exit(1);
}
const flag = (name, def) => {
  const i = args.indexOf('--' + name);
  return i >= 0 && args[i + 1] ? args[i + 1] : def;
};
const outDir = resolve(flag('out', './design-md-output'));
const waitMs = parseInt(flag('wait', '1800'), 10);
const nameArg = flag('name', null);

// Runs inside the page. Walks every visible element and tallies design signals.
function collect() {
  const parseColor = (str) => {
    if (!str) return null;
    str = str.trim();
    if (str === 'transparent') return null;
    const m = str.match(/^rgba?\(([^)]+)\)$/i);
    if (m) {
      const p = m[1].split(/[,\s/]+/).map((s) => s.trim()).filter(Boolean);
      const r = +p[0], g = +p[1], b = +p[2];
      const a = p[3] !== undefined ? +p[3] : 1;
      if (!a) return null; // fully transparent
      const hex = '#' + [r, g, b]
        .map((x) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, '0'))
        .join('');
      return hex;
    }
    return str.startsWith('#') ? str.toLowerCase() : null;
  };

  const colors = {};
  const addColor = (hex, ctx) => {
    if (!hex) return;
    if (!colors[hex]) colors[hex] = { count: 0, text: 0, background: 0, border: 0 };
    colors[hex].count++;
    colors[hex][ctx]++;
  };

  const fonts = {};
  const typeScale = {};
  const spacing = {};
  const radii = {};
  const shadows = {};

  let analyzed = 0;
  for (const el of document.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) continue;
    analyzed++;
    const tag = el.tagName.toLowerCase();
    const hasText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim());

    if (hasText) addColor(parseColor(cs.color), 'text');
    addColor(parseColor(cs.backgroundColor), 'background');
    for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
      if (parseFloat(cs['border' + side + 'Width']) > 0) {
        addColor(parseColor(cs['border' + side + 'Color']), 'border');
      }
    }

    const ff = (cs.fontFamily || '').split(',')[0].replace(/["']/g, '').trim();
    if (ff) {
      if (!fonts[ff]) fonts[ff] = { count: 0, tags: {} };
      fonts[ff].count++;
      fonts[ff].tags[tag] = (fonts[ff].tags[tag] || 0) + 1;
    }

    if (hasText) {
      const key = [cs.fontSize, cs.fontWeight, cs.lineHeight, cs.letterSpacing].join('|');
      if (!typeScale[key]) {
        typeScale[key] = {
          count: 0, tags: {},
          fontSize: cs.fontSize, fontWeight: cs.fontWeight,
          lineHeight: cs.lineHeight, letterSpacing: cs.letterSpacing, fontFamily: ff,
        };
      }
      typeScale[key].count++;
      typeScale[key].tags[tag] = (typeScale[key].tags[tag] || 0) + 1;
    }

    const px = (v) => (/px$/.test(v) ? parseFloat(v) : NaN);
    for (const v of [cs.paddingTop, cs.paddingRight, cs.paddingBottom, cs.paddingLeft,
      cs.marginTop, cs.marginRight, cs.marginBottom, cs.marginLeft, cs.rowGap, cs.columnGap]) {
      const n = px(v);
      if (n > 0) { const k = Math.round(n) + 'px'; spacing[k] = (spacing[k] || 0) + 1; }
    }
    for (const corner of ['TopLeft', 'TopRight', 'BottomRight', 'BottomLeft']) {
      const n = px(cs['border' + corner + 'Radius']);
      if (n > 0) { const k = Math.round(n) + 'px'; radii[k] = (radii[k] || 0) + 1; }
    }
    if (cs.boxShadow && cs.boxShadow !== 'none') {
      shadows[cs.boxShadow] = (shadows[cs.boxShadow] || 0) + 1;
    }
  }

  return {
    meta: {
      url: location.href,
      title: document.title,
      description: (document.querySelector('meta[name="description"]') || {}).content || '',
      lang: document.documentElement.lang || '',
    },
    analyzed, colors, fonts, typeScale, spacing, radii, shadows,
  };
}

const chromium = loadChromium();
mkdirSync(outDir, { recursive: true });

console.log(`- Launching headless Chromium…`);
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  console.log(`- Loading ${url} …`);
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  } catch {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  }
  await page.waitForTimeout(waitMs);

  const raw = await page.evaluate(collect);

  // Mine the authored CSS (same-origin sheets) for variable NAMES and @media
  // breakpoints — gives us the semantic intent computed styles can't see.
  const cssInfo = await page.evaluate(() => {
    const variables = [];
    const breakpoints = new Set();
    const walk = (rules) => {
      for (const rule of Array.from(rules || [])) {
        if (rule.type === 1 && rule.style) {
          for (let i = 0; i < rule.style.length; i++) {
            const prop = rule.style[i];
            if (prop.startsWith('--')) {
              variables.push({
                name: prop,
                value: rule.style.getPropertyValue(prop).trim(),
                selector: rule.selectorText || '',
              });
            }
          }
        } else if (rule.type === 4 && rule.media) {
          const m = rule.media.mediaText.match(/min-width:\s*([\d.]+(?:px|rem|em))/i);
          if (m) breakpoints.add(m[1]);
          walk(rule.cssRules);
        } else if (rule.cssRules) {
          walk(rule.cssRules);
        }
      }
    };
    for (const sheet of Array.from(document.styleSheets)) {
      try { walk(sheet.cssRules); } catch { /* cross-origin sheet — skip */ }
    }
    const seen = new Set();
    const deduped = [];
    for (const v of variables) {
      const k = v.name + '|' + v.value;
      if (!seen.has(k) && v.value) { seen.add(k); deduped.push(v); }
    }
    return { variables: deduped.slice(0, 400), breakpoints: [...breakpoints] };
  });

  const shotPath = join(outDir, 'screenshot.png');
  await page.screenshot({ path: shotPath, fullPage: true }).catch(() => {});

  // Dual-theme capture (getdesign approach): re-render under prefers-color-scheme: dark
  // and keep the dark palette only if it actually differs from light.
  let darkColors = [];
  const lightSet = new Set(Object.keys(raw.colors));
  try {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForTimeout(600);
    const darkRaw = await page.evaluate(collect);
    const darkKeys = Object.keys(darkRaw.colors);
    const differs = darkKeys.some((k) => !lightSet.has(k)) &&
      darkKeys.filter((k) => !lightSet.has(k)).length >= 3;
    if (differs) {
      darkColors = Object.entries(darkRaw.colors)
        .sort((a, b) => b[1].count - a[1].count)
        .slice(0, 14)
        .map(([hex, v]) => ({
          hex, count: v.count,
          contexts: ['text', 'background', 'border'].filter((c) => v[c] > 0),
        }));
      await page.screenshot({ path: join(outDir, 'screenshot-dark.png'), fullPage: true }).catch(() => {});
    }
    await page.emulateMedia({ colorScheme: 'light' });
  } catch { /* dark capture is best-effort */ }

  // ---- rank + trim into a clean, synthesis-friendly shape ----
  const byCountDesc = (obj) =>
    Object.entries(obj).sort((a, b) => b[1].count - a[1].count || 0);

  const colors = byCountDesc(raw.colors)
    .slice(0, 30)
    .map(([hex, v]) => ({
      hex, count: v.count,
      contexts: ['text', 'background', 'border'].filter((c) => v[c] > 0),
    }));

  const fonts = Object.entries(raw.fonts)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 8)
    .map(([family, v]) => ({
      family, count: v.count,
      topTags: Object.entries(v.tags).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([t]) => t),
    }));

  const typeScale = Object.values(raw.typeScale)
    .sort((a, b) => parseFloat(b.fontSize) - parseFloat(a.fontSize) || b.count - a.count)
    .slice(0, 16)
    .map((t) => ({
      role: inferTypeRole(t.fontSize),
      fontFamily: t.fontFamily,
      fontSize: t.fontSize,
      fontWeight: t.fontWeight,
      lineHeight: t.lineHeight,
      letterSpacing: t.letterSpacing,
      count: t.count,
      topTags: Object.entries(t.tags).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k]) => k),
    }));

  // Role-classify color CSS variables by name/selector — a semantic prior for synthesis.
  const colorVariables = cssInfo.variables
    .filter((v) => COLORISH.test(v.value))
    .map((v) => ({
      name: v.name,
      value: v.value,
      role: classifyColorRole(v.name + ' ' + v.selector),
    }));
  const colorRoles = {};
  for (const v of colorVariables) {
    (colorRoles[v.role] ??= []).push({ name: v.name, value: v.value });
  }

  const breakpoints = cssInfo.breakpoints
    .map((v) => ({ value: v, px: parseFloat(v) * (/rem|em/.test(v) ? 16 : 1) }))
    .sort((a, b) => a.px - b.px)
    .map(({ value }) => value);

  const rankNum = (obj, limit) =>
    Object.entries(obj)
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit)
      .map(([value, count]) => ({ value, count }));

  const spacing = rankNum(raw.spacing, 16)
    .sort((a, b) => parseFloat(a.value) - parseFloat(b.value));
  const radii = rankNum(raw.radii, 10)
    .sort((a, b) => parseFloat(a.value) - parseFloat(b.value));
  const shadows = rankNum(raw.shadows, 8);

  const out = {
    generatedAt: new Date().toISOString(),
    name: nameArg || raw.meta.title || raw.meta.url,
    meta: raw.meta,
    elementsAnalyzed: raw.analyzed,
    colors, colorRoles, darkColors,
    fonts, typeScale, spacing, radii, shadows, breakpoints,
  };

  const jsonPath = join(outDir, 'design-data.json');
  writeFileSync(jsonPath, JSON.stringify(out, null, 2));

  console.log(`\n  Done. Analyzed ${raw.analyzed} elements.`);
  console.log(`  Colors: ${colors.length}  Vars: ${colorVariables.length}  Fonts: ${fonts.length}  Type: ${typeScale.length}  Spacing: ${spacing.length}  Radii: ${radii.length}  Shadows: ${shadows.length}  Breakpoints: ${breakpoints.length}  Dark: ${darkColors.length ? 'yes' : 'no'}`);
  console.log(`\n  ${jsonPath}`);
  console.log(`  ${shotPath}`);
} finally {
  await browser.close();
}

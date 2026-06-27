#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

function usage() {
  console.error(
    "Usage: node render_clientvars.js <clientvars.json> <output-prefix> [image-dir]"
  );
  process.exit(2);
}

const [, , inputPath, outputPrefix, imageDir = "feishu_images"] = process.argv;
if (!inputPath || !outputPrefix) usage();

const data = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const blockMap = data.block_map || {};
const rootId = data.id;

function block(id) {
  return blockMap[id];
}

function clean(value) {
  return String(value || "")
    .replace(/[\u200B\uFEFF]/g, "")
    .replace(/\r/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{4,}/g, "\n\n\n");
}

function blockText(item) {
  const node = item?.data?.text?.initialAttributedTexts?.text;
  if (node == null) return "";
  if (typeof node === "string") return clean(node);
  if (typeof node === "object") {
    return clean(
      Object.keys(node)
        .sort((a, b) => Number(a) - Number(b))
        .map((key) => node[key] || "")
        .join("")
    );
  }
  return "";
}

function inline(id, seen = new Set()) {
  const item = block(id);
  if (!item || seen.has(id)) return "";
  seen.add(id);

  const type = item.data?.type;
  if (type === "image") {
    const image = item.data.image || {};
    return `![${image.name || "image"}](${imageDir}/${id}.png)`;
  }

  const parts = [];
  const text = blockText(item).trim();
  if (text) parts.push(text);
  for (const child of item.data?.children || []) {
    const childText = inline(child, seen).trim();
    if (childText) parts.push(childText);
  }
  return parts.join("\n");
}

function escapeCell(value) {
  return clean(value).replace(/\|/g, "\\|").replace(/\n+/g, "<br>").trim();
}

function cellByRowCol(cellSet, row, col) {
  return (
    cellSet[`${row}${col}`] ||
    cellSet[`${row}_${col}`] ||
    Object.values(cellSet).find(
      (value) => value && value.row_id === row && value.column_id === col
    )
  );
}

function renderTable(item) {
  const rows = item.data?.rows_id || [];
  const cols = item.data?.columns_id || [];
  const cellSet = item.data?.cell_set || {};
  if (!rows.length || !cols.length) return [];

  const matrix = rows.map((row) =>
    cols.map((col) => escapeCell(inline(cellByRowCol(cellSet, row, col)?.block_id)))
  );
  if (!matrix.length) return [];

  const output = [];
  output.push(`| ${matrix[0].join(" | ")} |`);
  output.push(`| ${cols.map(() => "---").join(" | ")} |`);
  for (const row of matrix.slice(1)) output.push(`| ${row.join(" | ")} |`);
  return ["", ...output, ""];
}

function render(id, depth = 0, seen = new Set()) {
  const item = block(id);
  if (!item || seen.has(id)) return [];
  seen.add(id);

  const type = item.data?.type;
  const children = item.data?.children || [];
  const text = blockText(item).trim();
  const output = [];
  const childLines = () => children.flatMap((child) => render(child, depth + 1, seen));

  if (type === "page") {
    if (text) output.push(`# ${text}`, "");
    for (const child of children) output.push(...render(child, 0, seen));
  } else if (type === "heading1") {
    if (text) output.push("", `## ${text}`, "");
    output.push(...childLines());
  } else if (type === "heading2") {
    if (text) output.push("", `### ${text}`, "");
    output.push(...childLines());
  } else if (type === "bullet") {
    if (text) output.push(`${"  ".repeat(depth)}- ${text}`);
    for (const child of children) output.push(...render(child, depth + 1, seen));
  } else if (type === "text") {
    if (text) output.push(text);
    for (const child of children) output.push(...render(child, depth, seen));
  } else if (type === "table") {
    output.push(...renderTable(item));
  } else if (type === "grid" || type === "grid_column" || type === "table_cell") {
    for (const child of children) output.push(...render(child, depth, seen));
  } else if (type === "callout") {
    const lines = children.flatMap((child) => render(child, depth, seen)).filter(Boolean);
    if (lines.length) {
      output.push("", ...lines.map((line) => (line.startsWith("|") ? line : `> ${line}`)), "");
    }
  } else if (type === "image") {
    const image = item.data?.image || {};
    output.push(`![${image.name || "image"}](${imageDir}/${id}.png)`);
  } else {
    if (text) output.push(text);
    for (const child of children) output.push(...render(child, depth, seen));
  }

  return output;
}

let markdown = render(rootId).join("\n");
markdown = `${clean(markdown).replace(/\n{3,}/g, "\n\n").trim()}\n`;

const images = Object.entries(blockMap)
  .filter(([, item]) => item?.data?.type === "image" && item.data.image?.token)
  .map(([id, item]) => ({
    id,
    token: item.data.image.token,
    name: item.data.image.name || "image.png",
    width: item.data.image.width,
    height: item.data.image.height,
  }));

fs.writeFileSync(`${outputPrefix}.md`, markdown, "utf8");
fs.writeFileSync(`${outputPrefix}.txt`, markdown.replace(/^#+\s*/gm, ""), "utf8");
fs.writeFileSync(
  `${outputPrefix}.images.json`,
  JSON.stringify({ imageDir, images }, null, 2),
  "utf8"
);

console.log(
  JSON.stringify(
    {
      blocks: Object.keys(blockMap).length,
      images: images.length,
      markdown: path.resolve(`${outputPrefix}.md`),
      text: path.resolve(`${outputPrefix}.txt`),
      imageManifest: path.resolve(`${outputPrefix}.images.json`),
    },
    null,
    2
  )
);

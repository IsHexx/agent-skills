---
name: obsidian
description: "Create and edit Obsidian content: Bases (.base files with views, filters, formulas, summaries) and Obsidian Flavored Markdown (wikilinks, embeds, callouts, properties, tags). Use when working with .base files, creating database-like views of notes, or when the user mentions Bases, table views, card views, filters, or formulas in Obsidian; also when working with .md files in Obsidian, or when the user mentions wikilinks, callouts, frontmatter, tags, embeds, or Obsidian notes. Triggers: 'obsidian base', '.base file', 'obsidian markdown', 'wikilink', 'callout', 'obsidian 笔记', 'obsidian 视图'."
---

# Obsidian

Two content domains. Read the relevant reference before editing.

## Bases (`.base` files)

For database-like dynamic views of notes (table/cards/list/map views, filters, formulas, summaries):

1. Read [`references/bases.md`](references/bases.md) completely — it covers the full YAML schema, filter syntax, formula syntax, all functions (global/date/duration/string/number/list/file/link/object/regexp), view types, default summaries, and complete examples.
2. Create/edit the `.base` file as valid YAML per the schema.
3. Bases can be embedded in Markdown: `![[MyBase.base]]` or `![[MyBase.base#View Name]]`.

Key concepts: global vs per-view filters (and/or/not), three property types (note/file/formula), Duration type from date subtraction (use `.days`/`.hours` fields before rounding), `this` keyword context.

## Obsidian Flavored Markdown

For notes with Obsidian-specific syntax (wikilinks, embeds, callouts, properties/frontmatter, tags, math, diagrams):

1. Read [`references/markdown.md`](references/markdown.md) completely — it covers formatting, internal links (wikilinks to notes/headings/blocks), embeds (notes/images/audio/PDF/lists/search), callouts (all types + foldable + nested), lists/quotes/code/tables, math (LaTeX), Mermaid diagrams, footnotes, comments, properties, tags, HTML.
2. Author the `.md` file using the appropriate syntax.

Key extensions beyond CommonMark/GFM: `[[wikilinks]]`, `![[embeds]]`, `> [!callout]`, `==highlight==`, `%%comments%%`, `[^footnotes]`, YAML frontmatter properties, `#tags` (nested with `/`).

## Routing

- User mentions `.base`, "Bases", "table/card/list/map view", "filters", "formulas", "summaries" → **Bases** section + `references/bases.md`.
- User mentions `.md` notes, wikilinks, callouts, frontmatter/properties, embeds, tags → **Markdown** section + `references/markdown.md`.
- Both → read both references.

## References

- [Bases syntax](https://help.obsidian.md/bases/syntax), [Bases functions](https://help.obsidian.md/bases/functions), [Bases views](https://help.obsidian.md/bases/views), [Bases formulas](https://help.obsidian.md/formulas)
- [Basic formatting](https://help.obsidian.md/syntax), [Advanced formatting](https://help.obsidian.md/advanced-syntax), [Obsidian Flavored Markdown](https://help.obsidian.md/obsidian-flavored-markdown), [Internal links](https://help.obsidian.md/links), [Embeds](https://help.obsidian.md/embeds), [Callouts](https://help.obsidian.md/callouts), [Properties](https://help.obsidian.md/properties)

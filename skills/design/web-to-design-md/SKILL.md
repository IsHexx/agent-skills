---
name: web-to-design-md
description: "Extract a live website's visual design into a DESIGN.md file following Google Stitch's design.md specification (YAML token front matter + 8 ordered prose sections). Use when the user says 'extract design to design.md', 'make a DESIGN.md from this site', 'generate design.md', 'turn this website into a design system file', or gives a URL and asks for design.md / a Stitch-format design spec."
allowed-tools: Bash, Read, Write, Glob
---

# Website → DESIGN.md

Turn any website URL into a spec-compliant `DESIGN.md` (Google Stitch / google-labs-code
`design.md` format): machine-readable design tokens in YAML front matter plus
human-readable rationale in eight ordered markdown sections.

The full format is in `reference/design-md-spec.md` (bundled — read it before writing).
Always follow that spec for field names, token types, and **section order**.

## Process

### 1. Extract raw design data from the live site

```bash
node "<SKILL_DIR>/scripts/extract-design-data.mjs" <url> --out ./design-md-output
```

Replace `<SKILL_DIR>` with this skill's directory. Useful flags:
- `--wait <ms>` — extra wait after load for slow SPAs (default 1800; try 3500 if the page looks empty)
- `--name "<Brand>"` — override the design-system name (defaults to page title)

This writes:
- `design-md-output/design-data.json` — ranked `colors` (rendered, with usage context),
  `colorRoles` (CSS variables bucketed into primary/accent/surface/border/neutral/semantic
  by their authored name), `darkColors` (if the site has a distinct dark theme),
  role-tagged `typeScale`, `fonts`, `spacing`, `radii`, `shadows`, `breakpoints`, meta
- `design-md-output/screenshot.png` — full-page screenshot (light)
- `design-md-output/screenshot-dark.png` — dark-mode screenshot (only if it differs)

> Requires Playwright + Chromium. If the script reports Playwright is missing, run once:
> `npm install -g playwright && npx playwright install chromium`

### 2. Read the evidence

- **Read** `design-md-output/design-data.json` for the exact values. Prefer `colorRoles`
  (authored CSS-variable names — the site's own intent) as the primary source for naming
  tokens; use `colors` (rendered usage counts) to confirm which actually dominate and to
  fill gaps when a site has no semantic variables (e.g. Tailwind/CSS-in-JS).
- **Read** (view) `design-md-output/screenshot.png` (and `-dark.png` if present) to judge
  the *atmosphere* — mood, density, contrast, personality. This drives `## Overview`.

### 3. Read the spec

**Read** `reference/design-md-spec.md` so the output matches the format exactly.

### 4. Synthesize `DESIGN.md`

Map the raw data into tokens + prose. Apply judgement — don't dump every raw value;
distill a coherent system.

> **Grounding rule (non-negotiable, adapted from getdesign).** Every concrete value —
> hex, font family, size, spacing, radius, shadow, breakpoint — must trace to something in
> `design-data.json` or a visible pixel in the screenshot. If you can't ground a value,
> describe the role qualitatively ("warm neutral gray") instead of inventing a hex. Do not
> copy values from other sites or hallucinate tokens the page doesn't use.

**Front matter (YAML):**
- `name`, `version: alpha`, optional `description`.
- `colors`: give **semantic role names** (`primary`, `secondary`, `accent`, `surface`,
  `background`, `text`, `on-primary`, `error`…) — not raw names. Start from `colorRoles`
  (the site's own variable buckets); confirm dominance with `colors[].count`/`contexts`
  (high-count background → `surface`/`background`; saturated low-count → `accent`).
- `typography`: collapse `typeScale` into named levels — each entry already carries an
  inferred `role` (`display`/`headline`/`title`/`subtitle`/`body`/`small`/`caption`).
  Merge near-duplicates; use the dominant `fontFamily`.
- `rounded`: derive a small scale (`sm`/`md`/`lg`, plus `full` for pills) from the radii.
- `spacing`: derive a clean numeric scale; infer the base unit and snap to it.
- `components`: define the obvious ones (`button-primary`, `button-secondary`, `card`,
  `input`) using **token references** like `{colors.primary}`, `{spacing.2}`,
  `{rounded.md}`. Add `-hover`/`-focus` variants where sensible.

**Body (markdown), in this exact order** — omit a section only if there's genuinely
nothing to say:
1. `## Overview` — personality/atmosphere (informed by the screenshot)
2. `## Colors` — each color's role and when to use it
3. `## Typography` — the levels and their usage
4. `## Layout` — spacing strategy, density, grid; cite the actual `breakpoints`
5. `## Elevation & Depth` — how hierarchy/shadows work
6. `## Shapes` — radius scale and shape language
7. `## Components` — guidance + variants/states
8. `## Do's and Don'ts` — concrete rules

Prose should reference the token names defined in the front matter. If `darkColors` is
non-empty, note the dark-theme palette in `## Colors` (the Stitch front matter has no
formal dark slot, so describe it in prose / a second color block).

### 5. Verify, then write

Run this self-check before writing (adapted from getdesign):
- [ ] Front matter is valid YAML; `name` present; `version: alpha`.
- [ ] All present sections use `##`, are in spec order, with no duplicate headings.
- [ ] Every `{...}` reference resolves to a token defined in the front matter.
- [ ] Every hex / font / size / breakpoint traces to `design-data.json` (grounding rule).
- [ ] No placeholder text ("TBD", "(example)", lorem ipsum).

Write the result to `./DESIGN.md` (or a path the user requests) — but if a `DESIGN.md`
you didn't create already exists there, write to a clearly-named file (e.g.
`<brand>-DESIGN.md`) and surface the conflict instead of overwriting. Then give a short
summary: brand name, primary palette, type system, and any judgement calls or gaps (e.g.
no dark theme detected, SPA needed a longer `--wait`).

## Notes
- The extractor combines **rendered computed styles** (what the browser actually painted)
  with **authored CSS variable names + `@media` breakpoints** (the site's intent) and a
  best-effort **dark-mode** pass.
- For multi-brand sites, run once per brand path and note both.

## Attribution
Token-name classification, type-role inference, breakpoint mining, dual light/dark
capture, and the grounding/verification discipline are adapted from
[getdesign](https://github.com/MohtashamMurshid/getdesign) (MIT, © 2026 getdesign /
Mohtasham Murshid Madani). Output format follows Google Labs' `design.md` spec (see
`reference/design-md-spec.md`).

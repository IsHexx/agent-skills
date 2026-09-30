# DESIGN.md format — condensed spec

Source: Google Labs `design.md` (https://github.com/google-labs-code/design.md,
spec at `docs/spec.md`; Stitch docs at https://stitch.withgoogle.com/docs/design-md/specification).

A `DESIGN.md` gives coding agents a persistent, structured understanding of a visual
identity. It has two parts:

1. **YAML front matter** — machine-readable design *tokens* (the exact values).
2. **Markdown body** — human-readable *rationale* (what the values mean and how/when to apply them).

> Tokens give agents exact values; prose tells them *why* those values exist and how to use them.

---

## 1. YAML front matter

Delimited by `---` fences at the very top of the file.

```yaml
version: alpha            # optional; current spec version
name: <string>           # required — the design system / brand name
description: <string>    # optional — one line
colors:
  <token-name>: <Color>
typography:
  <token-name>:
    fontFamily: <string>
    fontSize: <Dimension>
    fontWeight: <number>
    lineHeight: <Dimension | number>
    letterSpacing: <Dimension>   # optional
    fontFeature: <string>        # optional
    fontVariation: <string>      # optional
rounded:
  <scale-level>: <Dimension>     # e.g. sm/md/lg or none/full
spacing:
  <scale-level>: <Dimension | number>
components:
  <component-name>:
    <property>: <string | token reference>
```

### Token value types
- **Color** — any valid CSS color: hex, named, `rgb()/hsl()`, wide-gamut `oklch()/oklab()/lch()/lab()`, or `color-mix()`.
- **Dimension** — number + unit: `px`, `em`, `rem`.
- **Typography** — object with the fields listed above.
- **Token reference** — `{path.to.token}` object-path notation, e.g. `{colors.primary}`, `{spacing.4}`.

### Token rules
- Use **semantic / role-based token names** (`primary`, `surface`, `accent`, `error`, `on-primary`) rather than raw names like `blue-500`.
- References must point to **primitive values** — except *inside* `components`, where a property may reference another token.
- Valid component properties: `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width`.
- Component **variants/states** are separate entries with related naming, e.g. `button-primary`, `button-primary-hover`.

---

## 2. Markdown body — sections IN THIS ORDER

All sections use `##` headings. Every section is optional, but when present it **must appear in this sequence**. Do not duplicate a section heading (that's an error).

1. **## Overview** (alias: *Brand & Style*) — brand personality, emotional tone, aesthetic intent / atmosphere.
2. **## Colors** — the palette and the semantic role of each color; light/dark notes.
3. **## Typography** — type levels (display/heading/body/caption), families, and usage.
4. **## Layout** (alias: *Layout & Spacing*) — spacing strategy, density, grid/container model.
5. **## Elevation & Depth** (alias: *Elevation*) — how hierarchy is conveyed (shadows, layering, blur).
6. **## Shapes** — corner radius scale and overall shape language.
7. **## Components** — guidance for common UI components and their variants/states.
8. **## Do's and Don'ts** — practical rules and pitfalls to avoid.

Prose should use descriptive names that map back to the systematic token names in the front matter.

---

## Minimal shape example

```markdown
---
name: Acme
version: alpha
colors:
  primary: "#3cbbeb"
  on-primary: "#ffffff"
  surface: "#f2f1ee"
  text: "#101010"
typography:
  display:
    fontFamily: Lab Grotesque
    fontSize: 60px
    fontWeight: 400
    lineHeight: 60px
    letterSpacing: -0.6px
  body:
    fontFamily: Lab Grotesque
    fontSize: 16px
    fontWeight: 400
    lineHeight: 24px
rounded:
  sm: 3px
  md: 10px
  lg: 20px
spacing:
  1: 4px
  2: 8px
  4: 16px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.sm}"
    padding: "{spacing.2}"
---

## Overview
Acme feels calm and precise…

## Colors
`primary` (#3cbbeb) drives interactive elements…
```

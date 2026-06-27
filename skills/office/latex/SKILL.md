---
name: latex
description: "LaTeX toolchain: compile .tex projects, diagnose TeX/Tectonic/TeX Live/MacTeX availability, and install a managed TeX Live runtime. Three sub-commands — compile (build/render/regenerate .tex), doctor (check what's installed/working), install (add or repair LaTeX support). Use when the user asks to compile, build, render, or regenerate a .tex file; asks whether LaTeX/Tectonic/TeX Live/MacTeX/latexmk/pdflatex/xelatex/lualatex/biber/kpsewhich are installed or working; or asks to install or repair LaTeX support. Triggers: 'compile tex', 'build latex', 'latex doctor', 'is latex installed', 'install texlive', '编译 latex', '装 latex'."
---

# LaTeX Toolchain

Three sub-commands covering the full LaTeX lifecycle. All scripts run from the plugin root.

## 1. Compile — build/render/regenerate a `.tex`

```bash
python3 scripts/compile_latex.py /absolute/path/to/main.tex
```

Default `auto` mode uses Tectonic first only when the project looks simple enough not to need a full TeX Live toolchain. It falls back to TeX Live or MacTeX when Tectonic fails or when the project uses bibliography, shell-escape, index/glossary, or explicit non-Tectonic engine features.

Common options:

```bash
python3 scripts/compile_latex.py /absolute/path/to/main.tex --compiler tectonic
python3 scripts/compile_latex.py /absolute/path/to/main.tex --compiler texlive
python3 scripts/compile_latex.py /absolute/path/to/main.tex --engine xelatex
python3 scripts/compile_latex.py /absolute/path/to/main.tex --output-directory /absolute/path/to/build
python3 scripts/compile_latex.py /absolute/path/to/main.tex --json
```

### Behavior

- Detects bundled or PATH Tectonic and existing TeX Live or MacTeX.
- Honors a leading `% !TEX root = ...` directive when present.
- Uses `latexmk` for TeX Live builds when available.
- Enables SyncTeX with `-synctex=1` for TeX Live builds.
- Does not install TeX.

If neither Tectonic nor a usable TeX installation is found, stop and route to the **Doctor** or **Install** sections below.

## 2. Doctor — check what's installed/working

Use when the user asks whether LaTeX, Tectonic, TeX Live, MacTeX, `latexmk`, `pdflatex`, `xelatex`, `lualatex`, `biber`, or `kpsewhich` are installed or working.

```bash
python3 scripts/latex_doctor.py
```

For machine-readable output:

```bash
python3 scripts/latex_doctor.py --json
```

### Interpretation

- `ready`: At least one runtime passed a smoke compile. Prefer **Compile** in `auto` mode.
- `existing-usable`: Use the existing TeX installation. Do not install managed TeX Live.
- `existing-partial`: Report the gaps. Do not install managed TeX Live unless the user explicitly asks to replace or bypass the partial installation.
- `missing`: Managed full TeX Live can be offered through the **Install** section below.

### Output Contract

Summarize: detector status; Tectonic path and smoke-test result when available; detected TeX bin directory; `TEXMFROOT` when available; missing required or recommended tools; TeX Live smoke-test result when a compile was attempted.

## 3. Install — add or repair LaTeX support

Use when the user asks to install or repair LaTeX support.

Default behavior is detect-only:

```bash
python3 scripts/install_texlive.py
```

The script exits without installing when it detects an existing TeX Live or MacTeX installation.

### Full Managed Install

Only run the full install after the user explicitly confirms they want to download and run the TeX Live installer. The install is large and can take a long time.

```bash
python3 scripts/install_texlive.py --install-managed-full
```

The managed runtime is installed under:

```text
~/.cache/codex-runtimes/codex-texlive/full
```

The installer does not use `sudo`, does not write `/Library/TeX`, does not write `/usr/local/texlive`, and does not modify shell startup files.

### Force Mode

If an existing TeX installation is partial or broken and the user still wants a separate managed runtime:

```bash
python3 scripts/install_texlive.py --install-managed-full --force-managed
```

Do not use force mode unless the user explicitly asks for it.

### Safety

Running `--install-managed-full` downloads and runs the upstream TeX Live installer. Ask for confirmation immediately before running that command.

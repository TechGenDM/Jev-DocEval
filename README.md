<div align="center">

# 📄 Jev DocEval

**Stop guessing if your docs are "good enough." Grade them automatically.**

Jev DocEval is a local, AI-powered reviewer for your technical documents — API specs, RFCs, onboarding guides, and more. It reads your markdown files and scores them on **Clarity**, **Completeness**, **Actionability**, and **Technical Depth**, so you know exactly what to fix before you ship.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](#running-tests)
[![Runs Locally](https://img.shields.io/badge/runs-100%25%20local-informational.svg)](#-quick-start-web-dashboard)

[Quick Start](#-quick-start-web-dashboard) •
[CLI Usage](#-power-users-cli-usage) •
[Output Formats](#4-output-formats-markdown-csv-json) •
[CI/CD Gating](#5-cicd-quality-gating) •
[Project Structure](#project-structure)

</div>

---

## Why Jev DocEval?

Reading through a 40-page RFC to guess whether it's "documentation-complete" doesn't scale. Jev DocEval automates that judgment call: point it at a markdown file or a whole directory, and it hands back objective, dimension-by-dimension scores plus the exact reasoning behind each one — all running entirely on your own machine.

- 🖥️ **Runs on localhost** — your documents never have to leave your machine's network boundary via the dashboard
- 🎯 **Four-dimension rubric** — Clarity, Completeness, Actionability, Technical Depth, each independently scored on a 0–4 scale
- 🧩 **Presets built-in** — RFC, API spec, and onboarding-guide scoring profiles out of the box
- ⚙️ **CI/CD-ready** — fail a build automatically when documentation quality drops below your bar
- 🚀 **Scales with async concurrency** — evaluate large docsets in parallel

---

## 🚀 Quick Start (Web Dashboard)

The easiest way to use Jev DocEval is through its built-in Web UI.

### 1. Requirements

- **Python 3.10+** installed on your computer
- We recommend [uv](https://docs.astral.sh/uv/getting-started/installation/), a fast Python package manager — standard `pip` also works

### 2. Add your API key

Jev DocEval uses AI to read and grade your documents, so it needs a TypeSafe API key:

1. Copy `.env.example` and rename it to `.env`
2. Open the new `.env` file and paste your API key inside

### 3. Start the tool

```bash
uv run doc-eval --ui
```

> No `uv`? Install the tool first, then run it the same way:
> ```bash
> pip install -e .
> doc-eval --ui
> ```

Open **http://localhost:8000** in your browser and start grading your documents.

---

## 💻 Power Users: CLI Usage

Prefer the terminal, or want to automate documentation checks in CI/CD? Jev DocEval is a full-featured CLI as well.

### 1. Basic evaluation

```bash
# Evaluate all documents in a directory
doc-eval samples/

# Evaluate specific files
doc-eval samples/api-rate-limiting.md samples/onboarding-checklist.md
```

### 2. Presets and custom weights

```bash
# Use the RFC preset
doc-eval samples/api-rate-limiting.md --preset rfc

# Use the Onboarding preset
doc-eval samples/onboarding-checklist.md --preset onboarding

# Custom weights (need not sum to 1)
doc-eval samples/ --weights clarity=0.4,completeness=0.2,actionability=0.3,technical_depth=0.1
```

### 3. Detailed inspection (`--details`)

Inspect the full probability distribution across levels (0–4) and the exact rubric text that was matched:

```bash
doc-eval samples/api-rate-limiting.md --preset api-spec --details
```

**Sample output:**

```text
Document: api-rate-limiting.md (/path/to/samples/api-rate-limiting.md)
Title:    API Rate Limiting Design
Overall:  0.689 (composite)
----------------------------------------------------------------------
  • Clarity          : 3.14 / 4  (Confidence: 0.87, Weight: 0.15)
    Distribution   : [L0: 0% | L1: 0% | L2: 1% | L3: 84% | L4: 15%]
    Primary Level  : Level 3 - "Clear and well-structured: logical section hierarchy, key concepts clearly defined..."
  • Completeness     : 2.48 / 4  (Confidence: 0.58, Weight: 0.35)
    Distribution   : [L0: 0% | L1: 1% | L2: 49% | L3: 50% | L4: 0%]
    Primary Level  : Level 2 - "Partial coverage: core components and happy path described..."
  ...
```

### 4. Output formats (Markdown, CSV, JSON)

```bash
# Markdown table (ready for GitHub PR comments)
doc-eval samples/ --format markdown

# CSV export
doc-eval samples/ --format csv > results.csv

# Full JSON output to stdout
doc-eval samples/ --format json

# Terminal table + save JSON to file
doc-eval samples/ --json results.json
```

### 5. CI/CD quality gating

Enforce documentation quality in git pre-commit hooks or GitHub Actions:

```bash
# Fail (exit code 1) if overall quality is below 0.60
doc-eval docs/ --fail-under 0.60

# Fail if specific dimensions don't meet minimum requirements (0-4 scale)
doc-eval docs/ --min-score clarity=2.5,technical_depth=2.0
```

### 6. High-throughput async concurrency

Batch evaluation runs concurrently over `AsyncTypeSafeClient`. Adjust concurrency with `-c`:

```bash
# Evaluate large docsets with 10 concurrent requests
doc-eval docs/ --concurrency 10
```

---

## Project Structure

```
src/doc_eval/
  cli.py          # CLI entry point, argument parsing, formats & quality gates
  dimensions.py   # 0–4 technical rubrics, presets, and weight composition
  documents.py    # Document loading, frontmatter parsing & state preparation
  evaluate.py     # Sync & Async TypeSafe System One client evaluation
samples/          # Example technical documents for evaluation
tests/            # Automated test suite (dimensions, parser, CLI, quality gates)
```

## Running Tests

```bash
uv run python -m unittest discover tests
```

## Contributing

Issues and pull requests are welcome. If you're proposing a larger change (a new preset, a new output format, a scoring-rubric tweak), consider opening an issue first to discuss the approach.

## License

Released under the [MIT License](LICENSE).
# Jev DocEval

**Jev DocEval** is an internal engineering tool designed to automatically grade and evaluate the quality of your technical documents (like API Specs, RFCs, and Onboarding Guides). 

Instead of reading through long documents to guess if they are "good enough", you simply run this tool. It acts as an automated reviewer that reads your markdown files and scores them on **Clarity**, **Completeness**, **Actionability**, and **Technical Depth**, letting you know exactly what needs improvement.

It runs entirely on your own machine (localhost) and opens a clean, beautiful web dashboard to view the results.

---

## 🚀 Quick Start (Web Dashboard)

The easiest way to use Jev DocEval is through its built-in Web UI.

### 1. Requirements
- You need **Python 3.10+** installed on your computer.
- We recommend installing [uv](https://docs.astral.sh/uv/getting-started/installation/), a fast Python package manager, though standard `pip` works too.

### 2. Add your API Key
Since this tool uses AI to read the documents, you need a TypeSafe API Key.
1. Copy the `.env.example` file and rename it to `.env`.
2. Open the new `.env` file and paste your API key inside.

### 3. Start the Tool
Open your terminal, navigate to this folder, and run:

```bash
uv run doc-eval --ui
```
*(If you don't have `uv`, you can install the tool first with `pip install -e .` and then run `doc-eval --ui`)*

That's it! Open **http://localhost:8000** in your web browser to start grading your documents.

---

## 💻 Power Users: CLI Usage

If you prefer staying in the terminal or want to automate checks in your CI/CD pipeline, Jev DocEval works as a powerful command-line tool.

### 1. Basic Evaluation

```bash
# Evaluate all documents in a directory
doc-eval samples/

# Evaluate specific files
doc-eval samples/api-rate-limiting.md samples/onboarding-checklist.md
```

### 2. Using Presets or Custom Weights

```bash
# Use the RFC preset
doc-eval samples/api-rate-limiting.md --preset rfc

# Use the Onboarding preset
doc-eval samples/onboarding-checklist.md --preset onboarding

# Custom weights (need not sum to 1)
doc-eval samples/ --weights clarity=0.4,completeness=0.2,actionability=0.3,technical_depth=0.1
```

### 3. Detailed Inspection (`--details`)

Inspect the complete probability distribution across levels (0–4) and the exact matching criteria text:

```bash
doc-eval samples/api-rate-limiting.md --preset api-spec --details
```

Output:
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

### 4. Output Formats (Markdown, CSV, JSON)

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

### 5. CI/CD Quality Gating

Enforce documentation quality in git pre-commit hooks or GitHub Actions:

```bash
# Fail (exit code 1) if overall quality is below 0.60
doc-eval docs/ --fail-under 0.60

# Fail if specific dimensions don't meet minimum requirements (0-4 scale)
doc-eval docs/ --min-score clarity=2.5,technical_depth=2.0
```

### 6. High-Throughput Async Concurrency

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

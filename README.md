# doc-eval

CLI to evaluate engineering and technical documents (API specs, RFCs, architecture designs, onboarding guides) across multiple quality dimensions using the **[TypeSafe](https://docs.typesafe.ai) System One API (Jev model)**.

Each document is judged across parallel **Score** questions with calibrated probabilities and confidence ratings, which your code composes into a weighted overall score.

---

## Dimensions

Evaluates technical documentation on four core quality dimensions using descriptive 0–4 level rubrics:

| Dimension | Id | What it measures |
| --- | --- | --- |
| **Clarity** | `clarity` | Structural organization, precise technical definitions, clean code/schema references, and scannability. |
| **Completeness** | `completeness` | Thoroughness across prerequisites, edge cases, system components, error states, and boundaries. |
| **Actionability** | `actionability` | Executable next steps, copy-pasteable commands/code, explicit parameters, and implementation guidance. |
| **Technical Depth** | `technical_depth` | Concrete mechanisms, data structures, failure modes, concurrency, latency/throughput tradeoffs, and architectural rigor. |

Scores are probability-weighted values on a **0–4** scale. The **Overall** score is a weight-normalized composite on a **0.0–1.0** scale.

---

## Weighting Presets

Choose from domain-tailored weighting presets or specify custom weights:

| Preset | Description | Weight Distribution |
| --- | --- | --- |
| `general` *(default)* | Balanced general technical assessment | Clarity: 25%, Completeness: 25%, Actionability: 25%, Technical Depth: 25% |
| `rfc` | Architecture RFCs and system proposals | Technical Depth: 40%, Completeness: 30%, Clarity: 20%, Actionability: 10% |
| `api-spec` | API and interface contracts | Completeness: 35%, Technical Depth: 35%, Clarity: 15%, Actionability: 15% |
| `onboarding` | Developer onboarding guides & runbooks | Actionability: 40%, Clarity: 35%, Completeness: 15%, Technical Depth: 10% |

---

## Installation & Setup

1. Configure your TypeSafe API key in a local `.env` file (or export `TYPESAFE_API_KEY`):

```bash
echo 'TYPESAFE_API_KEY=your_api_key_here' > .env
```

2. Install dependencies with `uv` or `pip`:

```bash
# with uv
uv sync

# or with pip
pip install -e .
```

---

## Usage

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

"""CLI entry point for engineering and technical document evaluation."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from doc_eval.dimensions import (
    DEFAULT_DIMENSIONS,
    Dimension,
    PRESETS,
    dimensions_by_id,
    get_preset_dimensions,
    with_weights,
)
from doc_eval.documents import load_documents
from doc_eval.evaluate import DocumentResult, evaluate_documents

# Load .env from the current working directory if present (never commit secrets).
load_dotenv()


def _parse_weights(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    weights: dict[str, float] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise argparse.ArgumentTypeError(
                f"Invalid weight {part!r}; expected id=float, e.g. clarity=0.4"
            )
        key, value = part.split("=", 1)
        key = key.strip()
        try:
            weights[key] = float(value.strip())
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"Invalid weight value for {key!r}: {value!r}"
            ) from exc
    if not weights:
        raise argparse.ArgumentTypeError("No weights parsed from --weights")
    return weights


def _parse_min_scores(raw: str | None) -> dict[str, float] | None:
    if not raw:
        return None
    min_scores: dict[str, float] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise argparse.ArgumentTypeError(
                f"Invalid min-score {part!r}; expected id=float, e.g. clarity=2.5"
            )
        key, value = part.split("=", 1)
        key = key.strip()
        try:
            min_scores[key] = float(value.strip())
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"Invalid min-score value for {key!r}: {value!r}"
            ) from exc
    return min_scores


def _build_parser() -> argparse.ArgumentParser:
    dim_ids = ", ".join(d.id for d in DEFAULT_DIMENSIONS)
    preset_names = ", ".join(PRESETS.keys())
    parser = argparse.ArgumentParser(
        prog="doc-eval",
        description=(
            "Evaluate technical documents (RFCs, API specs, architecture, onboarding) "
            "on Clarity, Completeness, Actionability, and Technical Depth using TypeSafe System One."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Document files and/or directories containing .md/.txt files (optional if using --ui)",
    )
    parser.add_argument(
        "--ui",
        "--serve",
        action="store_true",
        help="Launch the interactive Web UI in your browser",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the Web UI server (default: 8000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open the browser when launching the Web UI",
    )
    parser.add_argument(
        "-p",
        "--preset",
        choices=tuple(PRESETS.keys()),
        default="general",
        help=f"Dimension weighting preset ({preset_names}; default: general)",
    )
    parser.add_argument(
        "-w",
        "--weights",
        metavar="SPEC",
        help=(
            f"Override dimension weights as id=float pairs (e.g. clarity=0.3,technical_depth=0.4). "
            f"Known ids: {dim_ids}."
        ),
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("table", "markdown", "csv", "json"),
        default="table",
        help="Output format (table, markdown, csv, json; default: table)",
    )
    parser.add_argument(
        "-d",
        "--details",
        action="store_true",
        help="Print detailed score breakdowns, confidence, and probability distributions",
    )
    parser.add_argument(
        "--json",
        metavar="FILE",
        help="Also write full JSON results to FILE (use '-' for stdout JSON)",
    )
    parser.add_argument(
        "--sort",
        choices=("overall", "name", "none"),
        default="overall",
        help="Sort results by overall score (desc), name, or keep input order (default: overall)",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=5,
        help="Maximum concurrent document evaluation requests (default: 5)",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        metavar="THRESHOLD",
        help="Fail (exit 1) if any document's overall score is strictly below this threshold (0.0–1.0)",
    )
    parser.add_argument(
        "--min-score",
        metavar="SPEC",
        help="Fail (exit 1) if any document scores below threshold on specific dimensions (e.g. clarity=2.5,completeness=2.0)",
    )
    return parser


def _format_table(results: list[DocumentResult], dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS) -> str:
    headers = ["Document", *[d.label for d in dimensions], "Overall"]
    rows: list[list[str]] = []
    for result in results:
        row = [result.name]
        for dim in dimensions:
            answer = result.dimensions[dim.id]
            row.append(f"{answer.score:.2f} ({answer.confidence:.2f})")
        row.append(f"{result.overall:.3f}")
        rows.append(row)

    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    lines = [
        fmt(headers),
        "  ".join("-" * w for w in widths),
        *[fmt(row) for row in rows],
        "",
        "Scores are 0–4 (probability-weighted). Values in parentheses are confidence.",
        "Overall is a weight-normalized composite of each dimension's score/4.",
    ]
    return "\n".join(lines)


def _format_markdown(results: list[DocumentResult], dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS) -> str:
    headers = ["Document", *[d.label for d in dimensions], "Overall"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for result in results:
        cols = [f"`{result.name}`"]
        for dim in dimensions:
            ans = result.dimensions[dim.id]
            cols.append(f"{ans.score:.2f} *({ans.confidence:.2f})*")
        cols.append(f"**{result.overall:.3f}**")
        lines.append("| " + " | ".join(cols) + " |")

    lines.append("")
    lines.append("> **Note**: Scores are 0–4 (probability-weighted). Values in parentheses are confidence.")
    lines.append("> Overall is a weight-normalized composite of each dimension's `score / 4`.")
    return "\n".join(lines)


def _format_csv(results: list[DocumentResult], dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS) -> str:
    out = io.StringIO()
    writer = csv.writer(out)

    header = ["Document", "Path", "Overall"]
    for dim in dimensions:
        header.extend([f"{dim.label} Score", f"{dim.label} Confidence", f"{dim.label} Weight"])
    writer.writerow(header)

    for result in results:
        row = [result.name, result.path, f"{result.overall:.4f}"]
        for dim in dimensions:
            ans = result.dimensions[dim.id]
            row.extend([f"{ans.score:.4f}", f"{ans.confidence:.4f}", f"{ans.weight:.4f}"])
        writer.writerow(row)

    return out.getvalue().strip()


def _format_details(results: list[DocumentResult], dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS) -> str:
    dim_map = dimensions_by_id(dimensions)
    lines: list[str] = []

    for r_idx, result in enumerate(results):
        if r_idx > 0:
            lines.append("=" * 70)
        lines.append(f"Document: {result.name} ({result.path})")
        if result.title and result.title != result.name:
            lines.append(f"Title:    {result.title}")
        lines.append(f"Overall:  {result.overall:.3f} (composite)")
        lines.append("-" * 70)

        for dim in dimensions:
            ans = result.dimensions[dim.id]
            dim_def = dim_map[dim.id]
            rounded_level = min(dim_def.max_level, max(0, round(ans.score)))
            matched_criterion = dim_def.criteria[rounded_level]

            lines.append(f"  • {dim.label:<16} : {ans.score:.2f} / {dim_def.max_level}  (Confidence: {ans.confidence:.2f}, Weight: {ans.weight:.2f})")

            # Probability distribution bar if available
            if ans.probabilities:
                prob_parts = [f"L{lvl}: {ans.probabilities.get(lvl, 0.0):.0%}" for lvl in range(dim_def.max_level + 1)]
                lines.append(f"    Distribution   : [{' | '.join(prob_parts)}]")

            lines.append(f"    Primary Level  : Level {rounded_level} - \"{matched_criterion}\"")
        lines.append("")

    return "\n".join(lines)


def _check_quality_gates(
    results: list[DocumentResult],
    fail_under: float | None,
    min_scores: dict[str, float] | None,
) -> list[str]:
    """Check if any document fails overall or dimensional thresholds."""
    violations: list[str] = []

    for res in results:
        if fail_under is not None and res.overall < fail_under:
            violations.append(
                f"Document {res.name!r} scored overall {res.overall:.3f}, below threshold {fail_under:.3f}"
            )

        if min_scores:
            for dim_id, threshold in min_scores.items():
                if dim_id in res.dimensions:
                    actual = res.dimensions[dim_id].score
                    if actual < threshold:
                        violations.append(
                            f"Document {res.name!r} scored {actual:.2f} on {dim_id!r}, below minimum {threshold:.2f}"
                        )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.ui or not args.paths:
        if not args.ui and not args.paths:
            # If no paths provided, show error or prompt to launch UI
            print("No document paths specified. Launching Web UI...\n(Pass document paths to evaluate in terminal, or run with --help)", file=sys.stderr)
        from doc_eval.server import start_server
        httpd = start_server(port=args.port, open_browser=not args.no_browser)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Web UI server...")
        finally:
            httpd.server_close()
        return 0

    try:
        # Resolve dimensions from preset + weight overrides
        dimensions = get_preset_dimensions(args.preset)
        weight_overrides = _parse_weights(args.weights)
        if weight_overrides:
            dimensions = with_weights(weight_overrides, dimensions)

        min_scores = _parse_min_scores(args.min_score)
        if min_scores:
            known_ids = set(dimensions_by_id(dimensions).keys())
            unknown = set(min_scores.keys()) - known_ids
            if unknown:
                raise ValueError(f"Unknown dimension id(s) in --min-score: {', '.join(sorted(unknown))}")

        documents = load_documents(args.paths)
        results = evaluate_documents(documents, dimensions, concurrency=args.concurrency)
    except Exception as exc:  # noqa: BLE001 — surface clean CLI errors
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Sorting
    if args.sort == "overall":
        results = sorted(results, key=lambda r: r.overall, reverse=True)
    elif args.sort == "name":
        results = sorted(results, key=lambda r: r.name.lower())

    payload = {
        "preset": args.preset,
        "dimensions": [
            {
                "id": d.id,
                "label": d.label,
                "weight": d.weight,
                "max_level": d.max_level,
            }
            for d in dimensions
        ],
        "results": [r.to_dict() for r in results],
    }

    # Handle JSON stdout
    if args.format == "json" or args.json == "-":
        print(json.dumps(payload, indent=2))
    elif args.details:
        print(_format_details(results, dimensions))
    elif args.format == "markdown":
        print(_format_markdown(results, dimensions))
    elif args.format == "csv":
        print(_format_csv(results, dimensions))
    else:
        print(_format_table(results, dimensions))

    # Optional JSON file dump
    if args.json and args.json != "-":
        out_path = Path(args.json)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote JSON results to {out_path}", file=sys.stderr)

    # Quality Gate Enforcement
    violations = _check_quality_gates(results, args.fail_under, min_scores)
    if violations:
        print("\n[QUALITY GATE FAILED]", file=sys.stderr)
        for v in violations:
            print(f"  ✖ {v}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for CLI parsing, formatters, and quality gate logic."""

import unittest

from doc_eval.cli import (
    _check_quality_gates,
    _format_csv,
    _format_details,
    _format_markdown,
    _format_table,
    _parse_min_scores,
    _parse_weights,
)
from doc_eval.dimensions import DEFAULT_DIMENSIONS
from doc_eval.evaluate import DimensionResult, DocumentResult


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.mock_dimensions = {
            "clarity": DimensionResult("clarity", "Clarity", 3.5, 0.85, 0.875, 0.25, {0: 0.0, 1: 0.05, 2: 0.1, 3: 0.7, 4: 0.15}),
            "completeness": DimensionResult("completeness", "Completeness", 3.0, 0.80, 0.75, 0.25, {0: 0.0, 1: 0.1, 2: 0.2, 3: 0.6, 4: 0.1}),
            "actionability": DimensionResult("actionability", "Actionability", 3.8, 0.90, 0.95, 0.25, {0: 0.0, 1: 0.0, 2: 0.1, 3: 0.2, 4: 0.7}),
            "technical_depth": DimensionResult("technical_depth", "Technical depth", 2.2, 0.75, 0.55, 0.25, {0: 0.0, 1: 0.2, 2: 0.6, 3: 0.2, 4: 0.0}),
        }
        self.mock_results = [
            DocumentResult(
                path="/path/to/spec.md",
                name="spec.md",
                title="API Spec",
                dimensions=self.mock_dimensions,
                overall=0.781,
            )
        ]

    def test_parse_weights(self):
        self.assertIsNone(_parse_weights(None))
        parsed = _parse_weights("clarity=0.4, technical_depth=0.6")
        self.assertEqual(parsed, {"clarity": 0.4, "technical_depth": 0.6})

    def test_parse_min_scores(self):
        self.assertIsNone(_parse_min_scores(None))
        parsed = _parse_min_scores("clarity=3.0, technical_depth=2.5")
        self.assertEqual(parsed, {"clarity": 3.0, "technical_depth": 2.5})

    def test_format_table(self):
        table_output = _format_table(self.mock_results, DEFAULT_DIMENSIONS)
        self.assertIn("spec.md", table_output)
        self.assertIn("3.50 (0.85)", table_output)
        self.assertIn("0.781", table_output)

    def test_format_markdown(self):
        md_output = _format_markdown(self.mock_results, DEFAULT_DIMENSIONS)
        self.assertIn("| Document | Clarity | Completeness | Actionability | Technical depth | Overall |", md_output)
        self.assertIn("`spec.md`", md_output)
        self.assertIn("**0.781**", md_output)

    def test_format_csv(self):
        csv_output = _format_csv(self.mock_results, DEFAULT_DIMENSIONS)
        self.assertIn("Document,Path,Overall", csv_output)
        self.assertIn("spec.md", csv_output)
        self.assertIn("0.7810", csv_output)

    def test_format_details(self):
        details_output = _format_details(self.mock_results, DEFAULT_DIMENSIONS)
        self.assertIn("Document: spec.md", details_output)
        self.assertIn("Distribution", details_output)
        self.assertIn("Primary Level", details_output)

    def test_quality_gates_pass(self):
        violations = _check_quality_gates(self.mock_results, fail_under=0.70, min_scores={"clarity": 3.0})
        self.assertEqual(len(violations), 0)

    def test_quality_gates_fail(self):
        violations = _check_quality_gates(self.mock_results, fail_under=0.85, min_scores={"technical_depth": 3.0})
        self.assertEqual(len(violations), 2)
        self.assertTrue(any("overall" in v for v in violations))
        self.assertTrue(any("technical_depth" in v for v in violations))

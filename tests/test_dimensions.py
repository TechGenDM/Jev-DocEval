"""Tests for dimension definitions, presets, and weighting."""

import unittest

from doc_eval.dimensions import (
    DEFAULT_DIMENSIONS,
    Dimension,
    PRESETS,
    dimensions_by_id,
    get_preset_dimensions,
    with_weights,
)


class TestDimensions(unittest.TestCase):
    def test_default_dimensions(self):
        self.assertEqual(len(DEFAULT_DIMENSIONS), 4)
        ids = [d.id for d in DEFAULT_DIMENSIONS]
        self.assertEqual(ids, ["clarity", "completeness", "actionability", "technical_depth"])
        for d in DEFAULT_DIMENSIONS:
            self.assertEqual(len(d.criteria), 5)
            self.assertEqual(d.max_level, 4)
            q = d.to_question()
            self.assertEqual(len(q.criteria), 5)

    def test_presets(self):
        for preset_name in ("general", "rfc", "api-spec", "onboarding"):
            dims = get_preset_dimensions(preset_name)
            self.assertEqual(len(dims), 4)
            dim_map = dimensions_by_id(dims)
            preset_weights = PRESETS[preset_name]
            for dim_id, expected_weight in preset_weights.items():
                self.assertAlmostEqual(dim_map[dim_id].weight, expected_weight)

    def test_invalid_preset(self):
        with self.assertRaises(ValueError) as ctx:
            get_preset_dimensions("non-existent")
        self.assertIn("Unknown preset", str(ctx.exception))

    def test_with_weights(self):
        overridden = with_weights({"clarity": 0.8, "technical_depth": 0.2})
        dim_map = dimensions_by_id(overridden)
        self.assertEqual(dim_map["clarity"].weight, 0.8)
        self.assertEqual(dim_map["technical_depth"].weight, 0.2)
        self.assertEqual(dim_map["completeness"].weight, 0.25)

    def test_with_unknown_weight(self):
        with self.assertRaises(ValueError) as ctx:
            with_weights({"non_existent_dim": 0.5})
        self.assertIn("Unknown dimension id", str(ctx.exception))

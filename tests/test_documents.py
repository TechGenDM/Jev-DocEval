"""Tests for document loading and metadata extraction."""

import tempfile
import unittest
from pathlib import Path

from doc_eval.documents import Document, _parse_frontmatter_and_headings, load_documents


class TestDocuments(unittest.TestCase):
    def test_parse_frontmatter_and_headings(self):
        raw = """---
title: System Architecture RFC
type: rfc
author: Platform Team
---

# RFC: Distributed Cache Architecture

## Abstract
This document outlines cache design.

### Invalidation Strategy
Details on invalidation.
"""
        clean_text, title, headings, metadata = _parse_frontmatter_and_headings(raw, "test.md")
        self.assertEqual(title, "System Architecture RFC")
        self.assertEqual(metadata["type"], "rfc")
        self.assertEqual(metadata["author"], "Platform Team")
        self.assertIn("RFC: Distributed Cache Architecture", headings)
        self.assertIn("Abstract", headings)
        self.assertIn("Invalidation Strategy", headings)

    def test_document_as_state(self):
        doc = Document(
            path=Path("/tmp/test.md"),
            text="# Sample Title\nSample text content",
            title="Sample Title",
            word_count=5,
            line_count=2,
            headings=["Sample Title"],
            metadata={"env": "prod"},
        )
        state = doc.as_state()
        self.assertIn("document", state)
        d = state["document"]
        self.assertEqual(d["title"], "Sample Title")
        self.assertEqual(d["name"], "test.md")
        self.assertEqual(d["word_count"], 5)
        self.assertEqual(d["metadata"]["env"], "prod")
        self.assertEqual(d["text"], doc.text)

    def test_load_documents_from_file(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as tmp:
            tmp.write("# Test Doc\nSome technical content here.")
            tmp_path = Path(tmp.name)

        try:
            docs = load_documents([str(tmp_path)])
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0].title, "Test Doc")
            self.assertGreater(docs[0].word_count, 0)
        finally:
            tmp_path.unlink()

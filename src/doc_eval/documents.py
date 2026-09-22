"""Load and parse documents from paths and directories."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

SUPPORTED_SUFFIXES = {".md", ".txt", ".markdown"}


@dataclass(frozen=True)
class Document:
    path: Path
    text: str
    title: str = ""
    word_count: int = 0
    line_count: int = 0
    headings: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.path.name

    def as_state(self) -> dict[str, object]:
        return {
            "document": {
                "path": str(self.path),
                "name": self.name,
                "title": self.title or self.name,
                "word_count": self.word_count,
                "line_count": self.line_count,
                "headings": self.headings,
                "metadata": self.metadata,
                "text": self.text,
            }
        }


def _parse_frontmatter_and_headings(raw_text: str, filename: str) -> tuple[str, str, list[str], dict[str, str]]:
    """Extract YAML frontmatter, document title, and Markdown headings."""
    clean_text = raw_text
    metadata: dict[str, str] = {}
    title = ""

    # Check for YAML frontmatter between leading --- delimiters
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw_text, flags=re.DOTALL)
    if frontmatter_match:
        fm_content = frontmatter_match.group(1)
        for line in fm_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            metadata[key] = val
        if "title" in metadata:
            title = metadata["title"]

    # Extract Markdown headings (# Heading)
    headings: list[str] = []
    for line in raw_text.splitlines():
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
        if heading_match:
            headings.append(heading_match.group(2).strip())
            if not title:
                title = heading_match.group(2).strip()

    if not title:
        title = filename

    return clean_text, title, headings, metadata


def collect_paths(inputs: list[str]) -> list[Path]:
    """Expand file and directory arguments into document paths."""
    found: list[Path] = []
    seen: set[Path] = set()

    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {raw}")

        candidates: list[Path]
        if path.is_dir():
            candidates = sorted(
                p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
            )
            if not candidates:
                raise FileNotFoundError(
                    f"No .md/.txt files under directory: {raw}"
                )
        elif path.is_file():
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                raise ValueError(
                    f"Unsupported file type {path.suffix!r} for {raw}; "
                    f"use one of {', '.join(sorted(SUPPORTED_SUFFIXES))}"
                )
            candidates = [path]
        else:
            raise ValueError(f"Not a file or directory: {raw}")

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.append(resolved)

    return found


def load_documents(inputs: list[str]) -> list[Document]:
    """Load documents from file or directory inputs."""
    docs: list[Document] = []
    for path in collect_paths(inputs):
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"Document is empty: {path}")

        clean_text, title, headings, metadata = _parse_frontmatter_and_headings(text, path.name)
        word_count = len(text.split())
        line_count = len(text.splitlines())

        docs.append(
            Document(
                path=path,
                text=clean_text,
                title=title,
                word_count=word_count,
                line_count=line_count,
                headings=headings,
                metadata=metadata,
            )
        )
    return docs

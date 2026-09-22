"""Evaluate documents with TypeSafe Score questions."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass

from typesafe_sdk import AsyncTypeSafeClient, TypeSafeClient

from doc_eval.dimensions import DEFAULT_DIMENSIONS, Dimension
from doc_eval.documents import Document


@dataclass(frozen=True)
class DimensionResult:
    id: str
    label: str
    score: float
    confidence: float
    normalized: float
    weight: float
    probabilities: dict[int, float]


@dataclass(frozen=True)
class DocumentResult:
    path: str
    name: str
    title: str
    dimensions: dict[str, DimensionResult]
    overall: float
    usage_tokens: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "name": self.name,
            "title": self.title,
            "overall": self.overall,
            "usage_tokens": self.usage_tokens,
            "dimensions": {
                dim_id: asdict(result) for dim_id, result in self.dimensions.items()
            },
        }


def _questions(dimensions: tuple[Dimension, ...]) -> dict:
    return {d.id: d.to_question() for d in dimensions}


def _composite(dimensions: tuple[Dimension, ...], scores: dict[str, DimensionResult]) -> float:
    total_weight = sum(d.weight for d in dimensions)
    if total_weight <= 0:
        raise ValueError("Dimension weights must sum to a positive number")
    return sum(scores[d.id].normalized * d.weight for d in dimensions) / total_weight


def _parse_dimension_results(
    dimensions: tuple[Dimension, ...], response
) -> tuple[dict[str, DimensionResult], int | None]:
    dim_results: dict[str, DimensionResult] = {}
    for dim in dimensions:
        answer = response.answers[dim.id]
        if answer.type != "score":
            raise TypeError(f"Expected score answer for {dim.id!r}, got {answer.type!r}")
        raw = float(answer.score)

        # Convert probabilities dict keys to int
        raw_probs = getattr(answer, "probabilities", None) or {}
        probs: dict[int, float] = {int(k): float(v) for k, v in raw_probs.items()}

        dim_results[dim.id] = DimensionResult(
            id=dim.id,
            label=dim.label,
            score=raw,
            confidence=float(answer.confidence),
            normalized=raw / dim.max_level,
            weight=dim.weight,
            probabilities=probs,
        )

    usage_tokens: int | None = None
    usage = getattr(response, "usage", None)
    if usage and (usage.input_tokens is not None or usage.output_tokens is not None):
        usage_tokens = (usage.input_tokens or 0) + (usage.output_tokens or 0)

    return dim_results, usage_tokens


def evaluate_document(
    client: TypeSafeClient,
    document: Document,
    dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS,
) -> DocumentResult:
    """Synchronously evaluate a single document."""
    response = client.system_one(
        state=document.as_state(),
        questions=_questions(dimensions),
    )
    dim_results, usage_tokens = _parse_dimension_results(dimensions, response)

    return DocumentResult(
        path=str(document.path),
        name=document.name,
        title=document.title or document.name,
        dimensions=dim_results,
        overall=_composite(dimensions, dim_results),
        usage_tokens=usage_tokens,
    )


async def evaluate_document_async(
    client: AsyncTypeSafeClient,
    document: Document,
    dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS,
) -> DocumentResult:
    """Asynchronously evaluate a single document."""
    response = await client.system_one(
        state=document.as_state(),
        questions=_questions(dimensions),
    )
    dim_results, usage_tokens = _parse_dimension_results(dimensions, response)

    return DocumentResult(
        path=str(document.path),
        name=document.name,
        title=document.title or document.name,
        dimensions=dim_results,
        overall=_composite(dimensions, dim_results),
        usage_tokens=usage_tokens,
    )


async def evaluate_documents_async(
    documents: list[Document],
    dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS,
    concurrency: int = 5,
) -> list[DocumentResult]:
    """Evaluate multiple documents concurrently using AsyncTypeSafeClient."""
    sem = asyncio.Semaphore(max(1, concurrency))

    async with AsyncTypeSafeClient() as client:
        async def _eval(doc: Document) -> DocumentResult:
            async with sem:
                return await evaluate_document_async(client, doc, dimensions)

        tasks = [_eval(doc) for doc in documents]
        return await asyncio.gather(*tasks)


def evaluate_documents(
    documents: list[Document],
    dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS,
    concurrency: int = 5,
) -> list[DocumentResult]:
    """Evaluate multiple documents, executing concurrently via asyncio."""
    if not documents:
        return []
    return asyncio.run(
        evaluate_documents_async(documents, dimensions, concurrency=concurrency)
    )

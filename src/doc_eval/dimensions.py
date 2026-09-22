"""Score dimensions for technical and engineering document evaluation.

Each dimension is a TypeSafe Score with five ordered levels (0–4).
Levels describe concrete technical situations so judgments stay comparable
across documents (RFCs, API specifications, system architecture designs, onboarding guides).
"""

from __future__ import annotations

from dataclasses import dataclass

from typesafe_sdk import Score


@dataclass(frozen=True)
class Dimension:
    id: str
    label: str
    weight: float
    instructions: str
    criteria: tuple[str, ...]

    def to_question(self) -> Score:
        return Score(instructions=self.instructions, criteria=list(self.criteria))

    @property
    def max_level(self) -> int:
        return len(self.criteria) - 1


# Default base dimensions for engineering & technical documentation.
DEFAULT_DIMENSIONS: tuple[Dimension, ...] = (
    Dimension(
        id="clarity",
        label="Clarity",
        weight=0.25,
        instructions=(
            "How clear, coherent, and well-structured is this technical document "
            "for an engineering reader? Evaluate organization, terminology definitions, "
            "and readability of `document.text`, not agreement with the content."
        ),
        criteria=(
            "Opaque or confusing: heavy undefined jargon, contradictory statements, "
            "tangled flow, or no coherent narrative.",
            "Difficult to follow: main point exists but is buried in disorganized thoughts, "
            "ambiguous terminology, or dense walls of text.",
            "Moderately clear: an engineer can follow the intent, but encounters occasional "
            "ambiguity, awkward transitions, or missing explanations for key terms.",
            "Clear and well-structured: logical section hierarchy, key concepts clearly defined, "
            "clean code/schema references, and easy to skim.",
            "Crystal clear: razor-sharp phrasing, rigorous structure, diagrams/tables/code snippets "
            "used effectively, with zero ambiguity on what each section conveys.",
        ),
    ),
    Dimension(
        id="completeness",
        label="Completeness",
        weight=0.25,
        instructions=(
            "How thoroughly does this document cover its apparent technical purpose "
            "(e.g., API spec, RFC, system design, guide, or runbook)? Evaluate whether all "
            "essential prerequisites, edge cases, system components, and boundaries are documented in `document.text`."
        ),
        criteria=(
            "Severely incomplete: missing almost all essential context, requirements, or architecture "
            "needed to understand or work with the system.",
            "Large gaps: covers introductory concepts but omits critical sections (e.g., schemas, "
            "error handling, auth, or boundary constraints).",
            "Partial coverage: core components and happy path described, but edge cases, failure scenarios, "
            "or operational prerequisites are omitted.",
            "Mostly complete: covers technical scope thoroughly with only minor gaps or secondary questions left unanswered.",
            "Thorough and comprehensive: complete lifecycle covered (assumptions, constraints, schemas/APIs, "
            "error states, rollback, and security/scale considerations).",
        ),
    ),
    Dimension(
        id="actionability",
        label="Actionability",
        weight=0.25,
        instructions=(
            "How actionable is this document for an engineer or technical practitioner? "
            "Judge whether a reader can take concrete next steps, execute commands, implement "
            "an interface, or make architectural decisions directly from `document.text`."
        ),
        criteria=(
            "Non-actionable: abstract commentary or vague musings with no actionable decisions, "
            "steps, interfaces, or owners.",
            "Weakly actionable: identifies a direction or goal, but lacks concrete commands, code examples, "
            "or specific implementation instructions.",
            "Moderately actionable: includes some concrete steps or endpoints, but leaves critical execution details "
            "(environment setup, parameters, sequencing, or validation) to guesswork.",
            "Actionable: provides clear steps, configuration parameters, code samples, or decision records "
            "that an engineer can follow with minimal friction.",
            "Highly actionable: battle-ready walkthrough or spec with copy-pasteable commands/code, "
            "explicit inputs/outputs, troubleshooting guidance, and testable verification criteria.",
        ),
    ),
    Dimension(
        id="technical_depth",
        label="Technical depth",
        weight=0.25,
        instructions=(
            "How much useful technical substance does this document provide? "
            "Judge mechanisms, data structures, protocol interactions, failure modes, "
            "and performance/system tradeoffs in `document.text`, rather than buzzwords or length alone."
        ),
        criteria=(
            "No technical substance: superficial claims, buzzwords, or marketing tone with no architecture or mechanics.",
            "Shallow: mentions technical keywords or tools without explaining how they interact, data flows, or protocol specifics.",
            "Moderate depth: explains component roles and data flow, but avoids addressing performance, scaling, "
            "concurrency, failure modes, or architectural tradeoffs.",
            "Deep: explains underlying mechanisms, contracts, constraints, state transitions, and tradeoffs with enough rigor "
            "for an engineer to critique and implement.",
            "Very deep: rigorous architectural breakdown with failure recovery semantics, latency/throughput tradeoffs, "
            "concurrency models, and concrete edge-case analysis.",
        ),
    ),
)


# Presets tailored to specific engineering documentation artifacts.
PRESETS: dict[str, dict[str, float]] = {
    "general": {
        "clarity": 0.25,
        "completeness": 0.25,
        "actionability": 0.25,
        "technical_depth": 0.25,
    },
    "rfc": {
        "technical_depth": 0.40,
        "completeness": 0.30,
        "clarity": 0.20,
        "actionability": 0.10,
    },
    "api-spec": {
        "completeness": 0.35,
        "technical_depth": 0.35,
        "clarity": 0.15,
        "actionability": 0.15,
    },
    "onboarding": {
        "actionability": 0.40,
        "clarity": 0.35,
        "completeness": 0.15,
        "technical_depth": 0.10,
    },
}


def dimensions_by_id(dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS) -> dict[str, Dimension]:
    return {d.id: d for d in dimensions}


def with_weights(
    weights: dict[str, float],
    dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS,
) -> tuple[Dimension, ...]:
    """Return dimensions with overridden weights. Weights need not sum to 1."""
    known = dimensions_by_id(dimensions)
    unknown = set(weights) - set(known)
    if unknown:
        raise ValueError(f"Unknown dimension id(s): {', '.join(sorted(unknown))}")
    return tuple(
        Dimension(
            id=d.id,
            label=d.label,
            weight=weights.get(d.id, d.weight),
            instructions=d.instructions,
            criteria=d.criteria,
        )
        for d in dimensions
    )


def get_preset_dimensions(
    preset_name: str,
    dimensions: tuple[Dimension, ...] = DEFAULT_DIMENSIONS,
) -> tuple[Dimension, ...]:
    """Return dimensions configured with weights from a named preset."""
    preset = PRESETS.get(preset_name.lower())
    if preset is None:
        valid = ", ".join(sorted(PRESETS.keys()))
        raise ValueError(f"Unknown preset {preset_name!r}. Available presets: {valid}")
    return with_weights(preset, dimensions)

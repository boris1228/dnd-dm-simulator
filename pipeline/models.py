"""Shared dataclasses and type aliases for the SD pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

SceneType = Literal["character", "battlemap", "cover", "regional_map"]

SCENE_TYPES: tuple[SceneType, ...] = (
    "character",
    "battlemap",
    "cover",
    "regional_map",
)


@dataclass(frozen=True)
class GenerateRequest:
    scene_type: SceneType
    description_zh: str
    english_tags: str | None = None
    needs_grid: bool = False
    seed: int = -1


@dataclass
class GenerateResult:
    image_path: Path
    markdown: str
    english_tags: str
    payload: dict
    generation_time_ms: int
    relative_path: str = field(default="")


class PipelineError(Exception):
    """Base exception for SD pipeline failures."""


class ForgeConnectionError(PipelineError):
    """Forge WebUI is unreachable or failed health check."""


class ForgeGenerationError(PipelineError):
    """Forge txt2img request failed."""


class PromptExtractionError(PipelineError):
    """LLM tag extraction failed."""

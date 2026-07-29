"""D&D Stable Diffusion image generation pipeline."""

from pipeline.models import (
    ForgeConnectionError,
    ForgeGenerationError,
    GenerateRequest,
    GenerateResult,
    PipelineError,
    PromptExtractionError,
    SceneType,
)

__all__ = [
    "ForgeConnectionError",
    "ForgeGenerationError",
    "GenerateRequest",
    "GenerateResult",
    "PipelineError",
    "PromptExtractionError",
    "SceneType",
    "generate_image",
    "generate_image_sync",
]


def __getattr__(name: str):
    """Lazy import to avoid runpy warning when executing python -m pipeline.sd_pipeline."""
    if name == "generate_image":
        from pipeline.sd_pipeline import generate_image

        return generate_image
    if name == "generate_image_sync":
        from pipeline.sd_pipeline import generate_image_sync

        return generate_image_sync
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

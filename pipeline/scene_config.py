"""Scene-type routing and SD parameter defaults (source: sd-pipeline.mdc)."""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.models import SceneType

# Forge checkpoint switching can take 5–15 s; added to per-scene generation timeouts.
CHECKPOINT_SWITCH_OVERHEAD_S: float = 15.0


@dataclass(frozen=True)
class SceneConfig:
    checkpoint: str
    sampler_name: str
    steps: int
    cfg_scale: float
    width: int
    height: int
    positive_template: str
    negative_template: str
    vae: str | None = None
    lora_suffix: str | None = None
    # Generation timeout excluding checkpoint overhead (seconds).
    base_timeout_s: float = 120.0


SCENE_CONFIGS: dict[SceneType, SceneConfig] = {
    "character": SceneConfig(
        checkpoint="DreamShaper_8_LCM.safetensors",
        sampler_name="LCM",
        steps=8,
        cfg_scale=2.0,
        width=512,
        height=768,
        positive_template=(
            "(masterpiece, top quality:1.2), DD_Painterly, official D&D illustration style, "
            "painterly texture, {description}"
        ),
        negative_template=(
            "(worst quality, low quality:1.4), 3d render, smooth skin, plastic, modern clothing, "
            "ugly, lowres, watermark"
        ),
        lora_suffix="<lora:DD_Painterly:1>",
        base_timeout_s=30.0,
    ),
    "battlemap": SceneConfig(
        checkpoint="dndMapGenerator_v3.safetensors",
        sampler_name="DPM++ 2M Karras",
        steps=20,
        cfg_scale=7.0,
        width=768,
        height=768,
        positive_template="2d dnd battlemap, top-down view, {grid_keywords} {description}",
        negative_template=(
            "{grid_negative}3d, perspective, isometric, characters, people, monsters, text, "
            "watermark, (worst quality, low quality:1.4), blurry"
        ),
        base_timeout_s=120.0,
    ),
    "cover": SceneConfig(
        checkpoint="dndCoverArt_v10_SD1.safetensors",
        sampler_name="DPM++ 2M Karras",
        steps=20,
        cfg_scale=7.0,
        width=512,
        height=768,
        positive_template=(
            "dnd cover art, book cover illustration, official D&D style, epic cinematic fantasy, "
            "{description}"
        ),
        negative_template=(
            "text, title, logo, watermark, typography, signature, words, "
            "(worst quality, low quality:1.4), 3d render"
        ),
        vae="vae-ft-mse-840000-ema-pruned.vae.pt",
        base_timeout_s=120.0,
    ),
    "regional_map": SceneConfig(
        checkpoint="dndCoverArt_v10_SD1.safetensors",
        sampler_name="DPM++ 2M Karras",
        steps=20,
        cfg_scale=7.0,
        width=768,
        height=512,
        positive_template=(
            "dnd cover art, 2d dnd map, fantasy regional map, top-down view, aged parchment style, "
            "cartography style, detailed terrain, {description}"
        ),
        negative_template="text, title, logo, watermark, signature, 3d render, photo, low quality",
        vae="vae-ft-mse-840000-ema-pruned.vae.pt",
        base_timeout_s=120.0,
    ),
}


def timeout_for(scene_type: SceneType) -> float:
    """Total httpx timeout including VRAM checkpoint-switch overhead."""
    cfg = SCENE_CONFIGS[scene_type]
    return cfg.base_timeout_s + CHECKPOINT_SWITCH_OVERHEAD_S

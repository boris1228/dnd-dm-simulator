"""Build Forge txt2img payloads from scene config and English tags."""

from __future__ import annotations

import copy

from pipeline.models import SceneType
from pipeline.scene_config import SCENE_CONFIGS


def _base_payload(cfg_dict: dict) -> dict:
    """Return a deep copy of a base payload template to prevent mutation bleed."""
    return copy.deepcopy(cfg_dict)


def build_sd_payload(
    scene_type: SceneType,
    description: str,
    needs_grid: bool = False,
    seed: int = -1,
) -> dict:
    """Assemble a Forge /sdapi/v1/txt2img JSON body for the given scene type."""
    cfg = SCENE_CONFIGS[scene_type]

    override_settings: dict[str, str] = {"sd_model_checkpoint": cfg.checkpoint}
    if cfg.vae:
        override_settings["sd_vae"] = cfg.vae

    if scene_type == "battlemap":
        grid_keywords = "square grid, gridded battlemap," if needs_grid else "gridless,"
        grid_negative = "" if needs_grid else "grid, hex grid, "
        positive = cfg.positive_template.format(
            grid_keywords=grid_keywords,
            description=description,
        )
        negative = cfg.negative_template.format(grid_negative=grid_negative)
    else:
        positive = cfg.positive_template.format(description=description)
        negative = cfg.negative_template

    if cfg.lora_suffix:
        positive = f"{positive}, {cfg.lora_suffix}"

    payload = _base_payload(
        {
            "override_settings": override_settings,
            "sampler_name": cfg.sampler_name,
            "steps": cfg.steps,
            "cfg_scale": cfg.cfg_scale,
            "width": cfg.width,
            "height": cfg.height,
            "prompt": positive,
            "negative_prompt": negative,
            "batch_size": 1,
            "n_iter": 1,
        }
    )

    if seed != -1:
        payload["seed"] = seed

    return payload

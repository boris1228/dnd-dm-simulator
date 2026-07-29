"""Save generated images and produce markdown links."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from pipeline.models import SceneType
from pipeline.paths import CAMPAIGN_ROOT, DEFAULT_OUTPUT_DIR

logger = logging.getLogger(__name__)

_ALNUM_RE = re.compile(r"[^a-zA-Z0-9]")


def get_output_dir() -> Path:
    """Resolve output directory — always under Campaign root."""
    import os

    env_dir = os.environ.get("OUTPUT_DIR", "")
    if env_dir:
        path = Path(env_dir)
        if not path.is_absolute():
            path = CAMPAIGN_ROOT / path
    else:
        path = DEFAULT_OUTPUT_DIR

    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize_alnum(value: str) -> str:
    """Keep alphanumeric characters only for safe filenames."""
    return _ALNUM_RE.sub("", value)


def _short_hash(text: str) -> str:
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return _sanitize_alnum(digest[:6])


def save_image(png_bytes: bytes, scene_type: SceneType, tags: str) -> tuple[Path, str]:
    """Write PNG to generated_images/ and return (absolute_path, relative_path)."""
    output_dir = get_output_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_scene = _sanitize_alnum(scene_type)
    tag_hash = _short_hash(tags)
    filename = f"{timestamp}_{safe_scene}_{tag_hash}.png"

    abs_path = output_dir / filename
    abs_path.write_bytes(png_bytes)

    rel_path = abs_path.relative_to(CAMPAIGN_ROOT).as_posix()
    logger.info("Saved image to %s", rel_path)
    return abs_path, rel_path


def to_markdown(relative_path: str, alt: str = "scene") -> str:
    """Build a markdown image link using a Campaign-root-relative path."""
    return f"![{alt}]({relative_path})"

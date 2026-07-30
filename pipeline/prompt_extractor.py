"""Extract English SD prompt tags from Chinese DM scene descriptions via LLM."""

from __future__ import annotations

import json
import logging
import os
import re

import httpx

from pipeline.models import PromptExtractionError, SceneType

logger = logging.getLogger(__name__)

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
# Strip markdown fences, quotes wrappers, and common conversational prefixes.
_FILLER_RE = re.compile(
    r"^(?:here(?:'s| is)?|sure|certainly|of course|the tags are|tags)\s*:?\s*",
    re.IGNORECASE,
)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)

_SYSTEM_PROMPT = """You convert D&D scene descriptions into Stable Diffusion prompt tags.

Rules:
- Output ONLY valid JSON: {"tags": "comma-separated English visual tags"}
- English only in the tags value.
- Include: subject, appearance, pose, environment, lighting, mood, art-relevant props.
- Exclude: dialogue, game mechanics, meta commentary, player intent.
- Max ~80 tokens of tags. No full sentences.
- No markdown, no explanation, no conversational filler."""

_SCENE_HINTS: dict[SceneType, str] = {
    "character": "Focus on character portrait elements: appearance, clothing, pose, expression.",
    "battlemap": "Focus on room/terrain layout, furniture, walls, doors — no character portraits.",
    "cover": "Focus on epic cinematic composition, dramatic lighting, scale.",
    "regional_map": "Focus on terrain features, rivers, forests, mountains, cartography style.",
}


def _is_mostly_english(text: str) -> bool:
    cjk_count = len(_CJK_RE.findall(text))
    return cjk_count / max(len(text), 1) < 0.10


def _clean_tags(raw: str) -> str:
    """Strip conversational filler and normalize tag string."""
    text = raw.strip()
    text = _JSON_BLOCK_RE.sub(r"\1", text).strip()
    text = text.strip("\"'`")
    text = _FILLER_RE.sub("", text).strip()
    # Remove leading punctuation left after filler stripping (e.g. "Here is: tags").
    text = re.sub(r"^[:;,\-\s]+", "", text).strip()
    # Remove any leading/trailing JSON artifact fragments.
    text = re.sub(r'^[\{\["\']+|[\}\]"\'\.,]+$', "", text).strip()
    # Collapse whitespace around commas.
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r",+", ",", text)
    return text.strip(", ")


def _parse_tags_from_response(content: str) -> str:
    """Parse tags from JSON-mode or free-text LLM response."""
    content = content.strip()
    if not content:
        raise PromptExtractionError("LLM returned empty response")

    # Try JSON parse first (JSON mode or model compliance).
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "tags" in data:
            tags = _clean_tags(str(data["tags"]))
            if tags:
                return tags
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON object embedded in text.
    match = re.search(r'\{[^{}]*"tags"\s*:\s*"([^"]+)"[^{}]*\}', content, re.DOTALL)
    if match:
        tags = _clean_tags(match.group(1))
        if tags:
            return tags

    # Last resort: treat entire response as tag string after cleanup.
    tags = _clean_tags(content)
    if tags:
        return tags

    raise PromptExtractionError(f"Could not extract tags from LLM response: {content[:200]!r}")


async def extract_tags(description: str, scene_type: SceneType) -> str:
    """Convert a Chinese (or English) scene description into comma-separated SD tags."""
    if _is_mostly_english(description):
        logger.info("Input appears to be English; skipping LLM translation")
        return _clean_tags(description)

    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    if not base_url:
        raise PromptExtractionError(
            "LLM_BASE_URL is not set. Provide --english-tags or configure LLM_BASE_URL."
        )

    # 1. 防呆纠错：如果 base_url 包含了 /chat/completions，先剥离掉
    if base_url.endswith("/chat/completions"):
        base_url = base_url[:-17].rstrip("/")

    # 2. 修改默认模型为 Gemini 2.0/1.5 Flash，并防呆移除 "models/" 前缀
    raw_model = os.environ.get("LLM_MODEL", "gemini-2.0-flash")
    model = raw_model.replace("models/", "")

    api_key = os.environ.get("LLM_API_KEY", "")
    scene_hint = _SCENE_HINTS.get(scene_type, "")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Scene type: {scene_type}. {scene_hint}\n\nDescription:\n{description}",
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    url = f"{base_url}/chat/completions"
    logger.info("Extracting SD tags via LLM (%s) at %s", model, url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise PromptExtractionError(f"LLM request failed: {exc}") from exc

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise PromptExtractionError(f"Unexpected LLM response shape: {data!r}") from exc

    tags = _parse_tags_from_response(content)
    logger.info("Extracted tags: %s", tags)
    return tags
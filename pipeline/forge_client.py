"""Async client for Stable Diffusion Forge WebUI API."""

from __future__ import annotations

import asyncio
import base64
import logging
import os

import httpx

from pipeline.models import ForgeConnectionError, ForgeGenerationError

logger = logging.getLogger(__name__)

DEFAULT_FORGE_BASE_URL = "http://127.0.0.1:7860"
HEALTH_CHECK_TIMEOUT_S = 5.0
_RETRY_BACKOFF_S = 2.0


def _base_url() -> str:
    return os.environ.get("FORGE_BASE_URL", DEFAULT_FORGE_BASE_URL).rstrip("/")


async def check_forge_health() -> None:
    """Mandatory pre-flight ping — fail fast if Forge is not running."""
    url = f"{_base_url()}/sdapi/v1/sd-models"
    logger.info("Checking Forge health at %s", url)

    async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT_S) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ForgeConnectionError(
                f"Forge is not reachable at {_base_url()}. "
                "Start Forge WebUI and verify FORGE_BASE_URL."
            ) from exc

    logger.info("Forge health check passed")


async def txt2img(payload: dict, *, timeout: float) -> bytes:
    """POST to /sdapi/v1/txt2img and return decoded PNG bytes."""
    url = f"{_base_url()}/sdapi/v1/txt2img"
    logger.info("Sending txt2img request (timeout=%.0fs)", timeout)

    last_error: Exception | None = None
    for attempt in range(2):
        if attempt > 0:
            logger.warning("Retrying txt2img after %ss backoff", _RETRY_BACKOFF_S)
            await asyncio.sleep(_RETRY_BACKOFF_S)

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            except httpx.ConnectError as exc:
                last_error = exc
                continue
            except httpx.ReadTimeout as exc:
                last_error = exc
                continue
            except httpx.HTTPStatusError as exc:
                body_snippet = exc.response.text[:300]
                raise ForgeGenerationError(
                    f"Forge returned HTTP {exc.response.status_code}: {body_snippet}"
                ) from exc
            except httpx.HTTPError as exc:
                raise ForgeGenerationError(f"Forge txt2img request failed: {exc}") from exc

            data = resp.json()
            try:
                return base64.b64decode(data["images"][0])
            except (KeyError, IndexError, TypeError) as exc:
                raise ForgeGenerationError(
                    f"Unexpected Forge response shape: {list(data.keys())}"
                ) from exc

    raise ForgeGenerationError(f"Forge txt2img failed after retry: {last_error}")

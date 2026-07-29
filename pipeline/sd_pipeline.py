"""SD pipeline orchestrator, public API, and CLI entry point."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from pipeline.forge_client import check_forge_health, txt2img
from pipeline.image_store import save_image, to_markdown
from pipeline.models import (
    GenerateRequest,
    GenerateResult,
    PipelineError,
    SCENE_TYPES,
    SceneType,
)
from pipeline.payload_builder import build_sd_payload
from pipeline.prompt_extractor import extract_tags
from pipeline.scene_config import timeout_for

# Load .env from Campaign root before reading env vars.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _configure_logging(verbose: bool = False) -> None:
    """Route all logging to stderr — stdout is reserved for JSON output."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def generate_image(request: GenerateRequest) -> GenerateResult:
    """Full pipeline: Forge health check → tag extraction → txt2img → save."""
    log = logging.getLogger(__name__)
    t0 = time.perf_counter()

    # Mandatory health check BEFORE spending LLM tokens.
    await check_forge_health()

    if request.english_tags:
        tags = request.english_tags.strip()
        log.info("Using pre-supplied English tags")
    else:
        tags = await extract_tags(request.description_zh, request.scene_type)

    payload = build_sd_payload(
        request.scene_type,
        tags,
        needs_grid=request.needs_grid,
        seed=request.seed,
    )

    png_bytes = await txt2img(payload, timeout=timeout_for(request.scene_type))
    abs_path, rel_path = save_image(png_bytes, request.scene_type, tags)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return GenerateResult(
        image_path=abs_path,
        relative_path=rel_path,
        markdown=to_markdown(rel_path),
        english_tags=tags,
        payload=payload,
        generation_time_ms=elapsed_ms,
    )


def generate_image_sync(request: GenerateRequest) -> GenerateResult:
    """Synchronous wrapper around generate_image for CLI and simple callers."""
    return asyncio.run(generate_image(request))


def _result_to_json(result: GenerateResult) -> str:
    return json.dumps(
        {
            "image_path": result.relative_path,
            "absolute_path": str(result.image_path),
            "markdown": result.markdown,
            "english_tags": result.english_tags,
            "generation_time_ms": result.generation_time_ms,
            "payload": result.payload,
        },
        ensure_ascii=False,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate D&D scene images via Stable Diffusion Forge API",
    )
    parser.add_argument(
        "scene_type",
        choices=SCENE_TYPES,
        help="Scene routing key (character, battlemap, cover, regional_map)",
    )
    parser.add_argument(
        "description",
        nargs="?",
        default="",
        help="Chinese (or English) scene description for tag extraction",
    )
    parser.add_argument(
        "--english-tags",
        dest="english_tags",
        default=None,
        help="Skip LLM extraction; use these English tags directly",
    )
    parser.add_argument(
        "--grid",
        action="store_true",
        help="Generate battlemap with square grid (battlemap scene only)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=-1,
        help="Fixed seed (-1 for random)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging on stderr",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Writes JSON to stdout; logs go to stderr."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(verbose=args.verbose)

    if not args.english_tags and not args.description:
        parser.error("Provide a description or --english-tags")

    request = GenerateRequest(
        scene_type=args.scene_type,
        description_zh=args.description,
        english_tags=args.english_tags,
        needs_grid=args.grid,
        seed=args.seed,
    )

    try:
        result = generate_image_sync(request)
    except PipelineError as exc:
        logging.getLogger(__name__).error("%s", exc)
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 2
    except Exception as exc:
        logging.getLogger(__name__).exception("Unexpected error")
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}), file=sys.stderr)
        return 1

    # stdout: JSON only — no logging, no print debug.
    sys.stdout.write(_result_to_json(result))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

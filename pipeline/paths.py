"""Campaign root and output directory resolution."""

from pathlib import Path

# pipeline/ lives at Campaign/pipeline/ — parent.parent is the Campaign root.
CAMPAIGN_ROOT: Path = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR: Path = CAMPAIGN_ROOT / "generated_images"

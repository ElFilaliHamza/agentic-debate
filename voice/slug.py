"""Motion-to-slug utility for naming debate audio directories."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def motion_to_slug(motion: str, max_length: int = 50) -> str:
    """Convert a debate motion into a filesystem-safe slug.

    Args:
        motion: The debate motion text.
        max_length: Maximum slug length (default 50).

    Returns:
        A lowercase, hyphenated slug derived from the motion.
        Returns "debate" for empty or whitespace-only input.
    """
    slug = motion.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    slug = slug[:max_length].rstrip("-")

    return slug or "debate"


def create_debate_dir(motion: str, base_dir: Path | None = None) -> Path:
    """Create a per-debate directory under base_dir for saving audio files.

    Args:
        motion: The debate motion text (used to derive directory name).
        base_dir: Parent directory. Defaults to ``audio_data`` in the
                  current working directory.

    Returns:
        Path to the created directory, e.g.
        ``audio_data/2026-06-25_ai-should-replace-teachers/``
    """
    if base_dir is None:
        base_dir = Path("audio_data")

    slug = motion_to_slug(motion)
    today = date.today().isoformat()
    dir_name = f"{today}_{slug}"
    debate_dir = base_dir / dir_name
    debate_dir.mkdir(parents=True, exist_ok=True)

    return debate_dir
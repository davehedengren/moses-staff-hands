"""Gemini-powered art generation with on-disk caching."""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image

import config

_ProgressFn = Callable[[str], None]


def _ensure_dir() -> None:
    config.ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _save_image_from_response(response, out_path: Path) -> bool:
    """Extract the first inline image from a google-genai response and save it."""
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        if content is None:
            continue
        for part in getattr(content, "parts", []) or []:
            inline = getattr(part, "inline_data", None)
            if inline is None:
                continue
            data = getattr(inline, "data", None)
            if not data:
                continue
            img = Image.open(io.BytesIO(data))
            img.save(out_path)
            return True
    return False


# Sprites that should have a transparent background. Kept in one place so the
# post-processing step knows which files to chroma-key.
_TRANSPARENT_SPRITES = {
    "israelite.png",
    "amalekite.png",
    "moses_icon.png",
    "victory_israel.png",
    "victory_amalek.png",
}


def _force_transparency_if_opaque(path: Path) -> None:
    """Chroma-key a solid background to alpha=0 when the generator ignored
    the transparency request.

    Strategy: if the image has very little existing transparency AND all four
    corners agree on a background color, flood any pixel within euclidean
    color distance 45 of that color to transparent. If the corners disagree,
    assume it's an intentional scene and leave it alone.
    """
    img = Image.open(path).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]

    # Already has meaningful transparency? Nothing to do.
    if (alpha < 10).mean() > 0.02:
        return

    h, w = arr.shape[:2]
    patch = max(8, min(40, h // 12, w // 12))
    corners = [
        arr[:patch, :patch, :3],
        arr[:patch, -patch:, :3],
        arr[-patch:, :patch, :3],
        arr[-patch:, -patch:, :3],
    ]
    corner_medians = np.array(
        [np.median(c.reshape(-1, 3), axis=0) for c in corners]
    )
    spread = np.std(corner_medians, axis=0).mean()
    if spread > 25:
        # Corners disagree — probably a full-bleed scene. Don't touch it.
        return

    bg = np.median(corner_medians, axis=0)
    rgb = arr[:, :, :3].astype(np.int32)
    dist = np.sqrt(np.sum((rgb - bg) ** 2, axis=2))
    mask = dist < 45
    arr[mask, 3] = 0
    Image.fromarray(arr).save(path)


def _generate_one(client, filename: str, prompt: str) -> None:
    """Call Gemini and write the result to assets/<filename>."""
    out_path = config.ASSETS_DIR / filename
    response = client.models.generate_content(
        model=config.MODEL_ID,
        contents=[prompt],
    )
    if not _save_image_from_response(response, out_path):
        raise RuntimeError(
            f"Gemini returned no image for {filename}. "
            f"Check that {config.MODEL_ID!r} supports image output."
        )
    if filename in _TRANSPARENT_SPRITES:
        _force_transparency_if_opaque(out_path)


def ensure_assets(force: bool = False, progress: Optional[_ProgressFn] = None) -> None:
    """Generate any missing sprites via Gemini. If force=True, regenerate all.

    Includes per-side soldier variations generated via Pro image-edit off the
    base israelite/amalekite sprites.
    """
    _ensure_dir()

    missing = [
        (fn, prompt)
        for fn, prompt in config.ART_PROMPTS.items()
        if force or not (config.ASSETS_DIR / fn).exists()
    ]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to .env or export it before running."
        )

    from google import genai  # lazy so cached-art launches stay offline
    client = genai.Client(api_key=api_key)

    for i, (filename, prompt) in enumerate(missing, 1):
        if progress:
            progress(f"Generating {filename} ({i}/{len(missing)})...")
        _generate_one(client, filename, prompt)

    _ensure_soldier_variations(client, force=force, progress=progress)

    if progress:
        progress("Art generation complete.")


def _ensure_soldier_variations(
    client,
    force: bool,
    progress: Optional[_ProgressFn],
) -> None:
    """Create N variations per side by passing the base sprite + a small edit
    prompt to Nano Banana Pro. Skips any variants that already exist unless
    force=True. Silently skips a side whose base sprite doesn't exist yet."""
    sides = [
        ("israelite", "israelite.png", config.ISRAELITE_VARIATION_PROMPTS),
        ("amalekite", "amalekite.png", config.AMALEKITE_VARIATION_PROMPTS),
    ]
    for prefix, base_name, prompts in sides:
        base_path = config.ASSETS_DIR / base_name
        if not base_path.exists():
            if progress:
                progress(f"Skipping {prefix} variants — {base_name} missing.")
            continue
        needed = []
        for i, variant_prompt in enumerate(prompts[: config.SOLDIER_VARIANT_COUNT], 1):
            out_path = config.ASSETS_DIR / f"{prefix}_{i:02d}.png"
            if force or not out_path.exists():
                needed.append((i, variant_prompt, out_path))
        for idx, (i, variant_prompt, out_path) in enumerate(needed, 1):
            if progress:
                progress(
                    f"Editing {prefix} variant {i:02d} ({idx}/{len(needed)})..."
                )
            _generate_variant(client, base_path, variant_prompt, out_path)


def _generate_variant(client, base_path: Path, variant_prompt: str, out_path: Path) -> None:
    """One image-edit call: pass the base sprite + an edit instruction."""
    ref = Image.open(base_path)
    instruction = (
        "Redraw this cartoon game character in a NEW POSE and EXPRESSION: "
        + variant_prompt
        + " HARD CONSTRAINTS that must not change: use the EXACT same "
        "Kingdom Rush cartoon art style as the reference — identical thick "
        "dark outlines, identical saturated palette, identical flat shading "
        "with painted highlights, identical chunky cartoon proportions. "
        "The character must occupy roughly the same vertical space, "
        "centered in the frame at the same scale as the reference (not "
        "zoomed in or out). Keep the same character identity (skin tone, "
        "tunic colors, equipment style) unless the prompt says otherwise. "
        "Background must be a PLAIN SOLID WHITE fill — absolutely NOT a "
        "checkerboard, grid, or transparency pattern. No text, no "
        "watermark, no new scenery, no ground, no shadow."
    )
    response = client.models.generate_content(
        model=config.MODEL_ID,
        contents=[instruction, ref],
    )
    if not _save_image_from_response(response, out_path):
        raise RuntimeError(f"Gemini returned no image for {out_path.name}")
    _force_transparency_if_opaque(out_path)

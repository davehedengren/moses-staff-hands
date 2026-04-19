"""Generate looping battle music via Gemini Lyria Realtime.

Lyria Realtime is a streaming model — we open a session, feed it weighted
prompts, let it play for MUSIC_DURATION_S seconds, capture the raw 48 kHz
16-bit stereo PCM chunks, and save the whole thing as a WAV that pygame.mixer
can loop.
"""
from __future__ import annotations

import asyncio
import os
import time
import wave
from pathlib import Path
from typing import Callable, Optional

import config

MUSIC_PATH = config.AUDIO_DIR / "battle_music.wav"
AMBIENCE_PATH = config.AUDIO_DIR / "battle_ambience.wav"

_ProgressFn = Callable[[str], None]

# Lyria Realtime's documented output format.
_SAMPLE_RATE = 48000
_CHANNELS = 2
_SAMPLE_WIDTH = 2  # bytes per sample (16-bit)


async def _lyria_capture(
    out_path: Path,
    duration_s: int,
    weighted_prompts,
    generation_config,
    label: str,
    progress: Optional[_ProgressFn],
) -> None:
    """Connect to Lyria, stream for `duration_s`, save a WAV."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Add it to .env before running with --regen-audio."
        )

    client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
    out_path.parent.mkdir(parents=True, exist_ok=True)

    buffer = bytearray()
    async with client.aio.live.music.connect(model=config.LYRIA_MODEL_ID) as session:
        prompts = [
            types.WeightedPrompt(text=text, weight=weight)
            for text, weight in weighted_prompts
        ]
        await session.set_weighted_prompts(prompts=prompts)
        await session.set_music_generation_config(config=generation_config)
        await session.play()

        start = time.time()
        last_report = start
        async for message in session.receive():
            server_content = getattr(message, "server_content", None)
            if server_content is not None:
                audio_chunks = getattr(server_content, "audio_chunks", None) or []
                for chunk in audio_chunks:
                    buffer.extend(chunk.data)
            elapsed = time.time() - start
            if progress and (time.time() - last_report) >= 5:
                progress(f"Capturing {label}... {int(elapsed)}s / {duration_s}s")
                last_report = time.time()
            if elapsed >= duration_s:
                break
        await session.stop()

    if not buffer:
        raise RuntimeError(
            f"Lyria returned no audio data for {label} — check model access."
        )

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(bytes(buffer))


def _music_config():
    from google.genai import types
    return types.LiveMusicGenerationConfig(bpm=110, density=0.75, brightness=0.7)


def _ambience_config():
    from google.genai import types
    # Low brightness, high density — want a thick wall of percussion/clashes,
    # not a melodic tune.
    return types.LiveMusicGenerationConfig(bpm=100, density=0.9, brightness=0.35)


def ensure_music(force: bool = False, progress: Optional[_ProgressFn] = None) -> None:
    """Generate battle_music.wav if missing. force=True regenerates anyway."""
    if MUSIC_PATH.exists() and not force:
        if progress:
            progress("Music cached.")
        return
    if progress:
        progress(f"Generating battle music via Lyria ({config.MUSIC_DURATION_S}s)...")
    asyncio.run(
        _lyria_capture(
            MUSIC_PATH,
            config.MUSIC_DURATION_S,
            config.BATTLE_MUSIC_PROMPTS,
            _music_config(),
            "music",
            progress,
        )
    )
    if progress:
        progress("Music ready.")


def ensure_ambience(force: bool = False, progress: Optional[_ProgressFn] = None) -> None:
    """Generate battle_ambience.wav if missing."""
    if AMBIENCE_PATH.exists() and not force:
        if progress:
            progress("Ambience cached.")
        return
    if progress:
        progress(f"Generating battle ambience via Lyria ({config.AMBIENCE_DURATION_S}s)...")
    asyncio.run(
        _lyria_capture(
            AMBIENCE_PATH,
            config.AMBIENCE_DURATION_S,
            config.BATTLE_AMBIENCE_PROMPTS,
            _ambience_config(),
            "ambience",
            progress,
        )
    )
    if progress:
        progress("Ambience ready.")

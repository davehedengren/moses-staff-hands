"""Entrypoint: wires webcam + pose + battle state + rendering together."""
from __future__ import annotations

import argparse
import sys
import time

import cv2
import numpy as np
import pygame
from dotenv import load_dotenv

import config
from art_gen import ensure_assets
from audio import AudioPlayer
from audio_gen import AMBIENCE_PATH, MUSIC_PATH, ensure_ambience, ensure_music
from battle import BattleState
from detection import PoseDetector
from render import Renderer


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Moses' Staff — hands-up battle game")
    dur = p.add_mutually_exclusive_group()
    dur.add_argument(
        "--duration",
        choices=list(config.DURATION_PRESETS.keys()),
        default=config.DEFAULT_DURATION,
        help="Duration preset (easy=60s, default=120s, hard=180s).",
    )
    dur.add_argument(
        "--duration-seconds",
        type=float,
        help="Override duration with an explicit number of seconds.",
    )
    p.add_argument("--camera", type=int, default=0, help="Webcam index (default 0).")
    p.add_argument(
        "--regen-art",
        action="store_true",
        help="(Re)generate all sprites via Gemini before starting. Without "
             "this flag, the game uses whatever is already in assets/ and "
             "falls back to plain shapes for anything missing.",
    )
    p.add_argument(
        "--regen-audio",
        action="store_true",
        help="(Re)generate battle music via Gemini Lyria (~45s of streaming). "
             "Without this flag, the game plays whatever is in audio/ and is "
             "silent if nothing is there.",
    )
    p.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip loading audio even if a cached track exists.",
    )
    return p.parse_args()


def resolve_duration(args: argparse.Namespace) -> float:
    if args.duration_seconds is not None:
        return float(args.duration_seconds)
    return float(config.DURATION_PRESETS[args.duration])


def open_camera(index: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera index {index}. "
            "Check permissions (System Settings → Privacy → Camera) and --camera."
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    return cap


def main() -> int:
    args = parse_args()
    load_dotenv()

    pygame.init()
    pygame.display.set_caption("Moses' Staff")
    screen = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H))
    renderer = Renderer(screen)
    clock = pygame.time.Clock()

    # Only (re)generate art when explicitly requested. Default launch is offline.
    if args.regen_art:
        renderer.draw_splash("Regenerating art (this may take a minute)...")
        pygame.display.flip()
        try:
            ensure_assets(
                force=True,
                progress=lambda msg: _show_progress(renderer, msg),
            )
        except Exception as e:
            _show_progress(renderer, f"Art gen failed: {e}")
            time.sleep(2.5)
        renderer.load_sprites()

    # Same story for audio: only (re)generate on explicit request.
    if args.regen_audio:
        renderer.draw_splash("Generating battle music via Lyria...")
        pygame.display.flip()
        try:
            ensure_music(
                force=True,
                progress=lambda msg: _show_progress(renderer, msg),
            )
            ensure_ambience(
                force=True,
                progress=lambda msg: _show_progress(renderer, msg),
            )
        except Exception as e:
            _show_progress(renderer, f"Audio gen failed: {e}")
            time.sleep(2.5)

    # Start looping battle music. Ambience playback is disabled by default —
    # Lyria renders the ambience as its own musical track too, so stacking
    # both gives a muddy double-music effect. The ambience WAV stays on disk
    # for future use if we ever swap to a true SFX model.
    audio = AudioPlayer()
    if not args.no_audio and MUSIC_PATH.exists():
        audio.play_music_loop(MUSIC_PATH)

    cap = open_camera(args.camera)
    detector = PoseDetector()
    state = BattleState(duration_s=resolve_duration(args))

    running = True
    last_t = time.perf_counter()

    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_q, pygame.K_ESCAPE):
                        running = False
                    elif event.key == pygame.K_r:
                        state.reset()

            ok, frame = cap.read()
            if not ok:
                frame = None
                detection = detector.process(
                    # Pose needs an image; if capture failed, reuse a dummy black frame.
                    _black_frame()
                )
            else:
                detection = detector.process(frame)

            now = time.perf_counter()
            dt = now - last_t
            last_t = now
            state.tick(dt, detection.arms_up)

            renderer.draw(state, detection, frame)
            pygame.display.flip()
            clock.tick(config.FPS)
    finally:
        audio.close()
        detector.close()
        cap.release()
        pygame.quit()

    return 0


def _show_progress(renderer: Renderer, msg: str) -> None:
    """Draw a splash message during setup and pump the event loop."""
    renderer.draw_splash(msg)
    pygame.display.flip()
    # Keep window responsive during long art generation.
    pygame.event.pump()


def _black_frame():
    return np.zeros((480, 640, 3), dtype="uint8")


if __name__ == "__main__":
    sys.exit(main())

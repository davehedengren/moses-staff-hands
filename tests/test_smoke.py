"""Smoke test: init pygame + renderer + battle + detector, run a few ticks
against a synthetic black frame. Verifies the wiring compiles and runs end-to-end
without a real camera or display.
"""
import numpy as np
import pygame
import pytest

import config
from battle import BattleState
from detection import PoseDetector
from render import Renderer


@pytest.fixture(scope="module")
def screen():
    pygame.init()
    s = pygame.display.set_mode((config.WINDOW_W, config.WINDOW_H))
    yield s
    pygame.quit()


def test_imports_and_main_module():
    # Importing main pulls in every subsystem.
    import main  # noqa: F401


def test_renderer_initializes_without_assets(screen):
    # Even with an empty assets/ directory, renderer should construct and
    # fall back to colored rectangles at draw time.
    r = Renderer(screen)
    # Basic sanity: battlefield + cam regions together span the full window.
    assert r.battle_rect.height + r.cam_rect.height == config.WINDOW_H


def test_full_frame_roundtrip(screen):
    """Render a handful of frames with synthetic inputs — must not raise."""
    renderer = Renderer(screen)
    state = BattleState(duration_s=10)
    detector = PoseDetector()
    try:
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(5):
            detection = detector.process(dummy_frame)
            # No person in a black frame — must report pose_found=False, arms_up=False.
            assert detection.pose_found is False
            assert detection.arms_up is False
            state.tick(0.1, detection.arms_up)
            renderer.draw(state, detection, dummy_frame)
            pygame.display.flip()
    finally:
        detector.close()


def test_splash_renders(screen):
    r = Renderer(screen)
    r.draw_splash("Generating art...")
    pygame.display.flip()

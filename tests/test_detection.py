"""Tests for the arms-up hysteresis classifier in detection.PoseDetector.

We exercise the internal classifier directly so we can feed synthetic
(wrist_y, shoulder_y) values without needing a webcam frame or MediaPipe.
"""
import pytest

from detection import PoseDetector
import config


@pytest.fixture
def detector():
    d = PoseDetector()
    yield d
    d.close()


def _classify(d: PoseDetector, lw, rw, ls=0.5, rs=0.5):
    return d._classify_with_hysteresis(
        left_wrist_y=lw, right_wrist_y=rw,
        left_shoulder_y=ls, right_shoulder_y=rs,
    )


def test_starts_down(detector):
    # Freshly constructed, arms are considered down.
    assert detector._arms_up_state is False


def test_both_wrists_clearly_above_flips_up(detector):
    # Wrists well above shoulders (smaller y in image coords).
    margin = config.HYSTERESIS + 0.05
    assert _classify(detector, lw=0.5 - margin, rw=0.5 - margin) is True


def test_only_one_wrist_above_stays_down(detector):
    # Must require BOTH wrists above to flip from down -> up.
    margin = config.HYSTERESIS + 0.05
    assert _classify(detector, lw=0.5 - margin, rw=0.5 + margin) is False


def test_small_drop_within_hysteresis_keeps_up(detector):
    # Drive up first.
    margin = config.HYSTERESIS + 0.05
    _classify(detector, lw=0.5 - margin, rw=0.5 - margin)
    assert detector._arms_up_state is True

    # Drop wrists slightly — still within hysteresis band. Should remain up.
    tiny = config.HYSTERESIS * 0.3
    assert _classify(detector, lw=0.5 - tiny, rw=0.5 - tiny) is True


def test_clear_drop_of_either_arm_flips_down(detector):
    margin = config.HYSTERESIS + 0.05
    _classify(detector, lw=0.5 - margin, rw=0.5 - margin)
    assert detector._arms_up_state is True

    # Left wrist drops well below shoulder — one arm is enough to flip down
    # (even though flipping up requires both). This models real fatigue.
    assert _classify(detector, lw=0.5 + margin, rw=0.5 - margin) is False


def test_flicker_near_threshold_does_not_oscillate(detector):
    """Hysteresis should suppress rapid flips when wrists are right at the line."""
    margin = config.HYSTERESIS + 0.05
    # Start up.
    _classify(detector, lw=0.5 - margin, rw=0.5 - margin)
    assert detector._arms_up_state is True

    # Wiggle within the dead band a bunch of times; state should stay up.
    for _ in range(50):
        _classify(detector, lw=0.5 - 0.001, rw=0.5 + 0.001)
    assert detector._arms_up_state is True

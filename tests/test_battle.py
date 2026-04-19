"""Unit tests for the pure battle state machine."""
from battle import BattleState, Status


def test_starts_playing_immediately():
    state = BattleState(duration_s=60)
    assert state.status is Status.PLAYING


def test_arms_up_pushes_toward_israel():
    state = BattleState(duration_s=60)
    start = state.line_pos
    state.tick(1.0, arms_up=True)
    assert state.line_pos > start


def test_arms_down_pushes_toward_amalek():
    state = BattleState(duration_s=60)
    start = state.line_pos
    state.tick(1.0, arms_up=False)
    assert state.line_pos < start


def test_israel_wins_when_line_reaches_1():
    state = BattleState(duration_s=300)
    # Push hard: a huge tick is far past 1.0; clamped.
    state.tick(2000.0, arms_up=True)
    assert state.line_pos == 1.0
    assert state.status is Status.ISRAEL_WON


def test_amalek_wins_when_line_reaches_0():
    state = BattleState(duration_s=300)
    state.tick(2000.0, arms_up=False)
    assert state.line_pos == 0.0
    assert state.status is Status.AMALEK_WON


def test_timeout_with_israel_ahead_awards_israel():
    state = BattleState(duration_s=5)
    # Small push toward Israel so line > 0.5, then time out while still ahead.
    state.tick(1.0, arms_up=True)
    assert 0.5 < state.line_pos < 1.0
    state.tick(3.999, arms_up=True)
    state.tick(0.1, arms_up=False)
    assert state.status is Status.ISRAEL_WON


def test_timeout_with_amalek_ahead_awards_amalek():
    state = BattleState(duration_s=5)
    state.tick(4.0, arms_up=False)
    state.tick(1.1, arms_up=True)
    assert state.status is Status.AMALEK_WON


def test_is_over_only_after_win_or_loss():
    state = BattleState(duration_s=60)
    assert not state.is_over
    state.tick(2000.0, arms_up=True)
    assert state.is_over


def test_reset_restores_initial_state():
    state = BattleState(duration_s=60)
    state.tick(1.0, arms_up=True)
    state.reset()
    assert state.line_pos == 0.5
    assert state.elapsed == 0.0
    assert state.status is Status.PLAYING


def test_tick_is_idempotent_after_game_over():
    state = BattleState(duration_s=60)
    state.tick(2000.0, arms_up=True)
    assert state.status is Status.ISRAEL_WON
    frozen_pos = state.line_pos
    frozen_elapsed = state.elapsed
    state.tick(5.0, arms_up=False)  # post-game-over tick must be a no-op
    assert state.status is Status.ISRAEL_WON
    assert state.line_pos == frozen_pos
    assert state.elapsed == frozen_elapsed

"""Pure game state for the Israel-vs-Amalek tug-of-war."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import config


class Status(str, Enum):
    PLAYING = "playing"
    ISRAEL_WON = "israel_won"
    AMALEK_WON = "amalek_won"


@dataclass
class BattleState:
    """Tug-of-war state.

    line_pos: 0.0 = Amalek has overrun Israel's camp (Amalek wins),
              1.0 = Israel has overrun Amalek's camp (Israel wins),
              start 0.5.
    Intuition: arms up pushes line toward 1.0; arms down pulls toward 0.0.
    """
    duration_s: float
    line_pos: float = 0.5
    elapsed: float = 0.0
    status: Status = Status.PLAYING

    push_rate: float = field(default_factory=lambda: config.PUSH_RATE)

    def tick(self, dt: float, arms_up: bool) -> None:
        if self.status in (Status.ISRAEL_WON, Status.AMALEK_WON):
            return

        self.elapsed += dt

        # PLAYING — arms up advances Israel slowly; arms down pulls Amalek
        # back faster (asymmetric, matches the "when Moses lowered his hand,
        # Amalek prevailed" beat).
        if arms_up:
            delta = self.push_rate * dt
        else:
            delta = -self.push_rate * config.PUSH_RATE_DOWN_MULT * dt
        self.line_pos += delta
        self.line_pos = max(0.0, min(1.0, self.line_pos))

        if self.line_pos >= 1.0:
            self.status = Status.ISRAEL_WON
            return
        if self.line_pos <= 0.0:
            self.status = Status.AMALEK_WON
            return

        if self.elapsed >= self.duration_s:
            # Time out: side holding more ground wins. A perfect tie defaults
            # to Israel (the faithful don't lose ties in this one).
            if self.line_pos >= 0.5:
                self.status = Status.ISRAEL_WON
            else:
                self.status = Status.AMALEK_WON

    @property
    def time_remaining(self) -> float:
        if self.status is Status.PLAYING:
            return max(0.0, self.duration_s - self.elapsed)
        return 0.0

    @property
    def is_over(self) -> bool:
        return self.status in (Status.ISRAEL_WON, Status.AMALEK_WON)

    def reset(self) -> None:
        self.line_pos = 0.5
        self.elapsed = 0.0
        self.status = Status.PLAYING

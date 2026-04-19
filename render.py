"""Pygame rendering for the battle scene, webcam overlay, and HUD."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
import pygame

import config
from battle import BattleState, Status
from detection import DetectionResult


# ---------- helpers -------------------------------------------------------

def _load_image_or_none(path: Path) -> Optional[pygame.Surface]:
    if not path.exists():
        return None
    try:
        return pygame.image.load(str(path)).convert_alpha()
    except pygame.error:
        return None


def _scale_to_height(surf: pygame.Surface, target_h: int) -> pygame.Surface:
    ratio = target_h / surf.get_height()
    target_w = max(1, int(surf.get_width() * ratio))
    return pygame.transform.smoothscale(surf, (target_w, target_h))


def _scale_cover(surf: pygame.Surface, target_w: int, target_h: int) -> pygame.Surface:
    """Scale to cover the target rect, preserving aspect; center crop."""
    src_w, src_h = surf.get_size()
    scale = max(target_w / src_w, target_h / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
    crop_x = (new_w - target_w) // 2
    crop_y = (new_h - target_h) // 2
    cropped = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
    cropped.blit(scaled, (-crop_x, -crop_y))
    return cropped


@dataclass
class _Soldier:
    """Per-soldier jitter parameters for the chaotic-march effect."""
    step: int                # how many soldier-widths behind the front line
    variant_idx: int         # which sprite variant this soldier wears
    bob_phase: float
    bob_freq: float          # vertical bob Hz
    bob_amp: float           # pixels
    sway_phase: float
    sway_freq: float         # horizontal sway Hz
    sway_amp: float          # pixels
    y_offset: float          # baseline vertical offset for variety


def _make_soldiers(n: int, rng: random.Random) -> List[_Soldier]:
    out = []
    for i in range(n):
        out.append(
            _Soldier(
                step=i,
                variant_idx=rng.randrange(10_000),  # modded by sprite count at draw
                bob_phase=rng.uniform(0, math.tau),
                bob_freq=rng.uniform(1.6, 2.8),
                bob_amp=rng.uniform(4.0, 10.0),
                sway_phase=rng.uniform(0, math.tau),
                sway_freq=rng.uniform(0.7, 1.4),
                sway_amp=rng.uniform(2.5, 6.0),
                y_offset=rng.uniform(-10.0, 10.0),
            )
        )
    return out


# ---------- renderer ------------------------------------------------------

class Renderer:
    """Draws the whole scene each frame."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.battle_rect = pygame.Rect(0, 0, self.w, int(self.h * config.BATTLEFIELD_H_FRAC))
        self.cam_rect = pygame.Rect(
            0,
            self.battle_rect.height,
            self.w,
            self.h - self.battle_rect.height,
        )

        self.font_small = pygame.font.SysFont("georgia", 22, bold=True)
        self.font_med = pygame.font.SysFont("georgia", 34, bold=True)
        self.font_big = pygame.font.SysFont("georgia", 72, bold=True)

        # Seeded RNG so soldier jitter is stable between runs.
        rng = random.Random(42)
        self._israel_soldiers = _make_soldiers(config.SOLDIERS_PER_SIDE, rng)
        self._amalek_soldiers = _make_soldiers(config.SOLDIERS_PER_SIDE, rng)

        self.load_sprites()

    def load_sprites(self) -> None:
        self._bg_raw = _load_image_or_none(config.ASSETS_DIR / "background.png")
        self._victory_israel = _load_image_or_none(config.ASSETS_DIR / "victory_israel.png")
        self._victory_amalek = _load_image_or_none(config.ASSETS_DIR / "victory_amalek.png")
        self._moses_icon = _load_image_or_none(config.ASSETS_DIR / "moses_icon.png")

        if self._bg_raw is not None:
            self._bg = _scale_cover(self._bg_raw, self.battle_rect.width, self.battle_rect.height)
        else:
            self._bg = None

        soldier_h = int(self.battle_rect.height * 0.48)
        self._israel_sprites = self._load_soldier_sprites("israelite", soldier_h)
        self._amalek_sprites = self._load_soldier_sprites("amalekite", soldier_h)

    def _load_soldier_sprites(self, prefix: str, soldier_h: int) -> List[pygame.Surface]:
        """Load base + numbered variants for one side. Order: base first, then
        variants. Returns [] if nothing is available (draw falls back to rects)."""
        sprites: List[pygame.Surface] = []
        base = _load_image_or_none(config.ASSETS_DIR / f"{prefix}.png")
        if base is not None:
            sprites.append(_scale_to_height(base, soldier_h))
        for i in range(1, config.SOLDIER_VARIANT_COUNT + 1):
            path = config.ASSETS_DIR / f"{prefix}_{i:02d}.png"
            img = _load_image_or_none(path)
            if img is not None:
                sprites.append(_scale_to_height(img, soldier_h))
        return sprites

    # ---------- top-level ---------------------------------------------

    def draw(
        self,
        state: BattleState,
        detection: DetectionResult,
        webcam_frame_bgr,
        status_message: Optional[str] = None,
    ) -> None:
        t = pygame.time.get_ticks() / 1000.0
        self.screen.fill(config.COLOR_BG)
        self._draw_battlefield(state, t)
        self._draw_webcam(webcam_frame_bgr, detection)
        self._draw_hud(state, detection)
        if state.is_over:
            self._draw_end_screen(state)
        if status_message:
            self._draw_centered_banner(status_message)

    def draw_splash(self, message: str) -> None:
        self.screen.fill(config.COLOR_BG)
        self._draw_centered_banner(message)

    # ---------- battlefield ------------------------------------------

    def _draw_battlefield(self, state: BattleState, t: float) -> None:
        r = self.battle_rect
        if self._bg is not None:
            self.screen.blit(self._bg, r.topleft)
        else:
            pygame.draw.rect(self.screen, (60, 55, 45), r)

        line_x = r.x + int(state.line_pos * r.width)
        soldier_y = r.y + int(r.height * 0.52)

        self._draw_army(
            soldiers=self._israel_soldiers,
            sprites=self._israel_sprites,
            fallback_color=config.COLOR_ISRAEL,
            leading_x=line_x,
            y_center=soldier_y,
            facing="right",
            t=t,
        )
        self._draw_army(
            soldiers=self._amalek_soldiers,
            sprites=self._amalek_sprites,
            fallback_color=config.COLOR_AMALEK,
            leading_x=line_x,
            y_center=soldier_y,
            facing="left",
            t=t,
        )

        # Battle-line marker.
        pygame.draw.line(
            self.screen,
            (240, 220, 150),
            (line_x, r.y + 10),
            (line_x, r.y + r.height - 10),
            2,
        )

    def _draw_army(
        self,
        soldiers: List[_Soldier],
        sprites: List[pygame.Surface],
        fallback_color,
        leading_x: int,
        y_center: int,
        facing: str,
        t: float,
    ) -> None:
        step_px = config.SOLDIER_STEP_PX
        direction = -1 if facing == "right" else +1  # trailing direction

        # Draw back-to-front so closer soldiers overlap farther ones correctly.
        ordered = sorted(soldiers, key=lambda s: -s.step)
        for s in ordered:
            dx = s.sway_amp * math.sin(s.sway_freq * t + s.sway_phase)
            dy = s.bob_amp * math.sin(s.bob_freq * t + s.bob_phase) + s.y_offset
            x = leading_x + direction * s.step * step_px + dx
            y = y_center + dy

            if sprites:
                # Each side's sprites are prompted to face the correct
                # direction (israelite right, amalekite left). No flip.
                sprite = sprites[s.variant_idx % len(sprites)]
                rect_s = sprite.get_rect()
                rect_s.midbottom = (int(x), int(y + sprite.get_height() * 0.48))
                if rect_s.right < self.battle_rect.x or rect_s.left > self.battle_rect.right:
                    continue
                self.screen.blit(sprite, rect_s)
            else:
                w, h = 48, 110
                pygame.draw.rect(self.screen, fallback_color, (int(x) - w // 2, int(y) - h // 2, w, h))

    # ---------- webcam + pose overlay --------------------------------

    def _draw_webcam(self, frame_bgr, detection: DetectionResult) -> None:
        r = self.cam_rect
        pygame.draw.rect(self.screen, (10, 10, 10), r)

        if frame_bgr is None:
            msg = self.font_med.render("No camera feed", True, config.COLOR_TEXT)
            mr = msg.get_rect(center=r.center)
            self.screen.blit(msg, mr)
            return

        # Mirror horizontally so player movement feels natural.
        frame_bgr = cv2.flip(frame_bgr, 1)
        fh, fw = frame_bgr.shape[:2]
        scale = min(r.width / fw, r.height / fh)
        new_w = int(fw * scale)
        new_h = int(fh * scale)
        resized = cv2.resize(frame_bgr, (new_w, new_h))

        self._draw_pose_overlay(resized, detection)

        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        surf = pygame.image.frombuffer(rgb.tobytes(), (new_w, new_h), "RGB")

        dest = surf.get_rect()
        dest.center = r.center
        self.screen.blit(surf, dest)

        # Side HUD in the letterbox bars: left = timer/status, right = wrist-vs-threshold indicator.
        self._draw_cam_sidebars(dest, detection)

    def _draw_pose_overlay(self, frame_bgr, detection: DetectionResult) -> None:
        h, w = frame_bgr.shape[:2]

        if not detection.pose_found:
            msg = "STEP INTO FRAME"
            cv2.putText(
                frame_bgr, msg, (20, h // 2),
                cv2.FONT_HERSHEY_DUPLEX, 1.0, (240, 240, 240), 2, cv2.LINE_AA,
            )
            return

        def to_px(pt):
            # Pose landmarks are on the ORIGINAL (un-mirrored) frame; flip x for display.
            return (int((1.0 - pt[0]) * w), int(pt[1] * h))

        up_color = (120, 230, 140)   # green
        down_color = (90, 110, 240)  # blue (not yet high enough)
        color = up_color if detection.arms_up else down_color

        # --- threshold bar (the line wrists must clear) ---
        if detection.left_shoulder and detection.right_shoulder:
            ls = to_px(detection.left_shoulder)
            rs = to_px(detection.right_shoulder)
            threshold_y = (ls[1] + rs[1]) // 2

            # Dashed-ish bar across the frame to make the threshold obvious.
            dash_color = (60, 230, 120) if detection.arms_up else (255, 200, 70)
            bar_thickness = 6
            dash_len = 24
            gap_len = 12
            x = 0
            while x < w:
                cv2.line(
                    frame_bgr,
                    (x, threshold_y),
                    (min(x + dash_len, w), threshold_y),
                    dash_color,
                    bar_thickness,
                    cv2.LINE_AA,
                )
                x += dash_len + gap_len

            # cv2.putText uses Hershey fonts which are ASCII-only — no em-dash.
            label = "ARMS UP - GO!" if detection.arms_up else "LIFT ARMS ABOVE THIS LINE"
            label_color = (60, 230, 120) if detection.arms_up else (255, 230, 100)
            # Put the label just above the threshold line.
            text_y = max(30, threshold_y - 14)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.8, 2)
            tx = max(10, min(w - tw - 10, (w - tw) // 2))
            # Dark backing rectangle for legibility.
            cv2.rectangle(
                frame_bgr,
                (tx - 8, text_y - th - 8),
                (tx + tw + 8, text_y + 4),
                (0, 0, 0),
                -1,
            )
            cv2.putText(
                frame_bgr, label, (tx, text_y),
                cv2.FONT_HERSHEY_DUPLEX, 0.8, label_color, 2, cv2.LINE_AA,
            )

        # --- skeleton bones ---
        if detection.left_shoulder and detection.left_wrist:
            cv2.line(frame_bgr, to_px(detection.left_shoulder), to_px(detection.left_wrist), color, 4, cv2.LINE_AA)
        if detection.right_shoulder and detection.right_wrist:
            cv2.line(frame_bgr, to_px(detection.right_shoulder), to_px(detection.right_wrist), color, 4, cv2.LINE_AA)
        if detection.left_shoulder and detection.right_shoulder:
            cv2.line(frame_bgr, to_px(detection.left_shoulder), to_px(detection.right_shoulder), color, 3, cv2.LINE_AA)

        # --- shoulder + wrist markers ---
        for pt, label, is_wrist in (
            (detection.left_shoulder, "L.sh", False),
            (detection.right_shoulder, "R.sh", False),
            (detection.left_wrist, "L.hand", True),
            (detection.right_wrist, "R.hand", True),
        ):
            if pt is None:
                continue
            px, py = to_px(pt)
            radius = 14 if is_wrist else 8
            # Outline + fill for high visibility.
            cv2.circle(frame_bgr, (px, py), radius + 2, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(frame_bgr, (px, py), radius, color, -1, cv2.LINE_AA)

    def _draw_cam_sidebars(self, frame_dest: pygame.Rect, detection: DetectionResult) -> None:
        """Use the widescreen letterbox area around the webcam for big HUD info."""
        left_band = pygame.Rect(self.cam_rect.x, self.cam_rect.y, frame_dest.x - self.cam_rect.x, self.cam_rect.height)
        right_band = pygame.Rect(frame_dest.right, self.cam_rect.y, self.cam_rect.right - frame_dest.right, self.cam_rect.height)

        # Left band: quick instructions / arms indicator echo.
        if left_band.width > 60:
            title = self.font_med.render("MOSES' STAFF", True, config.COLOR_TEXT)
            self.screen.blit(title, (left_band.x + 16, left_band.y + 24))
            hint_lines = [
                "Raise staff overhead.",
                "Dashed line = threshold.",
                "Friends may lift your arms.",
            ]
            for i, line in enumerate(hint_lines):
                surf = self.font_small.render(line, True, (190, 185, 170))
                self.screen.blit(surf, (left_band.x + 16, left_band.y + 70 + i * 28))

        # Right band: big arms-up readout so the player doesn't have to squint.
        if right_band.width > 60:
            if not detection.pose_found:
                label = "NO POSE"
                color = (200, 200, 200)
            elif detection.arms_up:
                label = "ARMS UP"
                color = config.COLOR_ARMS_UP
            else:
                label = "ARMS DOWN"
                color = config.COLOR_ARMS_DOWN
            surf = self.font_med.render(label, True, color)
            sr = surf.get_rect()
            sr.center = right_band.center
            self.screen.blit(surf, sr)

            # Little moses icon above the readout if we have it.
            if self._moses_icon is not None and right_band.width > 140:
                icon = _scale_to_height(self._moses_icon, min(140, right_band.height // 2))
                ir = icon.get_rect()
                ir.midbottom = (right_band.centerx, sr.top - 12)
                self.screen.blit(icon, ir)

    # ---------- HUD ---------------------------------------------------

    def _draw_hud(self, state: BattleState, detection: DetectionResult) -> None:
        # Progress bar across the top.
        bar_h = 16
        bar = pygame.Rect(20, 12, self.w - 40, bar_h)
        pygame.draw.rect(self.screen, config.COLOR_HUD_BG, bar, border_radius=6)
        fill_w = int(bar.width * state.line_pos)
        israel_rect = pygame.Rect(bar.x, bar.y, fill_w, bar.height)
        amalek_rect = pygame.Rect(bar.x + fill_w, bar.y, bar.width - fill_w, bar.height)
        pygame.draw.rect(self.screen, config.COLOR_ISRAEL, israel_rect, border_radius=6)
        pygame.draw.rect(self.screen, config.COLOR_AMALEK, amalek_rect, border_radius=6)

        cx = bar.x + bar.width // 2
        pygame.draw.line(self.screen, (240, 230, 200), (cx, bar.y - 3), (cx, bar.y + bar.height + 3), 2)

        # Row just under the progress bar: ISRAEL (left), AMALEK (right).
        il = self.font_small.render("ISRAEL", True, config.COLOR_ISRAEL)
        al = self.font_small.render("AMALEK", True, config.COLOR_AMALEK)
        label_row_y = bar.y + bar.height + 4
        self.screen.blit(il, (bar.x, label_row_y))
        al_rect = al.get_rect()
        al_rect.topright = (bar.right, label_row_y)
        self.screen.blit(al, al_rect)

        # Timer, centered below the progress-bar row.
        secs = int(round(state.time_remaining))
        mins = secs // 60
        rem = secs % 60
        label = f"{mins}:{rem:02d}"
        if state.status is Status.WARMUP:
            label = f"Get ready... {secs}"
        timer_surf = self.font_med.render(label, True, config.COLOR_TEXT)
        tr = timer_surf.get_rect()
        tr.midtop = (self.w // 2, label_row_y + il.get_height() + 2)
        self.screen.blit(timer_surf, tr)
        # Big arms-state readout lives in the webcam sidebar only — no
        # duplicate top-right indicator here (it collided with AMALEK label).

    # ---------- end screen + splash ----------------------------------

    def _draw_end_screen(self, state: BattleState) -> None:
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        if state.status is Status.ISRAEL_WON:
            text = "Israel Prevails"
            banner = self._victory_israel
            color = config.COLOR_ISRAEL
        else:
            text = "Amalek Prevails"
            banner = self._victory_amalek
            color = config.COLOR_AMALEK

        if banner is not None:
            banner_scaled = _scale_to_height(banner, int(self.h * 0.38))
            br = banner_scaled.get_rect()
            br.center = (self.w // 2, int(self.h * 0.4))
            self.screen.blit(banner_scaled, br)
        else:
            t = self.font_big.render(text, True, color)
            tr = t.get_rect(center=(self.w // 2, int(self.h * 0.4)))
            self.screen.blit(t, tr)

        sub = self.font_med.render("Press R to replay, Q to quit", True, config.COLOR_TEXT)
        sr = sub.get_rect(center=(self.w // 2, int(self.h * 0.62)))
        self.screen.blit(sub, sr)

    def _draw_centered_banner(self, message: str) -> None:
        surf = self.font_med.render(message, True, config.COLOR_TEXT)
        rect = surf.get_rect(center=(self.w // 2, self.h // 2))
        pad = 20
        bg_rect = rect.inflate(pad * 2, pad * 2)
        pygame.draw.rect(self.screen, config.COLOR_HUD_BG, bg_rect, border_radius=10)
        self.screen.blit(surf, rect)

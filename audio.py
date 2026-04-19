"""Thin pygame.mixer wrapper for background music loops.

Safe to import and construct even if audio initialization fails (some CI/
headless envs have no audio device). In that case every method is a no-op.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame

import config


class AudioPlayer:
    def __init__(self) -> None:
        try:
            pygame.mixer.init(frequency=48000, size=-16, channels=2, buffer=512)
            # Reserve a dedicated channel for ambience so pygame doesn't
            # recycle it underneath us.
            pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
            self._ambience_channel = pygame.mixer.Channel(7)
            self._ambience_sound: Optional[pygame.mixer.Sound] = None
            self._available = True
        except pygame.error:
            self._available = False
            self._ambience_channel = None
            self._ambience_sound = None

    @property
    def available(self) -> bool:
        return self._available

    def play_music_loop(self, path: Path, volume: Optional[float] = None) -> None:
        if not self._available or not path.exists():
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(
                config.MUSIC_VOLUME if volume is None else volume
            )
            pygame.mixer.music.play(loops=-1, fade_ms=400)
        except pygame.error:
            pass

    def play_ambience_loop(self, path: Path, volume: Optional[float] = None) -> None:
        """Loop a second layer (battle clanks/shouts) on a dedicated channel."""
        if not self._available or not path.exists() or self._ambience_channel is None:
            return
        try:
            self._ambience_sound = pygame.mixer.Sound(str(path))
            self._ambience_sound.set_volume(
                config.AMBIENCE_VOLUME if volume is None else volume
            )
            self._ambience_channel.play(self._ambience_sound, loops=-1, fade_ms=600)
        except pygame.error:
            pass

    def stop(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.music.fadeout(400)
            if self._ambience_channel is not None:
                self._ambience_channel.fadeout(400)
        except pygame.error:
            pass

    def close(self) -> None:
        if not self._available:
            return
        try:
            pygame.mixer.music.stop()
            if self._ambience_channel is not None:
                self._ambience_channel.stop()
            pygame.mixer.quit()
        except pygame.error:
            pass

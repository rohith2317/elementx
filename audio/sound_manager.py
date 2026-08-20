"""
audio/sound_manager.py
Central sound manager. Loads sound effects/music from assets/sounds
if present; if a file is missing, that sound simply becomes a no-op
so the game still runs perfectly without any audio assets.

Place your own audio files at the paths listed in config.SOUND_FILES
to enable real sound. See README.md for details.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

import pygame

from config import SOUND_FILES


class SoundManager:
    def __init__(self, master_volume: float = 0.7) -> None:
        self.enabled = False
        self.master_volume = master_volume
        self.sfx: Dict[str, pygame.mixer.Sound] = {}
        self.music_path: Optional[str] = SOUND_FILES.get("menu_music")
        self._init_mixer()
        self._load_sounds()

    def _init_mixer(self) -> None:
        try:
            pygame.mixer.init()
            self.enabled = True
        except Exception:
            self.enabled = False

    def _load_sounds(self) -> None:
        if not self.enabled:
            return
        for key, path in SOUND_FILES.items():
            if key == "menu_music":
                continue
            if os.path.exists(path):
                try:
                    self.sfx[key] = pygame.mixer.Sound(path)
                    self.sfx[key].set_volume(self.master_volume)
                except Exception:
                    pass  # corrupt/unsupported file — silently skip

    def play(self, key: str) -> None:
        if not self.enabled:
            return
        sound = self.sfx.get(key)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def play_music(self, loop: bool = True) -> None:
        if not self.enabled or not self.music_path or not os.path.exists(self.music_path):
            return
        try:
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.set_volume(self.master_volume * 0.6)
            pygame.mixer.music.play(-1 if loop else 0)
        except Exception:
            pass

    def stop_music(self) -> None:
        if not self.enabled:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def set_volume(self, volume: float) -> None:
        self.master_volume = max(0.0, min(1.0, volume))
        for sound in self.sfx.values():
            sound.set_volume(self.master_volume)
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.master_volume * 0.6)
            except Exception:
                pass

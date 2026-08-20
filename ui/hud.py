"""
ui/hud.py
Renders the in-game HUD: HP/energy bars for player and enemy, current
gesture/ability, combo counter, score, level label, and the webcam
preview panel with landmark overlay.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
import pygame

from config import (
    SCREEN_WIDTH, COLOR_HP, COLOR_HP_BG, COLOR_ENERGY, COLOR_ENERGY_BG,
    CAM_PREVIEW_WIDTH, CAM_PREVIEW_HEIGHT, CAM_PREVIEW_POS, COLOR_ACCENT,
)
from utils.helpers import draw_text, draw_bar
from vision.gesture_detector import GestureResult


GESTURE_ICONS = {
    "NONE": "—",
    "OPEN_PALM": "🖐 SHIELD",
    "FIST": "✊ PUNCH",
    "ONE_FINGER": "☝ LIGHTNING",
    "TWO_FINGERS": "✌ WIND",
    "THREE_FINGERS": "🤟 BLAST",
    "THUMBS_UP": "👍 HEAL",
    "ULTIMATE": "🙌 ULTIMATE",
}


class HUD:
    def __init__(self, fonts: dict) -> None:
        self.fonts = fonts  # keys: "large", "medium", "small"
        self._cam_surface_cache: Optional[pygame.Surface] = None

    # ------------------------------------------------------------------
    def draw_top_bars(self, surface: pygame.Surface, player, enemy, level_name: str, level_number: int, score: int) -> None:
        # Player HP/Energy (top-left)
        draw_text(surface, "PLAYER", self.fonts["small"], (200, 200, 210), (24, 16))
        draw_bar(surface, (24, 36), (320, 22), player.hp / player.max_hp, COLOR_HP, COLOR_HP_BG)
        draw_text(surface, f"{int(player.hp)}/{player.max_hp}", self.fonts["small"], (255, 255, 255), (24 + 320 + 10, 38))
        draw_bar(surface, (24, 62), (320, 14), player.energy / player.max_energy, COLOR_ENERGY, COLOR_ENERGY_BG)

        # Title (center)
        draw_text(surface, "ELEMENTX", self.fonts["large"], COLOR_ACCENT, (SCREEN_WIDTH // 2, 34), center=True)

        # Enemy HP (top-right)
        if enemy is not None:
            label = enemy.name.upper()
            draw_text(surface, label, self.fonts["small"], (200, 200, 210), (SCREEN_WIDTH - 344, 16))
            draw_bar(surface, (SCREEN_WIDTH - 344, 36), (320, 22), enemy.hp / enemy.max_hp, COLOR_HP, COLOR_HP_BG)
            draw_text(surface, f"{int(enemy.hp)}/{enemy.max_hp}", self.fonts["small"], (255, 255, 255),
                      (SCREEN_WIDTH - 344, 62))

        # Level / score (below title)
        draw_text(surface, f"LEVEL {level_number}: {level_name}", self.fonts["small"], (200, 200, 210),
                  (SCREEN_WIDTH // 2, 62), center=True)

    def draw_bottom_status(self, surface: pygame.Surface, gesture: str, ability_name: str,
                            combo_count: int, score: int) -> None:
        y = surface.get_height() - 64
        icon_text = GESTURE_ICONS.get(gesture, gesture)
        draw_text(surface, f"GESTURE: {icon_text}", self.fonts["medium"], (255, 255, 255), (300, y))
        draw_text(surface, f"ABILITY: {ability_name}", self.fonts["small"], (200, 200, 210), (300, y + 30))

        if combo_count > 1:
            combo_text = f"COMBO x{combo_count}"
            draw_text(surface, combo_text, self.fonts["medium"], (255, 210, 60),
                      (surface.get_width() - 260, y), center=False)

        draw_text(surface, f"SCORE: {score:05d}", self.fonts["small"], (200, 200, 210),
                  (surface.get_width() - 260, y + 30))

    def draw_webcam_preview(self, surface: pygame.Surface, frame_bgr, result: GestureResult,
                             detector) -> None:
        if frame_bgr is None:
            panel = pygame.Rect(*CAM_PREVIEW_POS, CAM_PREVIEW_WIDTH, CAM_PREVIEW_HEIGHT)
            pygame.draw.rect(surface, (20, 20, 30), panel, border_radius=8)
            draw_text(surface, "NO CAMERA", self.fonts["small"], (200, 80, 80), panel.center, center=True)
            return

        annotated = detector.draw_debug_overlay(frame_bgr, result)
        annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        annotated_rgb = cv2.resize(annotated_rgb, (CAM_PREVIEW_WIDTH, CAM_PREVIEW_HEIGHT))
        # Transpose to match pygame's surface array format (W x H x 3)
        annotated_rgb = np.transpose(annotated_rgb, (1, 0, 2))
        cam_surface = pygame.surfarray.make_surface(annotated_rgb)

        surface.blit(cam_surface, CAM_PREVIEW_POS)
        pygame.draw.rect(surface, (255, 200, 60),
                          (*CAM_PREVIEW_POS, CAM_PREVIEW_WIDTH, CAM_PREVIEW_HEIGHT), width=2, border_radius=4)

    def draw_countdown(self, surface: pygame.Surface, value: str) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))
        draw_text(surface, value, self.fonts["large"], (255, 255, 255),
                  (surface.get_width() // 2, surface.get_height() // 2), center=True)

    def draw_center_message(self, surface: pygame.Surface, title: str, subtitle: str = "") -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))
        cx, cy = surface.get_width() // 2, surface.get_height() // 2
        draw_text(surface, title, self.fonts["large"], (255, 210, 60), (cx, cy - 20), center=True)
        if subtitle:
            draw_text(surface, subtitle, self.fonts["medium"], (230, 230, 235), (cx, cy + 30), center=True)

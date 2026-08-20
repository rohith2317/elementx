"""
ui/menu.py
Main menu, How-To-Play, and Settings screens. Each screen exposes
handle_event()/update()/draw() and communicates state changes back to
the GameController via callbacks passed at construction time.
"""
from __future__ import annotations

from typing import Callable, Dict, List

import pygame

from config import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_ACCENT, KEY_BINDINGS_HELP
from ui.buttons import Button
from utils.helpers import draw_text


class MainMenu:
    def __init__(self, fonts: dict, on_start, on_how_to_play, on_settings, on_exit) -> None:
        self.fonts = fonts
        cx = SCREEN_WIDTH // 2
        btn_w, btn_h, gap = 300, 56, 18
        start_y = 360
        self.buttons: List[Button] = [
            Button((cx - btn_w // 2, start_y, btn_w, btn_h), "START GAME", fonts["medium"], on_start),
            Button((cx - btn_w // 2, start_y + (btn_h + gap), btn_w, btn_h), "HOW TO PLAY", fonts["medium"], on_how_to_play),
            Button((cx - btn_w // 2, start_y + 2 * (btn_h + gap), btn_w, btn_h), "SETTINGS", fonts["medium"], on_settings),
            Button((cx - btn_w // 2, start_y + 3 * (btn_h + gap), btn_w, btn_h), "EXIT", fonts["medium"], on_exit),
        ]
        self._phase = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        self._phase += dt

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((12, 14, 28))
        cx = SCREEN_WIDTH // 2
        draw_text(surface, "ELEMENTX", self.fonts["title"], COLOR_ACCENT, (cx, 150), center=True)
        draw_text(surface, "AI GESTURE BATTLE", self.fonts["medium"], (230, 230, 235), (cx, 210), center=True)
        draw_text(surface, "\"Your Hands. Your Power. Your Battle.\"", self.fonts["small"], (170, 170, 185),
                  (cx, 250), center=True)
        for b in self.buttons:
            b.draw(surface)


class HowToPlayScreen:
    def __init__(self, fonts: dict, on_back) -> None:
        self.fonts = fonts
        self.back_button = Button((40, SCREEN_HEIGHT - 80, 160, 48), "BACK", fonts["small"], on_back)
        self.gesture_rows = [
            ("OPEN PALM", "Activate Shield — block incoming attacks"),
            ("FIST", "Basic Attack — energy punch"),
            ("ONE FINGER", "Lightning Attack — fast, medium damage"),
            ("TWO FINGERS", "Wind Attack — area damage"),
            ("THREE FINGERS", "Energy Blast — high damage"),
            ("THUMBS UP", "Heal — recover a little HP"),
            ("BOTH HANDS OPEN", "Ultimate Attack — needs full energy"),
            ("LEFT HAND MOVE", "Move your character left / right"),
        ]

    def handle_event(self, event: pygame.event.Event) -> None:
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((14, 16, 30))
        cx = SCREEN_WIDTH // 2
        draw_text(surface, "HOW TO PLAY", self.fonts["large"], COLOR_ACCENT, (cx, 60), center=True)

        y = 130
        for gesture, desc in self.gesture_rows:
            draw_text(surface, gesture, self.fonts["medium"], (255, 210, 60), (140, y))
            draw_text(surface, desc, self.fonts["small"], (220, 220, 225), (420, y + 6))
            y += 52

        draw_text(surface, "KEYBOARD FALLBACK (if webcam unavailable):", self.fonts["small"],
                  (170, 170, 185), (140, y + 10))
        y += 40
        for key, desc in KEY_BINDINGS_HELP.items():
            draw_text(surface, f"{key}: {desc}", self.fonts["small"], (200, 200, 210), (160, y))
            y += 26

        self.back_button.draw(surface)


class SettingsScreen:
    def __init__(self, fonts: dict, on_back, get_settings: Callable[[], Dict],
                 set_setting: Callable[[str, object], None]) -> None:
        self.fonts = fonts
        self.on_back = on_back
        self.get_settings = get_settings
        self.set_setting = set_setting
        self.back_button = Button((40, SCREEN_HEIGHT - 80, 160, 48), "BACK", fonts["small"], on_back)

        cx = SCREEN_WIDTH // 2
        self.volume_down = Button((cx + 40, 260, 44, 40), "-", fonts["medium"], lambda: self._adjust_volume(-0.1))
        self.volume_up = Button((cx + 100, 260, 44, 40), "+", fonts["medium"], lambda: self._adjust_volume(0.1))

        self.difficulty_buttons = [
            Button((cx + 40 + i * 90, 340, 80, 40), name, fonts["small"], (lambda n=name: self._set_difficulty(n)))
            for i, name in enumerate(["EASY", "NORMAL", "HARD"])
        ]

        self.sensitivity_down = Button((cx + 40, 420, 44, 40), "-", fonts["medium"], lambda: self._adjust_sensitivity(-0.1))
        self.sensitivity_up = Button((cx + 100, 420, 44, 40), "+", fonts["medium"], lambda: self._adjust_sensitivity(0.1))

        self.camera_cycle = Button((cx + 40, 500, 200, 40), "CYCLE CAMERA", fonts["small"], self._cycle_camera)

    def _adjust_volume(self, delta: float) -> None:
        s = self.get_settings()
        self.set_setting("volume", max(0.0, min(1.0, s["volume"] + delta)))

    def _adjust_sensitivity(self, delta: float) -> None:
        s = self.get_settings()
        self.set_setting("sensitivity", max(0.3, min(1.0, s["sensitivity"] + delta)))

    def _set_difficulty(self, name: str) -> None:
        self.set_setting("difficulty", name)

    def _cycle_camera(self) -> None:
        s = self.get_settings()
        self.set_setting("camera_index", (s["camera_index"] + 1) % 4)

    def handle_event(self, event: pygame.event.Event) -> None:
        self.back_button.handle_event(event)
        self.volume_down.handle_event(event)
        self.volume_up.handle_event(event)
        self.sensitivity_down.handle_event(event)
        self.sensitivity_up.handle_event(event)
        self.camera_cycle.handle_event(event)
        for b in self.difficulty_buttons:
            b.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((14, 16, 30))
        cx = SCREEN_WIDTH // 2
        draw_text(surface, "SETTINGS", self.fonts["large"], COLOR_ACCENT, (cx, 60), center=True)

        s = self.get_settings()
        draw_text(surface, f"Volume: {int(s['volume'] * 100)}%", self.fonts["medium"], (230, 230, 235), (cx - 300, 270))
        self.volume_down.draw(surface)
        self.volume_up.draw(surface)

        draw_text(surface, "Difficulty:", self.fonts["medium"], (230, 230, 235), (cx - 300, 350))
        for b in self.difficulty_buttons:
            selected = b.text == s["difficulty"]
            b.border_color = (255, 210, 60) if selected else (120, 120, 140)
            b.draw(surface)

        draw_text(surface, f"Gesture sensitivity: {int(s['sensitivity'] * 100)}%", self.fonts["medium"],
                  (230, 230, 235), (cx - 300, 430))
        self.sensitivity_down.draw(surface)
        self.sensitivity_up.draw(surface)

        draw_text(surface, f"Camera index: {s['camera_index']}", self.fonts["medium"], (230, 230, 235), (cx - 300, 510))
        self.camera_cycle.draw(surface)

        self.back_button.draw(surface)

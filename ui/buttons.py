"""
ui/buttons.py
A small reusable Button widget for menu/settings screens, with hover
and click states, used to keep menu.py declarative and clean.
"""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import pygame

from utils.helpers import draw_text


class Button:
    def __init__(
        self,
        rect: Tuple[int, int, int, int],
        text: str,
        font: pygame.font.Font,
        on_click: Optional[Callable[[], None]] = None,
        base_color: Tuple[int, int, int] = (40, 44, 70),
        hover_color: Tuple[int, int, int] = (70, 78, 120),
        text_color: Tuple[int, int, int] = (240, 240, 245),
        border_color: Tuple[int, int, int] = (255, 200, 60),
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.on_click = on_click
        self.base_color = base_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.hovered = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        color = self.hover_color if self.hovered else self.base_color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        border_w = 3 if self.hovered else 1
        pygame.draw.rect(surface, self.border_color, self.rect, width=border_w, border_radius=10)
        draw_text(surface, self.text, self.font, self.text_color, self.rect.center, center=True)

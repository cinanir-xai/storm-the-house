"""
Background decoration layer – distant dunes / hills along the horizon
and a small fence near the house.

Rendered between sky and ground for depth.
"""

import math
import random
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HORIZON_Y_RATIO,
    SAND_FAR, SAND_DARK,
)
from storm_the_house.utils.drawing import lerp_color


class BackgroundRenderer:
    """Draws distant dunes, horizon detail, and a perimeter fence."""

    def __init__(self):
        self.horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        self._dunes_cache = self._generate_dunes()
        self._fence_cache = self._generate_fence()

    # ── dunes ─────────────────────────────────────────────────────────────

    def _generate_dunes(self) -> pygame.Surface:
        """Pre-render layered sand dunes along the horizon."""
        surf = pygame.Surface((SCREEN_WIDTH, 80), pygame.SRCALPHA)

        layers = [
            {"amp": 18, "freq": 0.004, "phase": 0.0,
             "color": lerp_color(SAND_FAR, (175, 155, 120), 0.3), "y_off": 30},
            {"amp": 12, "freq": 0.007, "phase": 1.5,
             "color": lerp_color(SAND_FAR, (185, 162, 125), 0.15), "y_off": 40},
            {"amp": 8, "freq": 0.012, "phase": 3.0,
             "color": SAND_FAR, "y_off": 50},
        ]

        for layer in layers:
            points = []
            for x in range(SCREEN_WIDTH + 1):
                y = layer["y_off"] - layer["amp"] * math.sin(
                    layer["freq"] * x + layer["phase"])
                points.append((x, int(y)))
            # Close the polygon at the bottom
            points.append((SCREEN_WIDTH, 80))
            points.append((0, 80))
            pygame.draw.polygon(surf, layer["color"], points)

        return surf

    # ── fence ─────────────────────────────────────────────────────────────

    def _generate_fence(self) -> pygame.Surface:
        """Pre-render a small wooden fence that runs across the ground."""
        fence_h = 60
        surf = pygame.Surface((SCREEN_WIDTH, fence_h), pygame.SRCALPHA)

        post_color = (120, 80, 45)
        rail_color = (130, 90, 50)
        highlight = (150, 110, 65)

        fence_y_top = 15
        fence_y_bot = fence_h - 8
        post_spacing = 60

        # Horizontal rails
        for ry in [fence_y_top + 5, fence_y_top + 22]:
            pygame.draw.line(surf, rail_color, (0, ry), (SCREEN_WIDTH, ry), 3)
            pygame.draw.line(surf, highlight, (0, ry - 1),
                             (SCREEN_WIDTH, ry - 1), 1)

        # Vertical posts
        for x in range(0, SCREEN_WIDTH, post_spacing):
            pw = 6
            pygame.draw.rect(surf, post_color,
                             pygame.Rect(x, fence_y_top, pw, fence_y_bot - fence_y_top))
            # Pointed top
            pygame.draw.polygon(surf, post_color, [
                (x, fence_y_top),
                (x + pw, fence_y_top),
                (x + pw // 2, fence_y_top - 6),
            ])
            # Highlight
            pygame.draw.line(surf, highlight,
                             (x + 1, fence_y_top - 4),
                             (x + 1, fence_y_bot), 1)

        return surf

    # ── public ────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time_ms: int):
        """Blit dunes and fence."""
        # Dunes right at the horizon
        surface.blit(self._dunes_cache, (0, self.horizon_y - 30))

        # Fence about 60 % down the ground area
        fence_y = self.horizon_y + int((SCREEN_HEIGHT - self.horizon_y) * 0.42)
        surface.blit(self._fence_cache, (0, fence_y))

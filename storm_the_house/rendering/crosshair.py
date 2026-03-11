"""
Crosshair cursor – replaces the system cursor with a custom crosshair.

Features:
  - Four lines with a gap in the center
  - Center dot
  - Drop shadow for visibility on any background
  - Radial arc showing reload progress
"""

from __future__ import annotations

import math
import pygame

from storm_the_house.core.settings import (
    CROSSHAIR_SIZE, CROSSHAIR_GAP, CROSSHAIR_THICK,
    CROSSHAIR_COLOR, CROSSHAIR_SHADOW, CROSSHAIR_DOT,
    RELOAD_ARC_RADIUS, RELOAD_ARC_THICK,
    RELOAD_ARC_BG, RELOAD_ARC_FG,
)


class CrosshairRenderer:
    """Draws a crosshair at the mouse position with optional reload arc."""

    def draw(self, surface: pygame.Surface, reload_progress: float = 0.0,
             recoil_offset: tuple[int, int] = (0, 0)):
        """
        Draw the crosshair at the current mouse position.

        *reload_progress* is 0.0 (not reloading) to 1.0 (reload complete).
        *recoil_offset* is a small (x, y) jitter applied for recoil feedback.
        """
        mx, my = pygame.mouse.get_pos()
        mx += recoil_offset[0]
        my += recoil_offset[1]

        # ── reload arc (behind crosshair) ───────────────────────────────
        if reload_progress > 0.0:
            self._draw_reload_arc(surface, mx, my, reload_progress)

        # ── shadow layer (offset by 1px) ────────────────────────────────
        self._draw_cross(surface, mx + 1, my + 1, CROSSHAIR_SHADOW[:3],
                         CROSSHAIR_THICK + 1, alpha=CROSSHAIR_SHADOW[3])

        # ── main crosshair ──────────────────────────────────────────────
        self._draw_cross(surface, mx, my, CROSSHAIR_COLOR, CROSSHAIR_THICK)

        # ── center dot ──────────────────────────────────────────────────
        pygame.draw.circle(surface, CROSSHAIR_COLOR, (mx, my), CROSSHAIR_DOT)

    # ── internals ───────────────────────────────────────────────────────

    @staticmethod
    def _draw_cross(surface: pygame.Surface, cx: int, cy: int,
                    color: tuple, thick: int, alpha: int | None = None):
        """Draw the four crosshair lines around (cx, cy)."""
        gap = CROSSHAIR_GAP
        size = CROSSHAIR_SIZE

        lines = [
            ((cx - size, cy), (cx - gap, cy)),   # left
            ((cx + gap, cy), (cx + size, cy)),    # right
            ((cx, cy - size), (cx, cy - gap)),    # top
            ((cx, cy + gap), (cx, cy + size)),    # bottom
        ]

        if alpha is not None:
            # Use alpha surface for shadow
            d = size * 2 + 4
            tmp = pygame.Surface((d, d), pygame.SRCALPHA)
            ox, oy = cx - d // 2, cy - d // 2
            for (x1, y1), (x2, y2) in lines:
                pygame.draw.line(tmp, (*color, alpha),
                                 (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), thick)
            surface.blit(tmp, (ox, oy))
        else:
            for (x1, y1), (x2, y2) in lines:
                pygame.draw.line(surface, color, (x1, y1), (x2, y2), thick)

    @staticmethod
    def _draw_reload_arc(surface: pygame.Surface, cx: int, cy: int,
                         progress: float):
        """Draw a radial arc around the crosshair showing reload progress."""
        r = RELOAD_ARC_RADIUS
        thick = RELOAD_ARC_THICK
        d = (r + thick) * 2 + 4
        tmp = pygame.Surface((d, d), pygame.SRCALPHA)
        center = (d // 2, d // 2)

        # Background ring (dim)
        pygame.draw.circle(tmp, RELOAD_ARC_BG, center, r, thick)

        # Foreground arc – draw as a series of small segments for smooth arc
        start_angle = -math.pi / 2  # 12 o'clock
        end_angle = start_angle + 2 * math.pi * progress
        num_segments = max(4, int(60 * progress))

        points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            angle = start_angle + t * (end_angle - start_angle)
            px = center[0] + math.cos(angle) * r
            py = center[1] + math.sin(angle) * r
            points.append((px, py))

        if len(points) >= 2:
            pygame.draw.lines(tmp, RELOAD_ARC_FG, False, points, thick)

            # Bright tip at the leading edge
            tip = points[-1]
            pygame.draw.circle(tmp, (255, 230, 120), (int(tip[0]), int(tip[1])),
                               thick)

        surface.blit(tmp, (cx - d // 2, cy - d // 2))

"""
Drawing utility helpers used across the rendering pipeline.
"""

import pygame
import math


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linearly interpolate between two RGB(A) colors."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def vertical_gradient(surface: pygame.Surface, top_color: tuple,
                      bottom_color: tuple, rect: pygame.Rect | None = None):
    """Draw a smooth vertical gradient on *surface* within *rect*."""
    if rect is None:
        rect = surface.get_rect()
    for y in range(rect.height):
        t = y / max(rect.height - 1, 1)
        color = lerp_color(top_color, bottom_color, t)
        pygame.draw.line(surface, color,
                         (rect.x, rect.y + y),
                         (rect.x + rect.width, rect.y + y))


def draw_ellipse_alpha(surface: pygame.Surface, color: tuple,
                       rect: pygame.Rect):
    """Draw an ellipse with per-pixel alpha onto *surface*."""
    tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.ellipse(tmp, color, tmp.get_rect())
    surface.blit(tmp, rect.topleft)


def draw_rect_alpha(surface: pygame.Surface, color: tuple,
                    rect: pygame.Rect):
    """Draw a rectangle with per-pixel alpha onto *surface*."""
    tmp = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    tmp.fill(color)
    surface.blit(tmp, rect.topleft)


def draw_rounded_rect(surface: pygame.Surface, color: tuple,
                      rect: pygame.Rect, radius: int):
    """Draw a rounded rectangle."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def ease_in_out(t: float) -> float:
    """Smooth ease-in-out curve (cubic)."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def oscillate(time_ms: int, period_ms: int, low: float = 0.0,
              high: float = 1.0) -> float:
    """Return a value oscillating smoothly between *low* and *high*."""
    t = (math.sin(2 * math.pi * time_ms / period_ms) + 1) / 2
    return low + (high - low) * t

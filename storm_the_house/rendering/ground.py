"""
Ground / terrain renderer – sand-colored ground with subtle detail.

The camera looks at the ground at an angle, so objects further from the
camera (near the horizon) are compressed vertically and lighter in color,
giving a pseudo-3D perspective feel.
"""

import math
import random
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HORIZON_Y_RATIO,
    SAND_NEAR, SAND_FAR, SAND_DARK,
    NUM_GROUND_TUFTS, NUM_GROUND_PEBBLES, NUM_GROUND_DUST_PARTICLES,
)
from storm_the_house.utils.drawing import (
    vertical_gradient, lerp_color, draw_ellipse_alpha,
)


# ── Static detail objects ────────────────────────────────────────────────────

class _Tuft:
    """A small grass / scrub tuft on the sand."""

    def __init__(self, horizon_y: int):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(horizon_y + 10, SCREEN_HEIGHT - 10)
        depth = (self.y - horizon_y) / (SCREEN_HEIGHT - horizon_y)
        self.scale = 0.3 + depth * 0.7
        self.blades = random.randint(3, 6)
        self.color_base = lerp_color((140, 155, 100), (120, 140, 85),
                                     random.random())
        self.sway_offset = random.random() * math.pi * 2

    def draw(self, surface: pygame.Surface, time_ms: int):
        sway = math.sin(time_ms / 1200.0 + self.sway_offset) * 2 * self.scale
        h = int(8 * self.scale)
        for i in range(self.blades):
            angle_spread = (i - self.blades / 2) * 0.25
            tip_x = self.x + int((angle_spread * 6 + sway) * self.scale)
            tip_y = self.y - h
            color = lerp_color(self.color_base, (100, 120, 70),
                               abs(angle_spread) * 0.5)
            pygame.draw.line(surface, color,
                             (self.x, self.y), (tip_x, tip_y),
                             max(1, int(1.5 * self.scale)))


class _Pebble:
    """A tiny pebble on the ground."""

    def __init__(self, horizon_y: int):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(horizon_y + 5, SCREEN_HEIGHT - 5)
        depth = (self.y - horizon_y) / (SCREEN_HEIGHT - horizon_y)
        self.radius = max(1, int((1 + random.random() * 2) * (0.3 + depth * 0.7)))
        base = random.randint(140, 175)
        self.color = (base, base - 10, base - 25)

    def draw(self, surface: pygame.Surface):
        pygame.draw.circle(surface, self.color,
                           (self.x, self.y), self.radius)
        # Tiny highlight
        if self.radius > 1:
            pygame.draw.circle(surface,
                               tuple(min(255, c + 35) for c in self.color),
                               (self.x - 1, self.y - 1), max(1, self.radius // 2))


# ── Floating dust mote ──────────────────────────────────────────────────────

class _DustMote:
    """A slowly drifting dust particle for atmosphere."""

    def __init__(self, horizon_y: int):
        self.horizon_y = horizon_y
        self.reset()

    def reset(self):
        self.x = random.uniform(0, SCREEN_WIDTH)
        self.y = random.uniform(self.horizon_y + 20, SCREEN_HEIGHT - 30)
        self.vx = random.uniform(3, 12)
        self.vy = random.uniform(-2, 2)
        self.alpha = random.randint(25, 70)
        self.radius = random.uniform(1.0, 2.5)
        self.life = random.uniform(4.0, 10.0)
        self.age = 0.0

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.age += dt
        if self.age > self.life or self.x > SCREEN_WIDTH + 10:
            self.reset()
            self.x = random.uniform(-20, 0)

    def draw(self, surface: pygame.Surface):
        fade = 1.0 - (self.age / self.life)
        a = int(self.alpha * fade)
        if a < 5:
            return
        r = max(1, int(self.radius))
        dust_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(dust_surf, (220, 200, 170, a), (r, r), r)
        surface.blit(dust_surf, (int(self.x) - r, int(self.y) - r))


# ── Public GroundRenderer ───────────────────────────────────────────────────

class GroundRenderer:
    """Renders the sand-colored ground plane with perspective gradient."""

    def __init__(self):
        self.horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        self.ground_h = SCREEN_HEIGHT - self.horizon_y

        # Pre-render base gradient
        self._base_cache = pygame.Surface(
            (SCREEN_WIDTH, self.ground_h))
        vertical_gradient(self._base_cache, SAND_FAR, SAND_NEAR)

        # Add subtle horizontal stripe variation for texture
        self._add_texture(self._base_cache)

        # Static detail objects
        self._tufts = [_Tuft(self.horizon_y) for _ in range(NUM_GROUND_TUFTS)]
        self._pebbles = [_Pebble(self.horizon_y)
                         for _ in range(NUM_GROUND_PEBBLES)]
        self._dust = [_DustMote(self.horizon_y)
                      for _ in range(NUM_GROUND_DUST_PARTICLES)]

        # Horizon haze line (pre-render)
        self._haze = pygame.Surface((SCREEN_WIDTH, 12), pygame.SRCALPHA)
        for y in range(12):
            alpha = int(60 * (1 - y / 12))
            pygame.draw.line(self._haze, (230, 220, 200, alpha),
                             (0, y), (SCREEN_WIDTH, y))

    @staticmethod
    def _add_texture(surf: pygame.Surface):
        """Paint subtle sand-ripple lines for visual texture."""
        w, h = surf.get_size()
        for y in range(0, h, 6):
            depth = y / h
            alpha = int(12 + depth * 10)
            stripe = pygame.Surface((w, 1), pygame.SRCALPHA)
            stripe.fill((0, 0, 0, alpha if y % 12 == 0 else alpha // 2))
            surf.blit(stripe, (0, y))

    # ── tick ──────────────────────────────────────────────────────────────
    def update(self, dt: float):
        for d in self._dust:
            d.update(dt)

    # ── draw ──────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, time_ms: int):
        # Base sand gradient
        surface.blit(self._base_cache, (0, self.horizon_y))

        # Horizon haze
        surface.blit(self._haze, (0, self.horizon_y - 2))

        # Pebbles (behind tufts)
        for p in self._pebbles:
            p.draw(surface)

        # Grass tufts
        for t in self._tufts:
            t.draw(surface, time_ms)

        # Dust motes
        for d in self._dust:
            d.draw(surface)

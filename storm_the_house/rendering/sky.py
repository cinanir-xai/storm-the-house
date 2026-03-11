"""
Sky renderer – dynamic gradient background, animated sun arc, and drifting clouds.

The sky changes colour throughout the day based on ``day_progress`` (0 → 1).
The sun follows a parabolic arc from the left horizon to the right horizon.

All visuals are procedurally generated (no external assets).
"""

import math
import random
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HORIZON_Y_RATIO,
    CLOUD_COLOR, CLOUD_SHADOW,
    NUM_CLOUDS, CLOUD_MIN_SPEED, CLOUD_MAX_SPEED,
    CLOUD_MIN_SCALE, CLOUD_MAX_SCALE,
    # Day / sky
    SKY_MORNING_TOP, SKY_MORNING_HOR,
    SKY_NOON_TOP, SKY_NOON_HOR,
    SKY_EVENING_TOP, SKY_EVENING_HOR,
    SKY_SUNSET_TOP2, SKY_SUNSET_HOR2,
    SUN_RADIUS, SUN_ARC_LEFT_X, SUN_ARC_RIGHT_X,
    SUN_ARC_PEAK_Y, SUN_ARC_HORIZON_Y,
)
from storm_the_house.utils.drawing import lerp_color


# ── Colour interpolation helpers ─────────────────────────────────────────────

# Sky colour keyframes: (time_fraction, top_colour, horizon_colour)
_SKY_STOPS: list[tuple[float, tuple, tuple]] = [
    (0.00, SKY_MORNING_TOP, SKY_MORNING_HOR),
    (0.15, SKY_MORNING_TOP, SKY_MORNING_HOR),
    (0.35, SKY_NOON_TOP,    SKY_NOON_HOR),
    (0.65, SKY_NOON_TOP,    SKY_NOON_HOR),
    (0.82, SKY_EVENING_TOP, SKY_EVENING_HOR),
    (0.95, SKY_SUNSET_TOP2, SKY_SUNSET_HOR2),
    (1.00, SKY_SUNSET_TOP2, SKY_SUNSET_HOR2),
]

# Sun disc colour keyframes: (time_fraction, core_colour, glow_colour, glow_alpha)
_SUN_STOPS: list[tuple[float, tuple, tuple, int]] = [
    (0.00, (255, 200, 110), (255, 180, 80),  50),
    (0.15, (255, 245, 200), (255, 240, 180), 35),
    (0.35, (255, 255, 230), (255, 255, 210), 28),
    (0.65, (255, 255, 230), (255, 255, 210), 28),
    (0.82, (255, 230, 160), (255, 200, 120), 40),
    (0.95, (255, 160, 60),  (255, 120, 40),  55),
    (1.00, (255, 120, 40),  (255, 90, 30),   60),
]


def _lerp_stops(stops, t: float):
    """Linearly interpolate between adjacent colour-stop entries."""
    if t <= stops[0][0]:
        return stops[0]
    if t >= stops[-1][0]:
        return stops[-1]
    for i in range(len(stops) - 1):
        t0 = stops[i][0]
        t1 = stops[i + 1][0]
        if t0 <= t <= t1:
            frac = (t - t0) / max(t1 - t0, 1e-9)
            a = stops[i]
            b = stops[i + 1]
            # Interpolate every element after the time key
            result = [t]
            for j in range(1, len(a)):
                if isinstance(a[j], tuple):
                    result.append(lerp_color(a[j], b[j], frac))
                else:
                    result.append(int(a[j] + (b[j] - a[j]) * frac))
            return tuple(result)
    return stops[-1]


# ── Cloud helper ─────────────────────────────────────────────────────────────

class _Cloud:
    """A single procedurally-drawn cloud that drifts across the sky."""

    def __init__(self, x: float | None = None):
        self.scale = random.uniform(CLOUD_MIN_SCALE, CLOUD_MAX_SCALE)
        self.speed = random.uniform(CLOUD_MIN_SPEED, CLOUD_MAX_SPEED)
        horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        self.y = random.randint(20, horizon_y - 40)
        self.x = x if x is not None else random.uniform(-200, SCREEN_WIDTH + 100)
        self.alpha = random.randint(160, 220)
        self._surface = self._generate()

    def _generate(self) -> pygame.Surface:
        base_w = int(140 * self.scale)
        base_h = int(50 * self.scale)
        surf = pygame.Surface((base_w + 40, base_h + 30), pygame.SRCALPHA)

        blobs = [
            (0.50, 0.55, 0.60, 0.55),
            (0.20, 0.60, 0.40, 0.45),
            (0.65, 0.58, 0.45, 0.48),
            (0.35, 0.40, 0.50, 0.40),
            (0.55, 0.65, 0.35, 0.38),
        ]
        sw, sh = surf.get_size()
        for (rx, ry, rw, rh) in blobs:
            ex, ey = int(rx * sw), int(ry * sh) + 4
            ew, eh = int(rw * sw), int(rh * sh)
            pygame.draw.ellipse(surf, (*CLOUD_SHADOW, self.alpha // 2),
                                pygame.Rect(ex - ew // 2, ey - eh // 2, ew, eh))
        for (rx, ry, rw, rh) in blobs:
            ex, ey = int(rx * sw), int(ry * sh)
            ew, eh = int(rw * sw), int(rh * sh)
            pygame.draw.ellipse(surf, (*CLOUD_COLOR, self.alpha),
                                pygame.Rect(ex - ew // 2, ey - eh // 2, ew, eh))
        # Highlight
        hx, hy = int(0.42 * sw), int(0.35 * sh)
        hw, hh = int(0.30 * sw), int(0.22 * sh)
        pygame.draw.ellipse(surf, (*CLOUD_COLOR, min(255, self.alpha + 30)),
                            pygame.Rect(hx - hw // 2, hy - hh // 2, hw, hh))
        return surf

    def update(self, dt: float):
        self.x += self.speed * dt

    def draw(self, surface: pygame.Surface):
        surface.blit(self._surface, (int(self.x), int(self.y)))

    @property
    def off_screen(self) -> bool:
        return self.x > SCREEN_WIDTH + 250


# ── Sun position ─────────────────────────────────────────────────────────────

def _sun_position(t: float) -> tuple[int, int]:
    """Return (x, y) of the sun centre for day-progress *t* (0 → 1).

    The sun follows a parabolic arc: high at noon (t=0.5), at the horizon
    at t=0 and t=1.
    """
    left_x = SCREEN_WIDTH * SUN_ARC_LEFT_X
    right_x = SCREEN_WIDTH * SUN_ARC_RIGHT_X
    x = left_x + (right_x - left_x) * t

    # Parabola: y = horizon at t=0 and t=1, peak at t=0.5
    horizon_y = SCREEN_HEIGHT * SUN_ARC_HORIZON_Y
    peak_y = SCREEN_HEIGHT * SUN_ARC_PEAK_Y
    # y(t) = horizon - 4*(horizon-peak)*t*(1-t)
    y = horizon_y - 4.0 * (horizon_y - peak_y) * t * (1.0 - t)
    return int(x), int(y)


# ── Public SkyRenderer ───────────────────────────────────────────────────────

class SkyRenderer:
    """Manages dynamic sky gradient, moving sun, and cloud layer."""

    def __init__(self):
        self.horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        self._gradient_surf = pygame.Surface(
            (SCREEN_WIDTH, self.horizon_y), pygame.SRCALPHA)
        self._clouds: list[_Cloud] = [_Cloud() for _ in range(NUM_CLOUDS)]
        self._last_top: tuple | None = None
        self._last_hor: tuple | None = None

    # ── gradient cache ────────────────────────────────────────────────────

    def _rebuild_gradient(self, top_color: tuple, hor_color: tuple):
        """Re-render the vertical gradient only when the colours change."""
        # Quantise to avoid rebuilding every single frame
        qt = tuple(int(c) for c in top_color)
        qh = tuple(int(c) for c in hor_color)
        if qt == self._last_top and qh == self._last_hor:
            return
        self._last_top = qt
        self._last_hor = qh
        for y in range(self.horizon_y):
            t = y / max(self.horizon_y - 1, 1)
            color = lerp_color(qt, qh, t)
            pygame.draw.line(self._gradient_surf, color, (0, y),
                             (SCREEN_WIDTH, y))

    # ── tick ──────────────────────────────────────────────────────────────

    def update(self, dt: float):
        for c in self._clouds:
            c.update(dt)
        self._clouds = [c for c in self._clouds if not c.off_screen]
        while len(self._clouds) < NUM_CLOUDS:
            self._clouds.append(_Cloud(x=random.uniform(-300, -100)))

    # ── draw ──────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time_ms: int,
             day_progress: float = 0.5):
        """Render sky, sun, and clouds.

        *day_progress* is 0.0 (sunrise) → 1.0 (sunset).
        """
        dp = max(0.0, min(1.0, day_progress))

        # ── sky gradient ──────────────────────────────────────────────
        _, top_col, hor_col = _lerp_stops(_SKY_STOPS, dp)
        self._rebuild_gradient(top_col, hor_col)
        surface.blit(self._gradient_surf, (0, 0))

        # ── sun ───────────────────────────────────────────────────────
        self._draw_sun(surface, time_ms, dp)

        # ── clouds ────────────────────────────────────────────────────
        for c in sorted(self._clouds, key=lambda cl: cl.y):
            c.draw(surface)

    # ── sun drawing ───────────────────────────────────────────────────

    def _draw_sun(self, surface: pygame.Surface, time_ms: int,
                  dp: float):
        cx, cy = _sun_position(dp)
        radius = SUN_RADIUS

        # Interpolate sun colours
        _, core_col, glow_col, glow_alpha = _lerp_stops(_SUN_STOPS, dp)

        # Outer glow rings
        for i in range(6, 0, -1):
            r = radius + i * 12
            a = max(6, glow_alpha - i * 7)
            glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*glow_col, a), (r, r), r)
            surface.blit(glow_surf, (cx - r, cy - r))

        # Sun disc
        pygame.draw.circle(surface, core_col, (cx, cy), radius)
        # Highlight
        highlight = lerp_color(core_col, (255, 255, 255), 0.35)
        pygame.draw.circle(surface, highlight,
                           (cx - radius // 5, cy - radius // 5),
                           radius - max(4, radius // 4))

        # Animated rays
        num_rays = 10
        ray_size = radius + 50
        ray_surf = pygame.Surface((ray_size * 2, ray_size * 2), pygame.SRCALPHA)
        phase = time_ms / 4000.0 * math.pi * 2
        ray_alpha = max(20, min(55, glow_alpha + 5))
        for i in range(num_rays):
            angle = phase + i * (2 * math.pi / num_rays)
            inner_r = radius + 8
            outer_r = radius + 22 + 6 * math.sin(time_ms / 2000.0 + i)
            x1 = ray_size + math.cos(angle) * inner_r
            y1 = ray_size + math.sin(angle) * inner_r
            x2 = ray_size + math.cos(angle) * outer_r
            y2 = ray_size + math.sin(angle) * outer_r
            pygame.draw.line(ray_surf, (*glow_col, ray_alpha),
                             (int(x1), int(y1)), (int(x2), int(y2)), 2)
        surface.blit(ray_surf, (cx - ray_size, cy - ray_size))

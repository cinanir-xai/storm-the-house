"""
Background decoration layer – distant dunes / hills along the horizon
and a small fence near the house, plus vegetation and dead trees.

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
    """Draws distant dunes, horizon detail, a perimeter fence, and vegetation."""

    def __init__(self):
        self.horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        self._dunes_cache = self._generate_dunes()
        self._fence_cache = self._generate_fence()
        # Generate random vegetation for this day
        self._grass_tufts = self._generate_grass_tufts()
        self._bushes = self._generate_bushes()
        self._dead_trees = self._generate_dead_trees()

    def regenerate_decorations(self):
        """Regenerate random decorations for a new day."""
        self._grass_tufts = self._generate_grass_tufts()
        self._bushes = self._generate_bushes()
        self._dead_trees = self._generate_dead_trees()

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

    # ── vegetation ───────────────────────────────────────────────────────

    def _generate_grass_tufts(self) -> list[tuple[int, int, float]]:
        """Generate random dried grass tuft positions."""
        tufts = []
        ground_h = SCREEN_HEIGHT - self.horizon_y
        for _ in range(random.randint(25, 45)):
            x = random.randint(0, SCREEN_WIDTH)
            # Place in lower half of ground area
            y = self.horizon_y + int(ground_h * random.uniform(0.3, 0.9))
            scale = random.uniform(0.6, 1.2)
            tufts.append((x, y, scale))
        return tufts

    def _generate_bushes(self) -> list[tuple[int, int, float]]:
        """Generate random dead bush positions."""
        bushes = []
        ground_h = SCREEN_HEIGHT - self.horizon_y
        for _ in range(random.randint(8, 15)):
            x = random.randint(0, SCREEN_WIDTH)
            y = self.horizon_y + int(ground_h * random.uniform(0.2, 0.7))
            scale = random.uniform(0.7, 1.3)
            bushes.append((x, y, scale))
        return bushes

    def _generate_dead_trees(self) -> list[tuple[int, int, float]]:
        """Generate random dead tree positions."""
        trees = []
        ground_h = SCREEN_HEIGHT - self.horizon_y
        for _ in range(random.randint(0, 3)):
            x = random.randint(50, SCREEN_WIDTH - 50)
            y = self.horizon_y + int(ground_h * random.uniform(0.15, 0.4))
            scale = random.uniform(0.8, 1.4)
            trees.append((x, y, scale))
        return trees

    def _draw_grass_tuft(self, surface: pygame.Surface, x: int, y: int, scale: float):
        """Draw a single dried grass tuft."""
        blade_col = (160, 140, 90)
        blade_dark = (130, 110, 70)
        num_blades = random.randint(5, 9)
        for i in range(num_blades):
            angle = random.uniform(-0.5, 0.5)
            length = int(random.uniform(8, 16) * scale)
            bx = x + int(random.uniform(-4, 4) * scale)
            bend = random.uniform(-3, 3) * scale
            # Draw curved blade
            points = [
                (bx, y),
                (bx + int(bend * 0.5), y - int(length * 0.5)),
                (bx + int(bend), y - length),
            ]
            col = blade_col if random.random() > 0.3 else blade_dark
            pygame.draw.lines(surface, col, False, points, max(1, int(scale)))

    def _draw_bush(self, surface: pygame.Surface, x: int, y: int, scale: float):
        """Draw a dead/dried bush."""
        bush_col = (140, 115, 75)
        bush_dark = (110, 90, 60)
        bush_light = (165, 140, 95)
        # Main bush body - multiple overlapping circles
        size = int(12 * scale)
        for _ in range(4):
            ox = int(random.uniform(-size * 0.5, size * 0.5))
            oy = int(random.uniform(-size * 0.3, size * 0.3))
            r = int(size * random.uniform(0.5, 0.9))
            col = random.choice([bush_col, bush_dark, bush_light])
            pygame.draw.circle(surface, col, (x + ox, y + oy), r)
        # Add some small stick details
        for _ in range(3):
            sx = x + int(random.uniform(-size, size))
            sy = y + int(random.uniform(-size * 0.5, size * 0.3))
            ex = sx + int(random.uniform(-6, 6) * scale)
            ey = sy - int(random.uniform(4, 10) * scale)
            pygame.draw.line(surface, bush_dark, (sx, sy), (ex, ey), max(1, int(scale * 0.7)))

    def _draw_dead_tree(self, surface: pygame.Surface, x: int, y: int, scale: float):
        """Draw a dead tree with bare branches."""
        trunk_col = (95, 70, 50)
        branch_col = (115, 90, 65)
        shadow_col = (70, 50, 35)

        trunk_h = int(50 * scale)
        trunk_w = int(8 * scale)

        # Shadow
        pygame.draw.ellipse(surface, (*shadow_col, 60),
                           pygame.Rect(x - int(15 * scale), y - 3, int(30 * scale), int(8 * scale)))

        # Trunk
        pygame.draw.polygon(surface, trunk_col, [
            (x - trunk_w // 2, y),
            (x + trunk_w // 2, y),
            (x + trunk_w // 3, y - trunk_h),
            (x - trunk_w // 3, y - trunk_h),
        ])

        # Main branches
        def draw_branch(sx, sy, angle, length, depth):
            if depth <= 0 or length < 4:
                return
            ex = sx + int(math.cos(angle) * length)
            ey = sy + int(math.sin(angle) * length)
            pygame.draw.line(surface, branch_col, (sx, sy), (ex, ey), max(1, int(2 * scale)))
            # Sub-branches
            if random.random() > 0.3:
                draw_branch(ex, ey, angle - random.uniform(0.3, 0.7), length * 0.65, depth - 1)
            if random.random() > 0.3:
                draw_branch(ex, ey, angle + random.uniform(0.3, 0.7), length * 0.65, depth - 1)

        # Main branches from top of trunk
        top_y = y - trunk_h
        branch_len = int(25 * scale)
        draw_branch(x, top_y, -math.pi * 0.7, branch_len, 3)  # left-up
        draw_branch(x, top_y, -math.pi * 0.3, branch_len, 3)  # right-up
        draw_branch(x - trunk_w // 3, top_y + int(10 * scale), -math.pi * 0.8, branch_len * 0.7, 2)
        draw_branch(x + trunk_w // 3, top_y + int(10 * scale), -math.pi * 0.2, branch_len * 0.7, 2)

    # ── public ────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time_ms: int):
        """Blit dunes, fence, and vegetation."""
        # Dunes right at the horizon
        surface.blit(self._dunes_cache, (0, self.horizon_y - 30))

        # Draw dead trees (behind fence)
        for tx, ty, ts in self._dead_trees:
            self._draw_dead_tree(surface, tx, ty, ts)

        # Draw bushes
        for bx, by, bs in self._bushes:
            self._draw_bush(surface, bx, by, bs)

        # Fence about 60 % down the ground area
        fence_y = self.horizon_y + int((SCREEN_HEIGHT - self.horizon_y) * 0.42)
        surface.blit(self._fence_cache, (0, fence_y))

        # Draw grass tufts (in front of fence)
        for gx, gy, gs in self._grass_tufts:
            self._draw_grass_tuft(surface, gx, gy, gs)


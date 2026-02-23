"""
House entity – the player's stronghold on the right side of the screen.

Drawn as a 3D-ish cube with an angled roof, windows, door, and chimney.
The house sits on the ground and covers most of the ground height.

When damaged, cracks, scorch marks, and a darkened tint appear
proportional to how much HP has been lost.
"""

import math
import random
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HORIZON_Y_RATIO,
    HOUSE_RIGHT_MARGIN, HOUSE_WIDTH_RATIO, HOUSE_HEIGHT_RATIO,
    HOUSE_WALL, HOUSE_WALL_LIGHT, HOUSE_WALL_DARK,
    HOUSE_ROOF, HOUSE_ROOF_EDGE,
    HOUSE_DOOR, HOUSE_WINDOW_FRAME, HOUSE_WINDOW_GLASS,
    HOUSE_WINDOW_GLASS_SHINE, HOUSE_CHIMNEY,
    HOUSE_MAX_HP, HOUSE_CRACK_COLOR, HOUSE_CRACK_SHADOW,
    HOUSE_SCORCH_COLOR,
)
from storm_the_house.utils.drawing import (
    lerp_color, draw_ellipse_alpha, oscillate,
)


# ── Crack generation ────────────────────────────────────────────────────────

def _generate_crack(cx: int, cy: int, length: int, branches: int,
                    seed: int) -> list[list[tuple[int, int]]]:
    """Generate a set of jagged crack lines originating near (cx, cy).

    Returns a list of polylines (each polyline is a list of (x, y) points).
    Deterministic for a given *seed* so cracks don't jitter each frame.
    """
    rng = random.Random(seed)
    lines: list[list[tuple[int, int]]] = []

    for _ in range(branches):
        angle = rng.uniform(0, math.pi * 2)
        pts = [(cx + rng.randint(-3, 3), cy + rng.randint(-3, 3))]
        seg_len = max(4, length // rng.randint(3, 6))
        num_segs = rng.randint(3, 7)
        for _ in range(num_segs):
            angle += rng.uniform(-0.8, 0.8)
            nx = pts[-1][0] + int(math.cos(angle) * seg_len)
            ny = pts[-1][1] + int(math.sin(angle) * seg_len)
            pts.append((nx, ny))
            # Occasional sub-branch
            if rng.random() < 0.35:
                sub_angle = angle + rng.choice([-1, 1]) * rng.uniform(0.5, 1.2)
                sub_pts = [pts[-1]]
                for _ in range(rng.randint(1, 3)):
                    sub_angle += rng.uniform(-0.4, 0.4)
                    sx = sub_pts[-1][0] + int(math.cos(sub_angle) * seg_len * 0.6)
                    sy = sub_pts[-1][1] + int(math.sin(sub_angle) * seg_len * 0.6)
                    sub_pts.append((sx, sy))
                if len(sub_pts) >= 2:
                    lines.append(sub_pts)
        if len(pts) >= 2:
            lines.append(pts)
    return lines


class House:
    """The player's house drawn procedurally."""

    def __init__(self):
        self.horizon_y = int(SCREEN_HEIGHT * HORIZON_Y_RATIO)
        self.width = int(SCREEN_WIDTH * HOUSE_WIDTH_RATIO)
        self.height = int(SCREEN_HEIGHT * HOUSE_HEIGHT_RATIO)

        # Position: right side, sitting on the ground
        self.x = SCREEN_WIDTH - HOUSE_RIGHT_MARGIN - self.width
        self.y = SCREEN_HEIGHT - self.height - 20  # 20 px above bottom

        # 3D offset for the "side face" of the cube
        self.depth_offset = int(self.width * 0.25)

        # Health
        self.hp: int = HOUSE_MAX_HP
        self.max_hp: int = HOUSE_MAX_HP

        # Fortification level (0 = none, 1 = sandbags + boards, 2 = more + barbed wire)
        self.fortify_level: int = 0

        # Damage visuals – generated incrementally as HP drops
        self._cracks: list[tuple[list[list[tuple[int, int]]], int]] = []
        # Each entry: (crack_polylines, thickness)
        self._crack_seed: int = 0
        self._last_crack_hp: int = self.max_hp  # HP when last crack was added
        self._scorch_marks: list[tuple[int, int, int]] = []  # (x, y, radius)

        # Pre-render static house surface (rebuilt if needed)
        self._cache: pygame.Surface | None = None
        self._cache_time: int = -1

        # Window positions (computed once, reused for boarding)
        self._win_w = int(self.width * 0.2)
        self._win_h = int(self.height * 0.16)
        self._win_positions: list[tuple[int, int]] = []
        col_offsets = [0.2, 0.6]
        row_offsets = [0.2, 0.55]
        for ry in row_offsets:
            for cx in col_offsets:
                wx = self.x + int(self.width * cx) - self._win_w // 2
                wy = self.y + int(self.height * ry) - self._win_h // 2
                self._win_positions.append((wx, wy))

    # ── geometry helpers ──────────────────────────────────────────────────

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x, self.y, self.width, self.height)

    # ── rendering ─────────────────────────────────────────────────────────

    def _draw_shadow(self, surface: pygame.Surface):
        """Draw a ground shadow beneath the house."""
        shadow_w = self.width + 30
        shadow_h = 18
        shadow_x = self.x - 10
        shadow_y = self.y + self.height - 4
        draw_ellipse_alpha(surface, (0, 0, 0, 35),
                           pygame.Rect(shadow_x, shadow_y, shadow_w, shadow_h))

    def _draw_front_wall(self, surface: pygame.Surface):
        """Main front-facing wall."""
        wall_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, HOUSE_WALL, wall_rect)

        # Subtle vertical gradient overlay for depth
        for y_off in range(self.height):
            t = y_off / self.height
            color = lerp_color(HOUSE_WALL_LIGHT, HOUSE_WALL, t * 0.5)
            pygame.draw.line(surface, color,
                             (self.x, self.y + y_off),
                             (self.x + self.width, self.y + y_off))

        # Wall edge highlight (left edge catches light)
        pygame.draw.line(surface, HOUSE_WALL_LIGHT,
                         (self.x, self.y), (self.x, self.y + self.height), 2)

        # Wall border
        pygame.draw.rect(surface, HOUSE_WALL_DARK, wall_rect, 2)

    def _draw_side_wall(self, surface: pygame.Surface):
        """The right-side face of the cube (darker, in shadow)."""
        dx = self.depth_offset
        points = [
            (self.x + self.width, self.y),                    # top-left of side
            (self.x + self.width + dx, self.y - dx // 2),     # top-right
            (self.x + self.width + dx, self.y + self.height - dx // 2),  # bottom-right
            (self.x + self.width, self.y + self.height),      # bottom-left
        ]
        pygame.draw.polygon(surface, HOUSE_WALL_DARK, points)
        pygame.draw.polygon(surface, (90, 58, 32), points, 2)

        # Subtle vertical lines for wood plank texture
        num_planks = 4
        for i in range(1, num_planks):
            t = i / num_planks
            x1 = int(points[0][0] + (points[1][0] - points[0][0]) * t)
            y1 = int(points[0][1] + (points[1][1] - points[0][1]) * t)
            x2 = int(points[3][0] + (points[2][0] - points[3][0]) * t)
            y2 = int(points[3][1] + (points[2][1] - points[3][1]) * t)
            pygame.draw.line(surface, (95, 60, 35), (x1, y1), (x2, y2), 1)

    def _draw_roof(self, surface: pygame.Surface):
        """Triangular / sloped roof with overhang."""
        overhang = 12
        dx = self.depth_offset
        roof_h = int(self.height * 0.3)

        # Front roof face (triangle)
        peak_x = self.x + self.width // 2
        peak_y = self.y - roof_h
        front_points = [
            (self.x - overhang, self.y),
            (self.x + self.width + overhang, self.y),
            (peak_x, peak_y),
        ]
        pygame.draw.polygon(surface, HOUSE_ROOF, front_points)
        pygame.draw.polygon(surface, HOUSE_ROOF_EDGE, front_points, 2)

        # Right roof slope (3D face)
        side_peak_x = peak_x + dx
        side_peak_y = peak_y - dx // 2
        side_points = [
            (self.x + self.width + overhang, self.y),
            (self.x + self.width + dx + overhang // 2, self.y - dx // 2),
            (side_peak_x, side_peak_y),
            (peak_x, peak_y),
        ]
        darker_roof = tuple(max(0, c - 20) for c in HOUSE_ROOF)
        pygame.draw.polygon(surface, darker_roof, side_points)
        pygame.draw.polygon(surface, HOUSE_ROOF_EDGE, side_points, 2)

        # Roof highlight line along the ridge
        pygame.draw.line(surface, lerp_color(HOUSE_ROOF, (200, 180, 160), 0.3),
                         (peak_x, peak_y), (side_peak_x, side_peak_y), 3)

    def _draw_chimney(self, surface: pygame.Surface):
        """Small chimney on the right side of the roof."""
        dx = self.depth_offset
        roof_h = int(self.height * 0.3)
        ch_w = int(self.width * 0.12)
        ch_h = int(roof_h * 0.7)
        ch_x = self.x + int(self.width * 0.7)
        ch_y = self.y - roof_h + int(roof_h * 0.15)

        # Front face
        pygame.draw.rect(surface, HOUSE_CHIMNEY,
                         pygame.Rect(ch_x, ch_y, ch_w, ch_h))
        pygame.draw.rect(surface, HOUSE_ROOF_EDGE,
                         pygame.Rect(ch_x, ch_y, ch_w, ch_h), 2)

        # Cap
        pygame.draw.rect(surface, (75, 40, 20),
                         pygame.Rect(ch_x - 2, ch_y - 3, ch_w + 4, 5))

        # Side face
        side_points = [
            (ch_x + ch_w, ch_y),
            (ch_x + ch_w + dx // 3, ch_y - dx // 6),
            (ch_x + ch_w + dx // 3, ch_y + ch_h - dx // 6),
            (ch_x + ch_w, ch_y + ch_h),
        ]
        pygame.draw.polygon(surface, (80, 45, 22), side_points)
        pygame.draw.polygon(surface, HOUSE_ROOF_EDGE, side_points, 1)

    def _draw_windows(self, surface: pygame.Surface, time_ms: int):
        """Draw windows on the front wall."""
        win_w = self._win_w
        win_h = self._win_h
        frame_thick = 3

        for i, (wx, wy) in enumerate(self._win_positions):
            # Glass pane
            glass_rect = pygame.Rect(wx, wy, win_w, win_h)
            pygame.draw.rect(surface, HOUSE_WINDOW_GLASS, glass_rect)

            # Animated shimmer / glow
            shimmer = oscillate(time_ms, 5000, 0.0, 0.3)
            shine_color = lerp_color(HOUSE_WINDOW_GLASS,
                                     HOUSE_WINDOW_GLASS_SHINE, shimmer)
            shine_rect = pygame.Rect(wx + 3, wy + 3,
                                     win_w // 2 - 2, win_h // 2 - 2)
            shine_surf = pygame.Surface(
                (shine_rect.width, shine_rect.height), pygame.SRCALPHA)
            shine_surf.fill((*shine_color, 90))
            surface.blit(shine_surf, shine_rect.topleft)

            # Frame
            pygame.draw.rect(surface, HOUSE_WINDOW_FRAME, glass_rect,
                             frame_thick)
            # Cross bars
            mid_x = wx + win_w // 2
            mid_y = wy + win_h // 2
            pygame.draw.line(surface, HOUSE_WINDOW_FRAME,
                             (mid_x, wy), (mid_x, wy + win_h), 2)
            pygame.draw.line(surface, HOUSE_WINDOW_FRAME,
                             (wx, mid_y), (wx + win_w, mid_y), 2)

            # ── Boarding (fortification visuals) ──────────────────────
            if self.fortify_level >= 1:
                self._draw_window_boards(surface, wx, wy, win_w, win_h,
                                         level=self.fortify_level, idx=i)

    def _draw_door(self, surface: pygame.Surface):
        """Draw a door at the bottom-center of the front wall."""
        door_w = int(self.width * 0.2)
        door_h = int(self.height * 0.28)
        door_x = self.x + (self.width - door_w) // 2
        door_y = self.y + self.height - door_h

        door_rect = pygame.Rect(door_x, door_y, door_w, door_h)
        pygame.draw.rect(surface, HOUSE_DOOR, door_rect)

        # Arch top
        pygame.draw.ellipse(surface, HOUSE_DOOR,
                            pygame.Rect(door_x, door_y - door_w // 4,
                                        door_w, door_w // 2))

        # Border
        pygame.draw.rect(surface, (60, 35, 18), door_rect, 2)
        pygame.draw.ellipse(surface, (60, 35, 18),
                            pygame.Rect(door_x, door_y - door_w // 4,
                                        door_w, door_w // 2), 2)

        # Knob
        knob_x = door_x + door_w - 8
        knob_y = door_y + door_h // 2
        pygame.draw.circle(surface, (180, 160, 100), (knob_x, knob_y), 3)
        pygame.draw.circle(surface, (210, 195, 140), (knob_x - 1, knob_y - 1), 1)

        # Wood plank lines
        for i in range(1, 3):
            lx = door_x + door_w * i // 3
            pygame.draw.line(surface, (70, 40, 22),
                             (lx, door_y + 10), (lx, door_y + door_h), 1)

    def _draw_wood_texture(self, surface: pygame.Surface):
        """Add subtle horizontal plank lines to the front wall."""
        plank_spacing = int(self.height * 0.08)
        for i in range(1, self.height // plank_spacing):
            y = self.y + i * plank_spacing
            alpha = 18
            line_surf = pygame.Surface((self.width, 1), pygame.SRCALPHA)
            line_surf.fill((0, 0, 0, alpha))
            surface.blit(line_surf, (self.x, y))

    # ── damage visuals ───────────────────────────────────────────────────

    def _add_crack(self):
        """Add a new crack pattern on the front wall."""
        self._crack_seed += 1
        damage_frac = 1.0 - self.hp / self.max_hp  # 0..1

        # Crack position: random on front wall
        rng = random.Random(self._crack_seed + 9999)
        cx = rng.randint(self.x + 15, self.x + self.width - 15)
        cy = rng.randint(self.y + 15, self.y + self.height - 15)

        # Crack size grows with damage
        length = int(15 + damage_frac * 35)
        branches = rng.randint(2, 3 + int(damage_frac * 2))
        thickness = 1 + int(damage_frac * 1.5)

        crack_lines = _generate_crack(cx, cy, length, branches, self._crack_seed)
        self._cracks.append((crack_lines, thickness))

        # Add a scorch mark around the crack origin
        scorch_r = rng.randint(6, 12 + int(damage_frac * 10))
        self._scorch_marks.append((cx, cy, scorch_r))

    def _draw_damage_overlay(self, surface: pygame.Surface):
        """Draw cracks, scorch marks, and damage tint on the house."""
        if self.hp >= self.max_hp:
            return

        damage_frac = 1.0 - self.hp / self.max_hp  # 0..1

        # Use a single alpha overlay for tint + scorch + crack shadows
        ow = self.width + 60
        oh = self.height + 60
        overlay = pygame.Surface((ow, oh), pygame.SRCALPHA)
        ox = self.x - 30
        oy = self.y - 30

        # Dark tint – gets darker as damage increases
        if damage_frac > 0.05:
            tint_alpha = int(damage_frac * 60)
            tint_rect = pygame.Rect(30, 30, self.width, self.height)
            pygame.draw.rect(overlay, (30, 15, 5, tint_alpha), tint_rect)

        # Scorch marks (dark smudges)
        for sx, sy, sr in self._scorch_marks:
            pygame.draw.circle(overlay, HOUSE_SCORCH_COLOR,
                               (sx - ox, sy - oy), sr)

        # Crack shadows (all on the same overlay)
        for crack_lines, thickness in self._cracks:
            for polyline in crack_lines:
                if len(polyline) < 2:
                    continue
                shifted = [(x + 1 - ox, y + 1 - oy) for x, y in polyline]
                pygame.draw.lines(overlay, HOUSE_CRACK_SHADOW, False,
                                  shifted, thickness + 1)

        surface.blit(overlay, (ox, oy))

        # Main crack lines (opaque, drawn directly)
        for crack_lines, thickness in self._cracks:
            for polyline in crack_lines:
                if len(polyline) < 2:
                    continue
                pygame.draw.lines(surface, HOUSE_CRACK_COLOR, False,
                                  polyline, thickness)

        # Broken window effect at high damage
        if damage_frac > 0.5:
            self._draw_broken_windows(surface, damage_frac)

    def _draw_broken_windows(self, surface: pygame.Surface, damage_frac: float):
        """At high damage, add dark diagonal lines across windows."""
        win_w = int(self.width * 0.2)
        win_h = int(self.height * 0.16)
        col_offsets = [0.2, 0.6]
        row_offsets = [0.2, 0.55]

        rng = random.Random(42)  # deterministic
        for ry in row_offsets:
            for cx_off in col_offsets:
                if rng.random() > damage_frac:
                    continue  # not all windows break at once
                wx = self.x + int(self.width * cx_off) - win_w // 2
                wy = self.y + int(self.height * ry) - win_h // 2

                # Diagonal crack lines across the window
                alpha = min(200, int(damage_frac * 250))
                crack_surf = pygame.Surface((win_w, win_h), pygame.SRCALPHA)
                pygame.draw.line(crack_surf, (*HOUSE_CRACK_COLOR, alpha),
                                 (2, 2), (win_w - 2, win_h - 2), 1)
                pygame.draw.line(crack_surf, (*HOUSE_CRACK_COLOR, alpha),
                                 (win_w - 2, 2), (2, win_h - 2), 1)
                # Small radiating lines from center
                mid = (win_w // 2, win_h // 2)
                for a in range(0, 360, 45):
                    rad = math.radians(a)
                    ex = mid[0] + int(math.cos(rad) * win_w * 0.4)
                    ey = mid[1] + int(math.sin(rad) * win_h * 0.4)
                    pygame.draw.line(crack_surf, (*HOUSE_CRACK_COLOR, alpha // 2),
                                     mid, (ex, ey), 1)
                surface.blit(crack_surf, (wx, wy))

    # ── public API ────────────────────────────────────────────────────────

    @property
    def hp_fraction(self) -> float:
        """0.0 (destroyed) → 1.0 (full health)."""
        return max(0.0, self.hp / self.max_hp)

    def take_damage(self, amount: int):
        """Apply *amount* damage to the house and generate visual cracks."""
        if self.hp <= 0:
            return
        self.hp = max(0, self.hp - amount)

        # Generate a new crack roughly every 20 HP lost
        hp_since_last_crack = self._last_crack_hp - self.hp
        if hp_since_last_crack >= 20:
            self._add_crack()
            self._last_crack_hp = self.hp

    def update(self, dt: float):
        """Tick house state (currently a no-op; damage is applied externally)."""

    def draw(self, surface: pygame.Surface, time_ms: int):
        """Draw the complete house onto *surface*."""
        self._draw_shadow(surface)
        self._draw_side_wall(surface)
        self._draw_front_wall(surface)
        self._draw_wood_texture(surface)
        self._draw_roof(surface)
        self._draw_chimney(surface)
        self._draw_windows(surface, time_ms)
        self._draw_door(surface)
        # Damage overlay on top of everything
        self._draw_damage_overlay(surface)
        # Fortification overlays (drawn on top of everything)
        if self.fortify_level >= 1:
            self._draw_sandbags(surface)
        if self.fortify_level >= 2:
            self._draw_barbed_wire(surface)

    # ── fortification visuals ──────────────────────────────────────────

    def _draw_window_boards(self, surface: pygame.Surface,
                            wx: int, wy: int, ww: int, wh: int,
                            level: int, idx: int):
        """Draw wooden boards nailed over a window.

        *level* 1: two diagonal boards on some windows.
        *level* 2: three boards (horizontal + diagonal) on all windows.
        """
        board_color = (120, 80, 40)
        board_dark = (90, 60, 30)
        nail_color = (80, 80, 85)

        if level == 1:
            # Only board the first and third windows (indices 0, 2)
            if idx not in (0, 2):
                return
            # Two diagonal boards
            pygame.draw.line(surface, board_color,
                             (wx + 2, wy + 2), (wx + ww - 2, wy + wh - 2), 4)
            pygame.draw.line(surface, board_dark,
                             (wx + 2, wy + 2), (wx + ww - 2, wy + wh - 2), 2)
            pygame.draw.line(surface, board_color,
                             (wx + ww - 2, wy + 2), (wx + 2, wy + wh - 2), 4)
            pygame.draw.line(surface, board_dark,
                             (wx + ww - 2, wy + 2), (wx + 2, wy + wh - 2), 2)
            # Nails at corners
            for nx, ny in [(wx + 4, wy + 4), (wx + ww - 4, wy + 4),
                           (wx + 4, wy + wh - 4), (wx + ww - 4, wy + wh - 4)]:
                pygame.draw.circle(surface, nail_color, (nx, ny), 2)
        else:
            # Level 2: heavy boarding on all windows
            # Horizontal boards
            for by_off in [0.25, 0.5, 0.75]:
                by = wy + int(wh * by_off)
                pygame.draw.line(surface, board_color,
                                 (wx - 3, by), (wx + ww + 3, by), 5)
                pygame.draw.line(surface, board_dark,
                                 (wx - 3, by - 1), (wx + ww + 3, by - 1), 1)
            # Diagonal cross brace
            pygame.draw.line(surface, board_color,
                             (wx + 2, wy + 2), (wx + ww - 2, wy + wh - 2), 3)
            pygame.draw.line(surface, board_dark,
                             (wx + 2, wy + 2), (wx + ww - 2, wy + wh - 2), 1)
            # Nails
            for nx, ny in [(wx + 3, wy + 3), (wx + ww - 3, wy + 3),
                           (wx + 3, wy + wh - 3), (wx + ww - 3, wy + wh - 3),
                           (wx + ww // 2, wy + wh // 2)]:
                pygame.draw.circle(surface, nail_color, (nx, ny), 2)

    def _draw_sandbags(self, surface: pygame.Surface):
        """Draw sandbag wall in front of the house base."""
        bag_color = (160, 145, 110)
        bag_dark = (130, 115, 85)
        bag_line = (110, 95, 70)
        bag_highlight = (180, 165, 130)

        base_y = self.y + self.height  # bottom of house
        bag_w = int(self.width * 0.14)
        bag_h = int(bag_w * 0.45)

        # Sandbag positions: a row in front of the house
        # Level 1: single row of bags
        # Level 2: double-stacked row + extra bags on the sides
        rows = 1 if self.fortify_level == 1 else 2
        start_x = self.x - bag_w

        for row in range(rows):
            y = base_y - (row + 1) * bag_h + row * 2
            # Offset every other row for brick-like stacking
            offset = bag_w // 2 if row % 2 == 1 else 0
            num_bags = (self.width + bag_w * 2) // bag_w + 1
            for i in range(num_bags):
                bx = start_x + i * bag_w + offset
                # Draw each sandbag as a rounded rectangle
                bag_rect = pygame.Rect(bx, y, bag_w - 2, bag_h - 1)
                pygame.draw.rect(surface, bag_color, bag_rect,
                                 border_radius=3)
                # Top highlight
                pygame.draw.line(surface, bag_highlight,
                                 (bx + 2, y + 1), (bx + bag_w - 4, y + 1), 1)
                # Bottom shadow
                pygame.draw.line(surface, bag_dark,
                                 (bx + 1, y + bag_h - 2),
                                 (bx + bag_w - 3, y + bag_h - 2), 1)
                # Seam line across center
                pygame.draw.line(surface, bag_line,
                                 (bx + 3, y + bag_h // 2),
                                 (bx + bag_w - 5, y + bag_h // 2), 1)

    def _draw_barbed_wire(self, surface: pygame.Surface):
        """Draw barbed wire in front of the sandbags (fortify level 2)."""
        wire_color = (100, 100, 105)
        barb_color = (80, 80, 85)

        base_y = self.y + self.height  # bottom of house
        bag_h = int(self.width * 0.14 * 0.45)
        wire_y = base_y - 2 * bag_h - 6  # above the sandbag stack

        # Draw two wavy wire lines
        start_x = self.x - 20
        end_x = self.x + self.width + 20
        for wire_offset in [0, 8]:
            wy = wire_y + wire_offset
            points = []
            x = start_x
            while x < end_x:
                # Zigzag pattern
                y_off = 4 if (int(x) // 8) % 2 == 0 else -4
                points.append((int(x), wy + y_off))
                x += 6
            if len(points) >= 2:
                pygame.draw.lines(surface, wire_color, False, points, 1)
            # Barbs every ~18 px
            for j in range(0, len(points), 3):
                px, py = points[j]
                # Small X barb
                pygame.draw.line(surface, barb_color,
                                 (px - 3, py - 3), (px + 3, py + 3), 1)
                pygame.draw.line(surface, barb_color,
                                 (px + 3, py - 3), (px - 3, py + 3), 1)

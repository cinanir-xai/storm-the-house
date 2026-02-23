"""
Main menu scene – title screen with a Play button.

Displays the game title over a stylised dusk-sky background with
drifting clouds.  The mouse cursor is visible here (no crosshair).
"""

from __future__ import annotations

import math
import random
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    MENU_TITLE_COLOR, MENU_SUBTITLE_COLOR,
    MENU_BTN_COLOR, MENU_BTN_HOVER, MENU_BTN_TEXT,
    MENU_BG_TOP, MENU_BG_BOT,
)
from storm_the_house.utils.drawing import lerp_color


class MainMenuScene:
    """Simple main-menu scene with a *Play* button."""

    # Set by the Game engine to allow scene transitions
    show_cursor = True  # signal to Game to show the system cursor

    def __init__(self):
        # Pre-render the background gradient
        self._bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t = y / max(SCREEN_HEIGHT - 1, 1)
            color = lerp_color(MENU_BG_TOP, MENU_BG_BOT, t)
            pygame.draw.line(self._bg, color, (0, y), (SCREEN_WIDTH, y))

        # Generate some static "stars" for atmosphere
        self._stars: list[tuple[int, int, int]] = []
        rng = random.Random(42)
        for _ in range(90):
            sx = rng.randint(0, SCREEN_WIDTH)
            sy = rng.randint(0, SCREEN_HEIGHT // 2)
            sa = rng.randint(40, 140)
            self._stars.append((sx, sy, sa))

        # Button geometry
        btn_w, btn_h = 260, 56
        self._btn_rect = pygame.Rect(
            (SCREEN_WIDTH - btn_w) // 2,
            SCREEN_HEIGHT // 2 + 60,
            btn_w, btn_h,
        )
        self._hovered = False
        self._start_game = False

        # Fonts (lazy-init to ensure pygame.init has been called)
        self._font_title: pygame.font.Font | None = None
        self._font_sub: pygame.font.Font | None = None
        self._font_btn: pygame.font.Font | None = None

    # ── helpers ────────────────────────────────────────────────────────

    def _get_font_title(self) -> pygame.font.Font:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("arial", 72, bold=True)
        return self._font_title

    def _get_font_sub(self) -> pygame.font.Font:
        if self._font_sub is None:
            self._font_sub = pygame.font.SysFont("arial", 24)
        return self._font_sub

    def _get_font_btn(self) -> pygame.font.Font:
        if self._font_btn is None:
            self._font_btn = pygame.font.SysFont("arial", 30, bold=True)
        return self._font_btn

    # ── public API (scene interface) ──────────────────────────────────

    @property
    def next_scene(self) -> str | None:
        """Return ``'play'`` when the player clicks the button."""
        if self._start_game:
            return "play"
        return None

    def update(self, dt: float, events: list[pygame.event.Event] | None = None):
        mx, my = pygame.mouse.get_pos()
        self._hovered = self._btn_rect.collidepoint(mx, my)

        if events:
            for ev in events:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self._hovered:
                        self._start_game = True

    def draw(self, surface: pygame.Surface, time_ms: int):
        # Background
        surface.blit(self._bg, (0, 0))

        # Stars twinkle
        for sx, sy, sa in self._stars:
            twinkle = int(sa * (0.5 + 0.5 * math.sin(time_ms / 800.0 + sx)))
            if twinkle > 10:
                star_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(star_surf, (255, 255, 255, twinkle),
                                   (2, 2), 1)
                surface.blit(star_surf, (sx - 2, sy - 2))

        # Ground silhouette
        ground_y = int(SCREEN_HEIGHT * 0.72)
        pygame.draw.rect(surface, (35, 28, 22),
                         pygame.Rect(0, ground_y, SCREEN_WIDTH,
                                     SCREEN_HEIGHT - ground_y))
        # Gentle dune silhouette
        pts = [(0, ground_y)]
        for x in range(0, SCREEN_WIDTH + 1, 4):
            y = ground_y - int(12 * math.sin(x * 0.005) + 6 * math.sin(x * 0.012 + 1))
            pts.append((x, y))
        pts.append((SCREEN_WIDTH, ground_y))
        pygame.draw.polygon(surface, (40, 32, 25), pts)

        # House silhouette (right side)
        hx = SCREEN_WIDTH - 220
        hw, hh = 120, 180
        hy = ground_y - hh + 20
        pygame.draw.rect(surface, (28, 22, 18),
                         pygame.Rect(hx, hy, hw, hh))
        # Roof
        pygame.draw.polygon(surface, (28, 22, 18), [
            (hx - 12, hy),
            (hx + hw + 12, hy),
            (hx + hw // 2, hy - 60),
        ])
        # Tiny lit window
        win_rect = pygame.Rect(hx + 30, hy + 50, 24, 20)
        pygame.draw.rect(surface, (80, 65, 40), win_rect)
        glow = pygame.Surface((40, 36), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (120, 100, 50, 40), glow.get_rect())
        surface.blit(glow, (win_rect.centerx - 20, win_rect.centery - 18))

        # Title
        font_t = self._get_font_title()
        title_surf = font_t.render("STORM THE HOUSE", True, MENU_TITLE_COLOR)
        title_shadow = font_t.render("STORM THE HOUSE", True, (0, 0, 0))
        tx = (SCREEN_WIDTH - title_surf.get_width()) // 2
        ty = SCREEN_HEIGHT // 2 - 100
        surface.blit(title_shadow, (tx + 2, ty + 2))
        surface.blit(title_surf, (tx, ty))

        # Subtitle
        font_s = self._get_font_sub()
        sub = font_s.render("Defend your stronghold against waves of enemies",
                            True, MENU_SUBTITLE_COLOR)
        surface.blit(sub, ((SCREEN_WIDTH - sub.get_width()) // 2, ty + 80))

        # Play button
        btn_color = MENU_BTN_HOVER if self._hovered else MENU_BTN_COLOR
        # Shadow
        shadow_rect = self._btn_rect.move(3, 3)
        pygame.draw.rect(surface, (0, 0, 0, 80),
                         shadow_rect, border_radius=10)
        # Main
        pygame.draw.rect(surface, btn_color, self._btn_rect, border_radius=10)
        # Highlight strip on top
        hl_rect = pygame.Rect(self._btn_rect.x + 4, self._btn_rect.y + 2,
                              self._btn_rect.width - 8, 6)
        hl_surf = pygame.Surface((hl_rect.width, hl_rect.height), pygame.SRCALPHA)
        hl_surf.fill((255, 255, 255, 35))
        surface.blit(hl_surf, hl_rect.topleft)
        # Border
        pygame.draw.rect(surface, lerp_color(btn_color, (255, 255, 255), 0.15),
                         self._btn_rect, width=2, border_radius=10)
        # Text
        font_b = self._get_font_btn()
        btn_text = font_b.render("PLAY", True, MENU_BTN_TEXT)
        bx = self._btn_rect.centerx - btn_text.get_width() // 2
        by = self._btn_rect.centery - btn_text.get_height() // 2
        surface.blit(btn_text, (bx, by))

        # Version / credit
        font_sm = self._get_font_sub()
        ver = pygame.font.SysFont("arial", 14).render(
            "v1.0  –  Procedural Graphics", True, (120, 110, 95))
        surface.blit(ver, (10, SCREEN_HEIGHT - 24))

"""
Game-over scene – shown when the house is destroyed.

Displays the number of days survived and a button to return to the main menu.
"""

from __future__ import annotations

import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    EOD_BTN_COLOR, EOD_BTN_HOVER, EOD_BTN_TEXT,
)
from storm_the_house.utils.drawing import lerp_color


class GameOverScene:
    """Simple game-over screen with day-survival count and main-menu button."""

    show_cursor = True

    def __init__(self, day: int):
        self.day = day
        self._go_menu = False

        # Button
        btn_w, btn_h = 300, 50
        self._btn_rect = pygame.Rect(
            (SCREEN_WIDTH - btn_w) // 2,
            SCREEN_HEIGHT // 2 + 120,
            btn_w, btn_h,
        )
        self._btn_hovered = False

        # Fade-in
        self._fade_alpha = 0.0

        # Fonts (lazy)
        self._font_big: pygame.font.Font | None = None
        self._font_med: pygame.font.Font | None = None
        self._font_btn: pygame.font.Font | None = None
        self._font_sub: pygame.font.Font | None = None

        # Background snapshot (set externally)
        self.bg_snapshot: pygame.Surface | None = None

    # ── fonts ──────────────────────────────────────────────────────────

    def _fb(self) -> pygame.font.Font:
        if self._font_big is None:
            self._font_big = pygame.font.SysFont("arial", 62, bold=True)
        return self._font_big

    def _fm(self) -> pygame.font.Font:
        if self._font_med is None:
            self._font_med = pygame.font.SysFont("arial", 30)
        return self._font_med

    def _fbt(self) -> pygame.font.Font:
        if self._font_btn is None:
            self._font_btn = pygame.font.SysFont("arial", 24, bold=True)
        return self._font_btn

    def _fsub(self) -> pygame.font.Font:
        if self._font_sub is None:
            self._font_sub = pygame.font.SysFont("arial", 20)
        return self._font_sub

    # ── scene interface ────────────────────────────────────────────────

    @property
    def next_scene(self) -> str | None:
        if self._go_menu:
            return "main_menu"
        return None

    def update(self, dt: float, events: list[pygame.event.Event] | None = None):
        # Fade in
        self._fade_alpha = min(self._fade_alpha + dt * 180, 255)

        mx, my = pygame.mouse.get_pos()
        self._btn_hovered = self._btn_rect.collidepoint(mx, my)

        if events:
            for ev in events:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self._btn_hovered:
                        self._go_menu = True

    def draw(self, surface: pygame.Surface, time_ms: int):
        # Background
        if self.bg_snapshot is not None:
            surface.blit(self.bg_snapshot, (0, 0))
        else:
            surface.fill((15, 10, 8))

        # Heavy dark-red overlay with fade-in
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        alpha = int(self._fade_alpha * 0.82)
        overlay.fill((35, 5, 5, alpha))
        surface.blit(overlay, (0, 0))

        # Panel
        pw, ph = 520, 290
        px = (SCREEN_WIDTH - pw) // 2
        py = SCREEN_HEIGHT // 2 - 160
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel_alpha = int(min(230, self._fade_alpha * 0.9))
        pygame.draw.rect(panel, (25, 15, 12, panel_alpha), panel.get_rect(),
                         border_radius=16)
        pygame.draw.rect(panel, (120, 40, 30, min(160, int(self._fade_alpha * 0.63))),
                         panel.get_rect(), width=2, border_radius=16)
        surface.blit(panel, (px, py))

        if self._fade_alpha < 30:
            return  # still too faded, skip text

        # "GAME OVER" title
        fb = self._fb()
        title = fb.render("GAME OVER", True, (220, 60, 40))
        title_shadow = fb.render("GAME OVER", True, (0, 0, 0))
        tx = (SCREEN_WIDTH - title.get_width()) // 2
        ty = py + 28
        surface.blit(title_shadow, (tx + 3, ty + 3))
        surface.blit(title, (tx, ty))

        # Decorative line under title
        line_y = ty + title.get_height() + 8
        line_w = 240
        lx = (SCREEN_WIDTH - line_w) // 2
        pygame.draw.line(surface, (120, 40, 30), (lx, line_y), (lx + line_w, line_y), 2)

        # Days survived
        fm = self._fm()
        days_text = f"You survived {self.day} day{'s' if self.day != 1 else ''}!"
        days_surf = fm.render(days_text, True, (220, 200, 170))
        days_shadow = fm.render(days_text, True, (0, 0, 0))
        dx = (SCREEN_WIDTH - days_surf.get_width()) // 2
        dy = line_y + 18
        surface.blit(days_shadow, (dx + 1, dy + 1))
        surface.blit(days_surf, (dx, dy))

        # Subtitle
        fsub = self._fsub()
        sub_text = "Your house has been destroyed."
        sub_surf = fsub.render(sub_text, True, (160, 140, 120))
        sx = (SCREEN_WIDTH - sub_surf.get_width()) // 2
        sy = dy + days_surf.get_height() + 10
        surface.blit(sub_surf, (sx, sy))

        # Skull icon (simple procedural)
        skull_cx = SCREEN_WIDTH // 2
        skull_cy = sy + 50
        self._draw_skull(surface, skull_cx, skull_cy, time_ms)

        # Main menu button
        btn_color = EOD_BTN_HOVER if self._btn_hovered else EOD_BTN_COLOR
        pygame.draw.rect(surface, (0, 0, 0, 70),
                         self._btn_rect.move(3, 3), border_radius=10)
        pygame.draw.rect(surface, btn_color, self._btn_rect, border_radius=10)
        # Top highlight
        hl = pygame.Surface((self._btn_rect.width - 8, 5), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 30))
        surface.blit(hl, (self._btn_rect.x + 4, self._btn_rect.y + 2))
        # Border
        pygame.draw.rect(surface,
                         lerp_color(btn_color, (255, 255, 255), 0.15),
                         self._btn_rect, width=2, border_radius=10)
        fbt = self._fbt()
        btn_txt = fbt.render("Return to Main Menu", True, EOD_BTN_TEXT)
        surface.blit(btn_txt,
                     (self._btn_rect.centerx - btn_txt.get_width() // 2,
                      self._btn_rect.centery - btn_txt.get_height() // 2))

    # ── decorative skull ───────────────────────────────────────────────

    @staticmethod
    def _draw_skull(surface: pygame.Surface, cx: int, cy: int, time_ms: int):
        """Draw a small stylised skull icon."""
        col = (180, 160, 140)
        dark = (100, 80, 65)
        # Head outline
        pygame.draw.ellipse(surface, col,
                            pygame.Rect(cx - 14, cy - 14, 28, 26))
        # Eye sockets
        for ox in [-6, 6]:
            pygame.draw.ellipse(surface, dark,
                                pygame.Rect(cx + ox - 4, cy - 6, 8, 8))
        # Nose
        pygame.draw.polygon(surface, dark, [
            (cx, cy + 2), (cx - 3, cy + 8), (cx + 3, cy + 8)])
        # Jaw
        pygame.draw.rect(surface, col,
                         pygame.Rect(cx - 10, cy + 10, 20, 6),
                         border_radius=2)
        # Teeth lines
        for tx in range(-8, 10, 4):
            pygame.draw.line(surface, dark,
                             (cx + tx, cy + 10), (cx + tx, cy + 16), 1)

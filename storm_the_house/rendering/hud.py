"""
HUD – heads-up display.

Elements:
  - Top-left:    ammo bullets + reload label
  - Top-right:   money display
  - Bottom-right: house HP bar with label
"""

from __future__ import annotations

import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HUD_AMMO_X, HUD_AMMO_Y,
    HUD_BULLET_W, HUD_BULLET_H, HUD_BULLET_GAP,
    HUD_BULLET_COLOR, HUD_BULLET_CASING, HUD_BULLET_EMPTY,
    HUD_BULLET_TIP, HUD_LABEL_COLOR,
    HUD_HOUSE_HP_MARGIN, HUD_HOUSE_HP_BAR_W, HUD_HOUSE_HP_BAR_H,
    HUD_HOUSE_HP_BG, HUD_HOUSE_HP_BORDER,
    HUD_HOUSE_HP_FULL, HUD_HOUSE_HP_MID, HUD_HOUSE_HP_LOW,
    HUD_HOUSE_HP_EMPTY,
    HUD_MONEY_MARGIN, HUD_MONEY_COLOR, HUD_MONEY_SHADOW,
    HUD_MONEY_ICON_COLOR,
)
from storm_the_house.utils.drawing import lerp_color


class HUDRenderer:
    """Renders the ammo indicator, house HP bar, and money display."""

    def __init__(self):
        self._font: pygame.font.Font | None = None
        self._font_lg: pygame.font.Font | None = None
        self._font_sm: pygame.font.Font | None = None

    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 14, bold=True)
        return self._font

    def _get_font_lg(self) -> pygame.font.Font:
        if self._font_lg is None:
            self._font_lg = pygame.font.SysFont("monospace", 20, bold=True)
        return self._font_lg

    def _get_font_sm(self) -> pygame.font.Font:
        if self._font_sm is None:
            self._font_sm = pygame.font.SysFont("monospace", 12, bold=True)
        return self._font_sm

    def draw(self, surface: pygame.Surface, ammo: int, max_ammo: int,
             reloading: bool, reload_progress: float,
             house_hp: int, house_max_hp: int,
             money: int, kills: int = 0):
        """Draw the full HUD overlay."""
        self._draw_ammo_bullets(surface, ammo, max_ammo)
        if reloading:
            self._draw_reload_label(surface, reload_progress)
        self._draw_house_hp(surface, house_hp, house_max_hp)
        self._draw_money(surface, money)
        self._draw_kills(surface, kills)

    # ── ammo bullets (top-left) ─────────────────────────────────────────

    def _draw_ammo_bullets(self, surface: pygame.Surface, ammo: int,
                           max_ammo: int):
        """Draw bullet icons – filled for available, dark for spent."""
        x = HUD_AMMO_X
        y = HUD_AMMO_Y
        bw = HUD_BULLET_W
        bh = HUD_BULLET_H

        # Background panel
        panel_w = max_ammo * (bw + HUD_BULLET_GAP) + HUD_BULLET_GAP + 8
        panel_h = bh + 16
        panel_rect = pygame.Rect(x - 6, y - 6, panel_w, panel_h)
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 100), panel.get_rect(),
                         border_radius=4)
        surface.blit(panel, panel_rect.topleft)

        for i in range(max_ammo):
            bx = x + i * (bw + HUD_BULLET_GAP)
            by = y

            if i < ammo:
                # ── live round ──────────────────────────────────────────
                casing_h = int(bh * 0.6)
                pygame.draw.rect(surface, HUD_BULLET_CASING,
                                 pygame.Rect(bx, by + bh - casing_h, bw, casing_h))
                bullet_h = bh - casing_h
                pygame.draw.rect(surface, HUD_BULLET_COLOR,
                                 pygame.Rect(bx, by, bw, bullet_h + 2))
                tip_r = bw // 2
                pygame.draw.circle(surface, HUD_BULLET_TIP,
                                   (bx + bw // 2, by + 1), tip_r)
                pygame.draw.line(surface, (240, 220, 130),
                                 (bx + 1, by + bullet_h + 2),
                                 (bx + 1, by + bh - 2), 1)
            else:
                # ── spent / empty ───────────────────────────────────────
                pygame.draw.rect(surface, HUD_BULLET_EMPTY,
                                 pygame.Rect(bx, by, bw, bh),
                                 border_radius=1)
                pygame.draw.rect(surface, (60, 58, 55),
                                 pygame.Rect(bx + 1, by + 1, bw - 2, bh - 2),
                                 border_radius=1)

    # ── reload label ────────────────────────────────────────────────────

    def _draw_reload_label(self, surface: pygame.Surface,
                           reload_progress: float):
        """Show 'RELOADING' text below the ammo display."""
        font = self._get_font()
        pct = int(reload_progress * 100)
        text = font.render(f"RELOADING {pct}%", True, HUD_LABEL_COLOR)

        tx = HUD_AMMO_X - 2
        ty = HUD_AMMO_Y + HUD_BULLET_H + 16

        shadow = font.render(f"RELOADING {pct}%", True, (0, 0, 0))
        surface.blit(shadow, (tx + 1, ty + 1))
        surface.blit(text, (tx, ty))

    # ── house HP bar (bottom-right) ─────────────────────────────────────

    def _draw_house_hp(self, surface: pygame.Surface,
                       hp: int, max_hp: int):
        """Draw a health bar for the house in the bottom-right corner."""
        margin = HUD_HOUSE_HP_MARGIN
        bar_w = HUD_HOUSE_HP_BAR_W
        bar_h = HUD_HOUSE_HP_BAR_H
        frac = max(0.0, hp / max_hp) if max_hp > 0 else 0.0

        # Position
        bar_x = SCREEN_WIDTH - margin - bar_w
        bar_y = SCREEN_HEIGHT - margin - bar_h

        # Label above bar
        font = self._get_font_sm()
        label_text = f"HOUSE  {hp}/{max_hp}"
        label = font.render(label_text, True, HUD_LABEL_COLOR)
        label_shadow = font.render(label_text, True, (0, 0, 0))

        label_x = bar_x + bar_w - label.get_width()
        label_y = bar_y - label.get_height() - 4

        # Background panel
        panel_w = bar_w + 16
        panel_h = bar_h + label.get_height() + 20
        panel_x = bar_x - 8
        panel_y = label_y - 6
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, HUD_HOUSE_HP_BG, panel.get_rect(),
                         border_radius=5)
        surface.blit(panel, (panel_x, panel_y))

        # Label
        surface.blit(label_shadow, (label_x + 1, label_y + 1))
        surface.blit(label, (label_x, label_y))

        # Bar background (empty)
        pygame.draw.rect(surface, HUD_HOUSE_HP_EMPTY,
                         pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                         border_radius=3)

        # Bar fill
        fill_w = max(0, int(bar_w * frac))
        if fill_w > 0:
            # Color transitions: green → yellow → red
            if frac > 0.5:
                bar_color = lerp_color(HUD_HOUSE_HP_MID, HUD_HOUSE_HP_FULL,
                                       (frac - 0.5) * 2)
            else:
                bar_color = lerp_color(HUD_HOUSE_HP_LOW, HUD_HOUSE_HP_MID,
                                       frac * 2)

            fill_rect = pygame.Rect(bar_x, bar_y, fill_w, bar_h)
            pygame.draw.rect(surface, bar_color, fill_rect, border_radius=3)

            # Subtle highlight on top half of fill
            highlight = pygame.Surface((fill_w, bar_h // 2), pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 30))
            surface.blit(highlight, (bar_x, bar_y))

        # Border
        pygame.draw.rect(surface, HUD_HOUSE_HP_BORDER,
                         pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                         width=1, border_radius=3)

        # Small house icon to the left of the label
        self._draw_house_icon(surface, bar_x - 2, label_y - 1,
                              label.get_height() + 2)

    @staticmethod
    def _draw_house_icon(surface: pygame.Surface, x: int, y: int, size: int):
        """Draw a tiny house icon."""
        s = size
        # Body
        body_rect = pygame.Rect(x, y + s // 3, s, s - s // 3)
        pygame.draw.rect(surface, (160, 120, 75), body_rect)
        pygame.draw.rect(surface, (120, 85, 50), body_rect, 1)
        # Roof (triangle)
        peak = (x + s // 2, y)
        left = (x - 2, y + s // 3 + 1)
        right = (x + s + 2, y + s // 3 + 1)
        pygame.draw.polygon(surface, (120, 70, 35), [peak, left, right])
        pygame.draw.polygon(surface, (90, 50, 25), [peak, left, right], 1)
        # Door
        dw = max(2, s // 4)
        dh = max(3, s // 3)
        pygame.draw.rect(surface, (80, 50, 25),
                         pygame.Rect(x + s // 2 - dw // 2,
                                     y + s - dh, dw, dh))

    # ── money display (top-right) ───────────────────────────────────────

    def _draw_money(self, surface: pygame.Surface, money: int):
        """Draw the money counter in the top-right corner."""
        margin = HUD_MONEY_MARGIN
        font = self._get_font_lg()

        money_str = f"${money:,}"
        text = font.render(money_str, True, HUD_MONEY_COLOR)
        text_shadow = font.render(money_str, True, HUD_MONEY_SHADOW)

        tx = SCREEN_WIDTH - margin - text.get_width()
        ty = margin

        # Background panel
        panel_w = text.get_width() + 36
        panel_h = text.get_height() + 12
        panel_x = tx - 24
        panel_y = ty - 6
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 110), panel.get_rect(),
                         border_radius=5)
        surface.blit(panel, (panel_x, panel_y))

        # Coin icon
        coin_r = 7
        coin_cx = panel_x + 14
        coin_cy = panel_y + panel_h // 2
        # Outer ring
        pygame.draw.circle(surface, HUD_MONEY_ICON_COLOR,
                           (coin_cx, coin_cy), coin_r)
        pygame.draw.circle(surface, (180, 160, 50),
                           (coin_cx, coin_cy), coin_r, 1)
        # Inner "$"
        font_tiny = self._get_font_sm()
        dollar = font_tiny.render("$", True, (120, 100, 30))
        surface.blit(dollar, (coin_cx - dollar.get_width() // 2,
                              coin_cy - dollar.get_height() // 2))
        # Highlight
        pygame.draw.circle(surface, (255, 240, 160),
                           (coin_cx - 2, coin_cy - 2), 2)

        # Money text
        surface.blit(text_shadow, (tx + 1, ty + 1))
        surface.blit(text, (tx, ty))

    # ── kills display (bottom-left) ──────────────────────────────────

    def _draw_kills(self, surface: pygame.Surface, kills: int):
        """Draw the kill counter in the bottom-left corner."""
        font = self._get_font()
        kill_str = f"Kills: {kills}"
        text = font.render(kill_str, True, HUD_LABEL_COLOR)
        text_shadow = font.render(kill_str, True, (0, 0, 0))

        tx = 20
        ty = SCREEN_HEIGHT - 36

        # Background panel
        panel_w = text.get_width() + 16
        panel_h = text.get_height() + 10
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 90), panel.get_rect(),
                         border_radius=4)
        surface.blit(panel, (tx - 8, ty - 5))

        surface.blit(text_shadow, (tx + 1, ty + 1))
        surface.blit(text, (tx, ty))

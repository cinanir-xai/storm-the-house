"""
End-of-day summary scene with upgrade shop.

Shows the day number, enemies killed, house health, and money earned,
upgrade cards for the selected weapon, weapon selection panel on the right,
house upgrades, and hired help.

The system cursor is visible on this screen.
"""

from __future__ import annotations

import math
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    EOD_PANEL_COLOR, EOD_TITLE_COLOR,
    EOD_STAT_LABEL, EOD_STAT_VALUE, EOD_BONUS_COLOR,
    EOD_BTN_COLOR, EOD_BTN_HOVER, EOD_BTN_TEXT,
    DAY_END_BONUS,
    UPGRADE_CARD_W, UPGRADE_CARD_H, UPGRADE_CARD_GAP,
    UPGRADE_CARD_BG, UPGRADE_CARD_BORDER, UPGRADE_CARD_HOVER,
    UPGRADE_CARD_LOCKED,
    UPGRADE_CARD_TITLE, UPGRADE_CARD_DESC,
    UPGRADE_CARD_PRICE, UPGRADE_CARD_PRICE_LOCKED,
    UPGRADE_CARD_LEVEL, UPGRADE_CARD_ICON,
    PLAYER_GUN_DAMAGE, PLAYER_MAX_AMMO,
    PISTOL_DAMAGE, PISTOL_MAX_AMMO, PISTOL_RELOAD_TIME,
    SHOTGUN_COST, ASSAULT_RIFLE_COST,
    REPAIRMAN_HEAL_PER_MAN, REPAIRMAN_HEAL_INTERVAL,
    GUNMAN_BASE_INTERVAL,
)
from storm_the_house.utils.drawing import lerp_color
from storm_the_house.entities.upgrades import UpgradeState


# ── Upgrade card descriptor ──────────────────────────────────────────────────

class _UpgradeCard:
    """Metadata + rect for one upgrade card."""

    def __init__(self, key: str, title: str, desc_fn, price_fn, level_fn,
                 can_buy_fn, buy_fn, icon_fn, rect: pygame.Rect,
                 maxed_fn=None):
        self.key = key
        self.title = title
        self.desc_fn = desc_fn        # () -> str
        self.price_fn = price_fn      # () -> int
        self.level_fn = level_fn      # () -> int
        self.can_buy_fn = can_buy_fn  # (money) -> bool
        self.buy_fn = buy_fn          # (money) -> int  (returns remaining)
        self.icon_fn = icon_fn        # (surf, cx, cy) -> None
        self.rect = rect
        self.hovered = False
        # Optional: returns True if this upgrade is maxed out
        self.maxed_fn = maxed_fn      # () -> bool  or None


class EndOfDayScene:
    """Displays end-of-day stats, upgrade shop, and a *Continue* button."""

    show_cursor = True

    def __init__(self, day: int, kills: int,
                 house_hp: int, house_max_hp: int,
                 money_before_bonus: int,
                 upgrades: UpgradeState | None = None,
                 house=None):
        self.day = day
        self.kills = kills
        self.house_hp = house_hp
        self.house_max_hp = house_max_hp
        self.money = money_before_bonus
        self.bonus = DAY_END_BONUS
        self.upgrades = upgrades if upgrades is not None else UpgradeState()
        self.house = house  # needed for Repair / Fortify

        # Continue button (pushed down to make room for cards)
        btn_w, btn_h = 300, 46
        self._btn_rect = pygame.Rect(
            (SCREEN_WIDTH - btn_w) // 2,
            SCREEN_HEIGHT - 58,
            btn_w, btn_h,
        )
        self._btn_hovered = False
        self._continue = False

        # Fonts (lazy)
        self._font_title: pygame.font.Font | None = None
        self._font_stat: pygame.font.Font | None = None
        self._font_btn: pygame.font.Font | None = None
        self._font_label: pygame.font.Font | None = None
        self._font_card_title: pygame.font.Font | None = None
        self._font_card_desc: pygame.font.Font | None = None
        self._font_card_price: pygame.font.Font | None = None
        self._font_card_level: pygame.font.Font | None = None

        # Build upgrade cards (two rows: 3 weapon + 2 house)
        self._cards = self._build_cards()

        # Snapshot of the game screen (set externally before switching)
        self.bg_snapshot: pygame.Surface | None = None

        # Flash feedback when buying
        self._flash_card: str | None = None
        self._flash_timer: float = 0.0

    # ── fonts ──────────────────────────────────────────────────────────

    def _ft(self) -> pygame.font.Font:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("arial", 36, bold=True)
        return self._font_title

    def _fs(self) -> pygame.font.Font:
        if self._font_stat is None:
            self._font_stat = pygame.font.SysFont("arial", 20, bold=True)
        return self._font_stat

    def _fl(self) -> pygame.font.Font:
        if self._font_label is None:
            self._font_label = pygame.font.SysFont("arial", 16)
        return self._font_label

    def _fb(self) -> pygame.font.Font:
        if self._font_btn is None:
            self._font_btn = pygame.font.SysFont("arial", 24, bold=True)
        return self._font_btn

    def _fct(self) -> pygame.font.Font:
        if self._font_card_title is None:
            self._font_card_title = pygame.font.SysFont("arial", 16, bold=True)
        return self._font_card_title

    def _fcd(self) -> pygame.font.Font:
        if self._font_card_desc is None:
            self._font_card_desc = pygame.font.SysFont("arial", 13)
        return self._font_card_desc

    def _fcp(self) -> pygame.font.Font:
        if self._font_card_price is None:
            self._font_card_price = pygame.font.SysFont("arial", 18, bold=True)
        return self._font_card_price

    def _fcl(self) -> pygame.font.Font:
        if self._font_card_level is None:
            self._font_card_level = pygame.font.SysFont("arial", 12)
        return self._font_card_level

    # ── build upgrade cards ──────────────────────────────────────────────

    def _build_cards(self) -> list[_UpgradeCard]:
        cw = UPGRADE_CARD_W
        ch = UPGRADE_CARD_H
        gap = UPGRADE_CARD_GAP

        # Row 1: 3 weapon upgrades (centered, shifted left for weapon panel)
        row1_total = 3 * cw + 2 * gap
        row1_x = (SCREEN_WIDTH - row1_total) // 2 - 100  # Shift left for weapon panel
        row1_y = 248

        # Row 2: 2 house upgrades (centered, shifted left)
        row2_total = 2 * cw + 1 * gap
        row2_x = (SCREEN_WIDTH - row2_total) // 2 - 100
        row2_y = row1_y + ch + gap

        # Row 3: 2 hired help upgrades (centered, shifted left)
        row3_total = 2 * cw + 1 * gap
        row3_x = (SCREEN_WIDTH - row3_total) // 2 - 100
        row3_y = row2_y + ch + gap

        u = self.upgrades
        house = self.house
        cards: list[_UpgradeCard] = []

        # Build weapon-specific upgrade cards
        if u.selected_weapon == "shotgun":
            cards.extend(self._build_shotgun_upgrade_cards(row1_x, row1_y, cw, ch, gap))
        elif u.selected_weapon == "assault_rifle":
            cards.extend(self._build_assault_rifle_upgrade_cards(row1_x, row1_y, cw, ch, gap))
        else:
            cards.extend(self._build_pistol_upgrade_cards(row1_x, row1_y, cw, ch, gap))

        # ── Row 2: House upgrades ─────────────────────────────────────

        # 4) Repair House
        cards.append(_UpgradeCard(
            key="repair",
            title="Repair House",
            desc_fn=lambda: (f"HP: {house.hp}/{house.max_hp}"
                             if house else "Full repair"),
            price_fn=lambda: u.repair_price,
            level_fn=lambda: u.repair_count,
            can_buy_fn=lambda m: u.can_buy_repair(m),
            buy_fn=lambda m: self._buy_repair(m),
            icon_fn=self._draw_repair_icon,
            rect=pygame.Rect(row2_x, row2_y, cw, ch),
        ))

        # 5) Fortify House
        cards.append(_UpgradeCard(
            key="fortify",
            title="Fortify House",
            desc_fn=lambda: (f"Max HP: {u.current_max_hp}"
                             if not u.fortify_maxed else "MAX LEVEL"),
            price_fn=lambda: u.fortify_price,
            level_fn=lambda: u.fortify_level,
            can_buy_fn=lambda m: u.can_buy_fortify(m),
            buy_fn=lambda m: self._buy_fortify(m),
            icon_fn=self._draw_fortify_icon,
            rect=pygame.Rect(row2_x + cw + gap, row2_y, cw, ch),
            maxed_fn=lambda: u.fortify_maxed,
        ))

        # ── Row 3: Hired Help ─────────────────────────────────────────

        # 6) Repair Man
        cards.append(_UpgradeCard(
            key="repairman",
            title="Repair Man",
            desc_fn=lambda: (f"Heals {u.repairman_count * REPAIRMAN_HEAL_PER_MAN} HP/{int(REPAIRMAN_HEAL_INTERVAL)}s"
                             if u.repairman_count > 0
                             else f"+{REPAIRMAN_HEAL_PER_MAN} HP/{int(REPAIRMAN_HEAL_INTERVAL)}s"),
            price_fn=lambda: u.repairman_price,
            level_fn=lambda: u.repairman_count,
            can_buy_fn=lambda m: u.can_buy_repairman(m),
            buy_fn=lambda m: u.buy_repairman(m),
            icon_fn=self._draw_repairman_icon,
            rect=pygame.Rect(row3_x, row3_y, cw, ch),
        ))

        # 7) Gun Man
        cards.append(_UpgradeCard(
            key="gunman",
            title="Gun Man",
            desc_fn=lambda: (f"Fires every {u.gunman_fire_interval:.1f}s"
                             if u.gunman_count > 0
                             else f"Auto-kills every {GUNMAN_BASE_INTERVAL:.0f}s"),
            price_fn=lambda: u.gunman_price,
            level_fn=lambda: u.gunman_count,
            can_buy_fn=lambda m: u.can_buy_gunman(m),
            buy_fn=lambda m: u.buy_gunman(m),
            icon_fn=self._draw_gunman_icon,
            rect=pygame.Rect(row3_x + cw + gap, row3_y, cw, ch),
        ))

        return cards

    def _build_pistol_upgrade_cards(self, row1_x: int, row1_y: int, cw: int, ch: int, gap: int) -> list[_UpgradeCard]:
        """Build upgrade cards for pistol."""
        u = self.upgrades
        weapon_upgrades = u.pistol_upgrades
        cards: list[_UpgradeCard] = []

        # 1) Damage
        cards.append(_UpgradeCard(
            key="damage",
            title="Damage +1",
            desc_fn=lambda: f"Current: {PISTOL_DAMAGE + weapon_upgrades.bonus_damage} dmg",
            price_fn=lambda: weapon_upgrades.damage_price,
            level_fn=lambda: weapon_upgrades.damage_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_damage(m),
            buy_fn=lambda m: weapon_upgrades.buy_damage(m),
            icon_fn=self._draw_damage_icon,
            rect=pygame.Rect(row1_x, row1_y, cw, ch),
        ))

        # 2) Ammo
        cards.append(_UpgradeCard(
            key="ammo",
            title="Ammo +1",
            desc_fn=lambda: f"Current: {PISTOL_MAX_AMMO + weapon_upgrades.bonus_ammo} rounds",
            price_fn=lambda: weapon_upgrades.ammo_price,
            level_fn=lambda: weapon_upgrades.ammo_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_ammo(m),
            buy_fn=lambda m: weapon_upgrades.buy_ammo(m),
            icon_fn=self._draw_ammo_icon,
            rect=pygame.Rect(row1_x + cw + gap, row1_y, cw, ch),
        ))

        # 3) Reload speed
        cards.append(_UpgradeCard(
            key="reload",
            title="Fast Reload",
            desc_fn=lambda: f"Current: {weapon_upgrades.reload_time(PISTOL_RELOAD_TIME):.1f}s reload",
            price_fn=lambda: weapon_upgrades.reload_price,
            level_fn=lambda: weapon_upgrades.reload_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_reload(m),
            buy_fn=lambda m: weapon_upgrades.buy_reload(m),
            icon_fn=self._draw_reload_icon,
            rect=pygame.Rect(row1_x + 2 * (cw + gap), row1_y, cw, ch),
        ))

        return cards

    def _build_shotgun_upgrade_cards(self, row1_x: int, row1_y: int, cw: int, ch: int, gap: int) -> list[_UpgradeCard]:
        """Build upgrade cards for shotgun with unique upgrades."""
        from storm_the_house.core.settings import (
            SHOTGUN_MAX_AMMO, SHOTGUN_PELLET_COUNT, SHOTGUN_SHELL_RELOAD_TIME,
            SHOTGUN_UPGRADE_AMMO_BONUS, SHOTGUN_UPGRADE_PELLET_BONUS, SHOTGUN_UPGRADE_SPEED_BONUS,
        )
        u = self.upgrades
        weapon_upgrades = u.shotgun_upgrades
        cards: list[_UpgradeCard] = []

        # 1) Longer Barrel (+1 ammo capacity)
        cards.append(_UpgradeCard(
            key="shotgun_ammo",
            title="Longer Barrel",
            desc_fn=lambda: f"Ammo: {SHOTGUN_MAX_AMMO + weapon_upgrades.bonus_ammo} shells (+{SHOTGUN_UPGRADE_AMMO_BONUS})",
            price_fn=lambda: weapon_upgrades.ammo_price,
            level_fn=lambda: weapon_upgrades.ammo_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_ammo(m),
            buy_fn=lambda m: weapon_upgrades.buy_ammo(m),
            icon_fn=self._draw_shotgun_barrel_icon,
            rect=pygame.Rect(row1_x, row1_y, cw, ch),
        ))

        # 2) Buckshot (+2 pellets)
        cards.append(_UpgradeCard(
            key="shotgun_pellet",
            title="Buckshot",
            desc_fn=lambda: f"Pellets: {SHOTGUN_PELLET_COUNT + weapon_upgrades.bonus_pellets} (+{SHOTGUN_UPGRADE_PELLET_BONUS})",
            price_fn=lambda: weapon_upgrades.pellet_price,
            level_fn=lambda: weapon_upgrades.pellet_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_pellet(m),
            buy_fn=lambda m: weapon_upgrades.buy_pellet(m),
            icon_fn=self._draw_shotgun_pellet_icon,
            rect=pygame.Rect(row1_x + cw + gap, row1_y, cw, ch),
        ))

        # 3) Faster Handling (20% faster reload/pump)
        speed_bonus = int(SHOTGUN_UPGRADE_SPEED_BONUS * 100 * (1 - (1 - SHOTGUN_UPGRADE_SPEED_BONUS) ** weapon_upgrades.speed_level))
        cards.append(_UpgradeCard(
            key="shotgun_speed",
            title="Faster Handling",
            desc_fn=lambda: f"Reload: {SHOTGUN_SHELL_RELOAD_TIME * weapon_upgrades.speed_multiplier:.2f}s ({int((1 - weapon_upgrades.speed_multiplier) * 100)}% faster)",
            price_fn=lambda: weapon_upgrades.speed_price,
            level_fn=lambda: weapon_upgrades.speed_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_speed(m),
            buy_fn=lambda m: weapon_upgrades.buy_speed(m),
            icon_fn=self._draw_shotgun_speed_icon,
            rect=pygame.Rect(row1_x + 2 * (cw + gap), row1_y, cw, ch),
        ))

        return cards

    def _build_assault_rifle_upgrade_cards(self, row1_x: int, row1_y: int, cw: int, ch: int, gap: int) -> list[_UpgradeCard]:
        """Build upgrade cards for assault rifle."""
        from storm_the_house.core.settings import (
            ASSAULT_RIFLE_MAX_AMMO, ASSAULT_RIFLE_RELOAD_TIME,
            ASSAULT_RIFLE_UPGRADE_MAG_BONUS, ASSAULT_RIFLE_UPGRADE_RECOIL_REDUCTION,
        )
        u = self.upgrades
        weapon_upgrades = u.assault_rifle_upgrades
        cards: list[_UpgradeCard] = []

        # 1) Larger Magazine (+5 ammo)
        cards.append(_UpgradeCard(
            key="rifle_mag",
            title="Larger Magazine",
            desc_fn=lambda: f"Ammo: {ASSAULT_RIFLE_MAX_AMMO + weapon_upgrades.bonus_ammo} (+{ASSAULT_RIFLE_UPGRADE_MAG_BONUS})",
            price_fn=lambda: weapon_upgrades.mag_price,
            level_fn=lambda: weapon_upgrades.mag_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_mag(m),
            buy_fn=lambda m: weapon_upgrades.buy_mag(m),
            icon_fn=self._draw_rifle_mag_icon,
            rect=pygame.Rect(row1_x, row1_y, cw, ch),
        ))

        # 2) Compensator (reduces recoil)
        cards.append(_UpgradeCard(
            key="rifle_comp",
            title="Compensator",
            desc_fn=lambda: f"Recoil: -{int((1 - (1 - ASSAULT_RIFLE_UPGRADE_RECOIL_REDUCTION) ** weapon_upgrades.compensator_level) * 100)}%",
            price_fn=lambda: weapon_upgrades.compensator_price,
            level_fn=lambda: weapon_upgrades.compensator_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_compensator(m),
            buy_fn=lambda m: weapon_upgrades.buy_compensator(m),
            icon_fn=self._draw_rifle_compensator_icon,
            rect=pygame.Rect(row1_x + cw + gap, row1_y, cw, ch),
        ))

        # 3) Faster Reload
        cards.append(_UpgradeCard(
            key="rifle_reload",
            title="Faster Reload",
            desc_fn=lambda: f"Reload: {ASSAULT_RIFLE_RELOAD_TIME * weapon_upgrades.reload_multiplier:.2f}s",
            price_fn=lambda: weapon_upgrades.reload_price,
            level_fn=lambda: weapon_upgrades.reload_level,
            can_buy_fn=lambda m: weapon_upgrades.can_buy_reload(m),
            buy_fn=lambda m: weapon_upgrades.buy_reload(m),
            icon_fn=self._draw_rifle_reload_icon,
            rect=pygame.Rect(row1_x + 2 * (cw + gap), row1_y, cw, ch),
        ))

        return cards

    # ── house upgrade wrappers (need self.house) ─────────────────────

    def _buy_repair(self, money: int) -> int:
        money = self.upgrades.buy_repair(money, self.house)
        # Update displayed HP
        if self.house:
            self.house_hp = self.house.hp
            self.house_max_hp = self.house.max_hp
        return money

    def _buy_fortify(self, money: int) -> int:
        money = self.upgrades.buy_fortify(money, self.house)
        # Update displayed HP
        if self.house:
            self.house_hp = self.house.hp
            self.house_max_hp = self.house.max_hp
        return money

    # ── icon drawers ─────────────────────────────────────────────────────

    @staticmethod
    def _draw_damage_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a small crosshair / target icon."""
        r = 14
        col = UPGRADE_CARD_ICON
        pygame.draw.circle(surface, col, (cx, cy), r, 2)
        pygame.draw.circle(surface, col, (cx, cy), r // 2, 1)
        pygame.draw.line(surface, col, (cx - r - 4, cy), (cx + r + 4, cy), 2)
        pygame.draw.line(surface, col, (cx, cy - r - 4), (cx, cy + r + 4), 2)

    @staticmethod
    def _draw_ammo_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a small bullet icon."""
        col = UPGRADE_CARD_ICON
        bw, bh = 8, 22
        bx = cx - bw // 2
        by = cy - bh // 2
        casing_h = int(bh * 0.6)
        pygame.draw.rect(surface, (180, 155, 60),
                         pygame.Rect(bx, by + bh - casing_h, bw, casing_h))
        pygame.draw.rect(surface, col,
                         pygame.Rect(bx, by, bw, bh - casing_h + 2))
        pygame.draw.circle(surface, col, (cx, by + 1), bw // 2)
        pygame.draw.line(surface, (255, 245, 200),
                         (bx + 1, by + 3), (bx + 1, by + bh - 4), 1)

    @staticmethod
    def _draw_reload_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a circular arrow / reload icon."""
        col = UPGRADE_CARD_ICON
        r = 14
        for i in range(20):
            a1 = -math.pi / 2 + i * (1.6 * math.pi / 20)
            a2 = -math.pi / 2 + (i + 1) * (1.6 * math.pi / 20)
            x1 = cx + int(math.cos(a1) * r)
            y1 = cy + int(math.sin(a1) * r)
            x2 = cx + int(math.cos(a2) * r)
            y2 = cy + int(math.sin(a2) * r)
            pygame.draw.line(surface, col, (x1, y1), (x2, y2), 2)
        end_a = -math.pi / 2 + 1.6 * math.pi
        ex = cx + int(math.cos(end_a) * r)
        ey = cy + int(math.sin(end_a) * r)
        for da in [-0.5, 0.5]:
            ax = ex + int(math.cos(end_a + da) * 7)
            ay = ey + int(math.sin(end_a + da) * 7)
            pygame.draw.line(surface, col, (ex, ey), (ax, ay), 2)

    @staticmethod
    def _draw_repair_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a wrench / repair icon."""
        col = UPGRADE_CARD_ICON
        # Simple wrench shape: a vertical bar with a circular head
        pygame.draw.rect(surface, col,
                         pygame.Rect(cx - 3, cy - 6, 6, 20),
                         border_radius=2)
        # Wrench head (open jaw)
        pygame.draw.circle(surface, col, (cx, cy - 8), 8, 2)
        # Cross (plus sign for "repair")
        pygame.draw.line(surface, (120, 210, 100),
                         (cx - 5, cy + 4), (cx + 5, cy + 4), 2)
        pygame.draw.line(surface, (120, 210, 100),
                         (cx, cy - 1), (cx, cy + 9), 2)

    @staticmethod
    def _draw_fortify_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a shield icon for fortification."""
        col = UPGRADE_CARD_ICON
        # Shield shape (pointed bottom)
        points = [
            (cx - 12, cy - 12),
            (cx + 12, cy - 12),
            (cx + 12, cy + 2),
            (cx, cy + 14),
            (cx - 12, cy + 2),
        ]
        pygame.draw.polygon(surface, col, points, 2)
        # Inner cross
        pygame.draw.line(surface, col, (cx, cy - 8), (cx, cy + 8), 2)
        pygame.draw.line(surface, col, (cx - 7, cy - 2), (cx + 7, cy - 2), 2)

    @staticmethod
    def _draw_repairman_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a hard hat + hammer icon for the Repair Man."""
        col = UPGRADE_CARD_ICON
        hat_col = (220, 180, 50)
        # Hard hat
        pygame.draw.ellipse(surface, hat_col,
                            pygame.Rect(cx - 10, cy - 14, 20, 10))
        pygame.draw.rect(surface, hat_col,
                         pygame.Rect(cx - 12, cy - 8, 24, 4), border_radius=1)
        # Hammer
        handle_top = (cx + 2, cy + 2)
        handle_bot = (cx + 2, cy + 14)
        pygame.draw.line(surface, (150, 100, 50), handle_top, handle_bot, 3)
        # Hammer head
        pygame.draw.rect(surface, col,
                         pygame.Rect(cx - 4, cy - 1, 12, 5), border_radius=1)

    @staticmethod
    def _draw_gunman_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a helmet + rifle icon for the Gun Man."""
        col = UPGRADE_CARD_ICON
        helmet_col = (85, 95, 80)
        gun_metal = (100, 100, 110)
        # Helmet
        pygame.draw.ellipse(surface, helmet_col,
                            pygame.Rect(cx - 10, cy - 14, 20, 12))
        # Rifle (horizontal)
        pygame.draw.line(surface, gun_metal,
                         (cx - 16, cy + 4), (cx + 16, cy + 4), 3)
        # Stock
        pygame.draw.rect(surface, (110, 70, 40),
                         pygame.Rect(cx + 8, cy + 2, 8, 5), border_radius=1)
        # Barrel tip
        pygame.draw.line(surface, col,
                         (cx - 16, cy + 4), (cx - 20, cy + 4), 2)
        # Trigger guard
        pygame.draw.circle(surface, gun_metal, (cx, cy + 8), 3, 1)

    # ── scene interface ───────────────────────────────────────────────

    @property
    def next_scene(self) -> str | None:
        if self._continue:
            return "next_day"
        return None

    def update(self, dt: float, events: list[pygame.event.Event] | None = None):
        mx, my = pygame.mouse.get_pos()
        self._btn_hovered = self._btn_rect.collidepoint(mx, my)

        for card in self._cards:
            card.hovered = card.rect.collidepoint(mx, my)

        # Flash timer
        if self._flash_timer > 0:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                self._flash_card = None

        if events:
            for ev in events:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    # Check continue button
                    if self._btn_hovered:
                        self._continue = True
                        continue

                    # Check weapon panel clicks
                    weapon_clicked = self._check_weapon_panel_click(mx, my)
                    if weapon_clicked:
                        continue

                    # Check upgrade cards
                    for card in self._cards:
                        if card.hovered and card.can_buy_fn(self.money):
                            self.money = card.buy_fn(self.money)
                            self._flash_card = card.key
                            self._flash_timer = 0.35

    def _check_weapon_panel_click(self, mx: int, my: int) -> bool:
        """Check if a weapon panel button was clicked. Returns True if handled."""
        u = self.upgrades

        # Weapon panel position (right side of screen)
        panel_x = SCREEN_WIDTH - 200
        panel_y = 248
        panel_w = 180
        btn_h = 60
        gap = 8

        # Check each weapon button
        weapons = [
            ("pistol", "Pistol", True),  # Always owned
            ("shotgun", "Shotgun", u.owns_shotgun),
            ("assault_rifle", "Assault Rifle", u.owns_assault_rifle),
        ]

        for i, (weapon_type, name, owned) in enumerate(weapons):
            btn_y = panel_y + i * (btn_h + gap)
            btn_rect = pygame.Rect(panel_x, btn_y, panel_w, btn_h)

            if btn_rect.collidepoint(mx, my):
                if owned:
                    # Select this weapon
                    u.selected_weapon = weapon_type
                    # Rebuild cards for new weapon
                    self._cards = self._build_cards()
                    return True
                else:
                    # Try to purchase
                    if weapon_type == "shotgun" and u.can_buy_shotgun(self.money):
                        self.money = u.buy_shotgun(self.money)
                        self._flash_card = "buy_shotgun"
                        self._flash_timer = 0.35
                        return True
                    elif weapon_type == "assault_rifle" and u.can_buy_assault_rifle(self.money):
                        self.money = u.buy_assault_rifle(self.money)
                        self._flash_card = "buy_assault_rifle"
                        self._flash_timer = 0.35
                        return True

        return False

    # ── draw ──────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, time_ms: int):
        # Background
        if self.bg_snapshot is not None:
            surface.blit(self.bg_snapshot, (0, 0))
        else:
            surface.fill((20, 18, 15))

        # Dark overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # ── stats panel (top portion) ────────────────────────────────
        pw, ph = 620, 195
        px = (SCREEN_WIDTH - pw) // 2 - 100  # Shift left for weapon panel
        py = 10
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, EOD_PANEL_COLOR, panel.get_rect(),
                         border_radius=14)
        pygame.draw.rect(panel, (80, 70, 55, 120), panel.get_rect(),
                         width=2, border_radius=14)
        surface.blit(panel, (px, py))

        # Title
        ft = self._ft()
        title = ft.render(f"Day {self.day} Complete", True, EOD_TITLE_COLOR)
        title_shadow = ft.render(f"Day {self.day} Complete", True, (0, 0, 0))
        tx = (SCREEN_WIDTH - title.get_width()) // 2 - 100
        ty = py + 12
        surface.blit(title_shadow, (tx + 2, ty + 2))
        surface.blit(title, (tx, ty))

        # Divider
        div_y = ty + title.get_height() + 6
        pygame.draw.line(surface, (100, 90, 70, 80),
                         (px + 30, div_y), (px + pw - 30, div_y), 1)

        # Stats (compact)
        fs = self._fs()
        fl = self._fl()
        stat_x_label = px + 40
        stat_x_value = px + pw - 40
        row_h = 28
        start_y = div_y + 8

        stats = [
            ("Enemies Killed", str(self.kills)),
            ("House Health", f"{self.house_hp} / {self.house_max_hp}"),
            ("Money", f"${self.money:,}"),
        ]

        for i, (label, value) in enumerate(stats):
            y = start_y + i * row_h
            lbl = fl.render(label, True, EOD_STAT_LABEL)
            val = fs.render(value, True, EOD_STAT_VALUE)
            surface.blit(lbl, (stat_x_label, y + 2))
            surface.blit(val, (stat_x_value - val.get_width(), y))

        # Bonus line
        bonus_y = start_y + len(stats) * row_h + 2
        pygame.draw.line(surface, (100, 90, 70, 80),
                         (px + 30, bonus_y - 2), (px + pw - 30, bonus_y - 2), 1)
        bonus_label = fl.render("Day Bonus", True, EOD_BONUS_COLOR)
        bonus_val = fs.render(f"+${self.bonus}", True, EOD_BONUS_COLOR)
        surface.blit(bonus_label, (stat_x_label, bonus_y + 2))
        surface.blit(bonus_val,
                     (stat_x_value - bonus_val.get_width(), bonus_y))

        # ── "Upgrades" section header ────────────────────────────────
        upgrades_label = ft.render("Upgrades", True, (200, 190, 165))
        upgrades_shadow = ft.render("Upgrades", True, (0, 0, 0))
        ulx = self._cards[0].rect.x + (3 * UPGRADE_CARD_W + 2 * UPGRADE_CARD_GAP) // 2 - upgrades_label.get_width() // 2
        uly = self._cards[0].rect.y - 34
        surface.blit(upgrades_shadow, (ulx + 1, uly + 1))
        surface.blit(upgrades_label, (ulx, uly))

        # ── upgrade cards ────────────────────────────────────────────
        for card in self._cards:
            self._draw_card(surface, card, time_ms)

        # ── weapon panel (right side) ────────────────────────────────────
        self._draw_weapon_panel(surface, time_ms)

        # ── continue button ──────────────────────────────────────────
        btn_color = EOD_BTN_HOVER if self._btn_hovered else EOD_BTN_COLOR
        pygame.draw.rect(surface, (0, 0, 0, 70),
                         self._btn_rect.move(3, 3), border_radius=10)
        pygame.draw.rect(surface, btn_color, self._btn_rect, border_radius=10)
        hl = pygame.Surface((self._btn_rect.width - 8, 5), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 30))
        surface.blit(hl, (self._btn_rect.x + 4, self._btn_rect.y + 2))
        pygame.draw.rect(surface,
                         lerp_color(btn_color, (255, 255, 255), 0.15),
                         self._btn_rect, width=2, border_radius=10)
        fb = self._fb()
        btn_txt = fb.render("Continue to Next Day", True, EOD_BTN_TEXT)
        surface.blit(btn_txt,
                     (self._btn_rect.centerx - btn_txt.get_width() // 2,
                      self._btn_rect.centery - btn_txt.get_height() // 2))

    def _draw_weapon_panel(self, surface: pygame.Surface, time_ms: int):
        """Draw the weapon selection panel on the right side."""
        u = self.upgrades

        # Panel position
        panel_x = SCREEN_WIDTH - 200
        panel_y = 248
        panel_w = 180
        btn_h = 60
        gap = 8

        # Panel header
        ft = self._ft()
        header = ft.render("Weapons", True, (200, 190, 165))
        header_shadow = ft.render("Weapons", True, (0, 0, 0))
        surface.blit(header_shadow, (panel_x + panel_w // 2 - header.get_width() // 2 + 1, panel_y - 34 + 1))
        surface.blit(header, (panel_x + panel_w // 2 - header.get_width() // 2, panel_y - 34))

        # Weapon buttons
        weapons = [
            ("pistol", "Pistol", True, 0),
            ("shotgun", "Shotgun", u.owns_shotgun, SHOTGUN_COST),
            ("assault_rifle", "Assault Rifle", u.owns_assault_rifle, ASSAULT_RIFLE_COST),
        ]

        fct = self._fct()
        fcd = self._fcd()
        fcp = self._fcp()

        mx, my = pygame.mouse.get_pos()

        for i, (weapon_type, name, owned, cost) in enumerate(weapons):
            btn_y = panel_y + i * (btn_h + gap)
            btn_rect = pygame.Rect(panel_x, btn_y, panel_w, btn_h)
            is_selected = u.selected_weapon == weapon_type
            is_hovered = btn_rect.collidepoint(mx, my)

            # Background color
            if is_selected:
                bg_color = (50, 70, 45, 230)
            elif owned and is_hovered:
                bg_color = (55, 50, 40, 230)
            elif owned:
                bg_color = (40, 38, 32, 220)
            elif not owned and is_hovered and self.money >= cost:
                bg_color = (60, 55, 35, 230)
            else:
                bg_color = (30, 28, 25, 180)

            # Draw button
            btn_surf = pygame.Surface((panel_w, btn_h), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, bg_color, btn_surf.get_rect(), border_radius=8)

            # Border
            if is_selected:
                border_col = (100, 180, 80)
            elif owned and is_hovered:
                border_col = lerp_color(UPGRADE_CARD_BORDER, (255, 255, 255), 0.2)
            elif not owned and self.money >= cost:
                border_col = (150, 130, 80)
            else:
                border_col = (60, 55, 50)

            pygame.draw.rect(btn_surf, border_col, btn_surf.get_rect(), width=2, border_radius=8)
            surface.blit(btn_surf, btn_rect.topleft)

            # Weapon number
            num_font = self._fs()
            num_text = num_font.render(f"{i + 1}", True, (150, 145, 135))
            surface.blit(num_text, (btn_rect.x + 8, btn_rect.y + 6))

            # Weapon name
            name_color = (230, 220, 190) if owned else (130, 120, 110)
            name_surf = fct.render(name, True, name_color)
            surface.blit(name_surf, (btn_rect.centerx - name_surf.get_width() // 2, btn_rect.y + 8))

            # Status
            if owned:
                status_text = "OWNED" if is_selected else "Select"
                status_color = (100, 180, 80) if is_selected else (150, 145, 130)
            else:
                if self.money >= cost:
                    status_text = f"${cost} - Buy"
                    status_color = (180, 160, 80)
                else:
                    status_text = f"${cost}"
                    status_color = (140, 80, 60)

            status_surf = fcd.render(status_text, True, status_color)
            surface.blit(status_surf, (btn_rect.centerx - status_surf.get_width() // 2, btn_rect.y + 32))

            # Draw weapon icon
            icon_x = btn_rect.x + 25
            icon_y = btn_rect.centery
            if weapon_type == "pistol":
                self._draw_pistol_icon(surface, icon_x, icon_y)
            elif weapon_type == "shotgun":
                self._draw_shotgun_icon(surface, icon_x, icon_y)
            elif weapon_type == "assault_rifle":
                self._draw_rifle_icon(surface, icon_x, icon_y)

    @staticmethod
    def _draw_pistol_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a small pistol icon."""
        col = UPGRADE_CARD_ICON
        # Slide
        pygame.draw.rect(surface, col, pygame.Rect(cx - 2, cy - 8, 4, 10), border_radius=1)
        # Barrel
        pygame.draw.rect(surface, col, pygame.Rect(cx - 2, cy - 12, 4, 6), border_radius=1)
        # Grip
        pygame.draw.rect(surface, (110, 70, 40), pygame.Rect(cx - 3, cy + 2, 6, 8), border_radius=1)
        # Trigger guard
        pygame.draw.arc(surface, col, pygame.Rect(cx - 4, cy, 8, 6), 0, math.pi, 1)

    @staticmethod
    def _draw_shotgun_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a small shotgun icon (M870 style)."""
        col = UPGRADE_CARD_ICON
        # Barrel (long)
        pygame.draw.rect(surface, col, pygame.Rect(cx - 2, cy - 16, 4, 18), border_radius=1)
        # Receiver
        pygame.draw.rect(surface, (70, 70, 75), pygame.Rect(cx - 3, cy - 4, 6, 10), border_radius=1)
        # Pump
        pygame.draw.rect(surface, (110, 70, 40), pygame.Rect(cx - 4, cy - 8, 8, 5), border_radius=1)
        # Stock
        pygame.draw.rect(surface, (110, 70, 40), pygame.Rect(cx - 3, cy + 4, 6, 8), border_radius=1)

    @staticmethod
    def _draw_rifle_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw a small assault rifle icon."""
        col = UPGRADE_CARD_ICON
        # Barrel
        pygame.draw.rect(surface, col, pygame.Rect(cx - 2, cy - 16, 4, 16), border_radius=1)
        # Front sight
        pygame.draw.rect(surface, (60, 60, 65), pygame.Rect(cx - 3, cy - 18, 6, 4), border_radius=1)
        # Receiver
        pygame.draw.rect(surface, (60, 60, 65), pygame.Rect(cx - 5, cy - 4, 10, 10), border_radius=1)
        # Carry handle
        pygame.draw.rect(surface, (80, 80, 85), pygame.Rect(cx - 4, cy - 8, 8, 3), border_radius=1)
        # Magazine
        pygame.draw.rect(surface, col, pygame.Rect(cx + 2, cy + 2, 5, 10), border_radius=1)
        # Stock
        pygame.draw.rect(surface, (100, 65, 35), pygame.Rect(cx - 6, cy + 4, 8, 6), border_radius=1)
        # Grip
        pygame.draw.rect(surface, (100, 65, 35), pygame.Rect(cx - 3, cy + 6, 4, 6), border_radius=1)

    # ── shotgun upgrade icons ─────────────────────────────────────────

    @staticmethod
    def _draw_shotgun_barrel_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw icon for Longer Barrel upgrade - extended barrel."""
        col = UPGRADE_CARD_ICON
        # Long barrel
        pygame.draw.rect(surface, col, pygame.Rect(cx - 2, cy - 18, 4, 24), border_radius=1)
        # Barrel extension (highlighted)
        pygame.draw.rect(surface, (100, 100, 110), pygame.Rect(cx - 3, cy - 22, 6, 6), border_radius=1)
        # Receiver
        pygame.draw.rect(surface, (60, 60, 65), pygame.Rect(cx - 4, cy + 4, 8, 8), border_radius=1)
        # Plus sign
        pygame.draw.line(surface, (120, 200, 100), (cx - 8, cy), (cx + 8, cy), 2)
        pygame.draw.line(surface, (120, 200, 100), (cx, cy - 8), (cx, cy + 8), 2)

    @staticmethod
    def _draw_shotgun_pellet_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw icon for Buckshot upgrade - multiple pellets."""
        # Draw multiple small pellets radiating outward
        pellet_col = (200, 50, 30)  # Red pellets
        pellet_outline = (150, 40, 25)

        # Center pellet
        pygame.draw.circle(surface, pellet_col, (cx, cy), 4)
        pygame.draw.circle(surface, pellet_outline, (cx, cy), 4, 1)

        # Surrounding pellets in a spread pattern
        positions = [
            (cx - 8, cy - 8), (cx + 8, cy - 8),
            (cx - 8, cy + 8), (cx + 8, cy + 8),
            (cx - 12, cy), (cx + 12, cy),
            (cx, cy - 12), (cx, cy + 12),
        ]
        for px, py in positions:
            pygame.draw.circle(surface, pellet_col, (px, py), 3)
            pygame.draw.circle(surface, pellet_outline, (px, py), 3, 1)

    @staticmethod
    def _draw_shotgun_speed_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw icon for Faster Handling upgrade - speed/gear."""
        col = UPGRADE_CARD_ICON
        # Clock face
        pygame.draw.circle(surface, col, (cx, cy), 12, 2)
        # Clock hands
        pygame.draw.line(surface, col, (cx, cy), (cx, cy - 8), 2)
        pygame.draw.line(surface, col, (cx, cy), (cx + 6, cy), 2)
        # Speed lines
        pygame.draw.line(surface, (120, 200, 100), (cx + 14, cy - 4), (cx + 20, cy - 4), 2)
        pygame.draw.line(surface, (120, 200, 100), (cx + 14, cy), (cx + 22, cy), 2)
        pygame.draw.line(surface, (120, 200, 100), (cx + 14, cy + 4), (cx + 20, cy + 4), 2)

    @staticmethod
    def _draw_rifle_mag_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw icon for Larger Magazine upgrade."""
        col = UPGRADE_CARD_ICON
        # Magazine body
        pygame.draw.rect(surface, col, pygame.Rect(cx - 6, cy - 10, 12, 22), border_radius=2)
        # Rounds window
        pygame.draw.rect(surface, (90, 85, 70), pygame.Rect(cx - 3, cy - 6, 6, 12), border_radius=1)
        # Plus sign
        pygame.draw.line(surface, (120, 200, 100), (cx - 10, cy), (cx - 2, cy), 2)
        pygame.draw.line(surface, (120, 200, 100), (cx - 6, cy - 4), (cx - 6, cy + 4), 2)

    @staticmethod
    def _draw_rifle_compensator_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw icon for Compensator upgrade."""
        col = UPGRADE_CARD_ICON
        # Barrel tip
        pygame.draw.rect(surface, col, pygame.Rect(cx - 12, cy - 3, 18, 6), border_radius=2)
        # Ports
        for i in range(3):
            pygame.draw.circle(surface, (60, 60, 65), (cx - 6 + i * 6, cy - 6), 2)
        # Downward arrow
        pygame.draw.line(surface, (120, 200, 100), (cx + 8, cy - 6), (cx + 8, cy + 6), 2)
        pygame.draw.polygon(surface, (120, 200, 100), [(cx + 8, cy + 8), (cx + 4, cy + 2), (cx + 12, cy + 2)])

    @staticmethod
    def _draw_rifle_reload_icon(surface: pygame.Surface, cx: int, cy: int):
        """Draw icon for Faster Reload upgrade."""
        col = UPGRADE_CARD_ICON
        # Circular arrow
        pygame.draw.circle(surface, col, (cx, cy), 12, 2)
        pygame.draw.arc(surface, col, pygame.Rect(cx - 12, cy - 12, 24, 24), math.pi * 0.2, math.pi * 1.6, 2)
        # Arrow head
        pygame.draw.polygon(surface, col, [(cx + 10, cy - 6), (cx + 16, cy - 2), (cx + 9, cy + 1)])

    # ── single card renderer ─────────────────────────────────────────

    def _draw_card(self, surface: pygame.Surface, card: _UpgradeCard,
                   time_ms: int):
        r = card.rect
        is_maxed = card.maxed_fn() if card.maxed_fn else False
        can_afford = (not is_maxed) and card.can_buy_fn(self.money)
        is_flashing = (self._flash_card == card.key and self._flash_timer > 0)

        # Card background
        if is_maxed:
            bg_color = (35, 35, 40, 200)
        elif is_flashing:
            bg_color = (70, 100, 55, 240)
        elif card.hovered and can_afford:
            bg_color = UPGRADE_CARD_HOVER
        elif not can_afford:
            bg_color = UPGRADE_CARD_LOCKED
        else:
            bg_color = UPGRADE_CARD_BG

        card_surf = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
        pygame.draw.rect(card_surf, bg_color, card_surf.get_rect(),
                         border_radius=10)

        # Border
        if is_maxed:
            border_col = (80, 80, 90)
        elif is_flashing:
            border_col = (120, 200, 100)
        elif card.hovered and can_afford:
            border_col = lerp_color(UPGRADE_CARD_BORDER, (255, 255, 255), 0.3)
        else:
            border_col = UPGRADE_CARD_BORDER
        pygame.draw.rect(card_surf, border_col, card_surf.get_rect(),
                         width=2, border_radius=10)

        surface.blit(card_surf, r.topleft)

        # Icon (centered near top)
        icon_cy = r.y + 22
        card.icon_fn(surface, r.centerx, icon_cy)

        # Title
        fct = self._fct()
        title_surf = fct.render(card.title, True, UPGRADE_CARD_TITLE)
        surface.blit(title_surf,
                     (r.centerx - title_surf.get_width() // 2, r.y + 38))

        # Description (current stat)
        fcd = self._fcd()
        desc_surf = fcd.render(card.desc_fn(), True, UPGRADE_CARD_DESC)
        surface.blit(desc_surf,
                     (r.centerx - desc_surf.get_width() // 2, r.y + 56))

        # Level indicator
        fcl = self._fcl()
        level = card.level_fn()
        if level > 0:
            if is_maxed:
                lvl_text = f"Lv {level} (MAX)"
            else:
                lvl_text = f"Lv {level}"
            lvl_surf = fcl.render(lvl_text, True, UPGRADE_CARD_LEVEL)
            surface.blit(lvl_surf,
                         (r.centerx - lvl_surf.get_width() // 2, r.y + 72))

        # Price / buy prompt
        fcp = self._fcp()
        if is_maxed:
            price_surf = fcp.render("MAXED", True, (120, 120, 130))
        else:
            price = card.price_fn()
            price_str = f"${price:,}"
            price_col = UPGRADE_CARD_PRICE if can_afford else UPGRADE_CARD_PRICE_LOCKED
            price_surf = fcp.render(price_str, True, price_col)
        surface.blit(price_surf,
                     (r.centerx - price_surf.get_width() // 2,
                      r.y + r.height - 28))

        # "Click to buy" / "Can't afford" / "Maxed out"
        if is_maxed:
            hint = fcd.render("Fully fortified", True, (100, 100, 110))
        elif can_afford:
            hint = fcd.render("Click to buy", True, (140, 190, 120))
        else:
            hint = fcd.render("Can't afford", True, (140, 100, 80))
        surface.blit(hint,
                     (r.centerx - hint.get_width() // 2,
                      r.y + r.height - 12))

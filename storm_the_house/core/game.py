"""
Core game engine – owns the Pygame display, clock, and main loop.

Scenes are swappable (menu → game → game-over etc.) via ``set_scene()``.
The engine polls each scene's ``next_scene`` property every frame and
performs the appropriate transition.
"""

from __future__ import annotations

import sys
import pygame

from storm_the_house.core.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, BLACK,
)


class Game:
    """Top-level game controller with scene management."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self._scene = None
        self._cursor_visible: bool | None = None  # track to avoid redundant calls

    # ── scene management ─────────────────────────────────────────────────

    def set_scene(self, scene):
        """Replace the active scene and update cursor visibility."""
        self._scene = scene
        self._sync_cursor()

    def _sync_cursor(self):
        """Show / hide the system cursor based on the active scene."""
        want = getattr(self._scene, "show_cursor", False)
        if want != self._cursor_visible:
            pygame.mouse.set_visible(want)
            self._cursor_visible = want

    # ── scene transitions ────────────────────────────────────────────────

    def _check_transition(self):
        """Poll the current scene's ``next_scene`` and act on it."""
        if self._scene is None:
            return
        ns = getattr(self._scene, "next_scene", None)
        if ns is None:
            return

        # Import here to avoid circular imports
        from storm_the_house.scenes.game_scene import GameScene
        from storm_the_house.scenes.end_of_day import EndOfDayScene
        from storm_the_house.scenes.main_menu import MainMenuScene
        from storm_the_house.scenes.game_over import GameOverScene
        from storm_the_house.entities.upgrades import UpgradeState

        if ns == "play":
            # MainMenu → first day
            upgrades = UpgradeState()
            gs = GameScene(day=1, money=0, upgrades=upgrades)
            self.set_scene(gs)

        elif ns == "end_of_day":
            # GameScene → EndOfDayScene
            gs = self._scene  # type: ignore[assignment]
            eod = EndOfDayScene(
                day=gs.day,
                kills=gs.kills,
                house_hp=gs.house.hp,
                house_max_hp=gs.house.max_hp,
                money_before_bonus=gs.money,
                upgrades=gs.upgrades,
                house=gs.house,
            )
            eod.bg_snapshot = gs.last_frame
            # Stash game state on the EOD scene so we can resume
            eod._carry_day = gs.day               # type: ignore[attr-defined]
            eod._carry_house = gs.house           # type: ignore[attr-defined]
            eod._carry_weapon_manager = gs.weapon_manager  # type: ignore[attr-defined]
            self.set_scene(eod)

        elif ns == "next_day":
            # EndOfDayScene → next GameScene
            eod_scene: EndOfDayScene = self._scene  # type: ignore[assignment]
            day = getattr(eod_scene, "_carry_day", 1) + 1
            money = eod_scene.money  # current money (after purchases)
            house = getattr(eod_scene, "_carry_house", None)
            weapon_manager = getattr(eod_scene, "_carry_weapon_manager", None)
            upgrades = eod_scene.upgrades

            # Sync weapon ownership from upgrades to weapon_manager
            if weapon_manager and upgrades:
                if upgrades.owns_shotgun and not weapon_manager.owns_weapon("shotgun"):
                    weapon_manager.purchase_shotgun()
                if upgrades.owns_assault_rifle and not weapon_manager.owns_weapon("assault_rifle"):
                    weapon_manager.purchase_assault_rifle()

            gs = GameScene(
                day=day,
                money=money,
                house=house,
                weapon_manager=weapon_manager,
                upgrades=upgrades,
            )
            self.set_scene(gs)

        elif ns == "game_over":
            # GameScene → GameOverScene
            gs = self._scene  # type: ignore[assignment]
            go = GameOverScene(day=gs.day)
            go.bg_snapshot = gs.last_frame
            self.set_scene(go)

        elif ns == "main_menu":
            # GameOverScene → MainMenuScene (fresh start)
            self.set_scene(MainMenuScene())

    # ── main loop ────────────────────────────────────────────────────────

    def run(self):
        """Enter the main game loop.  Blocks until the window is closed."""
        self._sync_cursor()

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            time_ms = pygame.time.get_ticks()

            # ── events ────────────────────────────────────────────────
            scene_events: list[pygame.event.Event] = []
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    else:
                        # Forward non-escape key presses to the scene
                        scene_events.append(event)
                else:
                    scene_events.append(event)

            # ── update ────────────────────────────────────────────────
            if self._scene is not None:
                self._scene.update(dt, scene_events)

            # ── scene transitions ─────────────────────────────────────
            self._check_transition()

            # ── draw ──────────────────────────────────────────────────
            self.screen.fill(BLACK)
            if self._scene is not None:
                self._scene.draw(self.screen, time_ms)

            pygame.display.flip()

        pygame.quit()
        sys.exit()

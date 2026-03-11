"""
Player weapon – tracks ammo, reload state, and fires shots.

The weapon doesn't know about enemies or particles; it just reports
whether a shot was fired and whether the player is reloading.
The scene wires hit-testing and effects on top.
"""

from __future__ import annotations

from storm_the_house.core.settings import (
    PLAYER_MAX_AMMO, PLAYER_GUN_DAMAGE, PLAYER_RELOAD_TIME,
)


class Weapon:
    """Simple gun with ammo count and timed reload."""

    def __init__(self):
        self.ammo: int = PLAYER_MAX_AMMO
        self.max_ammo: int = PLAYER_MAX_AMMO
        self.damage: int = PLAYER_GUN_DAMAGE
        self.reload_time: float = PLAYER_RELOAD_TIME

        self._reloading: bool = False
        self._reload_elapsed: float = 0.0

    # ── properties ──────────────────────────────────────────────────────

    @property
    def is_reloading(self) -> bool:
        return self._reloading

    @property
    def reload_progress(self) -> float:
        """0.0 → 1.0 showing how far through the reload we are."""
        if not self._reloading:
            return 0.0
        return min(1.0, self._reload_elapsed / self.reload_time)

    @property
    def can_fire(self) -> bool:
        return self.ammo > 0 and not self._reloading

    # ── actions ─────────────────────────────────────────────────────────

    def try_fire(self) -> bool:
        """Attempt to fire one shot.  Returns True if successful.

        Automatically begins reloading when the last round is spent.
        """
        if not self.can_fire:
            return False
        self.ammo -= 1
        # Auto-reload on empty
        if self.ammo <= 0:
            self.start_reload()
        return True

    def start_reload(self):
        """Begin reloading (only if not already reloading and ammo isn't full)."""
        if self._reloading or self.ammo == self.max_ammo:
            return
        self._reloading = True
        self._reload_elapsed = 0.0

    def _finish_reload(self):
        self.ammo = self.max_ammo
        self._reloading = False
        self._reload_elapsed = 0.0

    # ── tick ────────────────────────────────────────────────────────────

    def update(self, dt: float):
        if self._reloading:
            self._reload_elapsed += dt
            if self._reload_elapsed >= self.reload_time:
                self._finish_reload()

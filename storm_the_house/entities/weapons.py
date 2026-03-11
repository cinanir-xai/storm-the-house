"""
Weapon system – multiple weapons with different behaviors.

Each weapon has unique firing mechanics, reload behavior, and visuals.
Weapons are managed by a WeaponManager that handles switching and state.
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from typing import NamedTuple

from storm_the_house.core.settings import (
    PISTOL_MAX_AMMO, PISTOL_DAMAGE, PISTOL_RELOAD_TIME, PISTOL_NAME,
    SHOTGUN_MAX_AMMO, SHOTGUN_PELLET_COUNT, SHOTGUN_PELLET_SPREAD,
    SHOTGUN_DAMAGE_PER_PELLET, SHOTGUN_SHELL_RELOAD_TIME, SHOTGUN_NAME,
    ASSAULT_RIFLE_MAX_AMMO, ASSAULT_RIFLE_DAMAGE, ASSAULT_RIFLE_RELOAD_TIME,
    ASSAULT_RIFLE_NAME, SHOTGUN_COST, ASSAULT_RIFLE_COST,
)


class FireResult(NamedTuple):
    """Result of firing a weapon."""
    success: bool
    pellets: list[tuple[int, int]]  # List of (x, y) pellet positions (empty for single-shot)


class Weapon(ABC):
    """Base class for all weapons."""

    def __init__(self, name: str, max_ammo: int, damage: int, reload_time: float):
        self.name = name
        self.max_ammo = max_ammo
        self.damage = damage
        self.reload_time = reload_time
        self.ammo = max_ammo
        self._reloading = False
        self._reload_elapsed = 0.0
        self._pump_animation = 0.0  # For shotgun pump visual

    @property
    def is_reloading(self) -> bool:
        return self._reloading

    @property
    def reload_progress(self) -> float:
        if not self._reloading:
            return 0.0
        return min(1.0, self._reload_elapsed / self.reload_time)

    @property
    def can_fire(self) -> bool:
        return self.ammo > 0 and not self._reloading

    @property
    def weapon_type(self) -> str:
        return "base"

    @abstractmethod
    def try_fire(self, target_x: int, target_y: int) -> FireResult:
        """Attempt to fire. Returns FireResult with pellet positions."""
        pass

    @abstractmethod
    def start_reload(self):
        """Begin reloading."""
        pass

    def update(self, dt: float):
        if self._pump_animation > 0:
            self._pump_animation -= dt

    def _finish_reload(self):
        self.ammo = self.max_ammo
        self._reloading = False
        self._reload_elapsed = 0.0


class Pistol(Weapon):
    """Standard pistol - single shot, full magazine reload."""

    def __init__(self):
        super().__init__(PISTOL_NAME, PISTOL_MAX_AMMO, PISTOL_DAMAGE, PISTOL_RELOAD_TIME)
        self._damage_upgrade = 0
        self._ammo_upgrade = 0

    @property
    def weapon_type(self) -> str:
        return "pistol"

    def apply_upgrades(self, damage_level: int, ammo_level: int, reload_level: int):
        """Apply upgrade levels to the pistol."""
        self._damage_upgrade = damage_level
        self._ammo_upgrade = ammo_level
        self.damage = PISTOL_DAMAGE + damage_level
        self.max_ammo = PISTOL_MAX_AMMO + ammo_level
        self.reload_time = PISTOL_RELOAD_TIME * (0.85 ** reload_level)
        self.ammo = self.max_ammo

    def try_fire(self, target_x: int, target_y: int) -> FireResult:
        if not self.can_fire:
            return FireResult(success=False, pellets=[])
        self.ammo -= 1
        if self.ammo <= 0:
            self.start_reload()
        return FireResult(success=True, pellets=[(target_x, target_y)])

    def start_reload(self):
        if self._reloading or self.ammo == self.max_ammo:
            return
        self._reloading = True
        self._reload_elapsed = 0.0

    def update(self, dt: float):
        super().update(dt)
        if self._reloading:
            self._reload_elapsed += dt
            if self._reload_elapsed >= self.reload_time:
                self._finish_reload()


class Shotgun(Weapon):
    """Pump-action shotgun - 8 pellets per shot, shell-by-shell reload."""

    def __init__(self):
        super().__init__(SHOTGUN_NAME, SHOTGUN_MAX_AMMO, SHOTGUN_DAMAGE_PER_PELLET, SHOTGUN_SHELL_RELOAD_TIME)
        self._shells_to_reload = 0
        self._is_pumping = False
        self._pump_timer = 0.0
        self._reload_held = False

    @property
    def weapon_type(self) -> str:
        return "shotgun"

    @property
    def is_reloading(self) -> bool:
        return self._reloading or self._is_pumping

    @property
    def reload_progress(self) -> float:
        if not self._reloading:
            return 0.0
        return min(1.0, self._reload_elapsed / SHOTGUN_SHELL_RELOAD_TIME)

    @property
    def can_fire(self) -> bool:
        return self.ammo > 0 and not self._reloading and not self._is_pumping

    def try_fire(self, target_x: int, target_y: int) -> FireResult:
        if not self.can_fire:
            return FireResult(success=False, pellets=[])

        self.ammo -= 1
        self._is_pumping = True
        self._pump_timer = 0.4  # Pump animation duration

        # Generate 8 pellets with spread
        pellets = []
        for _ in range(SHOTGUN_PELLET_COUNT):
            offset_x = random.randint(-SHOTGUN_PELLET_SPREAD, SHOTGUN_PELLET_SPREAD)
            offset_y = random.randint(-SHOTGUN_PELLET_SPREAD, SHOTGUN_PELLET_SPREAD)
            pellets.append((target_x + offset_x, target_y + offset_y))

        return FireResult(success=True, pellets=pellets)

    def start_reload(self):
        """Start loading one shell."""
        if self._reloading or self._is_pumping or self.ammo >= self.max_ammo:
            return
        self._reloading = True
        self._reload_elapsed = 0.0
        self._reload_held = True

    def release_reload(self):
        """Called when reload key is released."""
        self._reload_held = False

    def update(self, dt: float):
        super().update(dt)

        # Pump animation
        if self._is_pumping:
            self._pump_timer -= dt
            if self._pump_timer <= 0:
                self._is_pumping = False

        # Shell-by-shell reload
        if self._reloading:
            self._reload_elapsed += dt
            if self._reload_elapsed >= SHOTGUN_SHELL_RELOAD_TIME:
                # Load one shell
                self.ammo = min(self.max_ammo, self.ammo + 1)
                self._reload_elapsed = 0.0

                # Stop if magazine full or reload key released
                if self.ammo >= self.max_ammo or not self._reload_held:
                    self._reloading = False

    def _finish_reload(self):
        # Shotgun uses shell-by-shell, this is not used
        pass


class AssaultRifle(Weapon):
    """Assault rifle - placeholder for future implementation."""

    def __init__(self):
        super().__init__(ASSAULT_RIFLE_NAME, ASSAULT_RIFLE_MAX_AMMO, ASSAULT_RIFLE_DAMAGE, ASSAULT_RIFLE_RELOAD_TIME)

    @property
    def weapon_type(self) -> str:
        return "assault_rifle"

    def try_fire(self, target_x: int, target_y: int) -> FireResult:
        if not self.can_fire:
            return FireResult(success=False, pellets=[])
        self.ammo -= 1
        if self.ammo <= 0:
            self.start_reload()
        return FireResult(success=True, pellets=[(target_x, target_y)])

    def start_reload(self):
        if self._reloading or self.ammo == self.max_ammo:
            return
        self._reloading = True
        self._reload_elapsed = 0.0

    def update(self, dt: float):
        super().update(dt)
        if self._reloading:
            self._reload_elapsed += dt
            if self._reload_elapsed >= self.reload_time:
                self._finish_reload()


class WeaponManager:
    """Manages all weapons and switching between them."""

    def __init__(self):
        self.pistol = Pistol()
        self.shotgun: Shotgun | None = None
        self.assault_rifle: AssaultRifle | None = None

        self._current_weapon_index = 0
        self._owned_weapons = [self.pistol]  # Pistol is always owned

    @property
    def current_weapon(self) -> Weapon:
        return self._owned_weapons[self._current_weapon_index]

    @property
    def current_weapon_index(self) -> int:
        return self._current_weapon_index

    @property
    def owned_count(self) -> int:
        return len(self._owned_weapons)

    def owns_weapon(self, weapon_type: str) -> bool:
        if weapon_type == "shotgun":
            return self.shotgun is not None
        elif weapon_type == "assault_rifle":
            return self.assault_rifle is not None
        return True  # Pistol is always owned

    def purchase_shotgun(self) -> bool:
        if self.shotgun is not None:
            return False
        self.shotgun = Shotgun()
        self._owned_weapons.append(self.shotgun)
        return True

    def purchase_assault_rifle(self) -> bool:
        if self.assault_rifle is not None:
            return False
        self.assault_rifle = AssaultRifle()
        self._owned_weapons.append(self.assault_rifle)
        return True

    def switch_to(self, index: int) -> bool:
        """Switch to weapon at index. Returns True if successful."""
        if 0 <= index < len(self._owned_weapons):
            self._current_weapon_index = index
            return True
        return False

    def switch_weapon(self, delta: int = 1):
        """Switch to next/previous weapon."""
        new_index = (self._current_weapon_index + delta) % len(self._owned_weapons)
        self._current_weapon_index = new_index

    def update(self, dt: float):
        for weapon in self._owned_weapons:
            weapon.update(dt)

    def get_weapon_by_type(self, weapon_type: str) -> Weapon | None:
        if weapon_type == "pistol":
            return self.pistol
        elif weapon_type == "shotgun":
            return self.shotgun
        elif weapon_type == "assault_rifle":
            return self.assault_rifle
        return None

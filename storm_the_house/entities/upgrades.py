"""
Upgrade state – tracks the level and escalating price of each upgrade.

Weapon upgrades (infinitely stackable):
  - **Damage**  : +1 damage per level
  - **Ammo**    : +1 max ammo per level
  - **Reload**  : 15 % faster reload per level (multiplicative)

House upgrades:
  - **Repair House** : fully heals the house; cost increases 50 % each buy.
  - **Fortify House** : max 2 levels; raises max HP to 500 / 1000 and adds
    visual fortifications (sandbags, boarded windows, barbed wire).

Hired help (infinitely stackable, flat price):
  - **Repair Man** : heals house periodically (1 HP per man per tick).
  - **Gun Man**    : auto-shoots the closest enemy (interval shrinks per man).
"""

from __future__ import annotations

from storm_the_house.core.settings import (
    UPGRADE_BASE_COST, UPGRADE_PRICE_MULTIPLIER,
    UPGRADE_DAMAGE_AMOUNT, UPGRADE_AMMO_AMOUNT, UPGRADE_RELOAD_FACTOR,
    PLAYER_RELOAD_TIME,
    REPAIR_BASE_COST, REPAIR_PRICE_MULTIPLIER,
    FORTIFY_MAX_LEVEL, FORTIFY_COSTS, FORTIFY_HP_LEVELS,
    HOUSE_MAX_HP,
    REPAIRMAN_COST, GUNMAN_COST,
    GUNMAN_BASE_INTERVAL, GUNMAN_SPEED_FACTOR,
)


class UpgradeState:
    """Persistent upgrade tracker that lives across days."""

    def __init__(self):
        # Weapon upgrade levels (0 = not purchased yet)
        self.damage_level: int = 0
        self.ammo_level: int = 0
        self.reload_level: int = 0

        # House upgrades
        self.repair_count: int = 0       # how many times Repair has been bought
        self.fortify_level: int = 0      # 0, 1, or 2

        # Hired help
        self.repairman_count: int = 0
        self.gunman_count: int = 0

    # ── price helpers ────────────────────────────────────────────────────

    @staticmethod
    def _price_for_level(level: int) -> int:
        """Return the cost to buy the *next* level (i.e. going from
        *level* → *level + 1*)."""
        return int(UPGRADE_BASE_COST * (UPGRADE_PRICE_MULTIPLIER ** level))

    @property
    def damage_price(self) -> int:
        return self._price_for_level(self.damage_level)

    @property
    def ammo_price(self) -> int:
        return self._price_for_level(self.ammo_level)

    @property
    def reload_price(self) -> int:
        return self._price_for_level(self.reload_level)

    @property
    def repair_price(self) -> int:
        return int(REPAIR_BASE_COST * (REPAIR_PRICE_MULTIPLIER ** self.repair_count))

    @property
    def fortify_price(self) -> int:
        if self.fortify_level >= FORTIFY_MAX_LEVEL:
            return 0  # maxed out
        return FORTIFY_COSTS[self.fortify_level]

    # ── computed weapon stats ────────────────────────────────────────────

    @property
    def bonus_damage(self) -> int:
        """Total extra damage from upgrades."""
        return self.damage_level * UPGRADE_DAMAGE_AMOUNT

    @property
    def bonus_ammo(self) -> int:
        """Total extra max-ammo from upgrades."""
        return self.ammo_level * UPGRADE_AMMO_AMOUNT

    @property
    def reload_time(self) -> float:
        """Current reload time after all reload upgrades."""
        return PLAYER_RELOAD_TIME * (UPGRADE_RELOAD_FACTOR ** self.reload_level)

    @property
    def current_max_hp(self) -> int:
        """House max HP considering fortification level."""
        if self.fortify_level == 0:
            return HOUSE_MAX_HP
        return FORTIFY_HP_LEVELS[self.fortify_level - 1]

    # ── purchase actions ─────────────────────────────────────────────────

    def can_buy_damage(self, money: int) -> bool:
        return money >= self.damage_price

    def can_buy_ammo(self, money: int) -> bool:
        return money >= self.ammo_price

    def can_buy_reload(self, money: int) -> bool:
        return money >= self.reload_price

    def can_buy_repair(self, money: int) -> bool:
        return money >= self.repair_price

    def can_buy_fortify(self, money: int) -> bool:
        if self.fortify_level >= FORTIFY_MAX_LEVEL:
            return False
        return money >= self.fortify_price

    @property
    def fortify_maxed(self) -> bool:
        return self.fortify_level >= FORTIFY_MAX_LEVEL

    # ── hired help pricing ─────────────────────────────────────────────

    @property
    def repairman_price(self) -> int:
        return REPAIRMAN_COST  # flat, never increases

    @property
    def gunman_price(self) -> int:
        return GUNMAN_COST  # flat, never increases

    def can_buy_repairman(self, money: int) -> bool:
        return money >= self.repairman_price

    def can_buy_gunman(self, money: int) -> bool:
        return money >= self.gunman_price

    @property
    def gunman_fire_interval(self) -> float:
        """Current gunman fire interval considering all purchased gunmen."""
        if self.gunman_count <= 0:
            return GUNMAN_BASE_INTERVAL
        # Each extra gunman beyond the first multiplies interval by SPEED_FACTOR
        return GUNMAN_BASE_INTERVAL * (GUNMAN_SPEED_FACTOR ** (self.gunman_count - 1))

    def buy_damage(self, money: int) -> int:
        """Purchase a damage upgrade.  Returns the remaining money."""
        cost = self.damage_price
        if money < cost:
            return money
        self.damage_level += 1
        return money - cost

    def buy_ammo(self, money: int) -> int:
        """Purchase an ammo upgrade.  Returns the remaining money."""
        cost = self.ammo_price
        if money < cost:
            return money
        self.ammo_level += 1
        return money - cost

    def buy_reload(self, money: int) -> int:
        """Purchase a reload upgrade.  Returns the remaining money."""
        cost = self.reload_price
        if money < cost:
            return money
        self.reload_level += 1
        return money - cost

    def buy_repair(self, money: int, house) -> int:
        """Purchase Repair House.  Fully heals the house.  Returns remaining money."""
        cost = self.repair_price
        if money < cost:
            return money
        self.repair_count += 1
        house.hp = house.max_hp
        return money - cost

    def buy_fortify(self, money: int, house) -> int:
        """Purchase Fortify House.  Raises max HP and updates visuals.
        Returns remaining money."""
        if self.fortify_level >= FORTIFY_MAX_LEVEL:
            return money
        cost = self.fortify_price
        if money < cost:
            return money
        self.fortify_level += 1
        new_max = FORTIFY_HP_LEVELS[self.fortify_level - 1]
        # Increase max HP and heal the difference
        hp_gain = new_max - house.max_hp
        house.max_hp = new_max
        house.hp = min(house.hp + hp_gain, house.max_hp)
        house.fortify_level = self.fortify_level
        return money - cost

    def buy_repairman(self, money: int) -> int:
        """Purchase a Repair Man.  Returns remaining money."""
        cost = self.repairman_price
        if money < cost:
            return money
        self.repairman_count += 1
        return money - cost

    def buy_gunman(self, money: int) -> int:
        """Purchase a Gun Man.  Returns remaining money."""
        cost = self.gunman_price
        if money < cost:
            return money
        self.gunman_count += 1
        return money - cost

    # ── apply to weapon ──────────────────────────────────────────────────

    def apply_to_weapon(self, weapon):
        """Sync the weapon's stats to match the current upgrade levels.

        Called at the start of each day so the weapon reflects any
        upgrades bought during the end-of-day screen.
        """
        from storm_the_house.core.settings import (
            PLAYER_GUN_DAMAGE, PLAYER_MAX_AMMO,
        )
        weapon.damage = PLAYER_GUN_DAMAGE + self.bonus_damage
        weapon.max_ammo = PLAYER_MAX_AMMO + self.bonus_ammo
        weapon.reload_time = self.reload_time
        # If ammo is currently higher than max (shouldn't happen, but guard)
        if weapon.ammo > weapon.max_ammo:
            weapon.ammo = weapon.max_ammo
        # Top off ammo at start of new day
        weapon.ammo = weapon.max_ammo

    def apply_to_house(self, house):
        """Sync the house's max HP and fortify level to match upgrades.

        Called at the start of each day.
        """
        house.max_hp = self.current_max_hp
        house.fortify_level = self.fortify_level
        if house.hp > house.max_hp:
            house.hp = house.max_hp

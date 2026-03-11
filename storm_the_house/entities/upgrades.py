"""
Upgrade state – tracks the level and escalating price of each upgrade.

Pistol upgrades (infinitely stackable):
  - **Damage**  : +1 damage per level
  - **Ammo**    : +1 max ammo per level
  - **Reload**  : 15 % faster reload per level (multiplicative)

Shotgun upgrades (infinitely stackable):
  - **Longer Barrel** : +1 ammo capacity per level
  - **Buckshot**      : +2 pellets per shot per level
  - **Faster Handling**: 20% faster reload and pump per level

Weapon purchases:
  - **Shotgun** : $500 to unlock
  - **Assault Rifle** : $1000 to unlock (placeholder)

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
    PLAYER_RELOAD_TIME, PISTOL_RELOAD_TIME,
    REPAIR_BASE_COST, REPAIR_PRICE_MULTIPLIER,
    FORTIFY_MAX_LEVEL, FORTIFY_COSTS, FORTIFY_HP_LEVELS,
    HOUSE_MAX_HP,
    REPAIRMAN_COST, GUNMAN_COST,
    GUNMAN_BASE_INTERVAL, GUNMAN_SPEED_FACTOR,
    SHOTGUN_COST, ASSAULT_RIFLE_COST,
    SHOTGUN_UPGRADE_AMMO_BONUS, SHOTGUN_UPGRADE_PELLET_BONUS, SHOTGUN_UPGRADE_SPEED_BONUS,
    SHOTGUN_MAX_AMMO, SHOTGUN_PELLET_COUNT, SHOTGUN_SHELL_RELOAD_TIME,
)


class WeaponUpgradeState:
    """Upgrade state for a single weapon (pistol-style upgrades)."""

    def __init__(self):
        self.damage_level: int = 0
        self.ammo_level: int = 0
        self.reload_level: int = 0

    @staticmethod
    def _price_for_level(level: int) -> int:
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
    def bonus_damage(self) -> int:
        return self.damage_level * UPGRADE_DAMAGE_AMOUNT

    @property
    def bonus_ammo(self) -> int:
        return self.ammo_level * UPGRADE_AMMO_AMOUNT

    def reload_time(self, base_time: float) -> float:
        return base_time * (UPGRADE_RELOAD_FACTOR ** self.reload_level)

    def can_buy_damage(self, money: int) -> bool:
        return money >= self.damage_price

    def can_buy_ammo(self, money: int) -> bool:
        return money >= self.ammo_price

    def can_buy_reload(self, money: int) -> bool:
        return money >= self.reload_price

    def buy_damage(self, money: int) -> int:
        cost = self.damage_price
        if money < cost:
            return money
        self.damage_level += 1
        return money - cost

    def buy_ammo(self, money: int) -> int:
        cost = self.ammo_price
        if money < cost:
            return money
        self.ammo_level += 1
        return money - cost

    def buy_reload(self, money: int) -> int:
        cost = self.reload_price
        if money < cost:
            return money
        self.reload_level += 1
        return money - cost


class ShotgunUpgradeState:
    """Upgrade state for shotgun with unique upgrades."""

    def __init__(self):
        # Longer Barrel: +1 ammo capacity
        self.ammo_level: int = 0
        # Buckshot: +2 pellets per shot
        self.pellet_level: int = 0
        # Faster Handling: 20% faster reload and pump
        self.speed_level: int = 0

    @staticmethod
    def _price_for_level(level: int) -> int:
        return int(UPGRADE_BASE_COST * (UPGRADE_PRICE_MULTIPLIER ** level))

    @property
    def ammo_price(self) -> int:
        """Price for Longer Barrel upgrade."""
        return self._price_for_level(self.ammo_level)

    @property
    def pellet_price(self) -> int:
        """Price for Buckshot upgrade."""
        return self._price_for_level(self.pellet_level)

    @property
    def speed_price(self) -> int:
        """Price for Faster Handling upgrade."""
        return self._price_for_level(self.speed_level)

    @property
    def bonus_ammo(self) -> int:
        return self.ammo_level * SHOTGUN_UPGRADE_AMMO_BONUS

    @property
    def bonus_pellets(self) -> int:
        return self.pellet_level * SHOTGUN_UPGRADE_PELLET_BONUS

    @property
    def speed_multiplier(self) -> float:
        """Returns the multiplier for reload/pump speed (lower = faster)."""
        return (1 - SHOTGUN_UPGRADE_SPEED_BONUS) ** self.speed_level

    def can_buy_ammo(self, money: int) -> bool:
        return money >= self.ammo_price

    def can_buy_pellet(self, money: int) -> bool:
        return money >= self.pellet_price

    def can_buy_speed(self, money: int) -> bool:
        return money >= self.speed_price

    def buy_ammo(self, money: int) -> int:
        """Buy Longer Barrel upgrade."""
        cost = self.ammo_price
        if money < cost:
            return money
        self.ammo_level += 1
        return money - cost

    def buy_pellet(self, money: int) -> int:
        """Buy Buckshot upgrade."""
        cost = self.pellet_price
        if money < cost:
            return money
        self.pellet_level += 1
        return money - cost

    def buy_speed(self, money: int) -> int:
        """Buy Faster Handling upgrade."""
        cost = self.speed_price
        if money < cost:
            return money
        self.speed_level += 1
        return money - cost


class UpgradeState:
    """Persistent upgrade tracker that lives across days."""

    def __init__(self):
        # Weapon ownership
        self.owns_shotgun: bool = False
        self.owns_assault_rifle: bool = False

        # Per-weapon upgrade states
        self.pistol_upgrades = WeaponUpgradeState()
        self.shotgun_upgrades = ShotgunUpgradeState()  # Special shotgun upgrades
        self.assault_rifle_upgrades = WeaponUpgradeState()

        # Currently selected weapon for upgrades display
        self.selected_weapon: str = "pistol"

        # House upgrades
        self.repair_count: int = 0       # how many times Repair has been bought
        self.fortify_level: int = 0      # 0, 1, or 2

        # Hired help
        self.repairman_count: int = 0
        self.gunman_count: int = 0

    def get_weapon_upgrades(self, weapon_type: str):
        """Get the upgrade state for a weapon type."""
        if weapon_type == "shotgun":
            return self.shotgun_upgrades
        elif weapon_type == "assault_rifle":
            return self.assault_rifle_upgrades
        return self.pistol_upgrades

    # ── weapon prices ────────────────────────────────────────────────────

    @property
    def shotgun_price(self) -> int:
        return SHOTGUN_COST

    @property
    def assault_rifle_price(self) -> int:
        return ASSAULT_RIFLE_COST

    def can_buy_shotgun(self, money: int) -> bool:
        return not self.owns_shotgun and money >= SHOTGUN_COST

    def can_buy_assault_rifle(self, money: int) -> bool:
        return not self.owns_assault_rifle and money >= ASSAULT_RIFLE_COST

    def buy_shotgun(self, money: int) -> int:
        if self.owns_shotgun or money < SHOTGUN_COST:
            return money
        self.owns_shotgun = True
        return money - SHOTGUN_COST

    def buy_assault_rifle(self, money: int) -> int:
        if self.owns_assault_rifle or money < ASSAULT_RIFLE_COST:
            return money
        self.owns_assault_rifle = True
        return money - ASSAULT_RIFLE_COST

    # ── price helpers (for selected weapon) ────────────────────────────────

    @staticmethod
    def _price_for_level(level: int) -> int:
        """Return the cost to buy the *next* level (i.e. going from
        *level* → *level + 1*)."""
        return int(UPGRADE_BASE_COST * (UPGRADE_PRICE_MULTIPLIER ** level))

    @property
    def damage_price(self) -> int:
        return self.get_weapon_upgrades(self.selected_weapon).damage_price

    @property
    def ammo_price(self) -> int:
        return self.get_weapon_upgrades(self.selected_weapon).ammo_price

    @property
    def reload_price(self) -> int:
        return self.get_weapon_upgrades(self.selected_weapon).reload_price

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
        """Total extra damage from upgrades for selected weapon."""
        return self.get_weapon_upgrades(self.selected_weapon).bonus_damage

    @property
    def bonus_ammo(self) -> int:
        """Total extra max-ammo from upgrades for selected weapon."""
        return self.get_weapon_upgrades(self.selected_weapon).bonus_ammo

    @property
    def reload_time(self) -> float:
        """Current reload time after all reload upgrades for selected weapon."""
        base = PISTOL_RELOAD_TIME
        return self.get_weapon_upgrades(self.selected_weapon).reload_time(base)

    @property
    def current_max_hp(self) -> int:
        """House max HP considering fortification level."""
        if self.fortify_level == 0:
            return HOUSE_MAX_HP
        return FORTIFY_HP_LEVELS[self.fortify_level - 1]

    # ── purchase actions ─────────────────────────────────────────────────

    def can_buy_damage(self, money: int) -> bool:
        return self.get_weapon_upgrades(self.selected_weapon).can_buy_damage(money)

    def can_buy_ammo(self, money: int) -> bool:
        return self.get_weapon_upgrades(self.selected_weapon).can_buy_ammo(money)

    def can_buy_reload(self, money: int) -> bool:
        return self.get_weapon_upgrades(self.selected_weapon).can_buy_reload(money)

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
        return self.get_weapon_upgrades(self.selected_weapon).buy_damage(money)

    def buy_ammo(self, money: int) -> int:
        """Purchase an ammo upgrade.  Returns the remaining money."""
        return self.get_weapon_upgrades(self.selected_weapon).buy_ammo(money)

    def buy_reload(self, money: int) -> int:
        """Purchase a reload upgrade.  Returns the remaining money."""
        return self.get_weapon_upgrades(self.selected_weapon).buy_reload(money)

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

    def apply_to_pistol(self, pistol):
        """Apply pistol-specific upgrades."""
        from storm_the_house.core.settings import PISTOL_DAMAGE, PISTOL_MAX_AMMO, PISTOL_RELOAD_TIME
        upgrades = self.pistol_upgrades
        pistol.damage = PISTOL_DAMAGE + upgrades.bonus_damage
        pistol.max_ammo = PISTOL_MAX_AMMO + upgrades.bonus_ammo
        pistol.reload_time = upgrades.reload_time(PISTOL_RELOAD_TIME)
        pistol.ammo = pistol.max_ammo

    def apply_to_shotgun(self, shotgun):
        """Apply shotgun-specific upgrades."""
        upgrades = self.shotgun_upgrades
        shotgun.apply_upgrades(
            ammo_level=upgrades.ammo_level,
            pellet_level=upgrades.pellet_level,
            speed_level=upgrades.speed_level,
        )

    def apply_to_house(self, house):
        """Sync the house's max HP and fortify level to match upgrades.

        Called at the start of each day.
        """
        house.max_hp = self.current_max_hp
        house.fortify_level = self.fortify_level
        if house.hp > house.max_hp:
            house.hp = house.max_hp

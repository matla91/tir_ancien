import random
from dataclasses import dataclass
from typing import Dict, Optional

import pygame

from src.settings import BLACK, BRASS, DATA_DIR, HEIGHT, SKIN, STEEL, WIDTH
from src.utils import clamp, safe_load_json


@dataclass
class WeaponStats:
    weapon_id: str
    name: str
    description: str
    price: int
    precision: float
    stability: float
    reload_time: float
    fouling_rate: float
    shot_delay_min: float
    shot_delay_max: float
    effective_range: int
    sprite: str
    sprite_scale: float


class Weapon:
    def __init__(self, stats: WeaponStats, sprite: Optional[pygame.Surface] = None) -> None:
        self.stats = stats
        self.sprite = sprite

        self.loaded = True
        self.reloading = False
        self.reload_progress = 0.0

        self.cleaning = False
        self.clean_progress = 0.0

        self.fouling = 0.0
        self.recoil = pygame.Vector2(0, 0)

        self.shot_effect_time = 0.0

    @staticmethod
    def from_dict(data: Dict, sprite: Optional[pygame.Surface] = None) -> "Weapon":
        stats = WeaponStats(
            weapon_id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            price=int(data["price"]),
            precision=float(data["precision"]),
            stability=float(data["stability"]),
            reload_time=float(data["reload_time"]),
            fouling_rate=float(data["fouling_rate"]),
            shot_delay_min=float(data["shot_delay_min"]),
            shot_delay_max=float(data["shot_delay_max"]),
            effective_range=int(data["effective_range"]),
            sprite=data["sprite"],
            sprite_scale=float(data.get("sprite_scale", 1.0)),
        )
        return Weapon(stats, sprite)

    @staticmethod
    def load_catalog(asset_manager) -> Dict[str, "Weapon"]:
        weapons_data = safe_load_json(DATA_DIR / "weapons.json")
        catalog = {}

        for weapon_data in weapons_data["weapons"]:
            sprite = asset_manager.image(weapon_data["sprite"])
            weapon = Weapon.from_dict(weapon_data, sprite)
            catalog[weapon.stats.weapon_id] = weapon

        return catalog

    @staticmethod
    def load_starting_weapon(asset_manager) -> "Weapon":
        catalog = Weapon.load_catalog(asset_manager)
        return next(iter(catalog.values()))

    def reset_runtime_state(self, clean_barrel: bool = True) -> None:
        self.loaded = True
        self.reloading = False
        self.reload_progress = 0.0
        self.cleaning = False
        self.clean_progress = 0.0
        self.recoil = pygame.Vector2(0, 0)
        self.shot_effect_time = 0.0

        if clean_barrel:
            self.fouling = 0.0

    def start_reload(self) -> bool:
        if self.loaded or self.reloading or self.cleaning:
            return False
        self.reloading = True
        self.reload_progress = 0.0
        return True

    def start_cleaning(self) -> bool:
        if self.reloading or self.cleaning:
            return False
        self.cleaning = True
        self.clean_progress = 0.0
        return True

    def random_shot_delay(self) -> float:
        return random.uniform(self.stats.shot_delay_min, self.stats.shot_delay_max)

    def update(self, dt: float) -> None:
        if self.reloading:
            duration = self.stats.reload_time + self.fouling * 0.08
            self.reload_progress += dt / max(duration, 0.01)
            if self.reload_progress >= 1.0:
                self.reload_progress = 1.0
                self.reloading = False
                self.loaded = True

        if self.cleaning:
            clean_duration = 2.2
            self.clean_progress += dt / clean_duration
            if self.clean_progress >= 1.0:
                self.clean_progress = 1.0
                self.cleaning = False
                self.fouling = clamp(self.fouling - 5.5, 0, 10)

        if self.shot_effect_time > 0:
            self.shot_effect_time = max(0, self.shot_effect_time - dt)

        self.recoil *= max(0, 1 - 7.0 * dt)

    def apply_shot_feedback(self) -> None:
        self.loaded = False
        self.fouling = clamp(self.fouling + random.uniform(0.7, 1.2) * self.stats.fouling_rate, 0, 10)
        self.recoil = pygame.Vector2(random.uniform(-8, 8), random.uniform(-32, -18))
        self.shot_effect_time = 0.16

    def dispersion_px(self, distance_m: int, fatigue: float, trigger_penalty: float) -> float:
        distance_factor = distance_m / 25
        precision_factor = clamp(1.25 - self.stats.precision / 100.0, 0.25, 1.25)

        base = 2.6 + 1.30 * (distance_factor ** 0.55)
        fouling_penalty = self.fouling * 0.62
        fatigue_penalty = fatigue * 0.036
        trigger_dispersion = trigger_penalty * (7.0 + distance_factor * 1.5)

        return (base + fouling_penalty + fatigue_penalty + trigger_dispersion) * precision_factor

    def anchor_screen_pos(self) -> pygame.Vector2:
        return pygame.Vector2(WIDTH * 0.91, HEIGHT * 0.82)

    def muzzle_screen_pos(self, aim_point: pygame.Vector2) -> pygame.Vector2:
        anchor = self.anchor_screen_pos()
        direction = aim_point - anchor
        if direction.length_squared() == 0:
            direction = pygame.Vector2(-1, -0.12)
        direction = direction.normalize()
        return anchor + direction * 305

    def draw(self, surface: pygame.Surface, aim_point: pygame.Vector2) -> None:
        if self.sprite:
            self._draw_sprite_weapon(surface, aim_point)
        else:
            self._draw_fallback_weapon(surface, aim_point)

    def _draw_sprite_weapon(self, surface: pygame.Surface, aim_point: pygame.Vector2) -> None:
        anchor = self.anchor_screen_pos() + self.recoil
        direction = aim_point - anchor
        if direction.length_squared() == 0:
            direction = pygame.Vector2(-1, -0.2)
        direction = direction.normalize()

        target_angle = pygame.Vector2(direction.x, -direction.y).angle_to(pygame.Vector2(-1, 0))
        angle = clamp(-target_angle, -22, 28)

        image = pygame.transform.rotozoom(self.sprite, angle, self.stats.sprite_scale)
        rect = image.get_rect()
        rect.bottomright = (WIDTH + 115 + int(self.recoil.x), HEIGHT + 25 + int(self.recoil.y))
        surface.blit(image, rect)

        if self.shot_effect_time > 0:
            muzzle = self.muzzle_screen_pos(aim_point)
            self._draw_muzzle_flash(surface, muzzle, direction)

    def _draw_muzzle_flash(self, surface: pygame.Surface, muzzle: pygame.Vector2, direction: pygame.Vector2) -> None:
        normal = pygame.Vector2(-direction.y, direction.x)
        k = self.shot_effect_time / 0.16
        flame_len = 54 * k
        flame_w = 22 * k

        points = [
            muzzle + direction * flame_len,
            muzzle - direction * 4 + normal * flame_w,
            muzzle - direction * 8,
            muzzle - direction * 4 - normal * flame_w,
        ]
        pygame.draw.polygon(surface, (245, 207, 83), points)
        pygame.draw.polygon(
            surface,
            (215, 91, 45),
            [points[0], muzzle + normal * flame_w * 0.45, muzzle - normal * flame_w * 0.45],
        )

    def _draw_fallback_weapon(self, surface: pygame.Surface, aim_point: pygame.Vector2) -> None:
        anchor = self.anchor_screen_pos() + self.recoil
        direction = aim_point - anchor
        if direction.length_squared() == 0:
            direction = pygame.Vector2(-1, -0.2)
        direction = direction.normalize()
        normal = pygame.Vector2(-direction.y, direction.x)

        muzzle = anchor + direction * 300
        barrel_start = anchor + direction * 35 - normal * 8

        pygame.draw.line(surface, STEEL, barrel_start, muzzle, 16)
        pygame.draw.line(surface, (160, 160, 150), barrel_start + normal * 2, muzzle + normal * 2, 3)
        pygame.draw.circle(surface, BLACK, muzzle, 8)

        stock_points = [
            anchor - direction * 10 + normal * 22,
            anchor + direction * 220 + normal * 19,
            anchor + direction * 255 + normal * 8,
            anchor + direction * 60 - normal * 27,
            anchor - direction * 35 - normal * 40,
            anchor - direction * 70 - normal * 12,
        ]
        pygame.draw.polygon(surface, (94, 55, 30), stock_points)
        pygame.draw.polygon(surface, (45, 27, 18), stock_points, 2)

        grip_points = [
            anchor - direction * 40 - normal * 8,
            anchor - direction * 95 - normal * 88,
            anchor - direction * 60 - normal * 108,
            anchor - direction * 10 - normal * 42,
        ]
        pygame.draw.polygon(surface, (104, 61, 34), grip_points)
        pygame.draw.polygon(surface, (45, 27, 18), grip_points, 2)

        lock_center = anchor + direction * 75 - normal * 20
        pygame.draw.ellipse(surface, BRASS, (lock_center.x - 34, lock_center.y - 14, 68, 28))
        pygame.draw.ellipse(surface, BLACK, (lock_center.x - 34, lock_center.y - 14, 68, 28), 1)

        cock_base = anchor + direction * 45 - normal * 30
        cock_tip = cock_base - direction * 18 - normal * 42
        pygame.draw.line(surface, (50, 50, 48), cock_base, cock_tip, 7)
        pygame.draw.circle(surface, (50, 50, 48), cock_tip, 9)

        trigger = anchor + direction * 28 - normal * 35
        pygame.draw.arc(surface, BLACK, (trigger.x - 20, trigger.y - 12, 40, 42), 0.1, 4.8, 3)

        hand = anchor - direction * 34 - normal * 36
        pygame.draw.circle(surface, SKIN, hand, 25)
        pygame.draw.circle(surface, (112, 76, 55), hand, 25, 2)

        if self.shot_effect_time > 0:
            self._draw_muzzle_flash(surface, muzzle, direction)

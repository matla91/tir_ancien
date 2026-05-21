import math
import random
import sys
from typing import List

import pygame

from src.assets import AssetManager
from src.effects import FloatingTextSystem, ImpactFeedbackSystem, SmokeSystem
from src.settings import (
    BLACK,
    FOREST,
    FOREST_DARK,
    FPS,
    GREEN,
    HEIGHT,
    RED,
    SAND,
    SAND_DARK,
    SHOTS_PER_STAGE,
    STAGES_METERS,
    WHITE,
    WIDTH,
    YELLOW,
)
from src.target import Shot, TARGET_CATALOG, Target
from src.ui import UI
from src.utils import clamp, lerp
from src.weapons import Weapon


class Game:
    def __init__(self) -> None:
        try:
            pygame.mixer.pre_init(44100, -16, 1, 512)
        except Exception:
            pass

        pygame.init()
        pygame.display.set_caption("Flintlock Range MVP")

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.world_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.clock = pygame.time.Clock()

        self.assets = AssetManager()
        self.background_image = self.load_background_image()
        self.ui = UI()
        self.target = Target()
        self.smoke = SmokeSystem()
        self.floating_text = FloatingTextSystem()
        self.impact_feedback = ImpactFeedbackSystem()

        self.weapon_catalog = Weapon.load_catalog(self.assets)
        self.shop_weapon_ids = list(self.weapon_catalog.keys())
        self.owned_weapon_ids = {self.shop_weapon_ids[0]}
        self.current_weapon_id = self.shop_weapon_ids[0]
        self.weapon = self.weapon_catalog[self.current_weapon_id]

        self.shop_target_ids = list(TARGET_CATALOG.keys())
        self.owned_target_ids = {"sport_precision"}
        self.current_target_id = "sport_precision"
        self.target.set_type(self.current_target_id)
        self.shop_selected_index = 0

        self.shot_sound = self.assets.build_flintlock_shot_sound()
        self.target_hit_sound = self.assets.build_target_hit_sound()

        self.money = 0
        self.last_reward = 0
        self.stages = STAGES_METERS[:]
        self.shots_per_stage = SHOTS_PER_STAGE
        self.state = "menu"
        self.stage_index = 0

        self.all_shots: List[Shot] = []
        self.stage_shots: List[Shot] = []
        self.pending_impacts = []

        self.mouse_pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.prev_mouse_pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.mouse_speed = 0.0
        self.prev_left_down = False

        self.breath = 100.0
        self.breath_hold_time = 0.0
        self.fatigue = 0.0

        self.wind = random.uniform(-0.8, 0.8)
        self.wind_target = self.wind
        self.time = 0.0

        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0
        self.pending_trigger_speed = 0.0

        self.last_stability_score = 0.0
        self.last_breath_quality = 0.0
        self.last_motion_quality = 0.0
        self.last_trigger_quality = 0.0
        self.last_aim_rating = "Instable"

        self.shake_time = 0.0
        self.shake_duration = 0.0
        self.shake_strength = 0.0
        self.camera_offset = pygame.Vector2(0, 0)

        self.message = "Entrée : commencer"
        self.message_time = 0.0

    def load_background_image(self) -> pygame.Surface | None:
        candidates = [
            "images/backgrounds/background_1.png",
            "images/backgrounds/background_1.jpg",
            "images/backgrounds/background_1.jpeg",
            "images/backgrounds/background_1.webp",
            "images/background_1.png",
            "images/background_1.jpg",
            "images/background_1.jpeg",
            "images/background_1.webp",
            "background_1.png",
            "background_1.jpg",
            "background_1.jpeg",
            "background_1.webp",
        ]

        for path in candidates:
            image = self.assets.image(path, alpha=False)
            if image is not None:
                return image
        return None

    @property
    def distance(self) -> int:
        return self.stages[self.stage_index]

    def shop_item_count(self) -> int:
        return len(self.shop_weapon_ids) + len(self.shop_target_ids)

    def reset(self) -> None:
        self.target.clear_stage()
        self.smoke = SmokeSystem()
        self.floating_text = FloatingTextSystem()
        self.impact_feedback = ImpactFeedbackSystem()
        self.pending_impacts.clear()

        self.stage_index = 0
        self.all_shots.clear()
        self.stage_shots.clear()

        self.breath = 100.0
        self.breath_hold_time = 0.0
        self.fatigue = 0.0
        self.last_stability_score = 0.0
        self.last_breath_quality = 0.0
        self.last_motion_quality = 0.0
        self.last_trigger_quality = 0.0
        self.last_aim_rating = "Instable"

        self.wind = random.uniform(-0.8, 0.8)
        self.wind_target = self.wind

        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0
        self.pending_trigger_speed = 0.0

        self.shake_time = 0.0
        self.shake_duration = 0.0
        self.shake_strength = 0.0
        self.camera_offset.update(0, 0)

        for weapon in self.weapon_catalog.values():
            weapon.reset_runtime_state(clean_barrel=True)

        self.weapon = self.weapon_catalog[self.current_weapon_id]
        self.target.set_type(self.current_target_id)
        self.show_message("Nouveau parcours : 25 m.", 1.5)

    def show_message(self, text: str, duration: float = 1.4) -> None:
        self.message = text
        self.message_time = duration

    def run(self) -> None:
        while True:
            pygame.mouse.set_visible(self.state == "shop")
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

    def quit(self) -> None:
        pygame.quit()
        sys.exit()

    def handle_primary_fire_input(self) -> None:
        if self.state == "menu":
            self.state = "playing"
            pygame.mouse.set_visible(False)
            self.show_message("25 m : série de 5 coups.", 1.5)
        elif self.state == "playing":
            self.try_fire()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "shop":
                    self.handle_shop_click(event.pos)
                else:
                    self.handle_primary_fire_input()

            if event.type == pygame.MOUSEMOTION and self.state == "shop":
                hovered = self.shop_index_from_pos(event.pos)
                if hovered is not None:
                    self.shop_selected_index = hovered

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()

                if self.state == "menu" and event.key == pygame.K_RETURN:
                    self.state = "playing"
                    pygame.mouse.set_visible(False)
                    self.show_message("25 m : série de 5 coups.", 1.5)

                elif self.state == "stage_done" and event.key == pygame.K_RETURN:
                    self.next_stage()

                elif self.state == "game_over" and event.key == pygame.K_RETURN:
                    self.reset()
                    self.state = "playing"
                    pygame.mouse.set_visible(False)

                elif self.state == "shop":
                    if event.key in (pygame.K_b, pygame.K_ESCAPE):
                        self.state = "playing"
                        pygame.mouse.set_visible(False)
                        self.show_message("Retour au pas de tir.", 1.0)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.shop_selected_index = (self.shop_selected_index + 1) % self.shop_item_count()
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.shop_selected_index = (self.shop_selected_index - 1) % self.shop_item_count()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.handle_shop_selection(self.shop_selected_index)
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        self.handle_shop_selection(event.key - pygame.K_1)

                elif self.state == "playing":
                    if event.key in (pygame.K_f, pygame.K_LCTRL, pygame.K_RCTRL):
                        self.handle_primary_fire_input()
                    elif event.key == pygame.K_b:
                        self.state = "shop"
                        pygame.mouse.set_visible(True)
                        self.show_message("Boutique ouverte.", 1.0)
                    elif event.key == pygame.K_r:
                        if self.weapon.start_reload():
                            self.show_message("Rechargement...", 0.8)
                        elif self.weapon.loaded:
                            self.show_message("Déjà chargé.", 0.8)
                    elif event.key == pygame.K_c:
                        if self.weapon.start_cleaning():
                            self.show_message("Nettoyage du canon...", 0.8)

    def shop_index_from_pos(self, pos: tuple[int, int]) -> int | None:
        x, y = pos
        start_x = 245
        card_w = 760
        if not (start_x <= x <= start_x + card_w):
            return None

        current_y = 195
        card_h = 62
        for index in range(len(self.shop_weapon_ids)):
            if current_y <= y <= current_y + card_h:
                return index
            current_y += card_h + 8

        current_y += 36
        target_card_h = 58
        base = len(self.shop_weapon_ids)
        for index in range(len(self.shop_target_ids)):
            if current_y <= y <= current_y + target_card_h:
                return base + index
            current_y += target_card_h + 8

        return None

    def handle_shop_click(self, pos: tuple[int, int]) -> None:
        index = self.shop_index_from_pos(pos)
        if index is not None:
            self.shop_selected_index = index
            self.handle_shop_selection(index)

    def update(self, dt: float) -> None:
        self.time += dt
        self.update_mouse()
        self.update_click_polling()

        if self.state == "playing":
            self.update_breathing(dt)
            self.update_wind(dt)
            self.update_aim_feedback()

        if self.state != "shop":
            self.weapon.update(dt)
            self.update_pending_shot(dt)
            self.update_pending_impacts(dt)

        self.smoke.update(dt)
        self.floating_text.update(dt)
        self.impact_feedback.update(dt)
        self.update_camera_shake(dt)

        if self.message_time > 0:
            self.message_time -= dt

    def update_mouse(self) -> None:
        self.prev_mouse_pos.update(self.mouse_pos)
        mx, my = pygame.mouse.get_pos()
        self.mouse_pos.update(mx, my)
        self.mouse_speed = self.mouse_pos.distance_to(self.prev_mouse_pos) * FPS

    def update_click_polling(self) -> None:
        left_down = pygame.mouse.get_pressed(num_buttons=3)[0]
        if self.state != "shop" and left_down and not self.prev_left_down:
            self.handle_primary_fire_input()
        self.prev_left_down = left_down

    def update_breathing(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        breath_control = keys[pygame.K_SPACE] and not self.weapon.reloading and not self.weapon.cleaning

        if breath_control and self.breath > 0:
            self.breath_hold_time += dt
            self.breath = clamp(self.breath - 24 * dt, 0, 100)
            self.fatigue = clamp(self.fatigue + 2.8 * dt, 0, 100)
        else:
            self.breath_hold_time = 0.0
            recovery = 16 if not self.weapon.reloading and not self.weapon.cleaning else 7
            self.breath = clamp(self.breath + recovery * dt, 0, 100)
            self.fatigue = clamp(self.fatigue - 4.5 * dt, 0, 100)

    def update_wind(self, dt: float) -> None:
        if random.random() < 0.008:
            self.wind_target = random.uniform(-1.1, 1.1)
        self.wind = lerp(self.wind, self.wind_target, 0.35 * dt)

    def breath_quality(self) -> float:
        keys = pygame.key.get_pressed()
        holding = keys[pygame.K_SPACE] and self.breath > 0 and self.state == "playing"
        if not holding:
            return 0.35

        if self.breath_hold_time < 0.35:
            hold_quality = self.breath_hold_time / 0.35
        elif self.breath_hold_time <= 2.10:
            hold_quality = 1.0
        else:
            hold_quality = clamp(1.0 - (self.breath_hold_time - 2.10) / 1.55, 0.0, 1.0)

        breath_amount_quality = clamp((self.breath - 8.0) / 35.0, 0.0, 1.0)
        return clamp(hold_quality * breath_amount_quality, 0.0, 1.0)

    def motion_quality(self) -> float:
        return clamp(1.0 - self.mouse_speed / 980.0, 0.0, 1.0)

    def stability_score(self) -> float:
        sway = self.current_sway().length()
        sway_quality = clamp(1.0 - sway / 42.0, 0.0, 1.0)
        breath = self.breath_quality()
        motion = self.motion_quality()
        fouling_quality = clamp(1.0 - self.weapon.fouling / 14.0, 0.0, 1.0)
        fatigue_quality = clamp(1.0 - self.fatigue / 120.0, 0.0, 1.0)
        return clamp(
            0.42 * sway_quality
            + 0.24 * breath
            + 0.20 * motion
            + 0.08 * fouling_quality
            + 0.06 * fatigue_quality,
            0.0,
            1.0,
        )

    def update_aim_feedback(self) -> None:
        self.last_breath_quality = self.breath_quality()
        self.last_motion_quality = self.motion_quality()
        self.last_stability_score = self.stability_score()

        if self.last_stability_score >= 0.78:
            self.last_aim_rating = "Stable"
        elif self.last_stability_score >= 0.52:
            self.last_aim_rating = "Correct"
        else:
            self.last_aim_rating = "Instable"

    def start_camera_shake(self, strength: float = 9.0, duration: float = 0.20) -> None:
        self.shake_strength = max(self.shake_strength, strength)
        self.shake_duration = duration
        self.shake_time = duration

    def update_camera_shake(self, dt: float) -> None:
        if self.shake_time <= 0:
            self.camera_offset.update(0, 0)
            return

        self.shake_time = max(0, self.shake_time - dt)
        t = self.shake_time / max(self.shake_duration, 0.001)
        strength = self.shake_strength * t * t
        self.camera_offset.update(random.uniform(-strength, strength), random.uniform(-strength, strength))

    def shot_speed_mps(self) -> float:
        if "percussion" in self.weapon.stats.weapon_id:
            return 205.0
        return 170.0

    def travel_time_seconds(self, distance_m: int) -> float:
        return distance_m / self.shot_speed_mps()

    def distance_depth_factor(self) -> float:
        return clamp((self.distance - 25) / 175, 0.0, 1.0)

    def try_fire(self) -> None:
        if self.pending_shot_delay > 0:
            return
        if self.weapon.reloading or self.weapon.cleaning:
            return
        if not self.weapon.loaded:
            self.show_message("Arme vide : R pour recharger.", 1.2)
            return

        self.update_aim_feedback()
        delay = self.weapon.random_shot_delay()
        self.pending_shot_delay = delay
        self.pending_shot_start_delay = delay
        self.pending_trigger_speed = self.mouse_speed
        self.last_trigger_quality = self.last_stability_score

        self.weapon.loaded = False
        self.show_message("Départ du coup...", 0.35)

    def update_pending_shot(self, dt: float) -> None:
        if self.pending_shot_delay <= 0:
            return

        self.pending_shot_delay -= dt
        if self.pending_shot_delay <= 0:
            self.finish_fire()

    def update_pending_impacts(self, dt: float) -> None:
        if not self.pending_impacts:
            return

        remaining = []
        for pending in self.pending_impacts:
            pending["time_left"] -= dt
            if pending["time_left"] <= 0:
                self.resolve_impact(pending)
            else:
                remaining.append(pending)
        self.pending_impacts = remaining

    def finish_fire(self) -> None:
        aim = self.current_aim_point()
        speed_penalty = clamp(self.pending_trigger_speed / 900.0, 0.0, 1.0)
        stability_penalty = 1.0 - clamp(self.last_trigger_quality, 0.0, 1.0)
        trigger_penalty = clamp(0.55 * speed_penalty + 0.45 * stability_penalty, 0.0, 1.0)

        dispersion = self.weapon.dispersion_px(self.distance, self.fatigue, trigger_penalty)
        dx = random.gauss(0, dispersion)
        dy = random.gauss(0, dispersion)
        wind_offset = self.wind * (self.distance / 100) * 12.0
        impact = pygame.Vector2(aim.x + dx + wind_offset, aim.y + dy)

        self.weapon.apply_shot_feedback()
        self.fatigue = clamp(self.fatigue + 3.5, 0, 100)

        muzzle = self.weapon.muzzle_screen_pos(aim)
        direction = aim - self.weapon.anchor_screen_pos()
        self.smoke.spawn(muzzle, direction, count=42)
        self.start_camera_shake(strength=9.0, duration=0.20)

        if self.shot_sound:
            try:
                self.shot_sound.play()
            except Exception:
                pass

        wait = self.travel_time_seconds(self.distance)
        self.pending_impacts.append(
            {
                "time_left": wait,
                "impact": impact,
                "distance": self.distance,
                "aim_rating": self.last_aim_rating,
            }
        )

        if self.distance >= 100:
            self.show_message(f"Coup parti... impact dans {wait:.1f}s", min(1.0, wait))

        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0
        self.pending_trigger_speed = 0.0

    def resolve_impact(self, pending: dict) -> None:
        shot = self.target.score_impact(pending["impact"], pending["distance"])
        self.all_shots.append(shot)
        self.stage_shots.append(shot)

        if self.target_hit_sound and shot.score > 0:
            try:
                self.target_hit_sound.play()
            except Exception:
                pass

        reward = self.cash_reward_for_shot(shot)
        self.money += reward
        self.last_reward = reward

        self.impact_feedback.spawn(pygame.Vector2(shot.x, shot.y), shot.score)

        if shot.score == 10:
            floating_color = (255, 226, 92)
            floating_text = f"PARFAIT 10  +${reward}"
            size = 32
        else:
            floating_color = YELLOW if reward > 0 else (220, 220, 220)
            floating_text = f"{shot.score} pts  +${reward}" if reward > 0 else f"{shot.score} pts"
            size = 28
        self.floating_text.spawn(floating_text, pygame.Vector2(shot.x + 18, shot.y - 28), floating_color, size=size)

        reward_text = f" +${reward}" if reward > 0 else ""
        aim_text = f" | {pending['aim_rating']}"
        if shot.score == 10:
            self.show_message(f"Plein centre : 10 points.{reward_text}{aim_text}", 1.6)
        elif shot.score >= 9:
            self.show_message(f"Très beau coup : {shot.score} points.{reward_text}{aim_text}", 1.4)
        elif shot.score >= 6:
            self.show_message(f"Impact correct : {shot.score} points.{reward_text}{aim_text}", 1.4)
        elif shot.score >= 1:
            self.show_message(f"Impact faible : {shot.score} point(s).{reward_text}{aim_text}", 1.4)
        else:
            self.show_message(f"Manqué. $0{aim_text}", 1.4)

        if len(self.stage_shots) >= self.shots_per_stage:
            if self.stage_index < len(self.stages) - 1:
                self.state = "stage_done"
                self.show_message("Série terminée. Entrée : distance suivante.", 999)
            else:
                self.state = "game_over"
                self.show_message("Parcours terminé. Entrée : recommencer.", 999)

    def cash_reward_for_shot(self, shot: Shot) -> int:
        if shot.score <= 0:
            return 0
        distance_multiplier = self.distance / 25
        target_multiplier = self.target.target_type.reward_multiplier
        reward = int(shot.score * distance_multiplier * target_multiplier * 3)
        if shot.score == 10:
            reward += int(5 * distance_multiplier * target_multiplier)
        return max(1, reward)

    def next_stage(self) -> None:
        self.stage_index += 1
        self.stage_shots.clear()
        self.target.clear_stage()
        self.floating_text = FloatingTextSystem()
        self.impact_feedback = ImpactFeedbackSystem()
        self.pending_impacts.clear()

        self.weapon.loaded = True
        self.weapon.reloading = False
        self.weapon.cleaning = False
        self.weapon.fouling = clamp(self.weapon.fouling * 0.25, 0, 10)

        self.breath = 100.0
        self.breath_hold_time = 0.0
        self.fatigue = clamp(self.fatigue * 0.35, 0, 100)

        self.wind = random.uniform(-0.9, 0.9)
        self.wind_target = self.wind
        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0

        self.show_message(f"Nouvelle distance : {self.distance} m.", 1.6)
        self.state = "playing"

    def handle_shop_selection(self, index: int) -> None:
        if index < len(self.shop_weapon_ids):
            self.handle_weapon_shop_selection(index)
            return

        target_index = index - len(self.shop_weapon_ids)
        self.handle_target_shop_selection(target_index)

    def handle_weapon_shop_selection(self, index: int) -> None:
        if index < 0 or index >= len(self.shop_weapon_ids):
            return

        weapon_id = self.shop_weapon_ids[index]
        weapon = self.weapon_catalog[weapon_id]

        if weapon_id in self.owned_weapon_ids:
            self.equip_weapon(weapon_id)
            return

        if self.money < weapon.stats.price:
            missing = weapon.stats.price - self.money
            self.show_message(f"Pas assez d'argent. Il manque ${missing}.", 1.6)
            return

        self.money -= weapon.stats.price
        self.owned_weapon_ids.add(weapon_id)
        self.equip_weapon(weapon_id)
        self.show_message(f"Acheté et équipé : {weapon.stats.name}.", 1.6)

    def handle_target_shop_selection(self, index: int) -> None:
        if index < 0 or index >= len(self.shop_target_ids):
            return

        target_id = self.shop_target_ids[index]
        target_type = TARGET_CATALOG[target_id]

        if target_id in self.owned_target_ids:
            self.equip_target(target_id)
            return

        if self.money < target_type.price:
            missing = target_type.price - self.money
            self.show_message(f"Pas assez d'argent. Il manque ${missing}.", 1.6)
            return

        self.money -= target_type.price
        self.owned_target_ids.add(target_id)
        self.equip_target(target_id)
        self.show_message(f"Cible achetée : {target_type.name}.", 1.6)

    def equip_target(self, target_id: str) -> None:
        if target_id not in TARGET_CATALOG:
            return
        self.current_target_id = target_id
        self.target.set_type(target_id)
        self.show_message(f"Cible équipée : {self.target.target_type.name}.", 1.2)

    def equip_weapon(self, weapon_id: str) -> None:
        if weapon_id not in self.weapon_catalog:
            return
        self.current_weapon_id = weapon_id
        self.weapon = self.weapon_catalog[weapon_id]
        self.weapon.reset_runtime_state(clean_barrel=False)
        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0
        self.pending_trigger_speed = 0.0
        self.breath_hold_time = 0.0
        self.show_message(f"Équipé : {self.weapon.stats.name}.", 1.2)

    def current_sway(self) -> pygame.Vector2:
        keys = pygame.key.get_pressed()
        holding_breath = keys[pygame.K_SPACE] and self.breath > 0 and self.state == "playing"
        distance_factor = (self.distance / 25) ** 0.5
        stability_factor = clamp(1.25 - self.weapon.stats.stability / 100.0, 0.35, 1.25)

        amp = 10.0 + distance_factor * 6.0 + self.fatigue * 0.08 + self.weapon.fouling * 0.6
        amp *= stability_factor

        if holding_breath:
            amp *= 0.34
            if self.breath_hold_time < 0.35:
                amp *= 1.0 - 0.35 * (self.breath_hold_time / 0.35)
            elif self.breath_hold_time > 2.10:
                amp *= 1.0 + clamp((self.breath_hold_time - 2.10) / 1.15, 0.0, 1.25)

        if self.breath <= 3 and keys[pygame.K_SPACE]:
            amp *= 1.85

        micro = 1.0
        if holding_breath and self.breath_hold_time > 2.10:
            micro += clamp((self.breath_hold_time - 2.10) / 1.2, 0.0, 1.0)

        sx = (
            math.sin(self.time * 1.18) * 0.84
            + math.sin(self.time * 2.55 + 1.4) * 0.30
            + math.sin(self.time * 6.90 + 0.3) * 0.08 * micro
        )
        sy = (
            math.cos(self.time * 1.05 + 0.7) * 0.76
            + math.sin(self.time * 2.22 + 2.1) * 0.30
            + math.cos(self.time * 6.30) * 0.09 * micro
        )
        return pygame.Vector2(sx * amp, sy * amp)

    def current_aim_point(self) -> pygame.Vector2:
        return self.mouse_pos + self.current_sway() + self.weapon.recoil

    def draw(self) -> None:
        self.world_surface.fill((0, 0, 0, 0))
        self.draw_background(self.world_surface)
        self.target.draw(self.world_surface, self.distance)
        self.impact_feedback.draw(self.world_surface)
        self.smoke.draw(self.world_surface)

        if self.state != "menu":
            self.weapon.draw(self.world_surface, self.current_aim_point())

        self.draw_crosshair(self.world_surface)
        self.floating_text.draw(self.world_surface)

        self.screen.fill((0, 0, 0))
        self.screen.blit(self.world_surface, self.camera_offset)

        if self.state == "menu":
            self.ui.draw_menu(self.screen)
        else:
            self.ui.draw_hud(self.screen, self)

        if self.state == "shop":
            self.ui.draw_shop(self.screen, self)
        elif self.state == "stage_done":
            self.ui.draw_stage_done(self.screen, self)
        elif self.state == "game_over":
            self.ui.draw_game_over(self.screen, self)

        pygame.display.flip()

    def draw_background(self, surface: pygame.Surface) -> None:
        if self.background_image is not None:
            self.draw_background_asset(surface)
            return

        depth = self.distance_depth_factor()
        horizon_y = int(218 - 28 * depth)
        lane_vanish = pygame.Vector2(WIDTH * 0.62, horizon_y + 12)

        surface.fill(FOREST_DARK)

        for y in range(0, horizon_y):
            k = y / max(1, horizon_y)
            color = (
                int(122 + 38 * k),
                int(157 + 34 * k),
                int(178 + 24 * k),
            )
            pygame.draw.line(surface, color, (0, y), (WIDTH, y))

        for i in range(-40, WIDTH + 60, 34):
            h = 75 + int(32 * math.sin(i * 0.041))
            base_y = horizon_y + 8
            color = (42, 72, 48) if (i // 34) % 2 else (34, 60, 42)
            pygame.draw.polygon(surface, color, [(i - 30, base_y), (i + 16, base_y - h), (i + 62, base_y)])

        pygame.draw.polygon(surface, SAND, [(0, horizon_y + 30), (WIDTH, horizon_y + 5), (WIDTH, HEIGHT), (0, HEIGHT)])
        pygame.draw.ellipse(surface, SAND_DARK, (WIDTH * 0.38, horizon_y - 36, 560, 190))
        pygame.draw.ellipse(surface, SAND, (WIDTH * 0.42, horizon_y - 16, 470, 130))

        lane_left_near = pygame.Vector2(WIDTH * 0.18, HEIGHT)
        lane_right_near = pygame.Vector2(WIDTH * 0.98, HEIGHT)
        lane_left_far = lane_vanish + pygame.Vector2(-34, 10)
        lane_right_far = lane_vanish + pygame.Vector2(58, 12)
        lane_color = (185, 151, 94)
        pygame.draw.polygon(surface, lane_color, [lane_left_near, lane_left_far, lane_right_far, lane_right_near])
        pygame.draw.line(surface, (122, 96, 62), lane_left_near, lane_left_far, 4)
        pygame.draw.line(surface, (122, 96, 62), lane_right_near, lane_right_far, 4)

        random.seed(3)
        for _ in range(85):
            z = random.random() ** 0.55
            y = int(HEIGHT - 18 - z * (HEIGHT - horizon_y - 60))
            half_width = int(72 + (1 - z) * 470)
            center_x = int(lerp(lane_vanish.x, WIDTH * 0.58, 0.25 + 0.35 * (1 - z)))
            x = random.randint(center_x - half_width, center_x + half_width)
            r = max(1, int((1 - z) * 4.2))
            pygame.draw.circle(surface, (130, 105, 73), (x, y), r)
        random.seed()

        if depth > 0.05:
            haze = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            haze_alpha = int(18 + 58 * depth)
            pygame.draw.rect(haze, (205, 199, 177, haze_alpha), (0, 0, WIDTH, int(horizon_y + 125)))
            pygame.draw.polygon(haze, (220, 210, 185, int(30 * depth)), [(0, horizon_y + 30), (WIDTH, horizon_y), (WIDTH, HEIGHT), (0, HEIGHT)])
            surface.blit(haze, (0, 0))

    def draw_background_asset(self, surface: pygame.Surface) -> None:
        image = self.background_image
        assert image is not None

        iw, ih = image.get_size()
        scale = max(WIDTH / iw, HEIGHT / ih)
        scaled_size = (int(iw * scale), int(ih * scale))
        scaled = pygame.transform.smoothscale(image, scaled_size)

        crop_x = max(0, min(scaled.get_width() - WIDTH, int((scaled.get_width() - WIDTH) * 0.48)))
        crop_y = max(0, min(scaled.get_height() - HEIGHT, int((scaled.get_height() - HEIGHT) * 0.36)))
        surface.blit(scaled, (-crop_x, -crop_y))

        depth = self.distance_depth_factor()
        if depth > 0.08:
            haze = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(haze, (218, 210, 188, int(18 + 34 * depth)), (0, 120, WIDTH, 310))
            surface.blit(haze, (0, 0))

        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 72), (0, 0, 350, HEIGHT))
        pygame.draw.rect(vignette, (0, 0, 0, 24), (350, 0, 160, HEIGHT))
        surface.blit(vignette, (0, 0))

    def crosshair_color(self) -> tuple[int, int, int]:
        if self.last_stability_score >= 0.78:
            return GREEN
        if self.last_stability_score >= 0.52:
            return YELLOW
        return RED

    def draw_crosshair(self, surface: pygame.Surface) -> None:
        if self.state == "shop":
            return

        aim = self.current_aim_point()
        color = self.crosshair_color()
        stability_radius = clamp(10 + (1.0 - self.last_stability_score) * 54 + self.mouse_speed * 0.010, 12, 72)

        pygame.draw.circle(surface, color, aim, int(stability_radius), 2)
        pygame.draw.circle(surface, BLACK, aim, int(stability_radius) + 2, 1)
        pygame.draw.circle(surface, color, aim, 13, 2)
        pygame.draw.circle(surface, WHITE, aim, 3)
        pygame.draw.line(surface, color, (aim.x - 28, aim.y), (aim.x - 9, aim.y), 3)
        pygame.draw.line(surface, color, (aim.x + 9, aim.y), (aim.x + 28, aim.y), 3)
        pygame.draw.line(surface, color, (aim.x, aim.y - 28), (aim.x, aim.y - 9), 3)
        pygame.draw.line(surface, color, (aim.x, aim.y + 9), (aim.x, aim.y + 28), 3)

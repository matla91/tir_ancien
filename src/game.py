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
    HEIGHT,
    SAND,
    SAND_DARK,
    SHOTS_PER_STAGE,
    STAGES_METERS,
    WIDTH,
    YELLOW,
)
from src.target import Shot, Target
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

        self.shot_sound = self.assets.build_flintlock_shot_sound()

        self.money = 0
        self.last_reward = 0

        self.stages = STAGES_METERS[:]
        self.shots_per_stage = SHOTS_PER_STAGE

        self.state = "menu"
        self.stage_index = 0

        self.all_shots: List[Shot] = []
        self.stage_shots: List[Shot] = []

        self.mouse_pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.prev_mouse_pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        self.mouse_speed = 0.0
        self.prev_left_down = False

        self.breath = 100.0
        self.fatigue = 0.0

        self.wind = random.uniform(-0.8, 0.8)
        self.wind_target = self.wind

        self.time = 0.0

        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0
        self.pending_trigger_speed = 0.0

        self.shake_time = 0.0
        self.shake_duration = 0.0
        self.shake_strength = 0.0
        self.camera_offset = pygame.Vector2(0, 0)

        self.message = "Entrée : commencer"
        self.message_time = 0.0

    @property
    def distance(self) -> int:
        return self.stages[self.stage_index]

    def reset(self) -> None:
        self.target.clear_stage()
        self.smoke = SmokeSystem()
        self.floating_text = FloatingTextSystem()
        self.impact_feedback = ImpactFeedbackSystem()

        self.stage_index = 0
        self.all_shots.clear()
        self.stage_shots.clear()

        self.breath = 100.0
        self.fatigue = 0.0

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

        self.message = "Nouveau parcours : 25 m."
        self.message_time = 1.5

    def show_message(self, text: str, duration: float = 1.4) -> None:
        self.message = text
        self.message_time = duration

    def run(self) -> None:
        pygame.mouse.set_visible(False)

        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

    def quit(self) -> None:
        pygame.quit()
        sys.exit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()

                if self.state == "menu" and event.key == pygame.K_RETURN:
                    self.state = "playing"
                    self.show_message("25 m : série de 5 coups.", 1.5)

                elif self.state == "stage_done" and event.key == pygame.K_RETURN:
                    self.next_stage()

                elif self.state == "game_over" and event.key == pygame.K_RETURN:
                    self.reset()
                    self.state = "playing"

                elif self.state == "shop":
                    if event.key == pygame.K_b:
                        self.state = "playing"
                        self.show_message("Retour au pas de tir.", 1.0)
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        index = event.key - pygame.K_1
                        self.handle_shop_selection(index)

                elif self.state == "playing":
                    if event.key == pygame.K_b:
                        self.state = "shop"
                        self.show_message("Boutique ouverte.", 1.0)
                    elif event.key == pygame.K_r:
                        if self.weapon.start_reload():
                            self.show_message("Rechargement...", 0.8)
                        elif self.weapon.loaded:
                            self.show_message("Déjà chargé.", 0.8)
                    elif event.key == pygame.K_c:
                        if self.weapon.start_cleaning():
                            self.show_message("Nettoyage du canon...", 0.8)

    def update(self, dt: float) -> None:
        self.time += dt

        self.update_mouse()
        self.update_click_polling()

        if self.state == "playing":
            self.update_breathing(dt)
            self.update_wind(dt)

        if self.state != "shop":
            self.weapon.update(dt)
            self.update_pending_shot(dt)

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
        if left_down and not self.prev_left_down:
            if self.state == "menu":
                self.state = "playing"
                self.show_message("25 m : série de 5 coups.", 1.5)
            elif self.state == "playing":
                self.try_fire()
        self.prev_left_down = left_down

    def update_breathing(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        breath_control = keys[pygame.K_SPACE] and not self.weapon.reloading and not self.weapon.cleaning

        if breath_control and self.breath > 0:
            self.breath = clamp(self.breath - 24 * dt, 0, 100)
            self.fatigue = clamp(self.fatigue + 2.8 * dt, 0, 100)
        else:
            recovery = 16 if not self.weapon.reloading and not self.weapon.cleaning else 7
            self.breath = clamp(self.breath + recovery * dt, 0, 100)
            self.fatigue = clamp(self.fatigue - 4.5 * dt, 0, 100)

    def update_wind(self, dt: float) -> None:
        if random.random() < 0.008:
            self.wind_target = random.uniform(-1.1, 1.1)
        self.wind = lerp(self.wind, self.wind_target, 0.35 * dt)

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

    def try_fire(self) -> None:
        if self.pending_shot_delay > 0:
            return
        if self.weapon.reloading or self.weapon.cleaning:
            return

        if not self.weapon.loaded:
            self.show_message("Arme vide : R pour recharger.", 1.2)
            return

        delay = self.weapon.random_shot_delay()
        self.pending_shot_delay = delay
        self.pending_shot_start_delay = delay
        self.pending_trigger_speed = self.mouse_speed

        self.weapon.loaded = False
        self.show_message("Départ du coup...", 0.35)

    def update_pending_shot(self, dt: float) -> None:
        if self.pending_shot_delay <= 0:
            return

        self.pending_shot_delay -= dt
        if self.pending_shot_delay <= 0:
            self.finish_fire()

    def finish_fire(self) -> None:
        aim = self.current_aim_point()
        trigger_penalty = clamp(self.pending_trigger_speed / 900.0, 0.0, 1.0)

        dispersion = self.weapon.dispersion_px(self.distance, self.fatigue, trigger_penalty)
        dx = random.gauss(0, dispersion)
        dy = random.gauss(0, dispersion)

        wind_offset = self.wind * (self.distance / 100) * 12.0
        impact = pygame.Vector2(aim.x + dx + wind_offset, aim.y + dy)

        shot = self.target.score_impact(impact, self.distance)
        self.all_shots.append(shot)
        self.stage_shots.append(shot)

        self.weapon.apply_shot_feedback()
        self.fatigue = clamp(self.fatigue + 3.5, 0, 100)

        reward = self.cash_reward_for_shot(shot)
        self.money += reward
        self.last_reward = reward

        muzzle = self.weapon.muzzle_screen_pos(aim)
        direction = aim - self.weapon.anchor_screen_pos()
        self.smoke.spawn(muzzle, direction, count=46 if shot.score >= 8 else 36)
        self.impact_feedback.spawn(pygame.Vector2(shot.x, shot.y), shot.score)

        floating_color = YELLOW if reward > 0 else (220, 220, 220)
        floating_text = f"{shot.score} pts  +${reward}" if reward > 0 else f"{shot.score} pts"
        self.floating_text.spawn(floating_text, pygame.Vector2(shot.x + 18, shot.y - 28), floating_color)

        self.start_camera_shake(strength=11.0 if shot.score >= 8 else 8.0, duration=0.22)

        if self.shot_sound:
            try:
                self.shot_sound.play()
            except Exception:
                pass

        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0
        self.pending_trigger_speed = 0.0

        reward_text = f" +${reward}" if reward > 0 else ""
        if shot.score >= 9:
            self.show_message(f"Très beau coup : {shot.score} points.{reward_text}", 1.4)
        elif shot.score >= 6:
            self.show_message(f"Impact correct : {shot.score} points.{reward_text}", 1.4)
        elif shot.score >= 1:
            self.show_message(f"Impact faible : {shot.score} point(s).{reward_text}", 1.4)
        else:
            self.show_message("Manqué. $0", 1.4)

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
        reward = int(shot.score * distance_multiplier * 3)

        if shot.score == 10:
            reward += int(5 * distance_multiplier)

        return max(1, reward)

    def next_stage(self) -> None:
        self.stage_index += 1

        self.stage_shots.clear()
        self.target.clear_stage()
        self.floating_text = FloatingTextSystem()
        self.impact_feedback = ImpactFeedbackSystem()

        self.weapon.loaded = True
        self.weapon.reloading = False
        self.weapon.cleaning = False
        self.weapon.fouling = clamp(self.weapon.fouling * 0.25, 0, 10)

        self.breath = 100.0
        self.fatigue = clamp(self.fatigue * 0.35, 0, 100)

        self.wind = random.uniform(-0.9, 0.9)
        self.wind_target = self.wind

        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0

        self.show_message(f"Nouvelle distance : {self.distance} m.", 1.6)
        self.state = "playing"

    def handle_shop_selection(self, index: int) -> None:
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

    def equip_weapon(self, weapon_id: str) -> None:
        if weapon_id not in self.weapon_catalog:
            return

        self.current_weapon_id = weapon_id
        self.weapon = self.weapon_catalog[weapon_id]
        self.weapon.reset_runtime_state(clean_barrel=False)
        self.pending_shot_delay = 0.0
        self.pending_shot_start_delay = 0.0
        self.pending_trigger_speed = 0.0
        self.show_message(f"Équipé : {self.weapon.stats.name}.", 1.2)

    def current_sway(self) -> pygame.Vector2:
        keys = pygame.key.get_pressed()
        holding_breath = keys[pygame.K_SPACE] and self.breath > 0 and self.state == "playing"

        distance_factor = (self.distance / 25) ** 0.5
        stability_factor = clamp(1.25 - self.weapon.stats.stability / 100.0, 0.35, 1.25)

        amp = 10.0 + distance_factor * 6.0 + self.fatigue * 0.08 + self.weapon.fouling * 0.6
        amp *= stability_factor

        if holding_breath:
            amp *= 0.36

        if self.breath <= 3 and keys[pygame.K_SPACE]:
            amp *= 1.85

        sx = (
            math.sin(self.time * 1.35) * 0.80
            + math.sin(self.time * 2.75 + 1.4) * 0.32
            + math.sin(self.time * 5.10 + 0.3) * 0.12
        )
        sy = (
            math.cos(self.time * 1.15 + 0.7) * 0.72
            + math.sin(self.time * 2.40 + 2.1) * 0.30
            + math.cos(self.time * 4.60) * 0.14
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
        surface.fill(FOREST_DARK)

        pygame.draw.rect(surface, (132, 162, 178), (0, 0, WIDTH, 140))

        for i in range(0, WIDTH, 38):
            h = 105 + int(45 * math.sin(i * 0.04))
            color = FOREST if (i // 38) % 2 else FOREST_DARK
            pygame.draw.polygon(surface, color, [(i - 30, 155), (i + 18, 155 - h), (i + 66, 155)])

        pygame.draw.polygon(surface, SAND, [(0, 250), (WIDTH, 220), (WIDTH, HEIGHT), (0, HEIGHT)])

        pygame.draw.ellipse(surface, SAND_DARK, (WIDTH * 0.40, 135, 500, 210))
        pygame.draw.ellipse(surface, SAND, (WIDTH * 0.43, 155, 430, 155))

        pygame.draw.polygon(
            surface,
            (185, 151, 94),
            [(WIDTH * 0.22, HEIGHT), (WIDTH * 0.50, 205), (WIDTH * 0.66, 205), (WIDTH * 0.95, HEIGHT)],
        )

        random.seed(3)
        for _ in range(55):
            x = random.randint(0, WIDTH)
            y = random.randint(280, HEIGHT)
            r = random.randint(1, 4)
            pygame.draw.circle(surface, (130, 105, 73), (x, y), r)
        random.seed()

    def draw_crosshair(self, surface: pygame.Surface) -> None:
        if self.state == "shop":
            return

        aim = self.current_aim_point()

        pygame.draw.circle(surface, BLACK, aim, 13, 2)
        pygame.draw.line(surface, BLACK, (aim.x - 24, aim.y), (aim.x - 8, aim.y), 2)
        pygame.draw.line(surface, BLACK, (aim.x + 8, aim.y), (aim.x + 24, aim.y), 2)
        pygame.draw.line(surface, BLACK, (aim.x, aim.y - 24), (aim.x, aim.y - 8), 2)
        pygame.draw.line(surface, BLACK, (aim.x, aim.y + 8), (aim.x, aim.y + 24), 2)

        stability_radius = clamp(6 + self.current_sway().length() * 0.8 + self.mouse_speed * 0.015, 8, 58)
        pygame.draw.circle(surface, (30, 30, 30), aim, stability_radius, 1)

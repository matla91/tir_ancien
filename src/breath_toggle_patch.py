import math

import pygame

from src.utils import clamp


def apply_breath_toggle_patch(GameClass) -> None:
    """Switch breath control from hold-to-breathe to toggle-to-breathe.

    Space toggles breath control in shooting mode. While breath control is active,
    firing is still handled independently through mouse polling and keyboard polling
    so the trigger is never blocked by the breathing state.
    """

    original_init = GameClass.__init__
    original_reset = GameClass.reset
    original_next_stage = GameClass.next_stage
    original_equip_weapon = GameClass.equip_weapon

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.breath_control_active = False
        self.trigger_input_locked = False

    def patched_reset(self, *args, **kwargs):
        self.breath_control_active = False
        self.trigger_input_locked = False
        return original_reset(self, *args, **kwargs)

    def patched_next_stage(self, *args, **kwargs):
        self.breath_control_active = False
        self.trigger_input_locked = False
        return original_next_stage(self, *args, **kwargs)

    def patched_equip_weapon(self, *args, **kwargs):
        self.breath_control_active = False
        self.trigger_input_locked = False
        return original_equip_weapon(self, *args, **kwargs)

    def toggle_breath_control(self) -> None:
        if self.weapon.reloading or self.weapon.cleaning:
            self.breath_control_active = False
            self.show_message("Respiration impossible pendant cette action.", 0.9)
            return

        if self.breath <= 3:
            self.breath_control_active = False
            self.show_message("Souffle épuisé.", 0.9)
            return

        self.breath_control_active = not self.breath_control_active
        if self.breath_control_active:
            self.show_message("Respiration contrôlée.", 0.8)
        else:
            self.show_message("Respiration relâchée.", 0.8)

    def fire_from_trigger_input(self) -> None:
        """Fire once from any trigger input, regardless of breathing state."""
        if self.state == "menu":
            self.state = "playing"
            pygame.mouse.set_visible(False)
            self.show_message("25 m : série de 5 coups.", 1.5)
            return

        if self.state != "playing":
            return

        self.try_fire()

    def patched_handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state == "shop":
                    self.handle_shop_click(event.pos)
                else:
                    self.fire_from_trigger_input()
                    self.trigger_input_locked = True

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.trigger_input_locked = False

            if event.type == pygame.MOUSEMOTION and self.state == "shop":
                hovered = self.shop_index_from_pos(event.pos)
                if hovered is not None:
                    self.shop_selected_index = hovered

            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_f, pygame.K_LCTRL, pygame.K_RCTRL):
                    self.trigger_input_locked = False

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
                    if event.key == pygame.K_SPACE:
                        self.toggle_breath_control()
                    elif event.key in (pygame.K_f, pygame.K_LCTRL, pygame.K_RCTRL):
                        self.fire_from_trigger_input()
                        self.trigger_input_locked = True
                    elif event.key == pygame.K_b:
                        self.breath_control_active = False
                        self.state = "shop"
                        pygame.mouse.set_visible(True)
                        self.show_message("Boutique ouverte.", 1.0)
                    elif event.key == pygame.K_r:
                        self.breath_control_active = False
                        if self.weapon.start_reload():
                            self.show_message("Rechargement...", 0.8)
                        elif self.weapon.loaded:
                            self.show_message("Déjà chargé.", 0.8)
                    elif event.key == pygame.K_c:
                        self.breath_control_active = False
                        if self.weapon.start_cleaning():
                            self.show_message("Nettoyage du canon...", 0.8)

    def patched_update_click_polling(self) -> None:
        mouse_left = pygame.mouse.get_pressed(num_buttons=3)[0]
        keys = pygame.key.get_pressed()
        keyboard_trigger = keys[pygame.K_f] or keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        trigger_down = mouse_left or keyboard_trigger

        if self.state == "shop":
            self.prev_left_down = mouse_left
            if not trigger_down:
                self.trigger_input_locked = False
            return

        # This is the important part: trigger input is checked independently from
        # Space/breathing. Even if breath_control_active is True, the shot can start.
        if trigger_down and not self.trigger_input_locked:
            self.fire_from_trigger_input()
            self.trigger_input_locked = True

        if not trigger_down:
            self.trigger_input_locked = False

        self.prev_left_down = mouse_left

    def patched_update_breathing(self, dt: float) -> None:
        if self.breath_control_active and (self.weapon.reloading or self.weapon.cleaning):
            self.breath_control_active = False

        if self.breath_control_active and self.breath <= 0:
            self.breath_control_active = False
            self.show_message("Souffle épuisé.", 0.9)

        breath_control = (
            self.breath_control_active
            and self.breath > 0
            and not self.weapon.reloading
            and not self.weapon.cleaning
        )

        if breath_control:
            self.breath_hold_time += dt
            self.breath = clamp(self.breath - 24 * dt, 0, 100)
            self.fatigue = clamp(self.fatigue + 2.8 * dt, 0, 100)
        else:
            self.breath_hold_time = 0.0
            recovery = 16 if not self.weapon.reloading and not self.weapon.cleaning else 7
            self.breath = clamp(self.breath + recovery * dt, 0, 100)
            self.fatigue = clamp(self.fatigue - 4.5 * dt, 0, 100)

    def patched_breath_quality(self) -> float:
        holding = self.breath_control_active and self.breath > 0 and self.state == "playing"
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

    def patched_current_sway(self):
        holding_breath = self.breath_control_active and self.breath > 0 and self.state == "playing"
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

        if self.breath <= 3 and self.breath_control_active:
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

    GameClass.__init__ = patched_init
    GameClass.reset = patched_reset
    GameClass.next_stage = patched_next_stage
    GameClass.equip_weapon = patched_equip_weapon
    GameClass.toggle_breath_control = toggle_breath_control
    GameClass.fire_from_trigger_input = fire_from_trigger_input
    GameClass.handle_events = patched_handle_events
    GameClass.update_click_polling = patched_update_click_polling
    GameClass.update_breathing = patched_update_breathing
    GameClass.breath_quality = patched_breath_quality
    GameClass.current_sway = patched_current_sway

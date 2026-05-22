from typing import Tuple

import pygame

from src.settings import BLACK, DARK_GREY, GREEN, HEIGHT, WHITE, WIDTH, YELLOW


class UI:
    def __init__(self) -> None:
        self.font = pygame.font.SysFont("arial", 22)
        self.small = pygame.font.SysFont("arial", 16)
        self.big = pygame.font.SysFont("arial", 42, bold=True)
        self.title_font = pygame.font.SysFont("arial", 56, bold=True)

    def draw_bar(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        value: float,
        label: str,
        color: Tuple[int, int, int],
    ) -> None:
        value = max(0.0, min(1.0, value))
        pygame.draw.rect(surface, DARK_GREY, (x, y, w, h), border_radius=4)
        pygame.draw.rect(surface, color, (x, y, int(w * value), h), border_radius=4)
        pygame.draw.rect(surface, BLACK, (x, y, w, h), 1, border_radius=4)
        txt = self.small.render(label, True, WHITE)
        surface.blit(txt, (x + 8, y + 3))

    def draw_hud(self, surface: pygame.Surface, game) -> None:
        panel = pygame.Surface((335, HEIGHT), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 112))
        surface.blit(panel, (0, 0))

        total = sum(s.score for s in game.all_shots)
        stage_total = sum(s.score for s in game.stage_shots)
        shots_left = game.shots_per_stage - len(game.stage_shots)
        weapon = game.weapon
        target = game.target.target_type

        if weapon.reloading:
            weapon_state = "rechargement"
        elif weapon.cleaning:
            weapon_state = "nettoyage"
        elif weapon.loaded:
            weapon_state = "chargée"
        else:
            weapon_state = "vide"

        y = 18
        lines = [
            f"Argent : ${game.money}",
            f"Arme : {weapon.stats.name}",
            f"Cible : {target.name}",
            f"Distance : {game.distance} m",
            f"Série : {len(game.stage_shots)}/{game.shots_per_stage} coups",
            f"Coups restants : {shots_left}",
            f"Score série : {stage_total}",
            f"Score total : {total}",
            "",
            f"État : {weapon_state}",
            f"Encrassement : {weapon.fouling:.1f}/10",
            f"Fatigue : {game.fatigue:.0f}/100",
            f"Vent latéral : {game.wind:+.2f}",
        ]

        for line in lines:
            txt = self.font.render(line, True, WHITE)
            surface.blit(txt, (20, y))
            y += 26

        breath_color = GREEN if game.breath > 25 else YELLOW
        self.draw_bar(surface, 20, y + 6, 290, 22, game.breath / 100, "Respiration", breath_color)
        y += 42

        if weapon.reloading:
            step = weapon.reload_step_index + 1
            total_steps = len(weapon.RELOAD_STEPS)
            label = f"Rechargement {step}/{total_steps}"
            self.draw_bar(surface, 20, y, 290, 22, weapon.reload_progress, label, (40, 72, 128))
            y += 28

            step_text = self.small.render(f"E : {weapon.current_reload_step_label()}", True, YELLOW)
            surface.blit(step_text, (20, y))
            y += 26

        if weapon.cleaning:
            self.draw_bar(surface, 20, y, 290, 22, weapon.clean_progress, "Nettoyage", YELLOW)
            y += 34

        if game.pending_shot_delay > 0:
            self.draw_bar(surface, 20, y, 290, 22, 1.0 - game.pending_shot_delay / max(game.pending_shot_start_delay, 0.01), "Allumage", (176, 35, 32))
            y += 34

        y += 6
        controls = [
            "Souris : viser",
            "Clic gauche / F / Ctrl : tirer",
            "Espace : contrôler la respiration",
            "R : lancer le rechargement",
            "E : étape de rechargement",
            "C : nettoyer le canon",
            "B : boutique",
            "Entrée : continuer",
            "Échap : quitter",
        ]
        for control in controls:
            txt = self.small.render(control, True, WHITE)
            surface.blit(txt, (20, y))
            y += 20

        if game.message_time > 0:
            msg = self.font.render(game.message, True, YELLOW)
            surface.blit(msg, (WIDTH / 2 - msg.get_width() / 2, HEIGHT - 48))

    def draw_menu(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        surface.blit(overlay, (0, 0))

        title = self.title_font.render("FLINTLOCK RANGE", True, WHITE)
        subtitle = self.font.render("MVP de tir sportif à l'arme ancienne", True, WHITE)
        prompt = self.big.render("Entrée ou clic gauche pour commencer", True, YELLOW)

        surface.blit(title, (WIDTH / 2 - title.get_width() / 2, 160))
        surface.blit(subtitle, (WIDTH / 2 - subtitle.get_width() / 2, 238))
        surface.blit(prompt, (WIDTH / 2 - prompt.get_width() / 2, 335))

        tips = [
            "Arme de départ : pistolet à silex de type Kentucky/Pennsylvania.",
            "Cible de départ : cible papier de précision, pas cible d'arc.",
            "Plus la cible est loin, plus chaque point rapporte d'argent.",
            "Appuie sur B pendant le jeu pour ouvrir la boutique.",
        ]

        y = 425
        for tip in tips:
            line = self.font.render("• " + tip, True, WHITE)
            surface.blit(line, (WIDTH / 2 - 430, y))
            y += 34

    def draw_shop(self, surface: pygame.Surface, game) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 178))
        surface.blit(overlay, (0, 0))

        title = self.big.render("Boutique", True, WHITE)
        money = self.font.render(f"Argent disponible : ${game.money}", True, YELLOW)
        hint = self.font.render("Touches 1-9 : acheter ou équiper | B : retour au pas de tir", True, WHITE)

        surface.blit(title, (WIDTH / 2 - title.get_width() / 2, 36))
        surface.blit(money, (WIDTH / 2 - money.get_width() / 2, 86))
        surface.blit(hint, (WIDTH / 2 - hint.get_width() / 2, 120))

        start_x = 245
        y = 165
        card_w = 760
        card_h = 62

        section = self.font.render("Armes", True, YELLOW)
        surface.blit(section, (start_x, y))
        y += 30

        for index, weapon_id in enumerate(game.shop_weapon_ids):
            weapon = game.weapon_catalog[weapon_id]
            owned = weapon_id in game.owned_weapon_ids
            equipped = weapon_id == game.current_weapon_id
            rect = pygame.Rect(start_x, y, card_w, card_h)
            self.draw_weapon_card(surface, rect, index + 1, weapon, owned, equipped, game.money)
            y += card_h + 8

        y += 6
        section = self.font.render("Cibles", True, YELLOW)
        surface.blit(section, (start_x, y))
        y += 30

        base_index = len(game.shop_weapon_ids)
        target_card_h = 58
        for index, target_id in enumerate(game.shop_target_ids):
            target = game.target.target_type if target_id == game.current_target_id else game.target.TARGET_CATALOG[target_id] if hasattr(game.target, 'TARGET_CATALOG') else None
            target = game.target.__class__.__mro__[0]

        # Keep target catalog access simple and explicit from game state.
        for index, target_id in enumerate(game.shop_target_ids):
            target = game.target.target_type if target_id == game.current_target_id else None
            if target is None:
                from src.target import TARGET_CATALOG
                target = TARGET_CATALOG[target_id]
            owned = target_id in game.owned_target_ids
            equipped = target_id == game.current_target_id
            rect = pygame.Rect(start_x, y, card_w, target_card_h)
            self.draw_target_card(surface, rect, base_index + index + 1, target, owned, equipped, game.money)
            y += target_card_h + 8

    def draw_weapon_card(self, surface, rect, key_number, weapon, owned, equipped, money) -> None:
        bg = (38, 38, 38) if not equipped else (46, 64, 46)
        border = YELLOW if equipped else WHITE
        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 2, border_radius=8)

        key_text = self.font.render(f"{key_number}", True, YELLOW)
        surface.blit(key_text, (rect.x + 16, rect.y + 10))
        name = self.font.render(weapon.stats.name, True, WHITE)
        surface.blit(name, (rect.x + 55, rect.y + 7))
        desc = self.small.render(weapon.stats.description, True, (220, 220, 220))
        surface.blit(desc, (rect.x + 55, rect.y + 34))

        if equipped:
            status = "ÉQUIPÉ"
            color = GREEN
        elif owned:
            status = "POSSÉDÉ"
            color = WHITE
        else:
            status = f"${weapon.stats.price}"
            color = YELLOW if money >= weapon.stats.price else (205, 95, 95)
        status_img = self.font.render(status, True, color)
        surface.blit(status_img, (rect.right - status_img.get_width() - 22, rect.y + 18))

    def draw_target_card(self, surface, rect, key_number, target, owned, equipped, money) -> None:
        bg = (38, 38, 38) if not equipped else (46, 54, 68)
        border = YELLOW if equipped else WHITE
        pygame.draw.rect(surface, bg, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 2, border_radius=8)

        key_text = self.font.render(f"{key_number}", True, YELLOW)
        surface.blit(key_text, (rect.x + 16, rect.y + 8))
        name = self.font.render(target.name, True, WHITE)
        surface.blit(name, (rect.x + 55, rect.y + 5))
        desc = self.small.render(target.description, True, (220, 220, 220))
        surface.blit(desc, (rect.x + 55, rect.y + 30))

        bonus = self.small.render(f"{target.difficulty} | gains x{target.reward_multiplier:.2f}", True, (205, 205, 205))
        surface.blit(bonus, (rect.x + 445, rect.y + 32))

        if equipped:
            status = "ÉQUIPÉE"
            color = GREEN
        elif owned:
            status = "POSSÉDÉE"
            color = WHITE
        else:
            status = f"${target.price}"
            color = YELLOW if money >= target.price else (205, 95, 95)
        status_img = self.font.render(status, True, color)
        surface.blit(status_img, (rect.right - status_img.get_width() - 22, rect.y + 16))

    def draw_stage_done(self, surface: pygame.Surface, game) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 115))
        surface.blit(overlay, (0, 0))

        score = sum(s.score for s in game.stage_shots)
        money_earned = sum(game.cash_reward_for_shot(s) for s in game.stage_shots)

        title = self.big.render(f"Série {game.distance} m terminée", True, WHITE)
        detail = self.font.render(f"Score sur cette distance : {score}/50 | Gains estimés : ${money_earned}", True, YELLOW)
        prompt = self.font.render("Entrée : passer à la distance suivante", True, WHITE)

        surface.blit(title, (WIDTH / 2 - title.get_width() / 2, 245))
        surface.blit(detail, (WIDTH / 2 - detail.get_width() / 2, 310))
        surface.blit(prompt, (WIDTH / 2 - prompt.get_width() / 2, 360))

    def draw_game_over(self, surface: pygame.Surface, game) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 132))
        surface.blit(overlay, (0, 0))

        total = sum(s.score for s in game.all_shots)
        max_score = len(game.stages) * game.shots_per_stage * 10

        title = self.big.render("Parcours terminé", True, WHITE)
        detail = self.font.render(f"Score final : {total}/{max_score} | Argent : ${game.money}", True, YELLOW)
        prompt = self.font.render("Entrée : recommencer | B en jeu : boutique | Échap : quitter", True, WHITE)

        surface.blit(title, (WIDTH / 2 - title.get_width() / 2, 215))
        surface.blit(detail, (WIDTH / 2 - detail.get_width() / 2, 285))
        surface.blit(prompt, (WIDTH / 2 - prompt.get_width() / 2, 340))

        y = 410
        x = WIDTH / 2 - 170
        for stage_distance in game.stages:
            stage_score = sum(s.score for s in game.all_shots if s.distance == stage_distance)
            line = self.font.render(f"{stage_distance:>3} m : {stage_score:>2}/50", True, WHITE)
            surface.blit(line, (x, y))
            y += 30

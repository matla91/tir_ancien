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

        y = 18
        lines = [
            f"Arme : {weapon.stats.name}",
            f"Distance : {game.distance} m",
            f"Série : {len(game.stage_shots)}/{game.shots_per_stage} coups",
            f"Coups restants : {shots_left}",
            f"Score série : {stage_total}",
            f"Score total : {total}",
            "",
            f"État : {'chargée' if weapon.loaded else 'vide'}",
            f"Encrassement : {weapon.fouling:.1f}/10",
            f"Fatigue : {game.fatigue:.0f}/100",
            f"Vent latéral : {game.wind:+.2f}",
        ]

        for line in lines:
            txt = self.font.render(line, True, WHITE)
            surface.blit(txt, (20, y))
            y += 28

        breath_color = GREEN if game.breath > 25 else YELLOW
        self.draw_bar(surface, 20, y + 6, 290, 22, game.breath / 100, "Respiration", breath_color)
        y += 44

        if weapon.reloading:
            self.draw_bar(surface, 20, y, 290, 22, weapon.reload_progress, "Rechargement", (40, 72, 128))
            y += 36

        if weapon.cleaning:
            self.draw_bar(surface, 20, y, 290, 22, weapon.clean_progress, "Nettoyage", YELLOW)
            y += 36

        if game.pending_shot_delay > 0:
            self.draw_bar(surface, 20, y, 290, 22, 1.0 - game.pending_shot_delay / max(game.pending_shot_start_delay, 0.01), "Allumage", (176, 35, 32))
            y += 36

        y += 10
        controls = [
            "Souris : viser",
            "Clic gauche : tirer",
            "Espace : contrôler la respiration",
            "R : recharger",
            "C : nettoyer le canon",
            "Entrée : continuer",
            "Échap : quitter",
        ]
        for control in controls:
            txt = self.small.render(control, True, WHITE)
            surface.blit(txt, (20, y))
            y += 22

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
            "Le contrôle de respiration réduit le mouvement, mais ne le supprime pas.",
            "Le silex crée un léger délai : garde la visée après le clic.",
            "L'encrassement augmente la dispersion : nettoie quand c'est nécessaire.",
        ]

        y = 425
        for tip in tips:
            line = self.font.render("• " + tip, True, WHITE)
            surface.blit(line, (WIDTH / 2 - 430, y))
            y += 34

    def draw_stage_done(self, surface: pygame.Surface, game) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 115))
        surface.blit(overlay, (0, 0))

        score = sum(s.score for s in game.stage_shots)
        title = self.big.render(f"Série {game.distance} m terminée", True, WHITE)
        detail = self.font.render(f"Score sur cette distance : {score}/50", True, YELLOW)
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
        detail = self.font.render(f"Score final : {total}/{max_score}", True, YELLOW)
        prompt = self.font.render("Entrée : recommencer | Échap : quitter", True, WHITE)

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

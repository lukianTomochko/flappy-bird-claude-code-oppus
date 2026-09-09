from typing import Tuple

import pygame

from ..utils import GameConfig, clamp, render_outlined
from .entity import Entity

BAR = pygame.Rect(8, 24, 96, 6)
BAR_RADIUS = 3
TRACK_COLOR = (0, 0, 0, 120)
LABEL_POS = (6, 4)
FLASH_FRAMES = 26
FLASH_TINT_ALPHA = 70


class DifficultyHUD(Entity):
    """Difficulty read-out: a level gauge plus a level-up flash.

    The gauge fills as the player approaches the next level and is drawn in
    that level's colour, matching the tint of the pipes on screen.
    """

    def __init__(self, config: GameConfig) -> None:
        super().__init__(config)
        self.shown_level = config.difficulty.level
        self.flash = 0

        # the gauge track is a constant black rounded rect: build it once
        self.track = pygame.Surface(BAR.size, pygame.SRCALPHA)
        pygame.draw.rect(
            self.track,
            TRACK_COLOR,
            self.track.get_rect(),
            border_radius=BAR_RADIUS,
        )
        # the flash tint is the only full-screen surface here; it is
        # re-filled every frame (fill overwrites, so this is identical to
        # allocating a fresh transparent surface) instead of reallocated
        self.tint = pygame.Surface(
            (config.window.width, config.window.height), pygame.SRCALPHA
        )
        # banner text is cached per level; ``banner`` rebuilds it whenever
        # ``shown_level`` moves, which is the only thing it depends on
        self.banner_level = None
        self.banner_lines: Tuple[pygame.Surface, ...] = ()

    def draw(self) -> None:
        difficulty = self.config.difficulty

        if difficulty.level != self.shown_level:
            self.shown_level = difficulty.level
            self.flash = FLASH_FRAMES

        self.draw_gauge()

        if self.flash > 0:
            self.draw_level_up()
            self.flash -= 1

    def draw_gauge(self) -> None:
        difficulty = self.config.difficulty
        screen = self.config.screen

        label = render_outlined(
            self.config.fonts.small,
            f"LV {difficulty.level}  {difficulty.name}",
            difficulty.color,
        )
        screen.blit(label, LABEL_POS)
        screen.blit(self.track, BAR.topleft)

        filled = int(BAR.width * clamp(difficulty.progress, 0.0, 1.0))
        if filled:
            pygame.draw.rect(
                screen,
                difficulty.color,
                pygame.Rect(BAR.x, BAR.y, filled, BAR.height),
                border_radius=BAR_RADIUS,
            )
        pygame.draw.rect(
            screen, (255, 255, 255), BAR, 1, border_radius=BAR_RADIUS
        )

        speed = render_outlined(
            self.config.fonts.tiny,
            f"x{difficulty.speed_multiplier:.2f}",
            (255, 255, 255),
        )
        screen.blit(speed, (BAR.right + 5, BAR.y - 4))

    def banner(self) -> Tuple[pygame.Surface, ...]:
        """The two level-up lines, rebuilt only when the level changes.

        These are private copies because ``draw_level_up`` fades them with
        ``set_alpha``, and ``render_outlined`` hands out shared surfaces.
        """
        if self.banner_level != self.shown_level:
            difficulty = self.config.difficulty
            self.banner_lines = (
                render_outlined(
                    self.config.fonts.medium,
                    f"LEVEL {difficulty.level}",
                    (255, 255, 255),
                ).copy(),
                render_outlined(
                    self.config.fonts.large, difficulty.name, difficulty.color
                ).copy(),
            )
            self.banner_level = self.shown_level
        return self.banner_lines

    def draw_level_up(self) -> None:
        difficulty = self.config.difficulty
        window = self.config.window
        screen = self.config.screen
        remaining = self.flash / FLASH_FRAMES

        self.tint.fill((*difficulty.color, int(FLASH_TINT_ALPHA * remaining)))
        screen.blit(self.tint, (0, 0))

        alpha = int(255 * min(1.0, remaining * 1.6))
        y = window.height * 0.32
        for line in self.banner():
            line.set_alpha(alpha)
            screen.blit(line, ((window.width - line.get_width()) / 2, y))
            y += line.get_height() + 2

import pygame

from ..utils import GameConfig, clamp, render_outlined
from .entity import Entity

BAR = pygame.Rect(8, 24, 96, 6)
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

        track = pygame.Surface(BAR.size, pygame.SRCALPHA)
        pygame.draw.rect(
            track, (0, 0, 0, 120), track.get_rect(), border_radius=3
        )
        screen.blit(track, BAR.topleft)

        filled = int(BAR.width * clamp(difficulty.progress, 0.0, 1.0))
        if filled:
            pygame.draw.rect(
                screen,
                difficulty.color,
                pygame.Rect(BAR.x, BAR.y, filled, BAR.height),
                border_radius=3,
            )
        pygame.draw.rect(screen, (255, 255, 255), BAR, 1, border_radius=3)

        speed = render_outlined(
            self.config.fonts.tiny,
            f"x{difficulty.speed_multiplier:.2f}",
            (255, 255, 255),
        )
        screen.blit(speed, (BAR.right + 5, BAR.y - 4))

    def draw_level_up(self) -> None:
        difficulty = self.config.difficulty
        window = self.config.window
        screen = self.config.screen
        remaining = self.flash / FLASH_FRAMES

        tint = pygame.Surface((window.width, window.height), pygame.SRCALPHA)
        tint.fill((*difficulty.color, int(FLASH_TINT_ALPHA * remaining)))
        screen.blit(tint, (0, 0))

        alpha = int(255 * min(1.0, remaining * 1.6))
        banner = (
            render_outlined(
                self.config.fonts.medium,
                f"LEVEL {difficulty.level}",
                (255, 255, 255),
            ),
            render_outlined(
                self.config.fonts.large, difficulty.name, difficulty.color
            ),
        )

        y = window.height * 0.32
        for line in banner:
            line.set_alpha(alpha)
            screen.blit(line, ((window.width - line.get_width()) / 2, y))
            y += line.get_height() + 2

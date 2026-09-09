"""Shared fonts and a text renderer that stays readable over the sprites."""

from typing import Tuple

import pygame

# comma separated so pygame can fall back on non-Windows systems
FONT_NAMES = "arial,dejavusans,freesans,helvetica"


class Fonts:
    tiny: pygame.font.Font
    small: pygame.font.Font
    medium: pygame.font.Font
    large: pygame.font.Font

    def __init__(self) -> None:
        if not pygame.font.get_init():
            pygame.font.init()

        self.tiny = pygame.font.SysFont(FONT_NAMES, 10, bold=True)
        self.small = pygame.font.SysFont(FONT_NAMES, 13, bold=True)
        self.medium = pygame.font.SysFont(FONT_NAMES, 17, bold=True)
        self.large = pygame.font.SysFont(FONT_NAMES, 24, bold=True)


def render_outlined(
    font: pygame.font.Font,
    text: str,
    color: Tuple[int, int, int],
    outline: Tuple[int, int, int] = (0, 0, 0),
    width: int = 1,
) -> pygame.Surface:
    """Renders ``text`` with a thin outline so it reads on any background."""
    body = font.render(text, True, color)
    if width <= 0:
        return body

    edge = font.render(text, True, outline)
    surface = pygame.Surface(
        (body.get_width() + width * 2, body.get_height() + width * 2),
        pygame.SRCALPHA,
    )
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx or dy:
                surface.blit(edge, (width + dx, width + dy))
    surface.blit(body, (width, width))
    return surface

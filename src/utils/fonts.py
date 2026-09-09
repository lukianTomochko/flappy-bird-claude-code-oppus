"""Shared fonts and a text renderer that stays readable over the sprites."""

from functools import lru_cache
from typing import Tuple

import pygame

# comma separated so pygame can fall back on non-Windows systems
FONT_NAMES = "arial,dejavusans,freesans,helvetica"

# Bounds the outlined-text cache. The game only ever draws a handful of
# distinct strings (6 level names, "x1.00".."x2.12", 5 score rows), so this
# is generous; an LRU keeps a hostile string never growing the cache.
OUTLINE_CACHE_SIZE = 256


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


@lru_cache(maxsize=OUTLINE_CACHE_SIZE)
def render_outlined(
    font: pygame.font.Font,
    text: str,
    color: Tuple[int, int, int],
    outline: Tuple[int, int, int] = (0, 0, 0),
    width: int = 1,
) -> pygame.Surface:
    """Renders ``text`` with a thin outline so it reads on any background.

    Costs 2 font renders plus 9 blits, and the HUD and the score board ask
    for the same unchanged strings on every frame, so the result is cached
    on all five arguments. Nothing else feeds into the pixels -- the fonts
    are immutable singletons built once in ``Fonts`` -- so an entry can
    never go stale and the cache never needs invalidating.

    The returned surface is shared: copy it before mutating it (notably
    ``set_alpha``).
    """
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

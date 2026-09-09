from functools import wraps
from typing import List, Tuple

import pygame

HitMaskType = List[List[bool]]


def clamp(n: float, minn: float, maxn: float) -> float:
    """Clamps a number between two values"""
    return max(min(maxn, n), minn)


def memoize(func):
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return wrapper


@memoize
def get_hit_mask(image: pygame.Surface) -> HitMaskType:
    """returns a hit mask using an image's alpha."""
    return list(
        (
            list(
                (
                    bool(image.get_at((x, y))[3])
                    for y in range(image.get_height())
                )
            )
            for x in range(image.get_width())
        )
    )


def pixel_collision(
    rect1: pygame.Rect,
    rect2: pygame.Rect,
    hitmask1: HitMaskType,
    hitmask2: HitMaskType,
):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y

    for x in range(rect.width):
        for y in range(rect.height):
            if hitmask1[x1 + x][y1 + y] and hitmask2[x2 + x][y2 + y]:
                return True
    return False


def colorize_surface(
    surface: pygame.Surface,
    color: Tuple[int, int, int],
    strength: float = 1.0,
) -> pygame.Surface:
    """Returns a copy of ``surface`` recoloured to ``color``.

    The sprite is reduced to its luminance, brightened so its lit areas
    reach full intensity, then multiplied by ``color``. Shading and
    outlines survive while the hue is replaced no matter what the original
    sprite looked like. ``strength`` blends the result back over the
    original, and the alpha channel (and therefore any hit mask derived
    from it) is left untouched.
    """
    strength = clamp(strength, 0.0, 1.0)
    if strength <= 0:
        return surface.copy()

    colorized = pygame.transform.grayscale(surface)
    # lift the luminance so the sprite's lit body lands on the full colour
    # instead of a darkened, muddy version of it
    mean = pygame.transform.average_color(colorized, consider_alpha=True)[0]
    lift = max(0, 255 - mean)

    colorized.blit(
        filled_surface(surface.get_size(), (lift, lift, lift)),
        (0, 0),
        special_flags=pygame.BLEND_RGB_ADD,
    )
    colorized.blit(
        filled_surface(surface.get_size(), color),
        (0, 0),
        special_flags=pygame.BLEND_RGB_MULT,
    )

    if strength >= 1.0:
        return colorized

    blended = surface.copy()
    colorized.set_alpha(int(255 * strength))
    blended.blit(colorized, (0, 0))
    return blended


def filled_surface(
    size: Tuple[int, int], color: Tuple[int, int, int]
) -> pygame.Surface:
    """An opaque surface of a single colour, for blend operations."""
    surface = pygame.Surface(size)
    surface.fill(color)
    return surface

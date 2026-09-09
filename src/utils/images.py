import random
from typing import Dict, Iterable, List, Tuple

import pygame

from .constants import BACKGROUNDS, PIPES, PLAYERS
from .difficulty import LEVELS
from .utils import colorize_surface, get_hit_mask

# how strongly pipes take on the current difficulty colour
PIPE_COLOR_STRENGTH = 0.85

PipePair = Tuple[pygame.Surface, pygame.Surface]


class Images:
    numbers: List[pygame.Surface]
    game_over: pygame.Surface
    welcome_message: pygame.Surface
    base: pygame.Surface
    background: pygame.Surface
    player: Tuple[pygame.Surface]
    pipe: PipePair

    def __init__(self) -> None:
        self.numbers = list(
            (
                pygame.image.load(f"assets/sprites/{num}.png").convert_alpha()
                for num in range(10)
            )
        )

        # game over sprite
        self.game_over = pygame.image.load(
            "assets/sprites/gameover.png"
        ).convert_alpha()
        # welcome_message sprite for welcome screen
        self.welcome_message = pygame.image.load(
            "assets/sprites/message.png"
        ).convert_alpha()
        # base (ground) sprite
        self.base = pygame.image.load("assets/sprites/base.png").convert_alpha()
        self.colored_pipes: Dict[Tuple, PipePair] = {}
        self.randomize()

    def randomize(self):
        # select random background sprites
        rand_bg = random.randint(0, len(BACKGROUNDS) - 1)
        # select random player sprites
        rand_player = random.randint(0, len(PLAYERS) - 1)
        # select random pipe sprites
        rand_pipe = random.randint(0, len(PIPES) - 1)

        self.background = pygame.image.load(BACKGROUNDS[rand_bg]).convert()
        self.player = (
            pygame.image.load(PLAYERS[rand_player][0]).convert_alpha(),
            pygame.image.load(PLAYERS[rand_player][1]).convert_alpha(),
            pygame.image.load(PLAYERS[rand_player][2]).convert_alpha(),
        )
        self.pipe = (
            pygame.transform.flip(
                pygame.image.load(PIPES[rand_pipe]).convert_alpha(),
                False,
                True,
            ),
            pygame.image.load(PIPES[rand_pipe]).convert_alpha(),
        )
        # base sprites changed, so previously recoloured copies are stale
        self.colored_pipes.clear()
        self.warm_pipe_colors(level.color for level in LEVELS)

    def warm_pipe_colors(self, colors: Iterable[Tuple[int, int, int]]) -> None:
        """Builds every difficulty's pipes (and hit masks) up front.

        Doing it lazily meant the first pipe of a new level paid two
        colourisations plus two pure-python hit masks (~21 ms) inside a
        single 33 ms frame, right under the level-up flash. Called from
        ``randomize`` so the warm cache invariant survives a re-roll.
        """
        for color in colors:
            for surface in self.pipes_colored(color):
                # masks are memoized per surface; touch them here so the
                # cost lands at load time and not mid-flight
                get_hit_mask(surface)

    def pipes_colored(
        self,
        color: Tuple[int, int, int],
        strength: float = PIPE_COLOR_STRENGTH,
    ) -> PipePair:
        """Upper/lower pipe sprites recoloured to ``color``.

        Results are cached: one pair per difficulty colour keeps the hit
        masks (which are memoized per surface) from being rebuilt for every
        single pipe that spawns.
        """
        key = (tuple(color), round(strength, 3))
        if key not in self.colored_pipes:
            self.colored_pipes[key] = (
                colorize_surface(self.pipe[0], color, strength),
                colorize_surface(self.pipe[1], color, strength),
            )
        return self.colored_pipes[key]

"""Shared fixtures for the high score and dynamic difficulty tests.

The game entities are exercised against a stubbed GameConfig so the tests
never need a real window, sound card or sprite files.
"""

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402  (must follow the driver setup above)

from src.utils import Difficulty, Window  # noqa: E402

PIPE_SIZE = (52, 320)
BASE_SIZE = (336, 112)
WINDOW_SIZE = (288, 512)


@pytest.fixture(scope="session", autouse=True)
def pygame_headless():
    """Boots pygame against the dummy drivers for the whole session."""
    pygame.display.init()
    pygame.display.set_mode(WINDOW_SIZE)
    yield
    pygame.display.quit()


@pytest.fixture
def scores_path(tmp_path):
    """Path to a score file inside an isolated temporary directory."""
    return str(tmp_path / "highscore.json")


@pytest.fixture
def write_scores_file(scores_path):
    """Writes raw content to the score file before it gets loaded."""

    def write(content):
        text = content if isinstance(content, str) else json.dumps(content)
        with open(scores_path, "w", encoding="utf-8") as file:
            file.write(text)
        return scores_path

    return write


@pytest.fixture
def sample_entries():
    """A saved table that is already full, out of order and dated."""
    return [
        {"score": 18, "date": "2024-01-02"},
        {"score": 41, "date": "2024-01-01"},
        {"score": 9, "date": "2024-01-05"},
        {"score": 27, "date": "2024-01-03"},
        {"score": 33, "date": "2024-01-04"},
    ]


@pytest.fixture
def sprite():
    """Factory for opaque stand-in sprites with a real alpha channel."""

    def make(size, color=(120, 180, 90, 255)):
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(color)
        return surface

    return make


@pytest.fixture
def fake_config(sprite):
    """A GameConfig stub carrying a real Difficulty and Window.

    ``images.pipes_colored`` is a mock so tests can assert which difficulty
    colour the pipes were spawned with.
    """
    images = MagicMock()
    images.base = sprite(BASE_SIZE)
    images.pipes_colored.side_effect = lambda color, **kwargs: (
        sprite(PIPE_SIZE),
        sprite(PIPE_SIZE),
    )

    return SimpleNamespace(
        screen=pygame.Surface(WINDOW_SIZE),
        window=Window(*WINDOW_SIZE),
        images=images,
        sounds=MagicMock(),
        fonts=MagicMock(),
        difficulty=Difficulty(),
        high_scores=MagicMock(),
        debug=False,
    )

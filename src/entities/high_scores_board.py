import pygame

from ..utils import GameConfig, render_outlined
from .entity import Entity

PANEL_WIDTH = 200
PADDING = 10
ROW_HEIGHT = 18
HEADER_HEIGHT = 22

BACKDROP = (10, 18, 30, 195)
BORDER = (255, 255, 255, 70)
HEADER = (235, 240, 250)
RANK = (150, 162, 180)
SCORE = (255, 255, 255)
DATE = (130, 142, 160)
HIGHLIGHT = (255, 214, 92)
WARNING = (240, 130, 130)


class HighScoresBoard(Entity):
    """Draws the persisted top scores.

    ``compact`` mode is the single best score for the splash screen, the
    full mode is the table shown after a crash with the run just played
    highlighted.
    """

    def __init__(self, config: GameConfig, compact: bool = False) -> None:
        super().__init__(config)
        self.compact = compact

    def draw(self) -> None:
        if self.compact:
            self.draw_best()
        else:
            self.draw_panel()

    # ------------------------------------------------------------------
    # splash screen
    # ------------------------------------------------------------------
    def draw_best(self) -> None:
        best = self.config.high_scores.best
        if not best:
            return

        label = render_outlined(
            self.config.fonts.small, f"BEST  {best}", HIGHLIGHT
        )
        self.config.screen.blit(
            label,
            (
                (self.config.window.width - label.get_width()) / 2,
                self.config.window.viewport_height - 34,
            ),
        )

    # ------------------------------------------------------------------
    # game over screen
    # ------------------------------------------------------------------
    def draw_panel(self) -> None:
        high_scores = self.config.high_scores
        rows = high_scores.top or [None]
        warning = high_scores.error

        height = HEADER_HEIGHT + ROW_HEIGHT * len(rows) + PADDING * 2
        if warning:
            height += ROW_HEIGHT

        panel = pygame.Surface((PANEL_WIDTH, height), pygame.SRCALPHA)
        panel_rect = panel.get_rect()
        pygame.draw.rect(panel, BACKDROP, panel_rect, border_radius=8)
        pygame.draw.rect(panel, BORDER, panel_rect, 2, border_radius=8)

        y = PADDING
        self.blit_centered(panel, self.header_label(), y)
        y += HEADER_HEIGHT

        for index, entry in enumerate(rows, start=1):
            self.draw_row(panel, entry, index, y)
            y += ROW_HEIGHT

        if warning:
            self.blit_centered(
                panel,
                render_outlined(
                    self.config.fonts.tiny,
                    "! scores are not being saved to disk",
                    WARNING,
                ),
                y,
            )

        self.config.screen.blit(panel, self.panel_position(height))

    def panel_position(self, height: int) -> tuple:
        window = self.config.window
        game_over = self.config.images.game_over
        top = window.height * 0.2 + game_over.get_height() + 14
        # keep the panel clear of the floor even if the table grows
        top = min(top, window.viewport_height - height - 8)
        return ((window.width - PANEL_WIDTH) / 2, top)

    def header_label(self) -> pygame.Surface:
        rank = self.config.high_scores.last_rank
        if rank == 1:
            text, color = "NEW BEST SCORE!", HIGHLIGHT
        elif rank:
            text, color = f"NEW TOP {rank} SCORE!", HIGHLIGHT
        else:
            text, color = "HIGH SCORES", HEADER
        return render_outlined(self.config.fonts.small, text, color)

    def draw_row(self, panel, entry, index: int, y: int) -> None:
        if entry is None:
            self.blit_centered(
                panel,
                render_outlined(
                    self.config.fonts.small, "no scores yet", RANK
                ),
                y,
            )
            return

        is_new = index == self.config.high_scores.last_rank
        score_color = HIGHLIGHT if is_new else SCORE
        row_color = HIGHLIGHT if is_new else RANK

        # the marker sits outside the rank column so ranks stay aligned
        if is_new:
            panel.blit(
                render_outlined(self.config.fonts.small, ">", HIGHLIGHT),
                (PADDING - 6, y + 2),
            )

        rank = render_outlined(
            self.config.fonts.small, f"{index}.", row_color
        )
        score = render_outlined(
            self.config.fonts.medium, str(entry["score"]), score_color
        )
        date = render_outlined(
            self.config.fonts.tiny,
            entry["date"] or "-",
            HIGHLIGHT if is_new else DATE,
        )

        panel.blit(rank, (PADDING + 6, y + 2))
        panel.blit(score, (PADDING + 36, y - 2))
        panel.blit(
            date, (PANEL_WIDTH - PADDING - date.get_width(), y + 3)
        )

    def blit_centered(self, panel, surface: pygame.Surface, y: int) -> None:
        panel.blit(surface, ((PANEL_WIDTH - surface.get_width()) / 2, y))

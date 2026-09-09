"""Persistent top-N high score table backed by a small JSON file.

The game must never crash because of the score file, so every failure mode
(missing file, corrupted JSON, unreadable/unwritable path, hand-edited
content) degrades to an in-memory table plus a message in ``self.error``.
"""

import json
import os
import tempfile
from datetime import date
from typing import Any, Dict, List, Optional

HighScoreEntry = Dict[str, Any]

DEFAULT_PATH = "highscore.json"
TOP_N = 5


class HighScores:
    """Keeps the best ``limit`` scores ever played, newest run highlighted."""

    def __init__(self, path: str = DEFAULT_PATH, limit: int = TOP_N) -> None:
        self.path = path
        self.limit = max(1, limit)
        # set when the file cannot be written, so we stop retrying every run
        self.read_only = False
        self.error: Optional[str] = None
        self.last_rank: Optional[int] = None
        self.entries: List[HighScoreEntry] = self.load()

    # ------------------------------------------------------------------
    # reading
    # ------------------------------------------------------------------
    def load(self) -> List[HighScoreEntry]:
        """Loads and sanitizes the table, returning [] when unavailable."""
        return self.sanitize(self.read_raw())

    def read_raw(self) -> Any:
        try:
            with open(self.path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            # first run: nothing has been saved yet, not an error
            return []
        except json.JSONDecodeError:
            self.error = "high score file was corrupted, table was reset"
            self.backup_corrupted_file()
            return []
        except (OSError, UnicodeDecodeError) as exc:
            # unreadable almost always means unwritable too, and blindly
            # overwriting a file we could not read would destroy scores
            self.read_only = True
            self.error = f"could not read high scores: {exc}"
            return []

    def backup_corrupted_file(self) -> None:
        """Moves a broken file aside so it stops failing on every launch."""
        try:
            os.replace(self.path, f"{self.path}.corrupted")
        except OSError:
            # nothing we can do about it, the table just starts empty
            self.read_only = True

    def sanitize(self, raw: Any) -> List[HighScoreEntry]:
        """Coerces arbitrary file content into a sorted, trimmed table."""
        if not isinstance(raw, list):
            self.error = self.error or "high score file had an unexpected shape"
            return []

        entries = []
        for item in raw:
            entry = self.as_entry(item)
            if entry:
                entries.append(entry)

        entries.sort(key=self.sort_key)
        return entries[: self.limit]

    @staticmethod
    def sort_key(entry: HighScoreEntry) -> Any:
        """Best score first, oldest first among equal scores.

        The sort is stable, so a freshly appended entry stays behind the
        runs it merely tied with.
        """
        return (-entry["score"], entry["date"])

    @staticmethod
    def as_entry(item: Any) -> Optional[HighScoreEntry]:
        """Accepts {"score": n, "date": s} rows and bare numbers alike."""
        if isinstance(item, dict):
            score, when = item.get("score"), item.get("date")
        else:
            score, when = item, None

        if isinstance(score, bool) or not isinstance(score, (int, float)):
            return None
        score = int(score)
        if score <= 0:
            return None

        return {"score": score, "date": when if isinstance(when, str) else ""}

    # ------------------------------------------------------------------
    # writing
    # ------------------------------------------------------------------
    def submit(self, score: int) -> Optional[int]:
        """Records ``score`` and returns its 1-based rank, or None if it
        did not make the table."""
        self.last_rank = None
        entry = self.as_entry(score)
        if not entry or not self.qualifies(entry["score"]):
            return None

        entry["date"] = date.today().isoformat()
        # self.entries is already sanitized and entry came from as_entry,
        # so merge them directly: re-sanitizing would replace entry with an
        # equal copy and lose the identity the rank is looked up by
        merged = self.entries + [entry]
        merged.sort(key=self.sort_key)
        self.entries = merged[: self.limit]
        # by identity, not equality: list.index() matches dicts by value, so
        # a run that tied an existing score reported that run's rank and
        # highlighted its row instead of its own
        self.last_rank = next(
            (
                index
                for index, other in enumerate(self.entries, start=1)
                if other is entry
            ),
            None,
        )
        self.save()
        return self.last_rank

    def qualifies(self, score: int) -> bool:
        if len(self.entries) < self.limit:
            return True
        return score > self.entries[-1]["score"]

    def save(self) -> bool:
        """Atomically rewrites the file; returns False when it is not
        writable (the in-memory table keeps working either way)."""
        if self.read_only:
            return False

        payload = json.dumps(self.entries, indent=2)
        folder = os.path.dirname(os.path.abspath(self.path))
        try:
            handle, tmp_path = tempfile.mkstemp(
                dir=folder, prefix=".highscore-", suffix=".tmp"
            )
            try:
                with os.fdopen(handle, "w", encoding="utf-8") as file:
                    file.write(payload)
                os.replace(tmp_path, self.path)
            except BaseException:
                self.remove_quietly(tmp_path)
                raise
        except OSError as exc:
            self.read_only = True
            self.error = f"could not save high scores: {exc}"
            return False

        self.error = None
        return True

    @staticmethod
    def remove_quietly(path: str) -> None:
        try:
            os.remove(path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def begin_round(self) -> None:
        """Clears the highlight of the previous run."""
        self.last_rank = None

    @property
    def top(self) -> List[HighScoreEntry]:
        return list(self.entries)

    @property
    def best(self) -> int:
        return self.entries[0]["score"] if self.entries else 0

    @property
    def is_empty(self) -> bool:
        return not self.entries

# Refactoring report — FlapPyBird

## Scope

### What was reviewed

The whole of `src/` (24 modules, ~1300 SLOC) at commit `b2d5ba0`
*"2 new features added - top 5 score and hardening level system"*, with
particular attention to the code that commit introduced.

The two features under review are:

1. **Top-5 high-score table** — `src/utils/highscore.py` (load / sanitize /
   submit / atomic save of a JSON table) and `src/entities/high_scores_board.py`
   (the on-screen panel drawn on the game-over screen and, in compact form, on
   the splash screen).
2. **Progressive difficulty ("hardening") system** — `src/utils/difficulty.py`
   (six levels, pipe-gap / speed ramp), `src/entities/difficulty_hud.py` (the
   level gauge and the level-up flash), `src/entities/wind.py` (speed streaks),
   and the per-level pipe recolouring in `src/utils/images.py`.

The work was done in three passes: **analyse** (baseline metrics + a prioritised
findings list), **refactor** (eight authorised findings), **verify** (this
document — every metric re-measured independently).

### Constraint

The refactor was run as a **behaviour-preserving** change, with one explicitly
authorised exception (the duplicate-score rank bug, change C1 below). Everything
that would visibly alter gameplay was deferred; see *Known issues* at the end.

### Tools and versions

| | |
|---|---|
| OS / Python | Windows 11, CPython 3.11.9 |
| Game runtime | pygame 2.4.0 (SDL 2.26.4) |
| Complexity / MI / raw | radon 6.0.1 |
| Static analysis | pylint 4.0.8, flake8 7.3.0 |
| Formatting | black 26.x, isort 9.0.1 |
| Tests / coverage | pytest 9.1.1 + pytest-cov |

### Reproducing the measurements

Run from the project root. `$SCRATCH` is the harness directory. Headless pygame
needs `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`.

```bash
python -m pip install radon pylint flake8 black isort

# static metrics
python -m radon cc src -s -a          # every block + average
python -m radon cc src -s -n C        # blocks ranked C or worse
python -m radon mi src -s
python -m radon raw src -s
python -m pylint src --max-line-length=100
python -m pylint src --disable=all --enable=duplicate-code
python -m pylint src --disable=all --enable=duplicate-code --min-similarity-lines=3
python -m flake8 src
python -m flake8 .
python -m black --check --target-version=py311 src
python -m isort --check-only --diff src

# tests + coverage
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest -q

# runtime: 6000 real frames of Flappy.start() driven by a deterministic
# autopilot (random.seed(20240909), config.fps = 10**7 so the clock never
# throttles), 3 runs per invocation, median reported
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=. python "$SCRATCH/bench.py"

# targeted per-frame costs (level-up spawn, game-over board, HUD flash)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=. python "$SCRATCH/micro.py"

# safety nets
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=. python "$SCRATCH/smoke.py"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=. OUT=<dir> python "$SCRATCH/render.py"
```

**Benchmark methodology note.** The runtime numbers below were *not* taken by
comparing an old session's log with a new one. An unrelated control in the same
harness — a bare `pygame.Surface((288,512), SRCALPHA)` allocation, which no
change touches — measured 30 µs during the baseline pass and ~450 µs during the
verification pass, i.e. the host machine was in a materially different state.
Cross-session numbers are therefore worthless. Instead the pre-refactor source
was reconstructed (`git archive HEAD src`) into a separate tree and **both trees
were benchmarked back-to-back in the same session**, 9 samples each. All
before/after runtime figures in this document come from that paired run.

---

## Metrics: before vs after

### Cyclomatic complexity (`radon cc`)

| Metric | Before | After | Delta |
|---|---|---|---|
| Blocks analysed | 135 | 142 | +7 |
| Average complexity | **A (2.34)** | **A (2.32)** | −0.02 |
| Blocks ranked C or worse | 0 | 0 | — |
| Blocks ranked B | 7 | 8 | +1 |
| Worst block | `Flappy.play` B (8) | `Flappy.play` B (8) | unchanged |

B-ranked blocks after the refactor:

| Block | Rank | Before |
|---|---|---|
| `Flappy.play` (`src/flappy.py:106`) | B (8) | B (8) |
| `Entity.__init__` (`src/entities/entity.py:9`) | B (8) | B (8) |
| `pixel_collision` (`src/utils/utils.py:43`) | B (7) | B (7) |
| `HighScoresBoard.draw_row` (`src/entities/high_scores_board.py:139`) | B (7) | B (7) |
| `Player.collided` (`src/entities/player.py:147`) | B (6) | B (6) |
| `HighScores.as_entry` (`src/utils/highscore.py:90`) | B (6) | B (6) |
| `render_outlined` (`src/utils/fonts.py:34`) | B (6) | B (6) |
| `Pipes.remove_old_pipes` (`src/entities/pipe.py:69`) | **B (6)** | A — *regressed* |

`Score.rect` went the other way, CC 5 → CC 3, after the digit logic was
extracted.

### Maintainability index (`radon mi`)

Every module ranked A both before and after. The modules that moved:

| Module | Before | After | Delta |
|---|---|---|---|
| `src/utils/fonts.py` | 60.52 | **77.01** | +16.49 |
| `src/entities/score.py` | 52.29 | **71.94** | +19.65 |
| `src/entities/high_scores_board.py` | 54.22 | 52.47 | **−1.75** |
| `src/entities/difficulty_hud.py` | 58.59 | 63.76 | +5.17 |
| `src/entities/entity.py` | 50.31 | 55.30 | +4.99 |
| `src/entities/pipe.py` | 50.32 | 55.05 | +4.73 |
| `src/utils/highscore.py` | 56.97 | 58.17 | +1.20 |
| `src/utils/images.py` | (not in bottom 10) | 77.22 | — |
| `src/flappy.py` | 42.21 | 42.21 | 0 (untouched) |
| `src/entities/player.py` | 50.31 | 50.31 | 0 (untouched) |
| `src/utils/difficulty.py` | 62.15 | 62.15 | 0 (untouched) |

`flappy.py` remains the worst module in the project at 42.21; it was out of
scope.

### Raw size and comment ratio (`radon raw`, totals)

| Metric | Before | After | Delta |
|---|---|---|---|
| LOC | 1662 | 1795 | +133 (+8.0 %) |
| LLOC | 1019 | 1068 | +49 (+4.8 %) |
| SLOC | 1264 | 1321 | +57 (+4.5 %) |
| Comments | 82 | 105 | +23 |
| Single comments | 81 | 105 | +24 |
| Multi (docstrings) | 39 | 72 | +33 |
| Comment ratio (C % L) | 5 % | **6 %** | +1 pt |
| Comment + docstring ratio (C+M % L) | 7 % | **10 %** | +3 pt |

The code grew. That is the price of the caches: every cache needs a key, a
store, a lookup and a documented invalidation rule.

### pylint

| Metric | Before | After | Delta |
|---|---|---|---|
| Score | 7.52 / 10 | **7.61 / 10** | +0.09 |
| Total messages | 171 | 171 | 0 |
| `duplicate-code` (R0801), default threshold | 0 | 0 | — |
| `duplicate-code`, `--min-similarity-lines=3` | 0 | 0 | — |

The message histogram is byte-identical before and after: 60
`missing-function-docstring`, 43 `attribute-defined-outside-init`, 20
`missing-module-docstring`, 18 `missing-class-docstring`, 10 `no-member`\*, 5
`too-many-instance-attributes`, 5 `no-name-in-module`\*, 4
`too-few-public-methods`, 2 `too-many-positional-arguments`, 2
`too-many-arguments`, 1 `consider-using-in`, 1 `arguments-differ`.

\* 15 of the 171 are pygame C-extension false positives.

The score moved only because the denominator (statement count) grew; **no pylint
finding was fixed**. The docstring / attribute-declaration cleanup that would
push this past 9/10 was not in the authorised scope.

### flake8, black, isort

| Check | Before | After |
|---|---|---|
| `flake8 src` (repo `.flake8`) | 0 violations | 0 violations |
| `flake8 .` | 0 violations | 0 violations |
| `black --check --target-version=py311 src` | **2 files would be reformatted** (`high_scores_board.py`, `wind.py`) | **0** — 24 files unchanged |
| `isort --check-only src` | **1 file unsorted** (`src/utils/__init__.py:7`) | **0** |

### Tests and coverage

| Metric | Before | After | Delta |
|---|---|---|---|
| Tests | 26 passed (12 functions) | **26 passed** | 0 |
| In-process time (median of 3) | 2.41 s | 2.14 s | −0.27 s |
| Wall clock incl. interpreter start (median of 3) | 6.52 s | 5.88 s | −0.64 s |
| Coverage TOTAL | **52 %** | **52 %** | 0 |
| Statements / missed | 951 / 459 | 990 / 479 | +39 / +20 |

Notable per-module coverage: `flappy.py` 0 % → 0 %, `player.py` 21 % → 21 %,
`difficulty_hud.py` 24 % → 27 %, `high_scores_board.py` 30 % → 29 %,
`score.py` 34 % → 42 %, `fonts.py` 37 % → 43 %, `entity.py` → 63 %,
`pipe.py` 91 % → 91 %, `highscore.py` 96 % → 97 %, `difficulty.py` 98 % → 98 %.

No test was added, removed or modified.

### Runtime benchmark — full game loop

6000 real frames, deterministic autopilot, both trees measured back-to-back in
one session (3 invocations × 3 runs = 9 samples each).

| Metric | Before | After | Delta |
|---|---|---|---|
| Median wall time | **5.750 s** | **3.758 s** | −1.99 s |
| Median throughput | **1043.5 fps** | **1596.6 fps** | **+53.0 %** |
| Sample range | 5.381 – 7.003 s | 3.324 – 4.272 s | — |
| Within-tree spread | ±14 % | ±13 % | — |

**Is it noise?** No. Run-to-run variance is large (±13–14 %), but the two
distributions do not overlap at all: the *slowest* post-refactor sample
(4.272 s) is faster than the *fastest* baseline sample (5.381 s). A 1.53×
speedup is comfortably outside that noise band.

For the record, and *not* comparable: the step-1 log reported a baseline median
of 5.366 s and the step-2 log reported 5.290 s → 4.824 s (+9.7 %). Those two
sessions ran on a differently-loaded host — see the methodology note above. The
paired measurement supersedes them.

### Runtime benchmark — targeted frames

These are the frames the refactor actually aimed at: the worst-case single
frames, not the average. Same paired-session methodology.

| Frame | Before | After | Delta |
|---|---|---|---|
| **Level-up hitch** — spawning the first pipe pair of a new level (recolour 2 sprites + build 2 hit masks), worst of 6 levels | **43.18 ms** | **0.031 ms** | **1390× faster** |
| Level-up hitch, median across the 6 levels | 28.19 ms | 0.005 ms | 5600× faster |
| **Game-over board frame** — full 5-row high-scores panel (median of 200 frames) | **790.2 µs** | **71.2 µs** | **11.1× faster** |
| **HUD frame during a level-up flash** (median of 480 frames) | **1330.7 µs** | **493.2 µs** | **2.7× faster** |

Context: at 30 fps the frame budget is 33.3 ms. The level-up hitch was
**exceeding a whole frame budget** — a visible stutter at exactly the moment the
level-up banner plays. That is the single most valuable fix in this refactor,
and it is invisible in the averaged fps number.

### Supporting micro-benchmarks (unchanged operations, for context)

| Operation | Before | After |
|---|---|---|
| `get_hit_mask` uncached build, 52×320 sprite | 9527 µs | 9703–12881 µs (unchanged code; host noise) |
| `pygame.mask.from_surface` 52×320 (the C alternative, not adopted) | 201 µs | 200–238 µs |
| `pixel_collision`, full 34×24 scan, no hit | 86.0 µs | 85.9–122.7 µs (unchanged code) |
| `render_outlined("LV 3  GUSTY")` | 66.28 µs | **0.29–0.55 µs** (now a cache hit — see the caveat) |

*Caveat:* the `render_outlined` row is not an apples-to-apples comparison. After
the change, calling it repeatedly with the same arguments measures a
`functools.lru_cache` dict lookup, not a render. A genuine cache **miss** still
costs ~66 µs. What improved is the number of misses per frame, not the cost of a
render.

---

## Changes made

Eight findings were authorised and implemented. No test was touched; no file
outside `src/` was modified by the refactor.

### Performance

#### P1 — Memoise `render_outlined`

**What / where.** `src/utils/fonts.py:3` (import `functools.lru_cache`), `:14`
(`OUTLINE_CACHE_SIZE = 256`), `:34` (`@lru_cache` on `render_outlined`),
docstring `:41-52`.

**Why it mattered.** `render_outlined` performs 2 `font.render` calls and 9 blits
into a fresh `SRCALPHA` surface — 66.3 µs, versus 4.9 µs for a plain
`font.render`. Profiling attributed **69 % of all blits in the game loop and
17 % of total runtime** to it, and none of the strings change between frames: the
gauge label only changes on a level-up, and the entire high-scores panel is
static for the whole game-over screen (17 calls × 66 µs = 1.12 ms per frame of
pure re-rasterisation).

**Invalidation.** There is nothing to invalidate. The output is a pure function
of `(font, text, color, outline, width)`; the four `Fonts` objects are immutable
singletons created once in `Fonts.__init__`. The 256-entry bound only guards
against a pathological string set — the game draws on the order of 130 distinct
strings.

**Hazard, and how it is closed.** The returned surface is now *shared*. A caller
that mutates it (e.g. `set_alpha`) would corrupt every other user. The one such
caller, the level-up banner, was changed to work on copies (P3), and the hazard
is stated in the function's docstring.

**Measured effect.** Cache hit 0.29–0.55 µs vs 66.28 µs for a render.
Underpins the board and HUD wins below.

#### P2 — Pre-warm the per-level pipe-colour cache

**What / where.** `src/utils/images.py:7-8` (imports), `:70` (call at the end of
`randomize()`), `:72-84` (`Images.warm_pipe_colors`).

**Why it mattered.** The "hardening" feature recolours the pipe sprites per
level. The first pipe pair of a new level therefore paid, inside one frame,
2 × `colorize_surface` (~1.2 ms each) **plus** 2 × `get_hit_mask` (9.5 ms each —
the real cost, a pure-Python double loop calling `Surface.get_at()` 16 640
times). Measured at **23–43 ms in a single frame**, against a 33.3 ms budget, at
exactly the moment the level-up flash animation plays.

`warm_pipe_colors` builds the recoloured pair *and touches its hit mask* for
every entry in `LEVELS` up front.

**Invalidation.** It is invoked from the end of `randomize()`, the only place
that clears `colored_pipes`. "Cache cleared" and "cache re-warmed" are literally
the same statement, so they cannot drift apart.

**Cost.** ~130 ms moved into process start-up. `difficulty.py` stays pygame-free:
the new dependency points from `images` (pygame) to `difficulty` (pure), not
back.

**Measured effect.** Level-up spawn frame **43.18 ms → 0.031 ms** worst case.

#### P3 — Cache the high-scores panel and the HUD surfaces

**What / where.**
- Panel: `src/entities/high_scores_board.py:37-38` (`panel_cache`,
  `panel_cache_key`), `:68-75` (`panel_key()`), `:77-84` (`draw_panel` is now a
  key check plus one blit), `:86-119` (the old body renamed `build_panel`).
- HUD: `src/entities/difficulty_hud.py:9-10` (`BAR_RADIUS`, `TRACK_COLOR`),
  `:28-45` (`self.track`, `self.tint`, `banner_level`, `banner_lines` in
  `__init__`), `:70` (blit the hoisted track), `:91-110` (`banner()`),
  `:118-119` (re-`fill()` the hoisted tint).

**Why it mattered.** Every game-over frame allocated a 200×140 `SRCALPHA`
surface, drew two rounded rects and issued 17 `render_outlined` calls plus ~34
blits, to produce pixels that only change once per game over. The HUD allocated
a fresh 96×6 track surface every frame and a fresh full-screen 288×512
`SRCALPHA` tint on each of the level-up flash's 26 frames.

**Invalidation.** `panel_key()` returns everything the pixels depend on —
`((score, date) for each row), last_rank, error` — by value, not by list
identity, so in-place mutation of `entries` still invalidates correctly. The
banner is keyed on `shown_level`, the sole input to both its strings and its
colour. The tint is re-`fill()`ed rather than reallocated; `Surface.fill`
overwrites rather than blends, so the result is identical to filling a fresh
transparent surface.

**Deliberately not cached:** the gauge label and the `x1.23` readout. P1 already
reduces those to dict lookups; a second cache layer there would be invalidation
state that buys nothing.

**Measured effect.** Game-over board frame **790.2 µs → 71.2 µs** (11.1×);
HUD flash frame **1330.7 µs → 493.2 µs** (2.7×).

#### P4 — Stop computing `rect` when the debug overlay is off; de-duplicate the digit logic

**What / where.** `src/entities/entity.py:62-65` — `rect = self.rect` moved
inside the `if self.config.debug:` branch. `src/entities/score.py:22-30`
(`digit_images()`), `:32-35` (`digits_origin()`), `:37-43` (`rect`), `:45-52`
(`draw`).

**Why it mattered.** `Entity.rect` is a property that allocates a new
`pygame.Rect` on every access; profiling counted **24.7 allocations per frame**
made purely to be discarded. Worse, `Score` overrides `rect` with a version that
re-derives the digit list, looks up 2+ sprite surfaces and runs `sum`/`max` over
them — so the most expensive rect in the game was computed once per frame for
nothing. Separately, `Score.rect` and `Score.draw` derived the same
digit→sprite→width list independently.

**Measured effect.** Not isolated on its own; contributes to the 53 % game-loop
speedup. `Score.rect` complexity dropped from CC 5 to CC 3 and `score.py` MI rose
52.29 → 71.94.

### Correctness

#### C1 — `HighScores.submit()` reported the wrong rank for a tied score

**What / where.** `src/utils/highscore.py:80-87` (new `sort_key` static method,
shared with `sanitize` at `:77`), `:116-133` (the merge in `submit`).

**Why it mattered.** The old code did
`self.entries = self.sanitize(self.entries + [entry])` then
`self.last_rank = self.entries.index(entry) + 1`. `list.index` compares dicts
**by value**, and two runs that score the same on the same day produce equal
dicts — so a run that merely *tied* an existing score received that run's rank.
Verified before: three consecutive `submit(30)` calls returned `1, 1, 1`. The
consequence is user-visible: the board highlighted the wrong row
(`high_scores_board.py:125`, `is_new = index == last_rank`) and `header_label()`
announced "NEW BEST SCORE!" for a tie. No test covered ties.

`submit` now merges directly — `self.entries` is already sanitized and `entry`
already came from `as_entry`, so re-sanitizing was redundant, and re-sanitizing
was precisely what destroyed the object identity — and looks the rank up with
`is`.

**This is the one authorised behaviour change in the refactor.** The sort remains
a stable `sorted` on `(-score, date)`, so a tied newcomer still lands *behind*
the run it tied with; the displayed ordering is unchanged, only the reported rank
is fixed.

**Measured effect.** Three consecutive `submit(30)` calls now return `1, 2, 3`.
All 26 existing tests submit distinct scores, so none of them changed behaviour.

#### C2 — `remove_old_pipes()` mutated the list it was iterating

**What / where.** `src/entities/pipe.py:69-84`.

**Why it mattered.** `for pipe in self.upper: ... self.upper.remove(pipe)` skips
the element after each removal. Verified before: 4 consecutively off-screen
pipes, one pass, **2 left behind**. It was latent because spawn spacing normally
retires one pair per frame — but if `upper` and `lower` ever dropped different
counts they would desync, and `Pipes.tick()` uses `zip(self.upper, self.lower)`,
which **silently stops ticking and drawing the surplus** while
`Player.collided()` still iterates both lists in full. The failure mode is an
invisible, frozen pipe that still kills the player.

Both lists are now rebuilt from one shared list of kept indices, so the pairing
cannot desync. The function early-returns when nothing is dropped, so the common
frame allocates nothing.

**Measured effect.** Verified after: 4 off-screen pipes + 1 live pair → 1 and 1.
Cost: `remove_old_pipes` went from CC A to **CC B (6)** — see the honest analysis
below.

#### C3 — Unreachable guard in `can_spawn_pipes()`

**What / where.** `src/entities/pipe.py:56-61`.

The old code read `last = self.upper[-1]` and *then* `if not last: return True`.
A `Pipe` object is always truthy, so the guard could never fire — and the empty
-list case it was evidently meant to protect against already raised `IndexError`
on the line above. Replaced with `if not self.upper: return True`.

**Measured effect.** None on runtime; removes dead code and a latent
`IndexError`.

#### C4 — `GameConfig.debug` treated any non-empty `DEBUG` value as true

**What / where.** `src/utils/game_config.py:12-14` (`DEBUG_ON` frozenset), `:39`.

`os.environ.get("DEBUG", False)` meant `DEBUG=0` and `DEBUG=false` both *enabled*
the debug overlay, and the attribute held a `str` under a boolean name. Now
`DEBUG` ∈ {`1`, `true`, `yes`, `on`}, case- and whitespace-insensitive, and the
attribute is a real `bool`.

**Measured effect.** Verified: `DEBUG=0` → `False`, `DEBUG=true` → `True`.

### Maintainability

#### M1 — Formatting and import-order conformance

**What / where.** `python -m isort --profile black src` fixed
`src/utils/__init__.py:7`. `python -m black --line-length 80 src` reformatted
`difficulty_hud.py`, `score.py`, `pipe.py`, `images.py`, `high_scores_board.py`
and `wind.py`.

**Why it mattered.** `high_scores_board.py` and `wind.py` were both introduced by
the feature commit and were not black-clean, which means the repo's own
`.pre-commit-config.yaml` was not run before committing.

**Measured effect.** `black --check`: 2 files → **0**. `isort --check-only`:
1 file → **0**. `flake8 .` stays at 0. No behaviour change.

#### M2 — Duplicate digit logic extracted (see P4)

`Score.rect` and `Score.draw` now share `digit_images()` / `digits_origin()`
instead of independently re-deriving the same list. `score.py` MI 52.29 → 71.94.

---

## Effect on code quality

An honest read of the table above: **the static-analysis metrics barely moved,
and the runtime metrics moved a lot.** That is the accurate summary, and it is
worth explaining why rather than dressing it up.

**Cyclomatic complexity had almost nothing to win.** The average was already
grade A (2.34) with **zero** blocks ranked C or worse — this is a small,
well-decomposed codebase with short methods. An average of 2.32 after is not an
improvement, it is the same number. Nothing in the authorised scope targeted the
one genuine complexity problem, `Flappy.play` at B(8) in the project's
worst-MI module, so it sits at B(8) still. The complexity metric is simply not
where this codebase's problems were.

**Complexity actually regressed in one place, and that was the right trade.**
`Pipes.remove_old_pipes` went A → B(6). The paired-index rebuild is more
branching code than the naive in-place `remove()` loop — but the naive loop was
*wrong*, and its failure mode (a desynced pipe list producing an invisible pipe
that still kills the player) is far worse than a CC of 6. A metric that rewards
the buggy version is a metric being applied badly.

**Maintainability index rose where code was consolidated and fell where state was
added.** `score.py` (+19.7) and `fonts.py` (+16.5) improved because duplication
was removed. `high_scores_board.py` **dropped 1.75 points** — the only module to
get worse — because caching the panel meant adding two instance attributes, a
key-builder method, and a branch that did not exist before. That is the honest
shape of the trade.

**Caching bought speed with state, and the state is real.** Before the refactor,
`draw()` on the board and the HUD were stateless functions of the world: read the
data, draw the pixels. Afterwards there are four caches (`render_outlined`'s
`lru_cache`, the panel surface, the HUD banner, the pre-warmed pipe colours) and
three of them need a correct invalidation rule. Each rule is documented at its
site and each is keyed on all of its inputs — or on nothing, because its inputs
are provably immutable — but "provably immutable" is a property of today's code,
not a guarantee. Sharing memoised surfaces introduced a specific new hazard: a
caller that mutates a returned surface (`set_alpha`, `fill`) now corrupts every
other user of that string. That hazard is closed for the one existing mutator and
documented in the docstring, but it is a footgun that did not exist before. The
codebase is now measurably faster and marginally harder to reason about. For a
game that was blowing a 33 ms frame budget at every level-up, that is a good
trade — but it *is* a trade.

**pylint did not improve, and the +0.09 is an artefact.** The score moved from
7.52 to 7.61 purely because the statement count grew while the message count
stayed at exactly 171 with an identical histogram. Not one pylint finding was
fixed. The 141 docstring and attribute-declaration messages that dominate the
score were out of scope; addressing them would plausibly reach 9+/10, but that is
future work, not something this refactor achieved.

**Formatting conformance is the one static check that genuinely went green.**
Two files that the feature commit left un-black-formatted and one unsorted import
block are now clean, so the repo's pre-commit config will pass. Small, but it was
a real regression introduced by the feature work.

**Code got bigger, not smaller.** +133 LOC, +57 SLOC. Caches, keys and their
documentation are net additions. The comment-and-docstring ratio rose 7 % → 10 %,
which partly reflects the invalidation rules being written down — that is the
right place for that growth, but the codebase is not leaner.

### What the safety nets actually prove — and what they do not

Two gates protected the "no behaviour change" claim.

**The pixel-identical screenshot check (15/15 PNGs byte-identical, SHA-256).**
This is the strong one, and it was independently re-run for this report, not
taken on trust. What it proves: for the 15 specific rendered states it covers —
every one of the six difficulty levels in steady state, five level-up flash
frames, the game-over board in its populated / empty / save-error variants, and
the splash screen with a best score — the refactored renderer produces literally
identical output, down to the byte. Given that most of the refactor is caching
inside drawing code, this is close to the ideal test for it.

What it does not prove: it is 15 frames out of a game that renders thousands, all
captured from a scripted harness that reconstructs the world directly rather than
playing the game. It says nothing about *timing*-dependent state, about frames
between the captured ones, about what happens when a cache key collides after
several rounds in one session, or about the cache-invalidation paths that the
harness never triggers (it never plays a second round, so it never re-runs
`randomize()`). Determinism was itself established first, by rendering the
baseline twice and confirming zero diffs — without that, byte-identity would have
proved nothing at all.

**The test suite (26 passed, coverage 52 %, unchanged).** What it proves: the
pure logic is intact — `highscore.py` at 97 % and `difficulty.py` at 98 % are
genuinely well covered, and those are where the two features' rules live.

What it does not prove, and this is the important part: **`src/flappy.py` is at
0 % coverage**, and the modules the refactor changed most are the least covered
in the project — `difficulty_hud.py` 27 %, `high_scores_board.py` 29 %,
`score.py` 42 %, `fonts.py` 43 %. The suite would not have caught a mistake in
any of the caching work. "26 tests still pass" here means "the parts that were
already tested are unaffected", not "the change is correct". The real safety net
for this refactor was the screenshot check plus the `smoke.py` end-to-end run
(which drives the actual game loop to level 4 with no exceptions and writes a
correct 5-row table) — and neither of those is a test in the repository, so
neither will run in CI. That is a gap this refactor did not close.

### Verification of the prior pass's claims

Every claim from the refactor log was re-checked independently. Three did not
survive as stated:

| Claim | Verdict |
|---|---|
| 15/15 PNGs byte-identical | Confirmed by independent re-render |
| 26 tests pass, coverage 52 % unchanged | Confirmed |
| `smoke.py` runs clean | Confirmed |
| black / isort / flake8 clean | Confirmed |
| Level-up hitch ~21 ms → 0.03 ms | Confirmed (measured 28 ms median, 43 ms worst → 0.005 / 0.031 ms) |
| Game-over board frame → 76.5 µs | Confirmed on the "after" side (71.2 µs). The quoted "before" of 1.15 ms was an arithmetic estimate; measured baseline is 790 µs, so the true ratio is **11×, not 15×** |
| Runtime **+9.7 %** (5.290 → 4.824 s) | **Understated.** Same-session paired A/B gives 5.750 → 3.758 s, **+53 %**. The original figure compared two differently-loaded sessions |
| HUD flash frame → **23.8 µs** | **Not reproducible.** A complete level-up-flash frame measures **493 µs**, twenty times that. The 23.8 µs figure appears to cover only the parts that changed (track blit + banner lookup), excluding the full-screen tint blit and gauge fill that dominate the frame. The improvement is real — 1331 µs → 493 µs, 2.7× — but an order of magnitude smaller than stated |

---

## Known issues and deliberately deferred work

Everything below was identified during the analysis pass and consciously left
alone. None of it is fixed in this refactor.

| # | Issue | Where | Why deferred | Cost / risk of fixing |
|---|---|---|---|---|
| 1 | **Hit masks are pure-Python `List[List[bool]]`**; `pygame.mask.Mask` + `Mask.overlap()` is the idiomatic answer — 201 µs to build vs 9.5 ms, and a C-speed overlap test vs up to 86 µs | `src/utils/utils.py:27-62`, `src/entities/entity.py:31,38,54-59` | `pygame.mask.from_surface` thresholds alpha at 127, whereas `get_hit_mask` tests `alpha != 0`. Semi-transparent sprite edges would collide differently — the hitbox shifts by a pixel or two and the game *feels* different. Incompatible with a "no behaviour change" refactor | Medium/high. Changes the public shape of `get_hit_mask`/`pixel_collision`, which `src/utils/__init__.py` exports. Needs its own change with its own collision tests. Pre-warming the cache (P2) captured the win that mattered at zero semantic risk |
| 2 | **`Entity` builds its hit mask from the *unscaled* image** — when `w`/`h` are given, `self.image` is scaled but line 31 calls `get_hit_mask(image)` on the original. Verified: asking for 100×50 from a 10×10 sprite yields a 10×10 mask on a 100×50 image | `src/entities/entity.py:22-31` | Latent: only `Background` uses the scaling path and it never collides | Trivial one-liner (`get_hit_mask(self.image)`), but it changes collision geometry for any future scaled entity, so it belongs with a collision test — and it would invalidate the pixel-identity gate |
| 3 | **`Player.update_image()` does not refresh `self.hit_mask`** — the bird's collision mask stays that of `player[0]` while the sprite cycles through 3 frames. It also shadows the never-called `Entity.update_image` with an incompatible signature (pylint `W0221`) | `src/entities/player.py:81-87` vs `src/entities/entity.py:34-40` | Harmless today (the three wing frames have near-identical alpha), but it is why the override exists at all | Low cost, but refreshing the mask *changes the hitbox mid-flap* — a real gameplay change. The safe part (deleting the dead `Entity.update_image`, renaming the Player one to `advance_animation()`) was simply not in the authorised list |
| 4 | **`Images.randomize()` runs once per process, not once per game** — the bird, background and pipe sprite are fixed for every round played in one session | `src/utils/images.py:43-46` | Identical in upstream FlapPyBird, so plausibly intentional | One line to call it from `Flappy.start()`, but visibly alters the game every round, and would clear (and force a re-warm of) the pipe-colour cache each round |
| 5 | **Undated legacy entries outrank dated ones at the same score** — `as_entry` defaults a missing date to `""`, which sorts before every real ISO date | `src/utils/highscore.py:77,94` | Changes the order the player sees; `tests/test_high_scores.py:94` would need revisiting | Low technical cost, but it is a visible behaviour change and needs a test |
| 6 | **`pixel_collision` re-does the outer list lookup on every inner iteration** — `hitmask1[x1 + x][y1 + y]`. Hoisting the column lists is worth ~30-40 % of the 86 µs worst case | `src/utils/utils.py:43-62` | Safe and cheap, simply not in the authorised eight. Superseded in value by issue 1 | Very low; do it if issue 1 is not taken |
| 7 | **`Pipes.sync_speed()` allocates a concatenated `self.upper + self.lower` list every frame**; `Player.collided` duplicates its pipe loop twice | `src/entities/pipe.py:48`, `src/entities/player.py:156-165` | Not in the authorised list | Very low — `itertools.chain`, or fold the speed assignment into the existing `zip` in `tick()` |
| 8 | **`Window` carries 12 attributes that are 6 values under 2 names each, and 4 are entirely dead** (`r`, `vr`, `viewport_ratio`, `viewport_width` are referenced only by their own assignment). pylint `R0902` (12/7) | `src/utils/window.py:1-14` | Not authorised | Low, but `config.window.vh/vw/w/h` are used across the codebase, so the short names must survive as properties |
| 9 | **171 pylint messages, 141 of them docstring or attribute-declaration noise** — 60 missing-function-docstring, 43 attribute-defined-outside-init (11 in `Flappy.start()`, the rest in `Player.reset_vals_*`), 20 missing-module-docstring, 18 missing-class-docstring | across `src/` | Not authorised; large diff, zero behaviour change, no runtime value | Low risk, high churn. Would move the score from 7.61 to 9+. 15 of the 171 are pygame C-extension false positives that a `extension-pkg-allow-list=pygame` setting would silence honestly |
| 10 | **`Flappy.play()` is the most complex block in the project** (B(8)) and `flappy.py` has the worst MI (42.21) with a 1 % comment ratio. The three loops duplicate the event-pump / `display.update()` / `config.tick()` scaffolding, and `game_over()` calls those two in the opposite order from the other two | `src/flappy.py:106-138,167-168` | Not authorised, and `flappy.py` is at **0 % test coverage** — restructuring it with no test behind it is the riskiest thing in this list | Medium. Should be preceded by promoting `smoke.py` into a real integration test |
| 11 | **Dead code:** `Pipe.top`/`Pipe.bottom` are never read; the hand-rolled `memoize` decorator duplicates `functools.lru_cache` and its unbounded dict pins every colourised surface for the process lifetime (bounded at 12 in practice, unbounded by construction) | `src/entities/pipe.py:25-26`, `src/utils/utils.py:14-24` | Not authorised | Very low |
| 12 | **No integration test exists.** `src/flappy.py` is at 0 % coverage and the two features' visual entities are the least-covered code the features added | `src/flappy.py`, `tests/` | Adding tests was outside the refactor's remit | Low risk, real value: `smoke.py` and `render.py` already do this work as scratchpad harnesses and could be promoted into the suite, giving the caching work an actual CI safety net |
| 13 | **`HighScores` has a bare `except BaseException`** at `:134` (it cleans up the temp file and re-raises, so it is *correct*, but it reads as a smell) and 6 undocumented public methods | `src/utils/highscore.py` | Cosmetic | Very low — `try/finally` with a success flag, or `contextlib.ExitStack`, states the intent better |

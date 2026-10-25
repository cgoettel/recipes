"""The mural stripes in the header and footer, drawn fresh for every page.

Seven stripes (three in the header, four in the footer) take seven different
colors from the mural palette, so no color repeats on a page, and no two pale
colors sit next to each other in a row. The thick header stripe lands in the
middle half the time and at the top or bottom a quarter each.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

PALETTE = (
    "navy",
    "cobalt",
    "sky",
    "pale",
    "yellow",
    "coral",
    "crimson",
    "peach",
    "violet",
    "lilac",
    "plum",
)
PALE = frozenset({"sky", "pale", "yellow", "peach", "lilac"})


@dataclass(frozen=True)
class Stripe:
    color: str
    width: int  # percent
    thick: bool = False


@dataclass(frozen=True)
class Stripes:
    header: list[Stripe]
    footer: list[Stripe]


def _no_pale_neighbors(colors: list[str]) -> bool:
    # Header (0-2) and footer (3-6) are separate rows; check within each.
    rows = (colors[:3], colors[3:])
    return all(
        not (a in PALE and b in PALE) for row in rows for a, b in zip(row, row[1:], strict=False)
    )


def draw(rng: random.Random | None = None) -> Stripes:
    rng = rng or random.Random()
    colors = rng.sample(PALETTE, 7)
    for _ in range(200):
        if _no_pale_neighbors(colors):
            break
        colors = rng.sample(PALETTE, 7)
    r = rng.random()
    thick = 1 if r < 0.5 else (0 if r < 0.75 else 2)
    header = [Stripe(c, rng.randint(40, 95), thick=i == thick) for i, c in enumerate(colors[:3])]
    footer = [Stripe(c, rng.randint(8, 30)) for c in colors[3:]]
    return Stripes(header=header, footer=footer)

"""Baker's percentages: every ingredient as a share of the total flour weight.

Works from the gram weights on a recipe's ingredient lines (real weighings, or
the ≈ estimates on the bread recipes). A recipe gets the view when at least one
flour line and one liquid line have weights.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

from recipes_site import catalog
from recipes_site import ingredients as ing

# role, pattern on the item text. First match wins.
_ROLES: list[tuple[str, str]] = [
    ("flour", r"\bflour\b"),
    ("water", r"\bwater\b"),
    ("milk", r"\bbuttermilk\b|\bmilk\b"),
    ("salt", r"\bsalt\b"),
    ("yeast", r"\byeast\b"),
    ("sugar", r"\bsugar\b|\bhoney\b|\bmolasses\b"),
    ("fat", r"\bbutter\b|\boil\b|\bshortening\b|\blard\b"),
]

# Milk is about 87% water; its water counts toward hydration.
_WATER_SHARE = {"water": Fraction(1), "milk": Fraction(87, 100)}

# Typical ranges and what moving through them does. Percent of flour weight.
GUIDE: dict[str, list[tuple[float, str]]] = {
    "hydration": [
        (60, "stiff dough: bagels, pretzels, some enriched breads"),
        (65, "firm: sandwich loaves and soft rolls"),
        (75, "the classic lean range: French bread, rustic loaves"),
        (999, "slack and wet: an open, holey crumb like ciabatta; harder to shape"),
    ],
    "salt": [
        (1.5, "light: fast fermentation and a flat taste"),
        (2.3, "the usual 1.8–2.2%: flavor, and it tightens gluten and slows the yeast a little"),
        (999, "salty: slows the yeast noticeably"),
    ],
    "yeast": [
        (0.5, "very little: a long, slow rise with more flavor"),
        (1.5, "the everyday range for instant yeast: a rise in an hour or two"),
        (999, "a lot: a fast rise, often needed for sweet or enriched doughs"),
    ],
    "sugar": [
        (5, "lean: barely sweet; feeds the yeast and browns the crust"),
        (15, "enriched: soft, sandwich-bread sweetness"),
        (
            999,
            "sweet dough: sugar pulls water from the yeast and slows it, so these use more yeast",
        ),
    ],
    "fat": [
        (5, "lean: a crisper crust and chewier crumb"),
        (15, "soft: tender crumb, softer crust, keeps longer"),
        (999, "rich: brioche territory; tender and cake-like"),
    ],
}


@dataclass
class Row:
    label: str  # the ingredient line, as written
    role: str | None
    grams: Fraction
    percent: Fraction


@dataclass
class Ratio:
    key: str
    label: str
    percent: Fraction
    note: str


@dataclass
class Breakdown:
    flour: Fraction
    total: Fraction
    rows: list[Row]
    ratios: list[Ratio]
    estimated: bool


def _role(item: str) -> str | None:
    text = item.lower()
    for role, pattern in _ROLES:
        if re.search(pattern, text):
            return role
    return None


def _note(key: str, percent: Fraction) -> str:
    for upper, text in GUIDE[key]:
        if percent < upper:
            return text
    return ""


def _mid(parsed: ing.Ingredient) -> Fraction | None:
    if parsed.grams_low is None:
        return None
    if parsed.grams_high is None:
        return parsed.grams_low
    return (parsed.grams_low + parsed.grams_high) / 2


def breakdown(recipe: catalog.Recipe) -> Breakdown | None:
    lines = [item for group in recipe.ingredient_groups for item in group.items]
    weighed: list[tuple[str, str | None, Fraction, bool]] = []
    for line in lines:
        parsed = ing.parse(line)
        grams = _mid(parsed)
        if grams is None or grams == 0:
            continue
        label = re.sub(r"\s*\(.*?\)", "", parsed.item).split(",")[0].strip() or line
        weighed.append((label, _role(parsed.item), grams, parsed.grams_estimated))
    flour = sum((g for _, role, g, _ in weighed if role == "flour"), Fraction(0))
    has_liquid = any(role in _WATER_SHARE for _, role, _, _ in weighed)
    if flour == 0 or not has_liquid:
        return None
    total = sum((g for _, _, g, _ in weighed), Fraction(0))
    rows = [
        Row(label=line, role=role, grams=g, percent=g / flour * 100) for line, role, g, _ in weighed
    ]
    rows.sort(key=lambda r: (r.role != "flour", -r.grams))

    def share(role: str) -> Fraction:
        return sum((r.grams for r in rows if r.role == role), Fraction(0)) / flour * 100

    hydration = (
        sum((r.grams * _WATER_SHARE[r.role] for r in rows if r.role in _WATER_SHARE), Fraction(0))
        / flour
        * 100
    )
    ratios = [Ratio("hydration", "Hydration", hydration, _note("hydration", hydration))]
    for key, label in (("salt", "Salt"), ("yeast", "Yeast"), ("sugar", "Sugar"), ("fat", "Fat")):
        pct = share(key)
        if pct:
            ratios.append(Ratio(key, label, pct, _note(key, pct)))
    return Breakdown(
        flour=flour,
        total=total,
        rows=rows,
        ratios=ratios,
        estimated=any(est for _, _, _, est in weighed),
    )


def dough_scale(target_grams: str | None, total: Fraction) -> Fraction | None:
    """The multiplier that makes the weighed dough `target_grams`, within ¼× to 4×."""
    if not target_grams:
        return None
    try:
        target = Fraction(int(float(target_grams)))
    except ValueError:
        return None
    if target <= 0 or total == 0:
        return None
    factor = target / total
    return min(max(factor, Fraction(1, 4)), Fraction(4))

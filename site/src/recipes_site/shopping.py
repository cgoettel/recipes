"""One shopping list from several recipes.

Duplicates merge by a normalized item name ("2 onions, diced" and "1 yellow
onion" stay apart, but "1 onion, diced" and "2 onions" become "3 onions").
Amounts in the same unit add up; different units sit side by side
("1 cup + 2 tablespoons"). Items are grouped by store section, and staples most
kitchens already have collapse to the bottom.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from fractions import Fraction

from recipes_site import catalog
from recipes_site import ingredients as ing

# Words that describe preparation or size, not what you buy.
_DROP = {
    "large",
    "small",
    "medium",
    "fresh",
    "freshly",
    "chopped",
    "diced",
    "minced",
    "sliced",
    "grated",
    "shredded",
    "warm",
    "cold",
    "softened",
    "melted",
    "packed",
    "finely",
    "roughly",
    "thinly",
    "optional",
    "about",
    "heaping",
    "scant",
    "room-temperature",
    "lukewarm",
    "crushed",
    "beaten",
}
# Never on a list.
_SKIP = {"water", "warm water", "cold water", "hot water", "ice", "ice water", "boiling water"}

STAPLES = {
    "salt",
    "kosher salt",
    "table salt",
    "sea salt",
    "pepper",
    "black pepper",
    "salt and pepper",
    "flour",
    "all-purpose flour",
    "sugar",
    "white sugar",
    "granulated sugar",
    "brown sugar",
    "oil",
    "vegetable oil",
    "olive oil",
    "neutral oil",
    "canola oil",
    "butter",
    "salted butter",
    "baking soda",
    "baking powder",
    "vanilla",
    "vanilla extract",
    "cornstarch",
}

# Whole words only, so "eggplant" isn't an egg and "graham" isn't ham. The last
# word of a key is already singular (normalize()).
SECTIONS: list[tuple[str, str]] = [
    (
        "Produce",
        r"\b(?:onion|garlic|shallot|scallion|green onion|cilantro|parsley|basil|mint|dill|thyme"
        r"|rosemary|lime|lemon|orange|apple|banana|berry|blueberry|strawberry|raspberry|tomato"
        r"|potato|carrot|celery|ginger|avocado|lettuce|cabbage|spinach|kale|cucumber|zucchini"
        r"|squash|mushroom|jalapeño|jalapeno|serrano|habanero|poblano|anaheim|bell pepper|chile"
        r"|eggplant|leek|radish|beet|pear|peach|mango|pineapple|fruit|herb|corn on the cob)s?\b",
    ),
    (
        "Dairy and eggs",
        r"\b(?:milk|buttermilk|cream|heavy cream|cheese|yogurt|egg|butter|sour cream"
        r"|half-and-half|ricotta|mozzarella|parmesan|cheddar)s?\b",
    ),
    (
        "Meat and fish",
        r"\b(?:beef|chicken|pork|sausage|bacon|shrimp|fish|salmon|lamb|turkey|ham|chorizo|brat"
        r"|bratwurst|hot dog|steak|chuck|veal|tuna|crab|hamburger)s?\b",
    ),
    ("Bakery", r"\b(?:bread|bun|tortilla|roll|pita|naan|baguette)s?\b"),
    ("Frozen", r"\bfrozen\b|\bice cream\b"),
]
# Shelf goods that would otherwise match a fresh section ("peanut butter",
# "apple cider vinegar", "rolled oats", "tomato paste").
_PANTRY_FIRST = re.compile(
    r"\b(?:peanut butter|apple butter|vinegar|cracker|oat|paste|powder|dried|ketchup|broth"
    r"|stock|sauce|syrup|chip|bouillon|extract|seed|flake)s?\b"
)


def normalize(item: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", item.lower())  # links before parens
    text = re.sub(r"\(.*?\)", "", text)
    text = text.split(",")[0].split(";")[0]
    text = re.sub(r"\b(for|to taste|as needed)\b.*$", "", text)
    words = [w for w in re.findall(r"[a-z][a-z'-]*", text) if w not in _DROP]
    if not words:
        return text.strip()
    last = words[-1]
    if last.endswith("oes"):
        last = last[:-2]
    elif last.endswith("ies") and len(last) > 4:
        last = last[:-3] + "y"
    elif last.endswith("s") and not last.endswith(("ss", "us")) and len(last) > 3:
        last = last[:-1]
    words[-1] = last
    return " ".join(words)


_SHELF_FORMS = {"can", "jar", "bottle", "package", "envelope"}


def section_for(key: str, forms: set[str | None] | None = None) -> str:
    if key in STAPLES:
        return "Staples"
    # Canned or jarred tomatoes are a pantry buy, not produce.
    if (forms and forms & _SHELF_FORMS) or _PANTRY_FIRST.search(key):
        return "Pantry"
    for name, pattern in SECTIONS:
        if re.search(pattern, key):
            return name
    return "Pantry"


# Singular -> (singular, plural) for the kept units (oz, clove, can, …).
_FORMS: dict[str, tuple[str, str]] = {f[0]: f for f in ing.COUNT_FORMS}


@dataclass
class Entry:
    key: str
    label: str
    amounts: dict[tuple[str | None, str | None], list[Fraction]] = field(default_factory=dict)
    unscaled: list[str] = field(default_factory=list)
    recipes: list[str] = field(default_factory=list)

    @property
    def amount(self) -> str:
        parts = []
        for (unit, form), (low, high) in self.amounts.items():
            forms = _FORMS.get(form) if form else None
            shown = ing.display(
                ing.Ingredient(
                    raw="", low=low, high=high if high != low else None, unit=unit, unit_forms=forms
                )
            )
            parts.append(shown.amount)
        return " + ".join(parts)


@dataclass
class Section:
    name: str
    entries: list[Entry]


def build(recipes: list[tuple[catalog.Recipe, Fraction]]) -> list[Section]:
    entries: OrderedDict[str, Entry] = OrderedDict()
    for recipe, scale in recipes:
        for group in recipe.ingredient_groups:
            for line in group.items:
                parsed = ing.parse(line)
                key = normalize(parsed.item)
                if not key or key in _SKIP:
                    continue
                label = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", parsed.item)
                label = re.sub(r"\s*\(.*?\)", "", label).split(",")[0].strip() or key
                entry = entries.setdefault(key, Entry(key=key, label=label))
                if recipe.title not in entry.recipes:
                    entry.recipes.append(recipe.title)
                if parsed.low is None:
                    if parsed.raw not in entry.unscaled:
                        entry.unscaled.append(parsed.raw)
                    continue
                form = parsed.unit_forms[0] if parsed.unit_forms else None
                slot = entry.amounts.setdefault((parsed.unit, form), [Fraction(0), Fraction(0)])
                slot[0] += parsed.low * scale
                slot[1] += (parsed.high if parsed.high is not None else parsed.low) * scale
    by_section: OrderedDict[str, list[Entry]] = OrderedDict(
        (name, []) for name, _ in [*SECTIONS, ("Pantry", ""), ("Staples", "")]
    )
    for entry in entries.values():
        forms = {form for _, form in entry.amounts}
        by_section[section_for(entry.key, forms)].append(entry)
    return [
        Section(name, sorted(items, key=lambda e: e.key))
        for name, items in by_section.items()
        if items
    ]


def parse_plan(values: list[str]) -> list[tuple[str, Fraction]]:
    """`slug@scale` pairs from the URL; unknown scales fall back to 1×."""
    plan = []
    for value in values[:20]:
        slug, _, scale = value.partition("@")
        plan.append((slug.strip("/"), ing.parse_scale(scale or "1")))
    return plan

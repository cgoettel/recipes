"""Parse ingredient lines into amount, unit and item, and scale them.

Recipes stay plain Markdown, so this reads the lines people actually write:
"2 cups flour", "1½ teaspoons salt", "3–4 cloves garlic", "450 g bread flour".
It also reads shorthand ("2 C", "1 tsp."), so an old or pasted recipe still
scales, but catalog.check() flags shorthand against the house spellings in
CLAUDE.md (HOUSE_UNITS below).
A line with no leading amount ("Salt to taste") isn't an error; it just doesn't
scale. A line that starts with a number this parser can't read is kept as text
and flagged, so it can be fixed in the Markdown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction

_UNICODE_FRACTIONS = {
    "½": Fraction(1, 2),
    "⅓": Fraction(1, 3),
    "⅔": Fraction(2, 3),
    "¼": Fraction(1, 4),
    "¾": Fraction(3, 4),
    "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8),
    "⅝": Fraction(5, 8),
    "⅞": Fraction(7, 8),
    "⅕": Fraction(1, 5),
    "⅖": Fraction(2, 5),
    "⅗": Fraction(3, 5),
    "⅘": Fraction(4, 5),
    "⅙": Fraction(1, 6),
    "⅚": Fraction(5, 6),
}
_FRAC_CHARS = "".join(_UNICODE_FRACTIONS)

# One number: "2", "2.5", "0,3" (decimal comma), "½", "1½", "1 ½", "1/2", "1 1/2".
_NUM = rf"(?:\d+(?:[.,]\d+)?(?:\s*[{_FRAC_CHARS}]|\s+\d+/\d+)?|\d+/\d+|[{_FRAC_CHARS}])"
# An amount: a number, or a range of two ("2–3", "2-3", "2 to 3"), optionally
# "or more" ("4+").
_AMOUNT_RE = re.compile(
    rf"^\s*(?P<approx>~\s*)?(?P<low>{_NUM})(?:\s*(?:–|-|to)\s*(?P<high>{_NUM}))?"
    rf"(?P<plus>\+)?(?=\s|$|[a-zA-Z\"])"
)

# "(≈240 g)" or "(240 g)" right after the amount and unit.
_GRAMS_RE = re.compile(
    r"^\((?P<est>≈)?\s*(?P<lo>\d+(?:\.\d+)?)(?:\s*–\s*(?P<hi>\d+(?:\.\d+)?))?\s*g\)\s*"
)

# "(6 tablespoons)", "(1 cup)" or "(6 tablespoons, ≈85 g)" after a butter stick
# amount.
# It's regenerated from the scaled stick amount, so the parser drops it.
_STICK_NOTE_RE = re.compile(
    r"^\((?P<tb>[^,)]*?)\s*(?:tablespoons?|cups?)"
    r"(?:,\s*(?P<est>≈)?\s*(?P<g>\d+(?:\.\d+)?)\s*g)?\)\s*"
)
_BUTTER_RE = re.compile(r"^(?:(?:salted|unsalted|cold|softened|melted|cubed),?\s+)*butter\b", re.I)

# Canonical unit -> (singular, plural, kind). Kind drives rounding and conversion.
_CANONICAL = {
    "cup": ("cup", "cups", "volume"),
    "tablespoon": ("tablespoon", "tablespoons", "volume"),
    "teaspoon": ("teaspoon", "teaspoons", "volume"),
    "g": ("g", "g", "metric"),
    "kg": ("kg", "kg", "metric"),
    "ml": ("mL", "mL", "metric"),
    "l": ("L", "L", "metric"),
    # Butter only: one US stick is 8 tablespoons (½ cup, about 113 g).
    "stick": ("stick", "sticks", "butter"),
}

# Written token -> canonical unit, or None to keep the token as written (it still
# scales). Case matters for the single letters: T is a tablespoon, t a teaspoon.
_UNIT_TOKENS: dict[str, str | None] = {
    "C": "cup",
    "C.": "cup",
    "c": "cup",
    "c.": "cup",
    "cup": "cup",
    "cups": "cup",
    "T": "tablespoon",
    "T.": "tablespoon",
    "Tbsp": "tablespoon",
    "Tbsp.": "tablespoon",
    "tbsp": "tablespoon",
    "tbsp.": "tablespoon",
    "Tbs": "tablespoon",
    "tbs": "tablespoon",
    "tablespoon": "tablespoon",
    "tablespoons": "tablespoon",
    "t": "teaspoon",
    "t.": "teaspoon",
    "tsp": "teaspoon",
    "tsp.": "teaspoon",
    "teas.": "teaspoon",
    "teaspoon": "teaspoon",
    "teaspoons": "teaspoon",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "ml": "ml",
    "mL": "ml",
    "L": "l",
    "l": "l",
    "liter": "l",
    "liters": "l",
}
# Units kept as written, with their singular and plural forms.
_COUNT_UNITS = {
    "oz": ("oz", "oz"),
    "oz.": ("oz", "oz"),
    "ounce": ("ounce", "ounces"),
    "ounces": ("ounce", "ounces"),
    "lb": ("lb", "lb"),
    "lb.": ("lb", "lb"),
    "lbs": ("lb", "lb"),
    "lbs.": ("lb", "lb"),
    "pound": ("pound", "pounds"),
    "pounds": ("pound", "pounds"),
    "gal": ("gallon", "gallons"),
    "gallon": ("gallon", "gallons"),
    "gallons": ("gallon", "gallons"),
    "pint": ("pint", "pints"),
    "pints": ("pint", "pints"),
    "quart": ("quart", "quarts"),
    "quarts": ("quart", "quarts"),
    "qt": ("quart", "quarts"),
    "clove": ("clove", "cloves"),
    "cloves": ("clove", "cloves"),
    "can": ("can", "cans"),
    "cans": ("can", "cans"),
    "stick": ("stick", "sticks"),
    "sticks": ("stick", "sticks"),
    "pkg": ("package", "packages"),
    "pkg.": ("package", "packages"),
    "package": ("package", "packages"),
    "packages": ("package", "packages"),
    "envelope": ("envelope", "envelopes"),
    "envelopes": ("envelope", "envelopes"),
    "bunch": ("bunch", "bunches"),
    "bunches": ("bunch", "bunches"),
    "sprig": ("sprig", "sprigs"),
    "sprigs": ("sprig", "sprigs"),
    "slice": ("slice", "slices"),
    "slices": ("slice", "slices"),
    "stalk": ("stalk", "stalks"),
    "stalks": ("stalk", "stalks"),
    "head": ("head", "heads"),
    "heads": ("head", "heads"),
    "part": ("part", "parts"),
    "parts": ("part", "parts"),
    "pinch": ("pinch", "pinches"),
    "pinches": ("pinch", "pinches"),
    "dash": ("dash", "dashes"),
    "dashes": ("dash", "dashes"),
    "batch": ("batch", "batches"),
    "batches": ("batch", "batches"),
    "handful": ("handful", "handfuls"),
    "handfuls": ("handful", "handfuls"),
    "jar": ("jar", "jars"),
    "jars": ("jar", "jars"),
    "bottle": ("bottle", "bottles"),
    "bottles": ("bottle", "bottles"),
}
# Unit tokens the parser accepts but the house style doesn't use, with the house
# spelling (CLAUDE.md, "Recipe formatting quirks", Units). catalog.check() fails
# a recipe that uses one, so the shorthand can't creep back.
HOUSE_UNITS: dict[str, str] = {
    **dict.fromkeys(("C", "C.", "c", "c."), "cup"),
    **dict.fromkeys(("T", "T.", "Tbsp", "Tbsp.", "tbsp", "tbsp.", "Tbs", "tbs"), "tablespoon"),
    **dict.fromkeys(("t", "t.", "tsp", "tsp.", "teas."), "teaspoon"),
    **dict.fromkeys(("gram", "grams"), "g"),
    "ml": "mL",
    **dict.fromkeys(("l", "liter", "liters"), "L"),
    **dict.fromkeys(("oz.", "ounce", "ounces"), "oz"),
    **dict.fromkeys(("lb.", "lbs", "lbs.", "pound", "pounds"), "lb"),
    "gal": "gallon",
    "qt": "quart",
    **dict.fromkeys(("pkg", "pkg."), "package"),
}


def unit_spelling(line: str) -> tuple[str, str] | None:
    """(token as written, house spelling) when a line's unit isn't the house spelling."""
    raw = line.strip()
    m = _AMOUNT_RE.match(raw)
    if not m:
        return None
    token_match = re.match(r"^(\S+)(?:\s+|$)", raw[m.end() :].lstrip())
    if not token_match:
        return None
    bare = token_match.group(1).rstrip(",")
    return (bare, HOUSE_UNITS[bare]) if bare in HOUSE_UNITS else None


# Every (singular, plural) pair the kept units use.
COUNT_FORMS: set[tuple[str, str]] = set(_COUNT_UNITS.values())


MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def singular(word: str) -> str:
    """A rough singular for matching: tomatoes, peaches, berries -> tomato, peach, berry."""
    if word.endswith(("oes", "ches", "shes", "xes")):
        return word[:-2]
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith(("ss", "us")) and len(word) > 3:
        return word[:-1]
    return word


@dataclass(frozen=True)
class Ingredient:
    raw: str
    low: Fraction | None = None
    high: Fraction | None = None
    approx: bool = False
    plus: bool = False  # "4+ cloves": at least this much
    # A weight note after the amount: "2 cups (≈240 g) flour".
    grams_low: Fraction | None = None
    grams_high: Fraction | None = None
    grams_estimated: bool = False
    unit: str | None = None  # canonical (cup, tablespoon, g, …) or None
    unit_forms: tuple[str, str] | None = None  # (singular, plural) for kept units
    item: str = ""
    flagged: bool = False  # starts with a number we couldn't read

    @property
    def scalable(self) -> bool:
        return self.low is not None


def _parse_number(text: str) -> Fraction:
    text = text.strip()
    total = Fraction(0)
    # Trailing unicode fraction: "1½" / "1 ½" / "½"
    if text and text[-1] in _UNICODE_FRACTIONS:
        total += _UNICODE_FRACTIONS[text[-1]]
        text = text[:-1].strip()
        if not text:
            return total
    parts = text.split()
    for part in parts:
        if "/" in part:
            num, den = part.split("/")
            total += Fraction(int(num), int(den))
        else:
            total += Fraction(part.replace(",", "."))
    return total


def parse(line: str) -> Ingredient:
    """Parse one ingredient line (list marker already removed)."""
    raw = line.strip()
    m = _AMOUNT_RE.match(raw)
    if not m:
        # Starts with a number we couldn't read. A hyphenated size ("1-inch
        # piece", "9-ounce bag") is a description, not a failure.
        flagged = bool(re.match(r"^\s*~?\s*\d", raw)) and not re.match(
            r"^\s*\d+(?:[.,]\d+)?-[a-zA-Z]", raw
        )
        return Ingredient(raw=raw, item=raw, flagged=flagged)
    try:
        low = _parse_number(m.group("low"))
        high = _parse_number(m.group("high")) if m.group("high") else None
    except ValueError, ZeroDivisionError:
        return Ingredient(raw=raw, item=raw, flagged=True)
    rest = raw[m.end() :].lstrip()
    unit: str | None = None
    forms: tuple[str, str] | None = None
    token_match = re.match(r"^(\S+)(?:\s+|$)", rest)
    if token_match:
        token = token_match.group(1)
        bare = token.rstrip(",")
        if bare in _UNIT_TOKENS:
            unit = _UNIT_TOKENS[bare]
            rest = rest[token_match.end() :]
        elif bare in _COUNT_UNITS:
            forms = _COUNT_UNITS[bare]
            rest = rest[token_match.end() :]
        elif bare in ('"', "in", "in.", "inch", "inches"):
            # A size, not an amount ("1\" piece ginger", "6 inch tortillas"):
            # scaling it would change the piece, not the count. Show as written.
            return Ingredient(raw=raw, item=raw)
    grams_low = grams_high = None
    grams_estimated = False
    stick_note = _STICK_NOTE_RE.match(rest) if forms == ("stick", "sticks") else None
    after_note = rest[stick_note.end() :] if stick_note else rest
    if forms == ("stick", "sticks") and _BUTTER_RE.match(after_note):
        unit, forms, rest = "stick", None, after_note
        if stick_note and stick_note.group("g"):
            grams_estimated = bool(stick_note.group("est"))
            grams_low = Fraction(stick_note.group("g"))
    note = _GRAMS_RE.match(rest)
    if note:
        grams_estimated = bool(note.group("est"))
        grams_low = Fraction(note.group("lo"))
        grams_high = Fraction(note.group("hi")) if note.group("hi") else None
        rest = rest[note.end() :]
    elif unit == "g":
        grams_low, grams_high = low, high
    if rest.startswith("of "):
        rest = rest[3:]
    return Ingredient(
        raw=raw,
        low=low,
        high=high,
        approx=bool(m.group("approx")),
        plus=bool(m.group("plus")),
        grams_low=grams_low,
        grams_high=grams_high,
        grams_estimated=grams_estimated,
        unit=unit,
        unit_forms=forms,
        item=rest.strip(),
    )


# --- formatting --------------------------------------------------------------

_NICE = [
    (Fraction(0), ""),
    (Fraction(1, 8), "⅛"),
    (Fraction(1, 4), "¼"),
    (Fraction(1, 3), "⅓"),
    (Fraction(3, 8), "⅜"),
    (Fraction(1, 2), "½"),
    (Fraction(5, 8), "⅝"),
    (Fraction(2, 3), "⅔"),
    (Fraction(3, 4), "¾"),
    (Fraction(7, 8), "⅞"),
    (Fraction(1), ""),
]


def format_number(value: Fraction, *, metric: bool = False) -> str:
    """Kitchen-friendly: fractions to the nearest eighth (or third), metric as decimals."""
    if metric:
        if value >= 10:
            return str(round(value))
        rounded = round(float(value), 1)
        return f"{rounded:g}"
    whole = int(value)
    rest = value - whole
    best_frac, best_text = min(_NICE, key=lambda pair: abs(pair[0] - rest))
    if best_frac == 1:
        whole += 1
        best_text = ""
    if whole == 0 and not best_text:
        # Too small to round to an eighth; show the eighth rather than zero.
        return "⅛"
    return f"{whole if whole else ''}{best_text}" or "0"


def _is_nice(value: Fraction, step: Fraction) -> bool:
    return (value / step).denominator == 1


def _convert(value: Fraction, unit: str) -> tuple[Fraction, str]:
    """Move a scaled volume to the unit a cook would use."""
    if unit == "teaspoon" and value >= 3 and _is_nice(value / 3, Fraction(1, 2)):
        return _convert(value / 3, "tablespoon")
    if unit == "tablespoon" and value >= 4 and _is_nice(value / 16, Fraction(1, 4)):
        return value / 16, "cup"
    if unit == "cup" and value < Fraction(1, 4) and _is_nice(value * 16, Fraction(1, 2)):
        return _convert(value * 16, "tablespoon")
    if unit == "tablespoon" and value < 1 and _is_nice(value * 3, Fraction(1, 2)):
        return value * 3, "teaspoon"
    return value, unit


def _butter_amount(sticks: Fraction, ing: Ingredient, scale: Fraction) -> str:
    """Sticks with tablespoons alongside; under a quarter stick, just tablespoons."""
    grams = ""
    if ing.grams_low is not None:
        mark = "≈" if ing.grams_estimated else ""
        grams = f"{mark}{format_number(ing.grams_low * scale, metric=True)} g"
    # Two sticks and up read as cups; under that, tablespoons.
    if sticks >= 2:
        spoons, spoon_unit = sticks / 2, "cup"
    else:
        spoons, spoon_unit = sticks * 8, "tablespoon"
        if spoons < 1:
            spoons, spoon_unit = _convert(spoons, "tablespoon")
    spoon_words = _CANONICAL[spoon_unit][1 if spoons > 1 else 0]
    spoon_text = f"{format_number(spoons)} {spoon_words}"
    if sticks >= Fraction(1, 4) and _is_nice(sticks, Fraction(1, 4)):
        stick_words = "sticks" if sticks > 1 else "stick"
        inner = ", ".join(x for x in (spoon_text, grams) if x)
        return f"{format_number(sticks)} {stick_words} ({inner})"
    return f"{spoon_text} ({grams})" if grams else spoon_text


@dataclass(frozen=True)
class Display:
    amount: str  # "1½ cups", "3–4 cloves", "" for unscaled lines
    item: str  # the rest of the line, Markdown
    scaled: bool


def display(ing: Ingredient, scale: Fraction = Fraction(1)) -> Display:
    """The line as it should read at this scale."""
    if ing.low is None:
        return Display(amount="", item=ing.raw, scaled=False)
    low = ing.low * scale
    high = ing.high * scale if ing.high is not None else None
    unit = ing.unit
    if unit == "stick" and high is None:
        prefix = "~" if ing.approx else ""
        return Display(amount=prefix + _butter_amount(low, ing, scale), item=ing.item, scaled=True)
    if unit in ("cup", "tablespoon", "teaspoon") and high is None and scale != 1:
        low, unit = _convert(low, unit)
    metric = unit is not None and _CANONICAL[unit][2] == "metric"
    number = format_number(low, metric=metric)
    if high is not None:
        number += "–" + format_number(high, metric=metric)
    top = high if high is not None else low
    plural = top > 1
    words = ""
    if unit is not None:
        singular, plural_form = _CANONICAL[unit][:2]
        words = plural_form if plural else singular
    elif ing.unit_forms is not None:
        words = ing.unit_forms[1] if plural else ing.unit_forms[0]
    prefix = "~" if ing.approx else ""
    suffix = "+" if ing.plus else ""
    amount = f"{prefix}{number}{suffix} {words}".strip()
    if ing.grams_low is not None and ing.unit != "g":
        grams = format_number(ing.grams_low * scale, metric=True)
        if ing.grams_high is not None:
            grams += "–" + format_number(ing.grams_high * scale, metric=True)
        amount += f" ({'≈' if ing.grams_estimated else ''}{grams} g)"
    return Display(amount=amount, item=ing.item, scaled=True)


SCALES: list[tuple[str, Fraction]] = [
    ("½×", Fraction(1, 2)),
    ("1×", Fraction(1)),
    ("2×", Fraction(2)),
    ("3×", Fraction(3)),
]


def parse_scale(value: str | None) -> Fraction:
    for _, scale in SCALES:
        if value is not None and value == str(scale):
            return scale
    return Fraction(1)


# The amount a serves/makes line leads with, after an optional "about" or
# "enough for". A number later in the line ("one 9x13 pan") isn't the amount.
_YIELD_RE = re.compile(
    rf"^(?:(?:about|roughly|enough for(?: about)?)\s+|~\s*)?"
    rf"(?P<low>{_NUM})(?:\s*(?:–|-|to)\s*(?P<high>{_NUM}))?"
)
_MEASURE_RE = re.compile(
    r"\s*(cups?|quarts?|gallons?|pints?|tablespoons?|teaspoons?|oz|lb|g|kg|mL|L)\b"
)


def _decimal(value: Fraction) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def scale_yield(text: str, scale: Fraction = Fraction(1), *, servings: bool = False) -> str:
    """Scale the amount a serves/makes line leads with: "6–8" at 2× reads "12–16".

    Servings round to whole people. A measured amount ("about 1½ cups") scales
    like an ingredient. A count of things ("2 loaves") only scales when it lands
    on whole numbers above one; otherwise, rather than "1 loaves" or "1½
    cheeseballs", the line keeps its amount and adds "× ½", as does a line that
    doesn't lead with a number ("one 9x13 pan"). A decimal ("3.375 gallons")
    scales exactly.
    """
    if scale == 1:
        return text
    m = _YIELD_RE.match(text)
    if not m:
        return text if servings else f"{text} × {format_number(scale)}"
    try:
        low = _parse_number(m.group("low"))
        high = _parse_number(m.group("high")) if m.group("high") else None
    except ValueError, ZeroDivisionError:
        return text
    values = [v * scale for v in (low, high) if v is not None]
    if "." in m.group("low"):
        scaled = "–".join(_decimal(v) for v in values)
    elif servings:
        people = list(dict.fromkeys(max(1, round(v)) for v in values))  # "2–2" reads "2"
        scaled = "–".join(str(p) for p in people)
    elif _MEASURE_RE.match(text, m.end()):
        scaled = "–".join(format_number(v) for v in values)
    elif all(v.denominator == 1 and v > 1 for v in values) and low > 1:
        scaled = "–".join(str(int(v)) for v in values)
    else:
        return f"{text} × {format_number(scale)}"
    return text[: m.start("low")] + scaled + text[m.end() :]

"""The index's ingredient search: which recipes use leeks, or leeks and cream.

The query is split on commas into terms. A term matches an ingredient line when
its words appear there as whole words, with plurals folded, so "leeks" finds
"1 leek" and "cream" finds "sour cream" but not "creamy". Nothing is stored.
"""

import re
import unicodedata
from dataclasses import dataclass

from markupsafe import Markup, escape

from recipes_site import catalog
from recipes_site import ingredients as ing

MAX_QUERY = 200
MAX_TERMS = 5

_WORD = re.compile(r"[a-zà-öø-ÿ]+(?:['’][a-z]+)?", re.I)
_EMPHASIS = re.compile(r"(\*\*|__|\*|_)(\S.*?)\1")


def fold(word: str) -> str:
    """One word, lowercased, unaccented and singular (the shopping list's plural rule).

    "cookie" and "cookies" both end as "cooky", so either spelling finds the other.
    """
    word = unicodedata.normalize("NFKD", word.lower().replace("’", "'"))
    word = ing.singular("".join(c for c in word if not unicodedata.combining(c)))
    return word[:-2] + "y" if word.endswith("ie") and len(word) > 4 else word


@dataclass(frozen=True)
class Term:
    text: str  # as typed, trimmed and lowercased
    words: tuple[str, ...]  # folded
    parts: tuple[int, ...]  # which comma-separated parts of the query it came from


@dataclass(frozen=True)
class Query:
    terms: list[Term]
    dropped: bool  # more terms than MAX_TERMS were typed


def parse(query: str) -> Query:
    """The comma-separated terms in a query, without repeats. A tag search ("#tea") has none."""
    query = query.strip()
    if query.startswith("#"):
        return Query(terms=[], dropped=False)
    parts = query[:MAX_QUERY].split(",")
    if len(query) > MAX_QUERY:
        parts = parts[:-1]  # cut off mid-word
    terms: list[Term] = []
    for i, part in enumerate(parts):
        if part.strip().startswith("#"):  # a tag, for the name filter
            continue
        words = tuple(fold(w) for w in _WORD.findall(part))
        if not words or len("".join(words)) < 2:
            continue
        same = next((t for t in terms if t.words == words), None)
        if same:  # "leeks, Leek" is one term; removing it removes both parts
            terms[terms.index(same)] = Term(same.text, same.words, (*same.parts, i))
        else:
            terms.append(Term(text=" ".join(part.lower().split()), words=words, parts=(i,)))
    return Query(terms=terms[:MAX_TERMS], dropped=len(terms) > MAX_TERMS)


@dataclass(frozen=True)
class Line:
    amount: str
    html: Markup  # the item, with each match in <mark>


@dataclass
class Hit:
    recipe: catalog.Recipe
    lines: list[Line]
    matched: int  # how many of the terms it uses


@dataclass
class Group:
    label: str
    hits: list[Hit]


@dataclass(frozen=True)
class _Indexed:
    amount: str
    text: str  # the item as plain text
    tokens: tuple[tuple[int, int, str], ...]  # (start, end, folded word)


_index_for: tuple[catalog.Catalog, list[tuple[catalog.Recipe, list[_Indexed]]]] | None = None


def _index(cat: catalog.Catalog) -> list[tuple[catalog.Recipe, list[_Indexed]]]:
    """Every ingredient line, parsed and tokenized once per catalog, not per keystroke."""
    global _index_for
    if _index_for is not None and _index_for[0] is cat:
        return _index_for[1]
    built = []
    for recipe in cat.recipes.values():
        lines = []
        for part in recipe.ingredient_groups:
            for raw in part.items:
                shown = ing.display(ing.parse(raw))
                text = _EMPHASIS.sub(r"\2", ing.MARKDOWN_LINK.sub(r"\1", shown.item))
                tokens = tuple((m.start(), m.end(), fold(m.group())) for m in _WORD.finditer(text))
                lines.append(_Indexed(amount=shown.amount, text=text, tokens=tokens))
        if lines:
            built.append((recipe, lines))
    _index_for = (cat, built)
    return built


def _spans(line: _Indexed, terms: list[Term]) -> tuple[list[tuple[int, int]], set[int]]:
    """Where the terms match in a line, overlaps merged, and which terms did."""
    folded = [t[2] for t in line.tokens]
    spans: list[tuple[int, int]] = []
    found: set[int] = set()
    for ti, term in enumerate(terms):
        k = len(term.words)
        for i in range(len(folded) - k + 1):
            if tuple(folded[i : i + k]) == term.words:
                spans.append((line.tokens[i][0], line.tokens[i + k - 1][1]))
                found.add(ti)
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged, found


def _highlight(text: str, spans: list[tuple[int, int]]) -> Markup:
    out: list[str] = []
    at = 0
    for start, end in spans:
        out.append(str(escape(text[at:start])))
        out.append(f"<mark>{escape(text[start:end])}</mark>")
        at = end
    out.append(str(escape(text[at:])))
    return Markup("".join(out))


def find(cat: catalog.Catalog, terms: list[Term]) -> list[Group]:
    """Recipes using the terms, most terms first, alphabetical within a group."""
    if not terms:
        return []
    hits: list[Hit] = []
    for recipe, indexed in _index(cat):
        lines: list[Line] = []
        used: set[int] = set()
        for line in indexed:
            spans, found = _spans(line, terms)
            if found:
                used |= found
                lines.append(Line(amount=line.amount, html=_highlight(line.text, spans)))
        if lines:
            hits.append(Hit(recipe=recipe, lines=lines, matched=len(used)))
    total = len(terms)
    groups: list[Group] = []
    for n in range(total, 0, -1):
        same = sorted((h for h in hits if h.matched == n), key=lambda h: h.recipe.title.casefold())
        if same:
            groups.append(Group(label=_label(n, total, terms), hits=same))
    return groups


def _label(n: int, total: int, terms: list[Term]) -> str:
    if total == 1:
        return f"Uses {terms[0].text}"
    if n == total:
        return "Uses both" if total == 2 else f"Uses all {total}"
    return "Uses one" if n == 1 else f"Uses {n}"

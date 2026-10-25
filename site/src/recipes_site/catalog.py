"""Read the recipe Markdown into records the site renders.

The README is the catalog: its `##` and `###` headings are the categories, and
its links are the recipes, in order. Each recipe file is split into sections by
`##` headings. The ingredients section is parsed line by line (see
`ingredients.py`); the steps section (Instructions, Directions, Method or Steps)
becomes a list of steps; everything else renders as Markdown. A recipe with no
ingredients section still renders, just without cook mode.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import mistune

from recipes_site import ingredients as ing

STEP_HEADINGS = {"instructions", "directions", "method", "steps"}
_LINK_RE = re.compile(r"\]\(([^)\s]+?\.md)(#[^)]*)?\)")
_LIST_ITEM_RE = re.compile(r"^(?P<indent>\s*)(?:[-*+]|\d+[.)])\s+(?P<text>.*)$")

# Top-level folders → category stripe color token (see input.css).
CATEGORY_COLORS = {
    "bread": "peach",
    "breakfast": "yellow",
    "drinks": "sky",
    "entrees": "crimson",
    "household": "lilac",
    "sauces-and-condiments": "plum",
    "sides-and-starters": "violet",
    "sweets": "pale",
}

_md = mistune.create_markdown(escape=False, plugins=["table", "strikethrough"])


def render_markdown(text: str, base_dir: str) -> str:
    html = _md(rewrite_links(text, base_dir))
    return html if isinstance(html, str) else ""


def render_inline(text: str, base_dir: str) -> str:
    html = render_markdown(text, base_dir).strip()
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return html


def rewrite_links(text: str, base_dir: str) -> str:
    """Point relative links to other recipes at their page on the site."""

    def repl(m: re.Match[str]) -> str:
        target = m.group(1)
        if "://" in target:
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join(base_dir, target))
        slug = resolved[:-3] if resolved.endswith(".md") else resolved
        return f"](/{slug}{m.group(2) or ''})"

    return _LINK_RE.sub(repl, text)


@dataclass
class Group:
    """A run of list items under an optional `###` subheading."""

    heading: str | None
    items: list[str] = field(default_factory=list)


@dataclass
class Section:
    heading: str
    body: str  # raw Markdown


@dataclass
class Recipe:
    slug: str  # "breakfast/pancake-dutch-baby"
    category: str  # top-level folder
    title: str
    subtitle: str | None
    intro: str  # raw Markdown
    ingredient_groups: list[Group]
    step_groups: list[Group]
    sections: list[Section]  # everything else, in order
    body: str  # the whole file minus the title, for unstructured recipes
    anchor: str = ""  # the index anchor of its README category

    @property
    def base_dir(self) -> str:
        return posixpath.dirname(self.slug)

    @property
    def structured(self) -> bool:
        return bool(self.ingredient_groups)

    @property
    def tag(self) -> str:
        return self.category.replace("-", " ")

    @property
    def color(self) -> str:
        return CATEGORY_COLORS.get(self.category, "sky")

    @property
    def flagged_lines(self) -> list[str]:
        return [
            item
            for group in self.ingredient_groups
            for item in group.items
            if ing.parse(item).flagged
        ]


@dataclass
class Entry:
    slug: str
    title: str  # the README's link text


@dataclass
class Category:
    title: str
    slug: str  # anchor
    color: str
    subcategories: list[Subcategory]


@dataclass
class Subcategory:
    title: str | None
    entries: list[Entry]


@dataclass
class Catalog:
    categories: list[Category]
    recipes: dict[str, Recipe]
    house_notes: str  # the README intro, raw Markdown


def _list_items(body: str) -> list[Group]:
    """Collect list items (joining continuation lines), grouped by `###`."""
    groups: list[Group] = [Group(heading=None)]
    current: list[str] | None = None
    base_indent: int | None = None
    for line in body.splitlines():
        if line.startswith("### "):
            groups.append(Group(heading=line[4:].strip()))
            current = None
            continue
        m = _LIST_ITEM_RE.match(line)
        if m:
            indent = len(m.group("indent"))
            if base_indent is None:
                base_indent = indent
            if indent <= base_indent:
                groups[-1].items.append(m.group("text").strip())
                current = groups[-1].items
                continue
            # A nested item: fold it into its parent.
            if current:
                current[-1] += " " + m.group("text").strip()
            continue
        if line.strip() and current is not None and line.startswith((" ", "\t")):
            current[-1] += " " + line.strip()
        elif not line.strip():
            continue
        else:
            current = None
    return [g for g in groups if g.items]


def _split_title(title: str) -> tuple[str, str | None]:
    m = re.match(r"^(.*?)\s*\(([^()]+)\)\s*$", title)
    if m and m.group(1):
        return m.group(1), m.group(2)
    return title, None


def parse_recipe(slug: str, text: str) -> Recipe:
    lines = text.splitlines()
    title = posixpath.basename(slug).replace("-", " ").capitalize()
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            start = i + 1
            break
    body_lines = lines[start:]
    intro: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in body_lines:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            intro.append(line)

    ingredient_groups: list[Group] = []
    step_groups: list[Group] = []
    other: list[Section] = []
    for heading, content in sections:
        body = "\n".join(content).strip("\n")
        key = heading.strip().lower()
        if key == "ingredients" and not ingredient_groups:
            ingredient_groups = _list_items(body)
            leftover = _prose(content)
            if leftover:
                other.append(Section(heading="Ingredient notes", body=leftover))
        elif key in STEP_HEADINGS and not step_groups:
            step_groups = _list_items(body)
            if not step_groups:
                if body:
                    other.append(Section(heading=heading, body=body))
            else:
                leftover = _prose(content)
                if leftover:
                    other.append(Section(heading=f"{heading} notes", body=leftover))
        else:
            other.append(Section(heading=heading, body=body))

    main_title, subtitle = _split_title(title)
    return Recipe(
        slug=slug,
        category=slug.split("/", 1)[0],
        title=main_title,
        subtitle=subtitle,
        intro="\n".join(intro).strip(),
        ingredient_groups=ingredient_groups,
        step_groups=step_groups,
        sections=other,
        body="\n".join(body_lines).strip(),
    )


def _prose(content: list[str]) -> str:
    """Lines in a list section that aren't list items, so they aren't lost."""
    return "\n".join(
        ln
        for ln in content
        if ln.strip()
        and not _LIST_ITEM_RE.match(ln)
        and not ln.startswith("### ")
        and not ln.startswith((" ", "\t"))
    )


def _anchor(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def load(content_dir: Path) -> Catalog:
    readme = (content_dir / "README.md").read_text(encoding="utf-8")
    categories: list[Category] = []
    recipes: dict[str, Recipe] = {}
    intro: list[str] = []
    for line in readme.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            categories.append(
                Category(
                    title=title,
                    slug=_anchor(title),
                    color="sky",
                    subcategories=[Subcategory(title=None, entries=[])],
                )
            )
            continue
        if not categories:
            intro.append(line)
            continue
        if line.startswith("### "):
            categories[-1].subcategories.append(Subcategory(title=line[4:].strip(), entries=[]))
            continue
        m = re.match(r"^\s*[-*]\s+\[(?P<title>[^\]]+)\]\((?P<path>[^)]+\.md)\)", line)
        if not m:
            continue
        path = m.group("path")
        file = content_dir / path
        if not file.is_file():
            continue
        slug = path[:-3]
        recipe = parse_recipe(slug, file.read_text(encoding="utf-8"))
        recipe.anchor = categories[-1].slug
        recipes[slug] = recipe
        categories[-1].subcategories[-1].entries.append(Entry(slug=slug, title=m.group("title")))
    for cat in categories:
        cat.subcategories = [s for s in cat.subcategories if s.entries]
        if cat.subcategories:
            first = cat.subcategories[0].entries[0].slug
            cat.color = CATEGORY_COLORS.get(first.split("/", 1)[0], "sky")
    return Catalog(
        categories=[c for c in categories if c.subcategories],
        recipes=recipes,
        house_notes="\n".join(intro).strip(),
    )


@lru_cache(maxsize=1)
def cached(content_dir: str) -> Catalog:
    return load(Path(content_dir))

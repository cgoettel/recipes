"""Read the recipe Markdown into records the site renders.

The folders are the catalog: top-level folders are categories, the next level
down are subcategories, and each Markdown file is a recipe. A recipe's YAML front
matter (all optional) carries `family` and `variant` for the index's family
grouping, `serves` or `makes`, and `tags`. The README's recipe list is generated
from this same data (`toc.py`); only its hand-written intro is read here, as the
house notes. Each recipe file is split into sections by `##` headings. The
ingredients section is parsed line by line (see `ingredients.py`); the steps
section (`Instructions`, the house heading; older `Directions`, `Method` or
`Steps` still read) becomes a list of steps; everything else renders as Markdown. A recipe with no
ingredients section still renders, just without cook mode.
"""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import mistune
import yaml

from recipes_site import ingredients as ing

STEP_HEADINGS = {"instructions", "directions", "method", "steps"}
_LINK_RE = re.compile(r"\]\(([^)\s]+?\.md)(#[^)]*)?\)")
_LIST_ITEM_RE = re.compile(r"^(?P<indent>\s*)(?:[-*+]|\d+[.)])\s+(?P<text>.*)$")

# Folder names the plain rule (dashes to spaces, first letter capitalized)
# gets wrong.
FOLDER_NAMES = {"entrees": "Entrées", "east-asian": "East Asian"}

# Markdown that isn't a recipe: every README, the repo's meta docs, the soda
# brew-day notes (logs), and the site app.
_NOT_RECIPES = {"README.md", "CLAUDE.md", "contributing.md"}
_NOT_RECIPE_DIRS = ("site/", ".claude/", ".git/", "drinks/sodas/brew-day-notes/", "node_modules/")

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
    anchor: str = ""  # the index anchor of its category
    family: str | None = None
    variant: str | None = None
    serves: str | None = None
    makes: str | None = None
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)  # old slugs that redirect here

    @property
    def full_title(self) -> str:
        return f"{self.title} ({self.subtitle})" if self.subtitle else self.title

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
    title: str  # the recipe's full title
    family: str | None = None
    variant: str | None = None


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
    rows: list[Row] = field(default_factory=list)


@dataclass
class Row:
    """One line of the index: a recipe, or a labeled family of recipes.

    A recipe's front matter can name its family and variant ("Pancakes",
    "Classic"). A family with two or more recipes shows its name once as a label
    over the variants, a family named after its own section ("Bread" under
    Bread) lists just the variants, and everything else shows its title.
    """

    label: str | None  # family name, for a group
    items: list[tuple[Entry, str]]  # (entry, what to show)


def _key(name: str) -> str:
    # "Pancake" and "Pancakes" are one family.
    return name.casefold().removesuffix("s")


def index_rows(entries: list[Entry], *section_titles: str | None) -> list[Row]:
    sections = {_key(t) for t in section_titles if t}
    families: dict[str, list[str]] = {}
    for e in entries:
        if e.family and e.variant:
            families.setdefault(_key(e.family), []).append(e.family)
    rows: list[Row] = []
    grouped: dict[str, Row] = {}
    for e in entries:
        key = _key(e.family) if e.family and e.variant else None
        if key and key in sections:
            rows.append(Row(label=None, items=[(e, e.variant or e.title)]))
        elif key and len(families[key]) > 1:
            if key not in grouped:
                names = families[key]
                grouped[key] = Row(label=max(sorted(set(names)), key=names.count), items=[])
                rows.append(grouped[key])
            grouped[key].items.append((e, e.variant or e.title))
        else:
            rows.append(Row(label=None, items=[(e, e.title)]))
    for row in rows:
        row.items.sort(key=lambda item: item[1].casefold())
    rows.sort(key=lambda r: (r.label or r.items[0][1]).casefold())
    return rows


@dataclass
class Catalog:
    categories: list[Category]
    recipes: dict[str, Recipe]
    house_notes: str  # the README intro, raw Markdown
    aliases: dict[str, str] = field(default_factory=dict)  # old slug -> current slug

    def current(self, slug: str) -> str | None:
        """The live slug for a slug that may have moved, or None if it's unknown."""
        if slug in self.recipes:
            return slug
        return self.aliases.get(slug)

    def slugs_for(self, slug: str) -> list[str]:
        """A recipe's slug plus every old slug it was known by (for database rows)."""
        recipe = self.recipes.get(slug)
        return [slug, *(recipe.aliases if recipe else [])]


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


_FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n?---\n", re.S)

# The front matter fields and the tag vocabulary (documented in CLAUDE.md).
# `check()` holds every recipe to them, so a typo fails CI instead of quietly
# dropping a tag or a family.
FRONT_MATTER_KEYS = {"family", "variant", "serves", "makes", "tags", "aliases"}
TAGS = {
    # method
    "grill", "smoker", "slow-cooker", "instant-pot", "no-cook", "make-ahead",
    # diet
    "vegetarian", "vegan",
    # occasion
    "thanksgiving", "christmas", "game-day", "hot-dog-contest",
    # kind
    "quick-bread", "ferment", "coffee", "tea",
}  # fmt: skip


def split_front_matter(text: str) -> tuple[dict[str, object], str]:
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("front matter must be a mapping")
    return data, text[m.end() :]


def _text(value: object) -> str | None:
    return None if value is None else str(value).strip() or None


def _tags(value: object) -> list[str]:
    return [str(t) for t in value] if isinstance(value, list) else []


def alias_slug(value: str) -> str:
    """An alias as written ("/salsas/sauce-habanero.md") to a slug ("salsas/sauce-habanero")."""
    value = value.strip().strip("/")
    return value[:-3] if value.endswith(".md") else value


def parse_aliases(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [alias_slug(a) for a in value if isinstance(a, str) and alias_slug(a)]


def parse_recipe(slug: str, text: str) -> Recipe:
    meta, text = split_front_matter(text)
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
        family=_text(meta.get("family")),
        variant=_text(meta.get("variant")),
        serves=_text(meta.get("serves")),
        makes=_text(meta.get("makes")),
        tags=_tags(meta.get("tags")),
        aliases=parse_aliases(meta.get("aliases")),
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


def folder_title(name: str) -> str:
    return FOLDER_NAMES.get(name) or name.replace("-", " ").capitalize()


def recipe_paths(content_dir: Path) -> list[str]:
    """Every recipe file, as a path relative to content_dir."""
    paths = []
    for file in content_dir.rglob("*.md"):
        rel = file.relative_to(content_dir).as_posix()
        if is_recipe_path(rel):
            paths.append(rel)
    return sorted(paths)


def is_recipe_path(rel: str) -> bool:
    """Whether a repo-relative .md path is a recipe file (it may sit too deep; check() says so)."""
    name = rel.rsplit("/", 1)[-1]
    return (
        rel.endswith(".md")
        and name not in _NOT_RECIPES
        and not rel.startswith(_NOT_RECIPE_DIRS)
        and "/." not in "/" + rel
    )


def house_notes(readme: str) -> str:
    """The README's hand-written intro: everything before the recipe list."""
    intro: list[str] = []
    for line in readme.splitlines():
        if line.startswith("## ") or line.startswith("<!-- recipes:start"):
            break
        if not line.startswith("# "):
            intro.append(line)
    return "\n".join(intro).strip()


def load(content_dir: Path) -> Catalog:
    recipes: dict[str, Recipe] = {}
    tree: dict[str, dict[str | None, list[Entry]]] = {}
    for rel in recipe_paths(content_dir):
        parts = rel.split("/")
        if len(parts) < 2 or len(parts) > 3:
            continue  # recipes live one or two folders deep
        slug = rel[:-3]
        recipe = parse_recipe(slug, (content_dir / rel).read_text(encoding="utf-8"))
        top = parts[0]
        sub = parts[1] if len(parts) == 3 else None
        recipe.anchor = _anchor(folder_title(top))
        recipes[slug] = recipe
        tree.setdefault(top, {}).setdefault(sub, []).append(
            Entry(slug=slug, title=recipe.full_title, family=recipe.family, variant=recipe.variant)
        )
    categories: list[Category] = []
    for top in sorted(tree):
        title = folder_title(top)
        subs = tree[top]
        subcategories = []
        for sub in sorted(subs, key=lambda s: (s is not None, s or "")):
            sub_title = folder_title(sub) if sub else None
            entries = subs[sub]
            rows = index_rows(entries, title, sub_title)
            subcategories.append(Subcategory(title=sub_title, entries=entries, rows=rows))
        categories.append(
            Category(
                title=title,
                slug=_anchor(title),
                color=CATEGORY_COLORS.get(top, "sky"),
                subcategories=subcategories,
            )
        )
    readme = content_dir / "README.md"
    notes = house_notes(readme.read_text(encoding="utf-8")) if readme.is_file() else ""
    aliases = {
        old: slug
        for slug, recipe in recipes.items()
        for old in recipe.aliases
        if old not in recipes  # check() reports a collision; the live recipe wins
    }
    return Catalog(categories=categories, recipes=recipes, house_notes=notes, aliases=aliases)


def check(content_dir: Path) -> list[str]:
    """Problems that would otherwise drop a recipe or its metadata silently."""
    problems: list[str] = []
    paths = recipe_paths(content_dir)
    slugs = {rel[:-3] for rel in paths}
    claimed: dict[str, str] = {}  # alias -> the file that claims it
    for rel in paths:
        depth = rel.count("/")
        if depth not in (1, 2):
            problems.append(f"{rel}: recipes live one or two folders deep, or the site skips them")
            continue
        raw = (content_dir / rel).read_bytes()
        if b"\r\n" in raw:
            problems.append(f"{rel}: Windows line endings (CRLF); save with LF")
            continue
        text = raw.decode("utf-8")
        if text.startswith("---") and not _FRONT_MATTER_RE.match(text):
            problems.append(f"{rel}: front matter isn't closed with a `---` line")
            continue
        try:
            meta, _ = split_front_matter(text)
        except (yaml.YAMLError, ValueError) as exc:
            problems.append(f"{rel}: front matter doesn't parse: {exc}")
            continue
        for key in sorted(set(meta) - FRONT_MATTER_KEYS):
            problems.append(f"{rel}: unknown front matter field `{key}`")
        for key in ("family", "variant", "serves", "makes"):
            value = meta.get(key)
            # YAML reads a bare No/Yes as a boolean and a list or mapping as such.
            textual = isinstance(value, (str, int, float)) and not isinstance(value, bool)
            if value is not None and not textual:
                problems.append(f"{rel}: `{key}` should be text, got {value!r} (quote it)")
        if bool(meta.get("family")) != bool(meta.get("variant")):
            problems.append(f"{rel}: `family` and `variant` go together")
        if "serves" in meta and "makes" in meta:
            problems.append(f"{rel}: use `serves` or `makes`, not both")
        tags = meta.get("tags")
        if tags is not None:
            if not isinstance(tags, list):
                problems.append(f"{rel}: `tags` should be a list, like [grill, make-ahead]")
            else:
                for tag in tags:
                    if tag not in TAGS:
                        problems.append(f"{rel}: tag `{tag}` isn't in catalog.TAGS")
        recipe = parse_recipe(rel[:-3], text)
        for group in recipe.ingredient_groups:
            for item in group.items:
                wrong = ing.unit_spelling(item)
                if wrong:
                    problems.append(
                        f"{rel}: write `{wrong[1]}`, not `{wrong[0]}`, in “{item.strip()[:50]}”"
                    )
        aliases = meta.get("aliases")
        if aliases is not None:
            if not isinstance(aliases, list) or not all(isinstance(a, str) for a in aliases):
                problems.append(
                    f"{rel}: `aliases` should be a list of old paths, like [salsas/sauce-habanero]"
                )
            else:
                for alias in map(alias_slug, aliases):
                    if alias.count("/") not in (1, 2):
                        problems.append(
                            f"{rel}: alias `{alias}` should be a full old path, like "
                            "sauces-and-condiments/salsas/sauce-habanero"
                        )
                    elif alias in slugs:
                        problems.append(f"{rel}: alias `{alias}` is a live recipe's path")
                    elif alias in claimed:
                        problems.append(
                            f"{rel}: alias `{alias}` is also claimed by {claimed[alias]}"
                        )
                    else:
                        claimed[alias] = rel
    return problems


@lru_cache(maxsize=1)
def cached(content_dir: str) -> Catalog:
    return load(Path(content_dir))

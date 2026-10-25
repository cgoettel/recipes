import random

from recipes_site import stripes
from recipes_site.catalog import Entry, Row, index_rows


def _shown(rows: list[Row]) -> list[tuple[str | None, list[str]]]:
    return [(r.label, [s for _, s in r.items]) for r in rows]


def test_section_prefix_drops_and_families_group() -> None:
    entries = [
        Entry("b/a", "Bread — Almond"),
        Entry("b/d", "Pancake — Dutch Baby (German Pancakes)"),
        Entry("b/c", "Pancakes — Classic"),
        Entry("b/w", "Pancakes — Whole Wheat"),
        Entry("b/g", "Granola"),
    ]
    assert _shown(index_rows(entries, "Bread", None)) == [
        (None, ["Almond"]),
        ("Pancakes", ["Dutch Baby (German Pancakes)", "Classic", "Whole Wheat"]),
        (None, ["Granola"]),
    ]


def test_stripes_never_repeat_a_color_or_stack_pale_neighbors() -> None:
    rng = random.Random(7)
    thick_positions = set()
    for _ in range(500):
        st = stripes.draw(rng)
        colors = [s.color for s in st.header + st.footer]
        assert len(set(colors)) == 7
        for row in (st.header, st.footer):
            for a, b in zip(row, row[1:], strict=False):
                assert not (a.color in stripes.PALE and b.color in stripes.PALE)
        assert sum(s.thick for s in st.header) == 1
        thick_positions.add([s.thick for s in st.header].index(True))
    assert thick_positions == {0, 1, 2}

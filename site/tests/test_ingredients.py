from fractions import Fraction

import pytest

from recipes_site import ingredients as ing


@pytest.mark.parametrize(
    ("line", "low", "unit", "item"),
    [
        ("2 C flour", Fraction(2), "cup", "flour"),
        ("½ cup milk", Fraction(1, 2), "cup", "milk"),
        ("1 ½ tsp. salt", Fraction(3, 2), "teaspoon", "salt"),
        ("1½ T sugar", Fraction(3, 2), "tablespoon", "sugar"),
        ("1/2 t baking soda", Fraction(1, 2), "teaspoon", "baking soda"),
        ("2 1/2 C water", Fraction(5, 2), "cup", "water"),
        ("450 g bread flour", Fraction(450), "g", "bread flour"),
        ("450g bread flour", Fraction(450), "g", "bread flour"),
        ("1.5 L stock", Fraction(3, 2), "l", "stock"),
        ("3 eggs", Fraction(3), None, "eggs"),
    ],
)
def test_parse_amounts(line: str, low: Fraction, unit: str | None, item: str) -> None:
    parsed = ing.parse(line)
    assert parsed.low == low
    assert parsed.unit == unit
    assert parsed.item == item
    assert not parsed.flagged


def test_t_versus_capital_t() -> None:
    assert ing.parse("1 t salt").unit == "teaspoon"
    assert ing.parse("1 T salt").unit == "tablespoon"


def test_range_and_kept_unit() -> None:
    parsed = ing.parse("3–4 cloves garlic, minced")
    assert (parsed.low, parsed.high) == (Fraction(3), Fraction(4))
    assert parsed.unit_forms == ("clove", "cloves")
    assert parsed.item == "garlic, minced"


def test_plus_and_decimal_comma() -> None:
    garlic = ing.parse("4+ cloves garlic")
    assert ing.display(garlic).amount == "4+ cloves"
    flour = ing.parse("0,3 liter of wheat flour")
    assert flour.low == Fraction(3, 10)
    assert flour.unit == "l"
    assert flour.item == "wheat flour"


def test_sizes_are_not_scaled() -> None:
    for line in ('1" piece ginger', "6 inch tortillas", "1-inch piece ginger"):
        parsed = ing.parse(line)
        assert parsed.low is None, line
        assert not parsed.flagged, line
        assert ing.display(parsed, Fraction(2)).amount == ""


def test_no_amount_is_not_flagged() -> None:
    parsed = ing.parse("Salt to taste")
    assert parsed.low is None
    assert not parsed.flagged
    assert ing.display(parsed, Fraction(2)).amount == ""


def test_parenthetical_can_size() -> None:
    parsed = ing.parse("2 (14 oz) cans tomatoes")
    assert parsed.low == 2
    assert parsed.item == "(14 oz) cans tomatoes"


def test_display_spells_out_units() -> None:
    assert ing.display(ing.parse("2 C flour")).amount == "2 cups"
    assert ing.display(ing.parse("1 T sugar")).amount == "1 tablespoon"
    assert ing.display(ing.parse("½ cup milk")).amount == "½ cup"


def test_scaling() -> None:
    eggs = ing.parse("3 eggs")
    assert ing.display(eggs, Fraction(1, 2)).amount == "1½"
    flour = ing.parse("½ cup flour")
    assert ing.display(flour, Fraction(3)).amount == "1½ cups"


def test_scaling_converts_to_the_cooks_unit() -> None:
    butter = ing.parse("4 tablespoons butter")
    assert ing.display(butter, Fraction(2)).amount == "½ cup"
    salt = ing.parse("1 tsp salt")
    assert ing.display(salt, Fraction(3)).amount == "1 tablespoon"
    milk = ing.parse("¼ cup milk")
    assert ing.display(milk, Fraction(1, 2)).amount == "2 tablespoons"


def test_metric_rounds_as_decimals() -> None:
    flour = ing.parse("450 g flour")
    assert ing.display(flour, Fraction(1, 2)).amount == "225 g"
    yeast = ing.parse("7 g yeast")
    assert ing.display(yeast, Fraction(1, 2)).amount == "3.5 g"


def test_scale_param() -> None:
    assert ing.parse_scale("2") == 2
    assert ing.parse_scale("1/2") == Fraction(1, 2)
    assert ing.parse_scale("9") == 1
    assert ing.parse_scale(None) == 1

import re

import pytest
from fastapi.testclient import TestClient

from recipes_site import counts, timers
from recipes_site.app import create_app
from recipes_site.config import Settings


def _found(html: str) -> list[tuple[str, str, str, str]]:
    marked = str(timers.mark(html, "s0-0"))
    return re.findall(
        r'data-low="(\d+)" data-high="(\d+)" data-label="([^"]*)"'
        r'.*?<span class="timer-text">([^<]*)<',
        marked,
    )


@pytest.mark.parametrize(
    ("text", "low", "high", "shown"),
    [
        ("Bake 30–35 minutes until deep brown.", "1800", "2100", "30–35 minutes"),
        ("Simmer 1 hour.", "3600", "3600", "1 hour"),
        ("Rest 1½ hours.", "5400", "5400", "1½ hours"),
        ("Whisk for 30 seconds.", "30", "30", "30 seconds"),
        ("Cook 5-10min.", "300", "600", "5-10min"),
        ("Cook 8 to 10 minutes.", "480", "600", "8 to 10 minutes"),
        ("Roast 1 hour 30 minutes.", "5400", "5400", "1 hour 30 minutes"),
        ("Bake 2 hours and 15 minutes.", "8100", "8100", "2 hours and 15 minutes"),
        ("Bake 5–10 more minutes.", "300", "600", "5–10 more minutes"),
    ],
)
def test_times_become_timers(text: str, low: str, high: str, shown: str) -> None:
    [(lo, hi, _label, text_shown)] = _found(text)
    assert (lo, hi, text_shown) == (low, high, shown)


def test_two_times_in_one_step() -> None:
    html = "Bake 30–35 minutes. If using parchment, remove after 20–25 minutes and finish."
    assert [(lab, shown) for _lo, _hi, lab, shown in _found(html)] == [
        ("bake", "30–35 minutes"),
        ("remove", "20–25 minutes"),
    ]
    assert 'data-timer="s0-0-1"' in str(timers.mark(html, "s0-0"))


@pytest.mark.parametrize(
    ("before", "label"),
    [
        ("Bake at 350°F for ", "bake"),
        ("Cover and refrigerate ", "refrigerate"),
        ("Then knead ", "knead"),
        ("Let rest at least ", "let rest"),
        ("", ""),
    ],
)
def test_labels(before: str, label: str) -> None:
    assert timers.label(before) == label


def test_too_long_or_zero_is_not_a_timer() -> None:
    assert _found("Ferment 24 hours.") == []
    assert _found("Wait 0 minutes.") == []
    assert _found("Bread in Five Minutes a Day") == []


def test_tags_are_left_alone_and_labels_reach_past_them() -> None:
    html = '<strong>Bake</strong> 5 minutes, then <span class="xref">rest</span> 10 minutes.'
    marked = str(timers.mark(html, "s0-0"))
    assert "<strong>Bake</strong>" in marked
    assert [lab for _lo, _hi, lab, _shown in _found(html)] == ["bake", "rest"]


def test_label_reads_text_not_entities() -> None:
    marked = str(timers.mark("Stir &quot;hard&quot; &amp; fast 5 minutes.", "s0-0"))
    assert 'data-label="stir hard fast"' in marked


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(counts, "bump", lambda *_args, **_kw: None)
    return TestClient(create_app(Settings(auth_disabled=False, asset_version="abc1234")))


def test_recipe_page_has_timers_and_no_nested_buttons(client: TestClient) -> None:
    r = client.get("/bread/bread-artisan-in-five")
    assert r.status_code == 200
    assert 'data-low="1800" data-high="2100"' in r.text
    assert "data-timer-tray" in r.text
    # Steps are divs now, so the timer buttons inside them are valid HTML; the
    # number is the toggle button.
    assert '<div class="step" data-check="s1-5"' in r.text
    assert 'class="num" aria-pressed="false" aria-label="Step 10 done"' in r.text
    assert '<button type="button" class="step"' not in r.text

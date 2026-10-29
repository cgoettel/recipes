"""Tap-to-start timers: turn the times named in a step into timer buttons.

"Bake 30–35 minutes" gets a button holding "30–35 minutes". A range checks in
at its low end and counts down to its high end (app.js runs the timers).
"""

import re

from markupsafe import Markup, escape

MAX_SECONDS = 12 * 3600  # longer than this is a rest or a ferment, not a timer

_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3}
_NUM = r"(?:\d+(?:\.\d+)?[½¼¾⅓⅔]?|[½¼¾⅓⅔])"
_TIME = re.compile(
    rf"(?<![\w.])(?P<lo>{_NUM})(?:\s*(?:–|-|to)\s*(?P<hi>{_NUM}))?\s*"
    r"(?:(?:more|additional|extra|further)\s+)?"  # "5–10 more minutes"
    # "1 hour 30 minutes" is one timer.
    rf"(?:(?P<hours>hours?|hrs?)\b(?:,?\s*(?:and\s+)?(?P<extra>{_NUM})\s*(?:minutes?|mins?)\b)?"
    r"|(?P<unit>seconds?|secs?|minutes?|mins?)\b)",
    re.I,
)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600}
_TAG = re.compile(r"(<[^>]+>)")
# Words around the action that say nothing about it: "and bake for", "then knead".
_FILLER = {
    "about", "additional", "after", "another", "approximately", "around", "at", "every", "for",
    "in", "least", "more", "or", "over", "roughly", "until", "up", "within", "a", "an", "the",
    "and", "then", "to", "once", "it",
}  # fmt: skip
_CLOCK = (
    '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.6" stroke-linecap="round"><circle cx="12" cy="13" r="8"/>'
    '<path d="M12 9v4l2.5 2M10 2h4"/></svg>'
)


def _number(text: str) -> float:
    if text[-1] in _FRACTIONS:
        return (float(text[:-1]) if text[:-1] else 0) + _FRACTIONS[text[-1]]
    return float(text)


def seconds(match: re.Match[str]) -> tuple[int, int]:
    """(low, high) in seconds; high equals low for a single time."""
    unit = 3600 if match.group("hours") else _UNIT_SECONDS[match.group("unit")[0].lower()]
    extra = round(_number(match.group("extra")) * 60) if match.group("extra") else 0
    low = round(_number(match.group("lo")) * unit) + extra
    high = round(_number(match.group("hi")) * unit) + extra if match.group("hi") else low
    return low, max(low, high)


def label(before: str) -> str:
    """What the timer is for, from the words just before the time: "Bake" -> "bake"."""
    clause = re.split(r"[.;:,()!?—–]", before)[-1]
    # Temperatures and other numbers aren't the action: "bake at 350°F" -> "bake".
    words = [w for w in re.findall(r"[a-z][a-z'/-]*|\S*\d\S*", clause.lower()) if w[0].isalpha()]
    while words and words[-1] in _FILLER:
        words.pop()
    if "and" in words:  # "cover and refrigerate" -> "refrigerate"
        words = words[len(words) - words[::-1].index("and") :]
    words = words[-3:]
    while words and words[0] in _FILLER:
        words.pop(0)
    return " ".join(words)


def mark(html: str, step_id: str) -> Markup:
    """The step's HTML with each time it names wrapped in a timer button."""
    out: list[str] = []
    said = ""  # the step's text so far, so a label can reach back past inline markup
    n = 0
    for piece in _TAG.split(html):
        if piece.startswith("<"):
            out.append(piece)
            continue
        at = 0
        for m in _TIME.finditer(piece):
            low, high = seconds(m)
            if low <= 0 or high > MAX_SECONDS:
                continue
            text = m.group()
            what = escape(label(Markup(said + piece[: m.start()]).unescape()))
            out.append(piece[at : m.start()])
            out.append(
                f'<button type="button" class="timer" data-timer="{step_id}-{n}" '
                f'data-low="{low}" data-high="{high}" data-label="{what}" '
                f'aria-label="Start a timer: {text}">{_CLOCK}'
                f'<span class="timer-text">{text}</span></button>'
            )
            at = m.end()
            n += 1
        out.append(piece[at:])
        said += piece
    return Markup("".join(out))

#!/usr/bin/env python3
"""Apply the edits a Designer export always needs, to designer-lambda.yaml.

Designer targets Home Assistant and does not know about the Homey slot
convention, so every export needs the same few corrections. Doing them by hand
is how `nan` ended up on the panel. Run this after pasting a new lambda:

    ./apply-post-export.py < pasted-lambda.cpp

It reads the raw lambda on stdin and writes designer-lambda.yaml, wrapped as a
YAML block scalar for `lambda: !include`.
"""

from __future__ import annotations

import pathlib
import re
import sys

OUT = pathlib.Path(__file__).with_name("designer-lambda.yaml")

FALLBACK_TILE = re.compile(r"slot[1-6]")
"""Tiles the slot package gives a ``${slotN_unit}`` substitution."""

DISPLAY_GUARD = """// Blank the panel when Homey has switched the display off, before anything is
// drawn. ePaper holds its last image with no power, so sleeping without
// clearing would leave stale data on screen.
if (!id(display_on)) {
  it.fill(Color(255, 255, 255));
  return;
}
"""


TOUCH_BUTTON = """{
  // Touch button. Designer's `touch_area` widget emits no drawing code, so the
  // box is added here rather than by hand after every export — the hit area in
  // reterminal-e1003.yaml matches this rectangle, so move one and move both.
  // Label and state come from Homey, so what the button controls is a Flow
  // decision.
  it.rectangle(60, 1258, 440, 120, color_on);
  it.rectangle(62, 1260, 436, 116, color_on);
  std::string label = id(homey_t_button1_label).state;
  if (label.empty()) label = "Button";
  std::string state = id(homey_t_button1_state).state;
  it.printf(80, 1288, id(font_roboto_400_44), color_on, TextAlign::TOP_LEFT, "%s", label.c_str());
  if (!state.empty())
    it.printf(480, 1288, id(font_roboto_400_44), color_on, TextAlign::TOP_RIGHT, "%s", state.c_str());
}
"""


def fix_weather(code: str) -> tuple[str, int]:
    """Point the weather icon at the slot instead of Designer's HA sensor.

    The weather_icon widget ignores `is_local_sensor`, so it always emits an id
    for a Home Assistant text sensor. Until that is fixed upstream the name has
    to be rewritten here.
    """
    return re.subn(r"id\(homey_t_weather_txt\)", "id(homey_t_weather)", code)


def apply_slot_units(code: str) -> tuple[str, int]:
    """Draw the unit Homey sent, replacing the one Designer compiled in.

    Designer only knows the widget was drawn from a temperature, so it writes
    "%.1f °C" into every slot. A slot carries whatever Homey maps to it —
    humidity, a battery percentage, volts — so the unit has to arrive at
    runtime, from the tile's `_unit` text sensor. Fixed tiles reading the
    node's own sensors keep the unit Designer gave them.
    """
    pattern = re.compile(
        r'(sprintf\(\w+, "%\.\d+f)(?: [^"]+)?(", id\(homey_n_(\w+)\)\.state)\);'
    )

    def replace(m: re.Match[str]) -> str:
        head, tail, stem = m.groups()
        # caption, value and unit share a tile name; only the value is suffixed
        tile = stem.removesuffix("_value")
        unit = f"id(homey_t_{tile}_unit).state"
        if FALLBACK_TILE.fullmatch(tile):
            # A node whose slot always shows the same kind of reading sets
            # ${slotN_unit} once and leaves the unit out of the Flow entirely.
            # Only slot1..6 have that substitution; anything else would fail
            # config validation on an undefined name.
            expr = f'{unit}.empty() ? "${{{tile}_unit}}" : {unit}.c_str()'
        else:
            expr = f"{unit}.c_str()"
        return f"{head} %s{tail}, {expr});"

    return pattern.subn(replace, code)


SMHI_TO_DESIGNER = {
    "cloudy": ("cloudysky", "overcast"),
    "fog": ("fog",),
    "lightning": ("thunder",),
    "lightning-rainy": ("thunderstorm",),
    "partlycloudy": ("halfclearsky", "variablecloudiness"),
    "pouring": ("heavyrain", "heavyrainshowers"),
    "rainy": ("lightrain", "lightrainshowers", "moderaterain", "moderaterainshowers"),
    "snowy": ("heavysnowfall", "heavysnowshowers", "lightsnowfall", "lightsnowshowers", "moderatesnowfall", "moderatesnowshowers"),
    "snowy-rainy": ("heavysleet", "heavysleetshowers", "lightsleet", "lightsleetshowers", "moderatesleet", "moderatesleetshowers"),
    "sunny": ("clearsky", "nearlyclearsky"),
}
"""Designer icon name -> the SMHI states that should draw it.

Taken from the Flow this replaces, so the panel keeps the same icon for the
same weather. Keys are Designer's Home Assistant vocabulary; values are the
Swedish Weather app's own states, lowercased and space-stripped.
"""


def fold_smhi_vocabulary(code: str) -> tuple[str, int]:
    """Teach the icon chain to understand SMHI's wording as well as HA's.

    Designer generates the chain against Home Assistant names, but the value
    now arrives straight from the Swedish Weather app, which has its own. That
    app's Flow conditions cannot do the translation: its
    `drivers/weather/driver.js` compares the capability to the dropdown id with
    `===`, so a state containing a space -- `Moderate rain` against
    `Moderaterain` -- never matches, and only the four single-word states ever
    fire.

    Folding here instead lets Homey write the raw state to the slot, which
    makes the 35 Flow cards that used to spell out this mapping unnecessary.
    Spaces are stripped rather than enumerated so each SMHI state can be
    written as one word, and a name that is already Designer's passes through:
    `fog` is the only string in both vocabularies and it maps to itself.
    """
    anchor = re.compile(r"(?m)^([ \t]*)if \(false\) \{\}")

    def insert(match: "re.Match[str]") -> str:
        pad = match.group(1)
        lines = [
            "// Fold the Swedish Weather app's vocabulary onto Designer's.",
            "std::string compact;",
            "for (auto &c : weather_state) if (c != ' ') compact += c;",
        ]
        keyword = "if"
        for name in sorted(SMHI_TO_DESIGNER):
            tests = " || ".join(
                'compact == "{}"'.format(state) for state in SMHI_TO_DESIGNER[name]
            )
            lines.append("{} ({})".format(keyword, tests))
            lines.append('  weather_state = "{}";'.format(name))
            keyword = "else if"
        return "\n".join(pad + line for line in lines) + "\n" + match.group(0)

    return anchor.subn(insert, code, count=1)


def guard_nan(code: str) -> tuple[str, int]:
    """Print a dash rather than `nan` for a slot nothing has written yet.

    Designer emits an unguarded sprintf of the sensor state, so a numeric slot
    with no value renders literally as "nan" on the panel.
    """
    pattern = re.compile(
        r'( *)sprintf\((\w+), "([^"]*%\.\d+f[^"]*)", id\((\w+)\)\.state\);'
    )

    def replace(m: re.Match[str]) -> str:
        indent, buf, fmt, entity = m.groups()
        return (
            f"{indent}if (std::isnan(id({entity}).state))\n"
            f'{indent}  sprintf({buf}, "\\u2014");\n'
            f"{indent}else\n"
            f'{indent}  sprintf({buf}, "{fmt}", id({entity}).state);'
        )

    return pattern.subn(replace, code)


def main() -> int:
    # The export carries ° and —, so never rely on the locale encoding.
    code = sys.stdin.buffer.read().decode("utf-8").rstrip("\n")
    if not code:
        print("no lambda on stdin", file=sys.stderr)
        return 1

    code, weather = fix_weather(code)
    # Order matters: `guard_nan` matches Designer's two-argument sprintf, and
    # `apply_slot_units` rewrites it to three. Guarding second would match
    # nothing and put `nan` back on every slot.
    code, nans = guard_nan(code)
    code, units = apply_slot_units(code)
    code, smhi = fold_smhi_vocabulary(code)
    code = DISPLAY_GUARD + code + "\n" + TOUCH_BUTTON

    body = "\n".join(("  " + line).rstrip() for line in code.split("\n"))
    OUT.write_text("|-\n" + body + "\n", encoding="utf-8")
    print(f"weather references rewritten: {weather}")
    print(f"slot units taken from Homey: {units}")
    print(f"SMHI states folded into the icon chain: {smhi}")
    print(f"numeric slots guarded against nan: {nans}")
    print("touch button drawn: 1")
    print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

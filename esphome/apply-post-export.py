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

DISPLAY_GUARD = """// Blank the panel when Homey has switched the display off, before anything is
// drawn. ePaper holds its last image with no power, so sleeping without
// clearing would leave stale data on screen.
if (!id(display_on)) {
  it.fill(Color(255, 255, 255));
  return;
}
"""


def fix_weather(code: str) -> tuple[str, int]:
    """Point the weather icon at the slot instead of Designer's HA sensor.

    The weather_icon widget ignores `is_local_sensor`, so it always emits an id
    for a Home Assistant text sensor. Until that is fixed upstream the name has
    to be rewritten here.
    """
    return re.subn(r"id\(homey_t_weather_txt\)", "id(homey_t_weather)", code)


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
    code = sys.stdin.read().rstrip("\n")
    if not code:
        print("no lambda on stdin", file=sys.stderr)
        return 1

    code, weather = fix_weather(code)
    code, nans = guard_nan(code)
    code = DISPLAY_GUARD + code

    body = "\n".join(("  " + line).rstrip() for line in code.split("\n"))
    OUT.write_text("|-\n" + body + "\n")
    print(f"weather references rewritten: {weather}")
    print(f"numeric slots guarded against nan: {nans}")
    print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

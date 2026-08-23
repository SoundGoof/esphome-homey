#!/usr/bin/env python3
"""Fill a Flow template's device placeholders in, ready to POST to a Homey.

Homey has no Flow export or import: the app offers neither, and a backup covers
the whole system rather than one Flow. What it does have is an API, so a Flow
round-trips as JSON — the obstacle is that a Flow is full of device ids, and
those are unique to one Homey.

A template keeps everything that is genuinely portable (card types, arguments,
wiring, layout) and names the parts that are not, so moving a Flow to another
Homey — or standing up a second panel on this one — is a matter of saying which
devices to use:

    ./import-flow.py reterminal-e1003-panel.flow.json \\
        --name "Hallway panel" \\
        --panel 1234abcd-... --weather 5678efgh-... \\
        --sensors-1-3 ... --sensors-4-6 ... > /tmp/flow.json
    homey api flow create-advanced-flow --body @/tmp/flow.json

`homey api devices get-devices --json` lists the ids to pass. Every placeholder
must be given a value: a Flow referring to a device that does not exist is
accepted by Homey and then fails silently at run time, so this refuses instead.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

PLACEHOLDER = re.compile(r"\{\{([a-z_0-9]+)\}\}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=pathlib.Path)
    parser.add_argument("--name", help="name for the created Flow")
    parser.add_argument("--panel", help="device id of the display")
    parser.add_argument("--weather", help="device id of the weather source")
    parser.add_argument("--sensors-1-3", dest="sensors_1_3")
    parser.add_argument("--sensors-4-6", dest="sensors_4_6")
    parser.add_argument("-o", "--out", type=pathlib.Path)
    args = parser.parse_args()

    text = args.template.read_text(encoding="utf-8")
    wanted = set(PLACEHOLDER.findall(text))
    given = {
        key: value
        for key, value in vars(args).items()
        if key not in {"template", "out"} and value is not None
    }

    missing = sorted(wanted - set(given))
    if missing:
        print(
            "missing values for: " + ", ".join("--" + m.replace("_", "-") for m in missing),
            file=sys.stderr,
        )
        return 1

    unknown = sorted(set(given) - wanted)
    if unknown:
        print(f"template has no placeholder for: {', '.join(unknown)}", file=sys.stderr)
        return 1

    for key, value in given.items():
        text = text.replace("{{%s}}" % key, value)

    left = PLACEHOLDER.findall(text)
    if left:
        print(f"unfilled placeholders remain: {sorted(set(left))}", file=sys.stderr)
        return 1

    json.loads(text)  # never hand Homey something that is not valid JSON
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

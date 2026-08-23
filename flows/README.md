# Flow templates

Homey cannot export or import a Flow. The app offers neither, and a backup
covers the whole system rather than one Flow — but the API returns a Flow as
JSON and accepts one back, so a Flow travels perfectly well as a file.

The obstacle is that a Flow is full of device ids, and those are unique to one
Homey. A template keeps everything portable and names the rest:

| placeholder | what to pass |
|---|---|
| `{{name}}` | the name the created Flow should have |
| `{{panel}}` | the display device |
| `{{weather}}` | the device supplying the weather situation |
| `{{sensors_1_3}}` | device feeding tiles 1–3 |
| `{{sensors_4_6}}` | device feeding tiles 4–6 |

```bash
homey api devices get-devices --json | jq -r 'to_entries[] | "\(.key)  \(.value.name)"'

./import-flow.py reterminal-e1003-panel.flow.json \
    --name "Hallway panel" \
    --panel <id> --weather <id> --sensors-1-3 <id> --sensors-4-6 <id> \
    > /tmp/flow.json
homey api flow create-advanced-flow --body @/tmp/flow.json
```

`import-flow.py` refuses to write unless every placeholder has a value: Homey
accepts a Flow that names a device it does not have and then fails silently at
run time, which is a much worse way to find out.

## reterminal-e1003-panel.flow.json

The Flow driving one reTerminal E1003. Three branches from their own triggers:

- **tiles** — a one-minute cron writes six caption/value pairs, each value read
  from a device capability by Flow token
- **weather** — the situation string goes to the panel verbatim and the node's
  lambda picks the icon, because the Swedish Weather app's Flow conditions only
  match states without a space in them
- **button** — a touch on the panel toggles its LED and the label follows

An `any` card joins each branch's triggers so the sources meet before fanning
out, and one `start` card makes the whole thing runnable by hand. Homey allows
exactly one `start` card per Flow, so it drives both the tile and weather
branches; it deliberately misses the button branch, which would otherwise
toggle the LED every time you pressed play.

**Exporting a new template** — take the Flow back out and re-blank the ids:

```bash
homey api flow get-advanced-flow --id <flow-id> --json > raw.json
# keep name/enabled/cards, then replace each device id with its placeholder
```

The 15 display cards carry their panel as a `panel` argument rather than in the
card id, so they are byte-identical between systems and only the argument needs
rewriting.

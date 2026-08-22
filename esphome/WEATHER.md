# Driving the weather icon

The panel's weather icon reads one text slot, `homey_t_weather`, and matches its
contents — lowercased — against a fixed list of states. Anything it does not
recognise, an empty slot included, draws a question mark. That is the icon
working as designed, not a fault: the slot simply has no source until a Flow
writes one.

## The states the icon knows

These come from ESPHome Designer, which targets Home Assistant, so the
vocabulary is Home Assistant's:

| State                | Drawn as                |
| -------------------- | ----------------------- |
| `clear-night`        | moon                    |
| `cloudy`             | cloud                   |
| `exceptional`        | alert                   |
| `fog`                | fog                     |
| `hail`               | hail                    |
| `lightning`          | lightning               |
| `lightning-rainy`    | lightning with rain     |
| `partlycloudy`       | sun behind cloud        |
| `partlycloudy-night` | moon behind cloud       |
| `pouring`            | heavy rain              |
| `rainy`              | rain                    |
| `snowy`              | snow                    |
| `snowy-rainy`        | sleet                   |
| `sunny`              | sun                     |
| `windy`              | wind                    |
| `windy-variant`      | wind with cloud         |

Re-exporting the layout regenerates this list, so treat the lambda as the
authority if the two ever disagree.

## Where the value comes from

Homey has no weather *capability*. Weather is a manager (`ManagerWeather`,
`GET /weather/state`), and on a Self-Hosted Server it returns `null` — no
cards, no tokens, nothing to read. Only `cron:sunrise` and `cron:sunset` exist
out of the box. A weather app therefore has to supply the condition, and each
app publishes its own vocabulary.

That is why no translation table ships in `homey-esphomedriver`. Capability
units live there because Homey defines them and they cannot drift per install;
weather strings are a third party's, they change on that party's schedule, and
a wrong entry would need a package release to correct. Map them in the Flow
instead, against the table below.

## Mapping a weather app to these states

Whichever app provides the condition, the Flow does the same thing: read its
value, and write the matching state into `homey_t_weather` with the
**Set a display text slot** action.

Common vocabularies, for reference — confirm against the app you install, since
these do change:

| Icon state           | OpenWeatherMap        | Met.no                          | Buienradar    |
| -------------------- | --------------------- | ------------------------------- | ------------- |
| `sunny`              | Clear                 | `clearsky_day`                  | zonnig        |
| `clear-night`        | Clear (night)         | `clearsky_night`                | helder        |
| `partlycloudy`       | Clouds (few/scattered)| `partlycloudy_day`              | halfbewolkt   |
| `cloudy`             | Clouds (broken/overcast) | `cloudy`                        | bewolkt       |
| `rainy`              | Rain (light/moderate) | `rain`, `lightrain`             | regen         |
| `pouring`            | Rain (heavy)          | `heavyrain`                     | zware regen   |
| `lightning`          | Thunderstorm          | `lightrainshowersandthunder`    | onweer        |
| `snowy`              | Snow                  | `snow`                          | sneeuw        |
| `fog`                | Mist, Fog, Haze       | `fog`                           | mist          |
| `windy`              | Squall                | —                               | —             |

Anything unmapped can be left to fall through to the question mark, which is a
truthful "no reading" rather than a wrong icon.

## SMHI (`se.swefa`, Weather Forecast from SMHI)

The device publishes `measure_weather_situation_cp`, and that string is
**localised** — the app resolves it through `homey.__('weather_situationN')`,
so it reads differently on a Swedish or Norwegian Homey than on an English one.
Map against the language your Homey is set to; the numbers below are SMHI's
Wsymb2 codes, which do not change, and the text is the `en` locale.

The app also defines a `weather_symbol_cp` capability holding the raw number,
which would be the stable thing to match on, but its driver never adds it to
the device. Only the string is available.

| Wsymb2 | Situation (`en`)      | Icon state       | At night |
| ------ | --------------------- | ---------------- | -------- |
| 1  | Clear sky             | `sunny`            | `clear-night` |
| 2  | Nearly clear sky      | `sunny`            | `clear-night` |
| 3  | Variable cloudiness   | `partlycloudy`     | `partlycloudy-night` |
| 4  | Halfclear sky         | `partlycloudy`     | `partlycloudy-night` |
| 5  | Cloudy sky            | `cloudy`           | `cloudy` |
| 6  | Overcast              | `cloudy`           | `cloudy` |
| 7  | Fog                   | `fog`              | `fog` |
| 8  | Light rain showers    | `rainy`            | `rainy` |
| 9  | Moderate rain showers | `rainy`            | `rainy` |
| 10 | Heavy rain showers    | `pouring`          | `pouring` |
| 11 | Thunderstorm          | `lightning-rainy`  | `lightning-rainy` |
| 12 | Light sleet showers   | `snowy-rainy`      | `snowy-rainy` |
| 13 | Moderate sleet showers | `snowy-rainy`      | `snowy-rainy` |
| 14 | Heavy sleet showers   | `snowy-rainy`      | `snowy-rainy` |
| 15 | Light snow showers    | `snowy`            | `snowy` |
| 16 | Moderate snow showers | `snowy`            | `snowy` |
| 17 | Heavy snow showers    | `snowy`            | `snowy` |
| 18 | Light rain            | `rainy`            | `rainy` |
| 19 | Moderate rain         | `rainy`            | `rainy` |
| 20 | Heavy rain            | `pouring`          | `pouring` |
| 21 | Thunder               | `lightning`        | `lightning` |
| 22 | Light sleet           | `snowy-rainy`      | `snowy-rainy` |
| 23 | Moderate sleet        | `snowy-rainy`      | `snowy-rainy` |
| 24 | Heavy sleet           | `snowy-rainy`      | `snowy-rainy` |
| 25 | Light snowfall        | `snowy`            | `snowy` |
| 26 | Moderate snowfall     | `snowy`            | `snowy` |
| 27 | Heavy snowfall        | `snowy`            | `snowy` |

Night variants matter for codes 1-4 only; the rest look the same either way.
Homey has no "is it dark" token, so pair the write with `cron:sunrise` /
`cron:sunset`, or ignore the night column and accept a sun icon after dark.

## Doing without a weather app

The panel reaches nothing but the LAN, and a weather app pulls from the
internet through Homey. A node that must stay fully local can still drive the
icon from `cron:sunrise` and `cron:sunset` alone — writing `sunny` at sunrise
and `clear-night` at sunset. It says nothing about the weather, only about the
hour, so use it only where that is understood.

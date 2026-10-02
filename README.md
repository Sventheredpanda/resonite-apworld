# Resonite apworld

One static apworld that turns **any** Resonite game world into an Archipelago
game. The world definition (items, regions, locations, logic) lives **in the
player YAML** — there is no build step and nothing per-world to maintain.

## Install

Drop `resonite.apworld` into your Archipelago installation's `custom_worlds`
folder. That's it — the same file works for every Resonite world you define.

## Player YAML

```yaml
name: YourSlotName
game: Resonite

Resonite:
  world_definition: |
    display_name: Crystal Caverns
    filler_item: Shiny Pebble
    death_link: true

    items:
      Lantern: { progression: true }
      Climbing Pick: { progression: true }
      Warm Socks: {}            # filler-ish extra (useful/filler)
      Cave-in: { trap: true }

    regions:
      Base Camp:
        starting: true
        connects_to: [Crystal Caves]
      Crystal Caves:
        connects_to: [Base Camp]
        requires: "|Lantern|"

    locations:
      - name: Base Camp - Supply Tent
        region: Base Camp
      - name: Caves - Summit Beacon
        region: Crystal Caves
        requires: "|Climbing Pick|"
        victory: true
```

See `examples/` for two complete player YAMLs.

## Definition reference

- `display_name` — shown in slot_data for the client (default `"Resonite World"`).
- `filler_item` — **required**; used to pad the item pool up to the location count.
- `death_link` — informational; the client decides whether to tag DeathLink.
  Exposed to the client via slot_data.
- `items` — mapping of name -> `{count, progression, useful, trap}`.
  Pick at most one of `progression`/`useful`/`trap`. `count` defaults to 1.
  Names must not contain `:` or `|`.
- `regions` — mapping of name -> `{starting, connects_to, requires}`.
  Exactly one region has `starting: true`. `requires` gates **entering** the
  region (it is applied to every entrance leading into it).
- `locations` — list of `{name, region, requires, victory}`.
  Exactly one location has `victory: true` (that's the goal).
- Requires grammar: `|Lantern|`, `|Coin:25|`, `|Coin:50%|`, combined with
  `and`, `or`, `not` and parentheses. `|Coin:50%|` means 50% of the Coins in
  the item pool.

## ID stability rule

Item/location IDs are assigned in **definition order** (items 1..N, locations
1..M). Once a campaign starts, **never reorder or rename** entries — only
append new ones. Reordering silently corrupts saves and multiworld state.

## Client contract (slot_data)

Because every slot can define a different world, the shared `"Resonite"`
DataPackage has no name maps. The universal in-world client must read its
name<->ID tables from `slot_data`, which contains:

```json
{
  "display_name": "Crystal Caverns",
  "goal": "Caves - Summit Beacon",
  "death_link": true,
  "item_name_to_id": {"Lantern": 1, "...": "..."},
  "location_name_to_id": {"Base Camp - Supply Tent": 1, "...": "..."}
}
```

## Known limitations

- **Universal Tracker is not supported.** It resolves names through the
  per-game DataPackage, which is necessarily empty when definitions live in
  player YAMLs. The blessed client is the in-world universal client reading
  slot_data (see above).
- **DeathLink/TrapLink** work from the client side: tag `DeathLink` on
  Connect if you want it (check `slot_data.death_link`), and use
  `Bounce`/`Bounced` messages for trap effects — no apworld changes needed.

## Tests

```bash
python3 tests/test_rules.py        # requires-expression parser
python3 tests/test_definition.py    # definition validation
AP_SRC=/path/to/Archipelago tests/test_generate.sh   # end-to-end generation
```

The end-to-end test generates a real 2-player multiworld with two *different*
Resonite definitions and asserts fill, playthrough and cross-world placement.

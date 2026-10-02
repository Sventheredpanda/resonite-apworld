"""Parse and validate a Resonite world definition.

The definition arrives as the ``world_definition`` YAML option: a YAML string
inside the player YAML. This module turns it into a normalized dict or raises
``DefinitionError`` with a human-readable message (surfaced at generation time).
"""

from __future__ import annotations

import re

import yaml

try:
    from .rules import RequiresError, parse_requires
except ImportError:  # allow importing definition.py standalone in unit tests
    from rules import RequiresError, parse_requires

NAME_FORBIDDEN_RE = re.compile(r"[|:]")


class DefinitionError(ValueError):
    """Raised when a world definition is invalid."""


def parse_definition(text: str) -> dict:
    """Parse and validate the world_definition option text.

    Returns a normalized dict with keys: display_name, filler_item, death_link,
    items, regions, locations, starting_region, victory_location.
    """
    if not isinstance(text, str) or not text.strip():
        fail("world_definition is empty; define your world in the Resonite YAML section")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        fail(f"world_definition is not valid YAML: {e}")
    if not isinstance(data, dict):
        fail("world_definition must be a YAML mapping")
    return validate(data)


def validate(data: dict) -> dict:
    display_name = data.get("display_name") or "Resonite World"
    filler_item = data.get("filler_item")
    if not isinstance(filler_item, str) or not filler_item.strip():
        fail("filler_item is required (name of the filler item)")
    death_link = bool(data.get("death_link", False))

    # --- items ---
    raw_items = data.get("items")
    if not isinstance(raw_items, dict) or not raw_items:
        fail("items must be a non-empty mapping of item name -> properties")
    items: dict = {}
    for name, props in raw_items.items():
        _check_name(name, "item")
        props = props or {}
        if not isinstance(props, dict):
            fail(f"item {name!r}: properties must be a mapping")
        count = props.get("count", 1)
        if not isinstance(count, int) or count < 1:
            fail(f"item {name!r}: count must be a positive integer")
        progression = bool(props.get("progression", False))
        useful = bool(props.get("useful", False))
        trap = bool(props.get("trap", False))
        if sum([progression, useful, trap]) > 1:
            fail(f"item {name!r}: pick at most one of progression/useful/trap")
        items[name] = {"count": count, "progression": progression,
                       "useful": useful, "trap": trap}
    if filler_item not in items:
        items[filler_item] = {"count": 0, "progression": False, "useful": False, "trap": False}

    # --- regions ---
    raw_regions = data.get("regions")
    if not isinstance(raw_regions, dict) or not raw_regions:
        fail("regions must be a non-empty mapping of region name -> properties")
    regions: dict = {}
    starting = None
    for name, props in raw_regions.items():
        _check_name(name, "region")
        props = props or {}
        if not isinstance(props, dict):
            fail(f"region {name!r}: properties must be a mapping")
        connects_to = props.get("connects_to", [])
        if not isinstance(connects_to, list):
            fail(f"region {name!r}: connects_to must be a list")
        requires = props.get("requires")
        if requires is not None and not isinstance(requires, str):
            fail(f"region {name!r}: requires must be a string")
        is_starting = bool(props.get("starting", False))
        if is_starting:
            if starting is not None:
                fail("only one region may have starting: true")
            if requires:
                fail(f"region {name!r}: the starting region must not have requires")
            starting = name
        regions[name] = {"connects_to": list(connects_to), "requires": requires}
    if starting is None:
        fail("one region must have starting: true")
    for name, info in regions.items():
        for target in info["connects_to"]:
            if target not in regions:
                fail(f"region {name!r} connects to unknown region {target!r}")

    # --- locations ---
    raw_locations = data.get("locations")
    if not isinstance(raw_locations, list) or not raw_locations:
        fail("locations must be a non-empty list")
    locations: dict = {}
    victory = None
    for entry in raw_locations:
        if not isinstance(entry, dict):
            fail(f"location entries must be mappings, got {entry!r}")
        name = entry.get("name")
        _check_name(name, "location")
        if name in locations:
            fail(f"duplicate location name {name!r}")
        region = entry.get("region")
        if region not in regions:
            fail(f"location {name!r} is in unknown region {region!r}")
        requires = entry.get("requires")
        if requires is not None and not isinstance(requires, str):
            fail(f"location {name!r}: requires must be a string")
        is_victory = bool(entry.get("victory", False))
        if is_victory:
            if victory is not None:
                fail("only one location may have victory: true")
            victory = name
        locations[name] = {"region": region, "requires": requires, "victory": is_victory}
    if victory is None:
        fail("one location must have victory: true")

    # --- cross-checks ---
    known_items = set(items)
    item_totals = {name: info["count"] for name, info in items.items()}
    for name, info in regions.items():
        if info["requires"]:
            _check_requires(info["requires"], known_items, item_totals, f"region {name!r}")
    for name, info in locations.items():
        if info["requires"]:
            _check_requires(info["requires"], known_items, item_totals, f"location {name!r}")

    pool_size = sum(info["count"] for name, info in items.items() if name != filler_item)
    if pool_size > len(locations):
        fail(f"item pool has {pool_size} items but only {len(locations)} locations")

    return {
        "display_name": display_name,
        "filler_item": filler_item,
        "death_link": death_link,
        "starting_region": starting,
        "victory_location": victory,
        "items": items,
        "regions": regions,
        "locations": locations,
    }


def _check_name(name, kind: str) -> None:
    if not isinstance(name, str) or not name.strip():
        fail(f"{kind} names must be non-empty strings")
    if NAME_FORBIDDEN_RE.search(name):
        fail(f"{kind} name {name!r} must not contain ':' or '|' (reserved by requires syntax)")


def _check_requires(text: str, known_items: set, item_totals: dict, where: str) -> None:
    try:
        parse_requires(text, player=1, item_totals=item_totals, known_items=known_items)
    except RequiresError as e:
        fail(f"bad requires on {where}: {e}")


def fail(msg: str) -> None:
    raise DefinitionError(f"invalid Resonite world definition: {msg}")

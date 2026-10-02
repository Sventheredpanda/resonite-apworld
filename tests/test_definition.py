"""Unit tests for world definition parsing/validation. Run: python3 tests/test_definition.py"""
import importlib.util
import pathlib

_RES = pathlib.Path(__file__).parent.parent / "resonite"
_spec = importlib.util.spec_from_file_location("definition", _RES / "definition.py")
definition = importlib.util.module_from_spec(_spec)
import sys
sys.path.insert(0, str(_RES))
_spec.loader.exec_module(definition)
DefinitionError = definition.DefinitionError
parse_definition = definition.parse_definition

GOOD = """
display_name: Test World
filler_item: Pebble
items:
  Lantern: { progression: true }
  Coin: { count: 2 }
regions:
  A: { starting: true, connects_to: [B] }
  B: { connects_to: [A], requires: "|Lantern|" }
locations:
  - { name: L1, region: A }
  - { name: L2, region: B, requires: "|Coin:5|" }
  - { name: L3, region: B, victory: true }
"""


def ok(text=GOOD):
    d = parse_definition(text)
    assert d["starting_region"] == "A"
    assert d["victory_location"] == "L3"
    assert d["filler_item"] == "Pebble"
    return d


def bad(text, fragment):
    try:
        parse_definition(text)
    except DefinitionError as e:
        assert fragment in str(e), f"expected {fragment!r} in {e}"
        return
    raise AssertionError(f"should have failed with {fragment!r}")


ok()
d = ok()
assert set(d["items"]) == {"Lantern", "Coin", "Pebble"}  # filler auto-added

bad("", "empty")
bad("not: [valid", "not valid YAML")
bad("[]", "must be a YAML mapping")
bad(GOOD.replace("filler_item: Pebble", "filler_item: ''"), "filler_item is required")
bad(GOOD.replace("starting: true", "starting: false"), "starting: true")
bad(GOOD.replace("victory: true", "victory: false"), "victory: true")
bad(GOOD.replace("|Lantern|", "|Nope|"), "Unknown item 'Nope'")
bad(GOOD.replace("- { name: L1, region: A }",
                 "- { name: L1, region: A }\n  - { name: L1, region: A }"), "duplicate location")
bad(GOOD.replace("region: B, requires", "region: ZZZ, requires"), "unknown region 'ZZZ'")
bad(GOOD.replace("connects_to: [B]", "connects_to: [ZZZ]"), "unknown region 'ZZZ'")
bad(GOOD.replace("name: L1", "name: 'A|B'"), "must not contain")
# two victories
two_vic = GOOD.replace("- { name: L2, region: B, requires: \"|Coin:5|\" }",
                       "- { name: L2, region: B, victory: true }")
bad(two_vic, "only one location may have victory")
# pool bigger than locations
big_pool = GOOD.replace("Coin: { count: 2 }", "Coin: { count: 10 }\n  Extra1: {}\n  Extra2: {}\n  Extra3: {}")
bad(big_pool, "item pool has")

print("all definition tests passed")

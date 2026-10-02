"""Unit tests for the requires-string parser. Run: python3 tests/test_rules.py"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "resonite"))

from rules import RequiresError, parse_requires


class FakeState:
    def __init__(self, items):
        self._items = items  # dict name -> count

    def has(self, item, player, count=1):
        return self._items.get(item, 0) >= count


def rule(text, totals=None, items=("Lantern", "Climbing Pick", "Diving Bell", "Coin")):
    totals = totals or {"Coin": 10}
    return parse_requires(text, player=1, item_totals=totals, known_items=set(items))


def check(text, owned, expected, **kw):
    got = rule(text, **kw)(FakeState(owned))
    assert got == expected, f"{text!r} with {owned}: expected {expected}, got {got}"


def expect_error(text, **kw):
    try:
        rule(text, **kw)
    except RequiresError:
        return
    raise AssertionError(f"{text!r} should have raised RequiresError")


# basics
check("|Lantern|", {"Lantern": 1}, True)
check("|Lantern|", {}, False)
check("|Coin:3|", {"Coin": 3}, True)
check("|Coin:3|", {"Coin": 2}, False)
check("|Coin:50%|", {"Coin": 5}, True, totals={"Coin": 10})
check("|Coin:50%|", {"Coin": 4}, False, totals={"Coin": 10})

# boolean logic
check("|Lantern| and |Diving Bell|", {"Lantern": 1, "Diving Bell": 1}, True)
check("|Lantern| and |Diving Bell|", {"Lantern": 1}, False)
check("|Lantern| or |Diving Bell|", {"Diving Bell": 1}, True)
check("|Lantern| or |Diving Bell|", {}, False)
check("not |Lantern|", {}, True)
check("not |Lantern|", {"Lantern": 1}, False)
check("(|Lantern| or |Diving Bell|) and |Climbing Pick|",
      {"Diving Bell": 1, "Climbing Pick": 1}, True)
check("(|Lantern| or |Diving Bell|) and |Climbing Pick|", {"Diving Bell": 1}, False)
check("|Lantern| and |Diving Bell| or |Climbing Pick|", {"Climbing Pick": 1}, True)  # and binds tighter
check("not (|Lantern| and |Diving Bell|)", {"Lantern": 1}, True)

# names with spaces / keywords inside pipes are safe
check("|Climbing Pick|", {"Climbing Pick": 1}, True)
rule("|Salt and Pepper|", items=("Salt and Pepper",))  # parses, 'and' inside pipes is literal

# errors
expect_error("")
expect_error("|Lantern")          # unterminated
expect_error("|\n|")              # empty name -- note: stripped to empty
expect_error("|Unknown Item|")    # unknown item
expect_error("|Lantern| and")     # trailing operator
expect_error("(|Lantern|")        # missing paren
expect_error("|Lantern| |Diving Bell|")  # missing operator
expect_error("|Coin:0|")          # bad count
expect_error("|Coin:abc|")        # bad count
expect_error("|Coin:150%|")       # bad percent

print("all parser tests passed")

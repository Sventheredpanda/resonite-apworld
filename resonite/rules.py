"""Parser for Resonite world `requires` strings.

Grammar:
    expr     := or_term ("or" or_term)*
    or_term  := and_term ("and" and_term)*
    and_term := "not" and_term | primary
    primary  := "(" expr ")" | item_ref
    item_ref := "|" name (":" count)? "|"

Item references:
    |Lantern|      has at least 1 Lantern
    |Coin:25|      has at least 25 Coins
    |Coin:50%|     has at least 50% of the Coins in the item pool

Keywords (and/or/not) are only special outside |...| references, so an item
may be named e.g. "Salt and Pepper" without confusion.
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Callable, Dict, List, Set

if TYPE_CHECKING:
    from BaseClasses import CollectionState

Token = str


class RequiresError(ValueError):
    """Raised when a requires string is malformed or references unknown items."""


_TOKEN_RE = re.compile(r"\(|\)|\||[^\s()|]+")


def _tokenize(text: str) -> List[Token]:
    return [t for t in _TOKEN_RE.findall(text) if t.strip()]


class _Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self) -> Token | None:
        tok = self.peek()
        self.pos += 1
        return tok

    def parse(self) -> tuple:
        if not self.tokens:
            raise RequiresError("Empty requires string")
        node = self.parse_or()
        if self.pos != len(self.tokens):
            raise RequiresError(f"Unexpected trailing input: {' '.join(self.tokens[self.pos:])!r}")
        return node

    def parse_or(self) -> tuple:
        node = self.parse_and()
        while self.peek() == "or":
            self.advance()
            node = ("or", node, self.parse_and())
        return node

    def parse_and(self) -> tuple:
        node = self.parse_unary()
        while self.peek() == "and":
            self.advance()
            node = ("and", node, self.parse_unary())
        return node

    def parse_unary(self) -> tuple:
        if self.peek() == "not":
            self.advance()
            return ("not", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> tuple:
        tok = self.peek()
        if tok == "(":
            self.advance()
            node = self.parse_or()
            if self.peek() != ")":
                raise RequiresError("Missing closing parenthesis")
            self.advance()
            return node
        if tok == "|":
            return self.parse_item_ref()
        raise RequiresError(f"Unexpected {tok!r}; expected '(' or '|Item|'")

    def parse_item_ref(self) -> tuple:
        self.advance()  # consume opening |
        parts: List[str] = []
        while True:
            tok = self.peek()
            if tok == "|":
                self.advance()
                break
            if tok is None:
                raise RequiresError("Unterminated |item| reference")
            parts.append(tok)
            self.advance()
        raw = " ".join(parts).strip()
        if ":" in raw:
            name, _, suffix = raw.rpartition(":")
            name, suffix = name.strip(), suffix.strip()
        else:
            name, suffix = raw, None
        if not name:
            raise RequiresError("Empty item name in ||")
        return ("item", name, suffix)


def _compile(node: tuple, player: int, item_totals: Dict[str, int],
             known_items: Set[str]) -> Callable[[CollectionState], bool]:
    kind = node[0]
    if kind == "or":
        left = _compile(node[1], player, item_totals, known_items)
        right = _compile(node[2], player, item_totals, known_items)
        return lambda state, left=left, right=right: left(state) or right(state)
    if kind == "and":
        left = _compile(node[1], player, item_totals, known_items)
        right = _compile(node[2], player, item_totals, known_items)
        return lambda state, left=left, right=right: left(state) and right(state)
    if kind == "not":
        child = _compile(node[1], player, item_totals, known_items)
        return lambda state, child=child: not child(state)
    if kind == "item":
        _, name, suffix = node
        if name not in known_items:
            raise RequiresError(f"Unknown item {name!r} in requires string")
        count = 1
        if suffix is not None:
            if suffix.endswith("%"):
                try:
                    pct = float(suffix[:-1])
                except ValueError:
                    raise RequiresError(f"Bad percentage {suffix!r} in requires string")
                if not 0 < pct <= 100:
                    raise RequiresError(f"Percentage out of range: {suffix!r}")
                total = item_totals.get(name, 0)
                if total <= 0:
                    raise RequiresError(f"Cannot use percentage on item {name!r} with no copies in the pool")
                count = max(1, math.ceil(total * pct / 100))
            else:
                try:
                    count = int(suffix)
                except ValueError:
                    raise RequiresError(f"Bad count {suffix!r} in requires string")
                if count < 1:
                    raise RequiresError(f"Count must be positive: {suffix!r}")
        return lambda state, name=name, count=count, player=player: state.has(name, player, count)
    raise RequiresError(f"Internal error: bad AST node {node!r}")  # pragma: no cover


def parse_requires(text: str, player: int, item_totals: Dict[str, int],
                   known_items: Set[str]) -> Callable[[CollectionState], bool]:
    """Parse a requires string into a ``state -> bool`` rule function.

    :param text: the requires string, e.g. ``"|Lantern| and (|A| or |B:3|)"``
    :param player: the slot number the rule is for
    :param item_totals: mapping of item name -> total copies in the item pool
                        (needed for percentage requirements)
    :param known_items: set of valid item names; unknown references raise
    """
    parser = _Parser(_tokenize(text))
    return _compile(parser.parse(), player, item_totals, known_items)

#!/usr/bin/env bash
# End-to-end test: package the resonite apworld as a zip, install it into an
# Archipelago checkout, and generate a multiworld with two DIFFERENT Resonite
# definitions (both embedded in player YAMLs).
# Usage: AP_SRC=/path/to/Archipelago tests/test_generate.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AP_SRC="${AP_SRC:?set AP_SRC to an Archipelago checkout}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "== packaging apworld =="
rm -f "$AP_SRC"/custom_worlds/resonite*.apworld "$AP_SRC"/custom_worlds/resonite/__init__.py
(cd "$ROOT" && zip -qr "$WORK/resonite.apworld" resonite)
mkdir -p "$AP_SRC/custom_worlds"
cp "$WORK/resonite.apworld" "$AP_SRC/custom_worlds/resonite.apworld"

echo "== player yamls =="
mkdir -p "$WORK/Players"
cp "$ROOT/examples/crystal_caverns.yaml" "$WORK/Players/p1.yaml"
cp "$ROOT/examples/ember_depths.yaml" "$WORK/Players/p2.yaml"

echo "== generating =="
cd "$AP_SRC"
SKIP_REQUIREMENTS_UPDATE=1 python3 Generate.py \
  --player_files_path "$WORK/Players" --seed 12345 --outputpath "$WORK/output" < /dev/null

echo "== verifying =="
ZIP="$(ls "$WORK/output"/AP_*.zip | head -1)"
echo "generated: $ZIP"
unzip -o -q "$ZIP" -d "$WORK/unzipped"
SPOILER="$(ls "$WORK"/unzipped/AP_*_Spoiler.txt | head -1)"
grep -q "Game:                            Resonite" "$SPOILER"
grep -q "Tower - Summit Beacon" "$SPOILER"
grep -q "Core - Heart of the Mountain" "$SPOILER"
# cross-world placement: a CavernPlayer location holding an EmberPlayer item
grep -q "(CavernPlayer): .* (EmberPlayer)" "$SPOILER"
echo "OK: both definitions generated in one multiworld with cross-world placement"

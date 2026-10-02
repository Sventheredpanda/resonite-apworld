"""Resonite apworld: any Resonite game world, defined in the player YAML.

Each player YAML carries a ``world_definition``: regions, locations, items and
logic for one Resonite world. This module turns that definition into a working
Archipelago game at generation time.

Design notes for maintainers:

* ``item_name_to_id`` / ``location_name_to_id`` are built per-slot in
  ``generate_early()`` from the YAML definition and stored as *instance*
  attributes. They are intentionally empty at class level.
* Consequence: the shared ``"Resonite"`` DataPackage has no name maps, so
  generic name-resolving clients (e.g. Universal Tracker) cannot be used with
  this game. The blessed client is the in-world universal client, which reads
  the full name<->ID tables from ``slot_data`` (see ``fill_slot_data``).
* IDs are assigned in definition order (items 1..N, locations 1..M). Do not
  reorder or rename items/locations after a campaign starts; only append.
"""

from typing import Dict

from BaseClasses import Entrance, Item, ItemClassification, Location, Region
from worlds.AutoWorld import World
from worlds.generic.Rules import set_rule

from .definition import parse_definition
from .Options import ResoniteOptions
from .rules import parse_requires


class ResoniteWorld(World):
    game = "Resonite"
    options_dataclass = ResoniteOptions
    topology_present = True
    data_version = 1

    # Placeholder entry for the static datapackage (see get_data_package_data).
    _DATAPACKAGE_PLACEHOLDER = "(per-world names live in slot_data)"

    # Empty placeholders: the world metaclass requires these at class level.
    # The real tables are built per-slot in generate_early() from the YAML
    # definition and stored as instance attributes, shadowing these.
    item_name_to_id = {}
    location_name_to_id = {}

    def generate_early(self) -> None:
        self.definition = parse_definition(self.options.world_definition.value)
        # Instance-level tables: each slot may define a different world.
        self.item_name_to_id: Dict[str, int] = {
            name: i + 1 for i, name in enumerate(self.definition["items"])}
        self.location_name_to_id: Dict[str, int] = {
            name: i + 1 for i, name in enumerate(self.definition["locations"])}
        self.item_id_to_name = {v: k for k, v in self.item_name_to_id.items()}
        self.location_id_to_name = {v: k for k, v in self.location_name_to_id.items()}

    def create_item(self, name: str) -> Item:
        info = self.definition["items"][name]
        if info.get("trap"):
            classification = ItemClassification.trap
        elif info.get("progression"):
            classification = ItemClassification.progression
        elif info.get("useful"):
            classification = ItemClassification.useful
        else:
            classification = ItemClassification.filler
        return Item(name, classification, self.item_name_to_id[name], self.player)

    def create_regions(self) -> None:
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)

        regions: Dict[str, Region] = {}
        for region_name in self.definition["regions"]:
            region = Region(region_name, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            regions[region_name] = region

        for loc_name, loc_info in self.definition["locations"].items():
            parent = regions[loc_info["region"]]
            location = Location(self.player, loc_name, self.location_name_to_id[loc_name], parent)
            parent.locations.append(location)

        def link(source: Region, target: Region, name: str) -> Entrance:
            entrance = Entrance(self.player, name, source)
            source.exits.append(entrance)
            entrance.connect(target)
            return entrance

        link(menu, regions[self.definition["starting_region"]], "Starting Area")
        for region_name, region_info in self.definition["regions"].items():
            for target_name in region_info.get("connects_to", []):
                link(regions[region_name], regions[target_name], f"{region_name} -> {target_name}")

    def create_items(self) -> None:
        filler = self.definition["filler_item"]
        pool = []
        for name, info in self.definition["items"].items():
            if name == filler:
                continue
            pool.extend(self.create_item(name) for _ in range(info.get("count", 1)))
        missing = len(self.definition["locations"]) - len(pool)
        if missing < 0:
            raise Exception(f"Item pool ({len(pool)}) is larger than location count "
                            f"({len(self.definition['locations'])})")
        pool.extend(self.create_item(filler) for _ in range(missing))
        self.multiworld.itempool.extend(pool)

    def set_rules(self) -> None:
        player = self.player
        totals = {name: info.get("count", 1) for name, info in self.definition["items"].items()}
        known = set(self.definition["items"])

        # Region requirements gate *entering* the region: the rule goes on every
        # entrance whose target is the region.
        for region in self.multiworld.get_regions(player):
            for entrance in region.exits:
                target = entrance.connected_region
                if target is None or target.name not in self.definition["regions"]:
                    continue
                requires = self.definition["regions"][target.name].get("requires")
                if requires:
                    set_rule(entrance, parse_requires(requires, player, totals, known))

        for loc_name, loc_info in self.definition["locations"].items():
            requires = loc_info.get("requires")
            if requires:
                location = self.multiworld.get_location(loc_name, player)
                set_rule(location, parse_requires(requires, player, totals, known))

        victory = self.definition["victory_location"]
        self.multiworld.completion_condition[player] = (
            lambda state, victory=victory, player=player: state.can_reach(victory, "Location", player)
        )

    def get_filler_item_name(self) -> str:
        return self.definition["filler_item"]

    @classmethod
    def get_data_package_data(cls) -> dict:
        # The real name<->ID tables are per-slot: built in generate_early()
        # from the player YAML and shipped to the client via slot_data. There
        # is no meaningful static datapackage for this game, but we must still
        # ship one entry per map because:
        #  1. archipelago.gg validates every game's datapackage on upload, and
        #     its schema rejects empty maps ("Missing key: <class 'str'>");
        #  2. the live server requires the game to be present in the multidata
        #     datapackage (it has no installed copy of this apworld to fall
        #     back to).
        # The placeholder is never used in gameplay. Generic name-resolving
        # clients (e.g. Universal Tracker) are not supported for this game;
        # the universal in-world client reads the real tables from slot_data.
        from worlds.AutoWorld import data_package_checksum
        res = {
            # sorted alphabetically (required by data_package_checksum)
            "item_name_groups": {"Everything": []},
            "item_name_to_id": {cls._DATAPACKAGE_PLACEHOLDER: 1},
            "location_name_groups": {"Everywhere": []},
            "location_name_to_id": {cls._DATAPACKAGE_PLACEHOLDER: 1},
        }
        res["checksum"] = data_package_checksum(res)
        return res

    def fill_slot_data(self) -> Dict[str, object]:
        # The universal in-world client reads everything it needs from here,
        # since the shared DataPackage has no per-world name maps.
        return {
            "display_name": self.definition["display_name"],
            "goal": self.definition["victory_location"],
            "death_link": self.definition["death_link"],
            "item_name_to_id": self.item_name_to_id,
            "location_name_to_id": self.location_name_to_id,
        }

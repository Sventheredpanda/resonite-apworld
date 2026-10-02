from dataclasses import dataclass

from Options import FreeText, PerGameCommonOptions


class WorldDefinition(FreeText):
    """The whole Resonite world: regions, locations, items and logic, as YAML.

    Example:
        Resonite:
          world_definition: |
            regions:
              Base Camp:
                starting: true
                connects_to: [Crystal Caves]
            ...
    """
    display_name = "World Definition"


@dataclass
class ResoniteOptions(PerGameCommonOptions):
    world_definition: WorldDefinition

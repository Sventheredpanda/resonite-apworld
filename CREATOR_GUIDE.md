# Making your Resonite world Archipelago-ready

So you built a game world in Resonite and you want it playable as part of an
Archipelago randomizer. Good news: you don't have to learn the Archipelago
protocol, run any servers, or install anything weird. There are two halves to
this, and you do each one once.

## The big idea

Your world never talks to Archipelago directly. A small client system lives
inside the world and handles all of that. Your world's only job is telling the
client two things:

- "The player just found *this check*."
- "The player just received *this item* — do something with it."

Everything else is the client's problem.

## Half 1: describe your world (in text, once)

Before anyone can play, your world needs a definition: its items, regions,
locations, and what unlocks what. It's just YAML, and it lives inside each
player's YAML file when the multiworld gets generated — not inside the
Resonite world itself.

```yaml
Resonite:
  world_definition: |
    display_name: Crystal Caverns
    filler_item: Shiny Pebble

    items:
      Lantern: { progression: true }
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
        victory: true
```

Requirements are written like `|Lantern|`, combined with `and`, `or`, `not`
and parentheses. `|Coin:25|` means "25 coins", `|Coin:50%|` means "half your
coins". Mark one location `victory: true` — that's the goal.

One rule, and it's the serious one: **once a campaign starts, don't rename or
reorder items or locations.** The save file remembers them by position. Add new
stuff at the end all you like, but don't shuffle what's there.

## Half 2: wire up your world

Drop the universal client into your world. Then hook up three things:

**Checks.** Every location in your definition needs a moment in the world: a
chest opening, a button pressed, a zone walked into. When that moment happens,
hand the location's *exact name* to the client's check input.

Exact means exact. "Tower - Summit Beacon" is not "tower - summit beacon".
Copy-paste the names straight from your definition. This is the step everyone
messes up, so when something doesn't work, check the names first. It's always
the names.

**Items.** When the client receives an item, it hands your world the item's
name — that's all it does. *You* decide what each name means in your world:
spawn the Lantern in the player's hand, flash the screen red for a trap, play
a little fanfare. Think of it as the client shouting "Lantern!" and your world
deciding what "Lantern!" does.

(The exact node/variable names for the client's check input and item output
ship with the client itself — this guide covers what to connect, not the node
names.)

**Winning.** Nothing to do. When the check matching your victory location goes
in, the client tells Archipelago the game is beaten.

**DeathLink (optional).** If you enabled it in your definition, there are two
wires: when your player dies, tell the client so it can pass the death on; when
the client reports someone else's death, kill your player. That's the whole
loop. Same idea works for trap effects.

## When something doesn't work

- **A check never registers?** The name doesn't match your definition. Copy-paste it.
- **An item arrives and nothing happens?** Your world doesn't know what that item name means yet — you haven't wired it.
- **Everything worked yesterday and broke today?** Something got renamed or reordered in the definition after generating. Generate fresh and it'll behave.
- **"It works for me but not my friend"?** You both need to generate from the same definition. Same YAML, same multiworld.

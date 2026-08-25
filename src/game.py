"""
Depthcrawl Generator - game logic (Pyodide edition)

This module is a refactor of the original Flask-based `depthcrawl.py`.
All the actual generator logic (dice rolling, tables, treasure/encounter
rules) is unchanged. What changed:

  * No Flask / no HTTP request handling.
  * `session` (server-side, cookie-backed) is replaced by a single
    in-memory `SESSION` dict, since everything now runs inside the
    visitor's own browser tab (via Pyodide) - there is no server and
    no other visitor to separate sessions from.
  * The Jinja2 template (`templates/index.html`) is replaced by a
    small set of pure-Python HTML-rendering functions
    (`render_page`, `_render_treasure_result`, ...) that build the same
    markup the template used to produce. The CSS/JS shell around it
    now lives in the surrounding .html file instead of Flask.
"""

import math
import random
import re

import markdown

from data import (
    LEVEL_MODIFIERS,
    LOCATIONS, DETAILS,
    LOCATION_MODIFIERS, DETAIL_MODIFIERS,
    LOCATION_DESCRIPTIONS, DETAIL_DESCRIPTIONS,
    TREASURE_TABLES, TREASURE_QUALITY_TABLE, TREASURE_EXTRA_ITEMS_TABLE,
    CONSUMABLE_SUBTYPES, AMPULES_TABLE, POTIONS_TABLE, MISCELLANY_TABLE, ARTIFACTS_TABLE,
    NEXT_LEVEL, ROLL_TWICE, MONSTERS, MONSTERS_WITHOUT_TREASURE, ENCOUNTER_TABLES,
)

Table = list[tuple[int, str]]

DEFAULT_TREASURE_DC = 8
DEFAULT_ENCOUNTER_DC = 8


# ----------------------------
# LOGIC (unchanged from the Flask version)
# ----------------------------

def roll_table(table: Table, depth: int) -> tuple[int, str]:
    roll = random.randint(1, 20) + depth
    for max_value, result in table:
        if roll <= max_value:
            return roll, result
    raise RuntimeError("Invalid table")


def roll_dice(dice_str) -> int:
    """Parses strings like '1d3', '2d6' and returns a total."""
    if isinstance(dice_str, int):
        return dice_str
    n, die = map(int, dice_str.lower().split("d"))
    return sum(random.randint(1, die) for _ in range(n))


def collect_modifiers(room: dict | None, trigger: str) -> dict:
    """
    trigger: "room" | "ransack"

    `room` may be None (e.g. a "check_encounter" roll made before any
    location has been generated yet) - that's treated as "no
    location/detail modifiers apply", not an error.
    """

    # Safe defaults
    loc_mod = LOCATION_MODIFIERS.get((room or {}).get("location"), {}) or {}
    det_mod = DETAIL_MODIFIERS.get((room or {}).get("detail"), {}) or {}

    sources = [loc_mod, det_mod]

    mods = {
        "treasure_roll": 0,
        "treasure_quality": 0,
        "encounter_roll": 0,
        "no_treasure": False,
    }

    # --- blocking flags ---
    block_pos_treasure_roll = any(
        s.get("block_positive_treasure_roll", False) for s in sources
    )

    block_pos_treasure_quality = any(
        s.get("block_positive_treasure_quality", False) for s in sources
    )

    # --- absolute blockers ---
    if any(s.get("no_treasure", False) for s in sources):
        mods["no_treasure"] = True
        return mods  # early exit, nothing else matters

    # --- aggregate modifiers ---
    for source in sources:
        scope = source.get("scope", "all")
        if scope != "all" and scope != trigger:
            continue

        # TREASURE ROLL
        val = source.get("treasure_roll", 0)
        if val > 0 and block_pos_treasure_roll:
            pass  # suppressed
        else:
            mods["treasure_roll"] += val

        # TREASURE QUALITY
        val = source.get("treasure_quality", 0)
        if val > 0 and block_pos_treasure_quality:
            pass
        else:
            mods["treasure_quality"] += val

        # ENCOUNTER ROLL (no blocking in your ruleset)
        mods["encounter_roll"] += source.get("encounter_roll", 0)

    return mods


def generate_treasure(quality_mod=0, dungeon_level=1):
    raw_roll = random.randint(1, 6)
    quality_roll = max(0, min(12, raw_roll + quality_mod))

    count, quality = TREASURE_QUALITY_TABLE[quality_roll]

    # base treasure items
    item_list = [
        TREASURE_TABLES[quality][random.randint(1, 20)]
        for _ in range(count)
    ]

    # --- ADD EXTRA ITEMS ---
    extra_items = generate_extra_items(quality_roll, dungeon_level)
    item_list.extend(extra_items)

    return {
        "quality_roll": quality_roll,
        "quality_mod": quality_mod,
        "raw_quality_roll": raw_roll,
        "number_of_items": count + len(extra_items),
        "quality": quality,
        "item_list": item_list,
    }


def generate_paint():
    return "Dose of paint"


def generate_consumable(subtype=None):
    if subtype is None:
        subtype = random.choice(CONSUMABLE_SUBTYPES)
    if subtype == "potion":
        return f"Potion: {POTIONS_TABLE[random.randint(1, len(POTIONS_TABLE))]}"
    elif subtype == "ampule":
        return f"Ampule: {AMPULES_TABLE[random.randint(1, len(AMPULES_TABLE))]}"
    elif subtype == "arrow":
        return f"Arrow: {AMPULES_TABLE[random.randint(1, len(AMPULES_TABLE))]}"
    elif subtype == "miscellany":
        return f"Magic Item: {MISCELLANY_TABLE[random.randint(1, len(MISCELLANY_TABLE))]}"
    else:
        return None


def generate_artifact(level):
    roll = random.randint(1, 18)
    if level > 6:
        roll += 6
    return f"Artifact: {ARTIFACTS_TABLE[roll]}"


def generate_extra_items(treasure_quality, dungeon_level):
    items = []

    rules = TREASURE_EXTRA_ITEMS_TABLE.get(treasure_quality, [])
    for rule in rules:
        count = roll_dice(rule["amount"])
        for _ in range(count):
            category = rule["category"]

            if category == "paint":
                items.append(generate_paint())
            elif category == "artifact":
                items.append(generate_artifact(dungeon_level))
            elif category == "consumable":
                # pick random subtype if none given
                items.append(generate_consumable())
            elif category == "paint_or_consumable":
                if random.choice([True, False]):
                    items.append(generate_paint())
                else:
                    items.append(generate_consumable())
    return items


def roll_location_treasure(current_dc: int, mods: dict, dungeon_level=1) -> dict:
    if mods["no_treasure"]:
        return {
            "blocked": True,
            "raw_roll": None,
            "mod": 0,
            "roll": None,
            "success": False,
            "treasure": None,
            "next_dc": current_dc,
        }

    raw_roll = random.randint(1, 6)
    treasure_mod = mods["treasure_roll"]
    roll = raw_roll + treasure_mod

    if roll >= current_dc:
        treasure = generate_treasure(
            quality_mod=mods["treasure_quality"],
            dungeon_level=dungeon_level
        )

        return {
            "roll": roll,
            "raw_roll": raw_roll,
            "mod": treasure_mod,
            "success": True,
            "treasure": treasure,
            "next_dc": DEFAULT_TREASURE_DC,
        }
    else:
        reduction = max(0, math.ceil(roll / 2))
        next_dc = max(1, current_dc - reduction)
        return {
            "roll": roll,
            "raw_roll": raw_roll,
            "mod": treasure_mod,
            "success": False,
            "treasure": None,
            "next_dc": next_dc,
        }


def roll_random_encounter(current_dc: int, mods: dict):
    raw_roll = random.randint(1, 6)
    encounter_mod = mods["encounter_roll"]
    roll = raw_roll + encounter_mod

    if roll >= current_dc:
        return {
            "roll": roll,
            "raw_roll": raw_roll,
            "mod": encounter_mod,
            "success": True,
            "next_dc": DEFAULT_ENCOUNTER_DC,
        }
    else:
        reduction = max(0, math.ceil(roll / 2))
        next_dc = max(1, current_dc - reduction)
        return {
            "roll": roll,
            "raw_roll": raw_roll,
            "mod": encounter_mod,
            "success": False,
            "next_dc": next_dc,
        }


# ----------------------------
# ENCOUNTER MONSTER GROUPS
# ----------------------------
# See the big comment above ENCOUNTER_TABLES / MONSTERS in data.py for
# the data format this operates on.

class EncounterDataError(RuntimeError):
    """Raised when ENCOUNTER_TABLES / MONSTERS in data.py are invalid."""


_DICE_RE = re.compile(r"^(\d+)d(\d+)$", re.IGNORECASE)
_RANGE_RE = re.compile(r"^(\d+)-(\d+)$")
_INT_RE = re.compile(r"^-?\d+$")


def _half_level(level: int) -> int:
    return level // 2  # rounds down (level 3 -> 1)


def _roll_formula_term(term: str, level: int) -> int:
    term = term.strip()

    dice_match = _DICE_RE.match(term)
    if dice_match:
        count, sides = int(dice_match.group(1)), int(dice_match.group(2))
        return sum(random.randint(1, sides) for _ in range(count))

    range_match = _RANGE_RE.match(term)
    if range_match:
        low, high = int(range_match.group(1)), int(range_match.group(2))
        return random.randint(low, high)

    normalized = term.lower().replace("_", "-").replace(" ", "-")
    if normalized == "level":
        return level
    if normalized == "half-level":
        return _half_level(level)

    if _INT_RE.match(term):
        return int(term)

    raise ValueError(f"Can't parse encounter formula term {term!r}.")


def roll_monster_count(formula: str, level: int) -> int:
    """
    Evaluates a monster's "number formula" (e.g. "3-5 + half-level")
    for the given dungeon level, returning how many of that monster
    appear in one group. The result is never less than 1.
    """
    parts = re.split(r"\s+([+-])\s+", formula.strip())
    total = _roll_formula_term(parts[0], level)

    i = 1
    while i < len(parts):
        sign_str, term = parts[i], parts[i + 1]
        value = _roll_formula_term(term, level)
        total += value if sign_str == "+" else -value
        i += 2

    return max(1, total)


_MAX_ENCOUNTER_SUBROLLS = 50


class _RollBudget:
    """
    Guards against pathological ENCOUNTER_TABLES data (e.g. a
    NEXT_LEVEL/ROLL_TWICE combination that never settles on an actual
    monster) causing runaway recursion. Shared across one whole call
    to roll_encounter_group(), including all of its ROLL_TWICE
    branches.
    """

    __slots__ = ("remaining",)

    def __init__(self, remaining: int):
        self.remaining = remaining

    def spend(self) -> None:
        self.remaining -= 1
        if self.remaining < 0:
            raise EncounterDataError(
                f"Encounter roll used up its safety budget of "
                f"{_MAX_ENCOUNTER_SUBROLLS} sub-rolls - check "
                "ENCOUNTER_TABLES for a NEXT_LEVEL/ROLL_TWICE chain "
                "that never resolves to an actual monster."
            )


def roll_encounter_group(level: int) -> dict:
    """
    Rolls on the encounter table for `level` - one d6 picks the row
    (1-2 / 3-4 / 5-6), the other picks the column (1-6) - and returns
    the resulting monster group(s) plus some info about each roll,
    for display purposes.

    Normally this resolves to exactly one group, but ROLL_TWICE
    entries make it resolve to two (or more, if one of those two also
    happens to be ROLL_TWICE) - see the ENCOUNTER_TABLES comment in
    data.py.
    """
    level = max(1, min(12, level))
    groups = _roll_encounter_groups_at(level, _RollBudget(_MAX_ENCOUNTER_SUBROLLS))
    return {"requested_level": level, "groups": groups}


def _roll_encounter_groups_at(level: int, budget: _RollBudget) -> list:
    budget.spend()
    current_level = level

    while True:
        table = ENCOUNTER_TABLES[current_level]
        row_die, col_die = random.randint(1, 6), random.randint(1, 6)
        row_index = (row_die - 1) // 2  # 1-2 -> 0, 3-4 -> 1, 5-6 -> 2
        col_index = col_die - 1
        entry = table[row_index][col_index]

        if entry == NEXT_LEVEL:
            current_level += 1
            if current_level > 12:
                # _validate_encounter_data() should already have
                # caught this at import time - this is just a
                # runtime safety net against the same data bug.
                raise EncounterDataError(
                    "Encounter table cascaded past level 12 - level "
                    "12's table must not contain a NEXT_LEVEL entry."
                )
            budget.spend()
            continue

        if entry == ROLL_TWICE:
            return (
                _roll_encounter_groups_at(current_level, budget)
                + _roll_encounter_groups_at(current_level, budget)
            )

        count = sum(
            roll_monster_count(MONSTERS[entry["monster"]], current_level)
            for _ in range(entry["multiplier"])
        )
        return [{
            "rolled_on_level": current_level,
            "dice": (row_die, col_die),
            "row": row_index + 1,
            "column": col_die,
            "monster": entry["monster"],
            "multiplier": entry["multiplier"],
            "count": count,
        }]


def roll_monster_treasure(monsters, level, level_modifiers):
    """
    Rolls the treasure carried by an encountered monster group, using
    only the current dungeon level's modifiers (LEVEL_MODIFIERS
    "wealth") - deliberately *not* the location/detail modifiers that
    apply to a location's own treasure, since this loot belongs to the
    monster(s), not the place they were found in.

    Returns None if there's nothing to roll for (no encounter, or
    every monster present is in MONSTERS_WITHOUT_TREASURE - e.g. a
    plain "Critters" swarm never carries loot). If an encounter mixes
    a treasure-less monster with one that can carry treasure, this
    still rolls (once) for the encounter as a whole.
    """
    if not monsters:
        return None

    monster_names = {group["monster"] for group in monsters["groups"]}
    if not (monster_names - MONSTERS_WITHOUT_TREASURE):
        return None

    return generate_treasure(
        quality_mod=level_modifiers.get("wealth", 0) if level else 0,
        dungeon_level=level if level else 1,
    )


def _validate_encounter_data() -> None:
    """
    Sanity-checks ENCOUNTER_TABLES / MONSTERS from data.py. Runs once
    at import time so authoring mistakes (typo'd monster name, a
    missing cell, a NEXT_LEVEL on level 12, ...) surface immediately
    with a clear message instead of as a confusing crash mid-game.
    """
    expected_levels = set(range(1, 13))
    actual_levels = set(ENCOUNTER_TABLES.keys())
    if actual_levels != expected_levels:
        raise EncounterDataError(
            f"ENCOUNTER_TABLES must have exactly levels 1-12, got {sorted(actual_levels)}."
        )

    for level, table in ENCOUNTER_TABLES.items():
        if len(table) != 3:
            raise EncounterDataError(
                f"Encounter table for level {level} must have exactly "
                f"3 rows, got {len(table)}."
            )

        for row_index, row in enumerate(table):
            row_number = row_index + 1
            if len(row) != 6:
                raise EncounterDataError(
                    f"Level {level}, row {row_number} must have exactly "
                    f"6 entries (one per column die 1-6), got {len(row)}."
                )

            for col_index, entry in enumerate(row):
                col_number = col_index + 1

                if entry == NEXT_LEVEL:
                    if level >= 12:
                        raise EncounterDataError(
                            "Level 12's encounter table must not contain "
                            "a NEXT_LEVEL entry (there is no level 13 to "
                            f"cascade to) - check row {row_number}, "
                            f"column {col_number}."
                        )
                    continue

                if entry == ROLL_TWICE:
                    # Allowed on every level, including 12 - it rerolls
                    # on the *same* level's table, so it never needs a
                    # higher level to exist.
                    continue

                monster = entry.get("monster")
                if monster not in MONSTERS:
                    raise EncounterDataError(
                        f"Level {level}, row {row_number}, column "
                        f"{col_number} references unknown monster "
                        f"{monster!r}. Add it to MONSTERS in data.py."
                    )

                try:
                    roll_monster_count(MONSTERS[monster], level)
                except ValueError as exc:
                    raise EncounterDataError(
                        f"Monster {monster!r} has an invalid number "
                        f"formula {MONSTERS[monster]!r}: {exc}"
                    ) from exc


_validate_encounter_data()


# ----------------------------
# UI HELPERS (unchanged from the Flask version)
# ----------------------------

def format_roll(raw, mod):
    if raw is None:
        return "-"
    if mod is None or mod == 0:
        return str(raw)

    sign = "+" if mod > 0 else "\u2212"
    return f"{raw} {sign} {abs(mod)}"


def format_modifier(mod):
    sign = "+" if mod is None or mod >= 0 else "\u2212"
    return f"{sign}{abs(mod)}"


def render_md(text):
    return markdown.markdown(text)


def get_modifier_badge_class(key: str, value: int) -> str:
    if value == 0:
        return ""  # no badge needed

    if key == "population":
        return "negative" if value > 0 else "positive"
    else:
        return "positive" if value > 0 else "negative"


# ----------------------------
# STATE
# ----------------------------
# Replaces Flask's server-side `session`. There is only ever one
# "visitor" (the person looking at this browser tab), so a single
# module-level dict is all we need.

def _default_session() -> dict:
    return {
        "depth": 0,
        "room": None,
        "treasure": None,
        "treasure_dc": DEFAULT_TREASURE_DC,
        "encounter_dc": DEFAULT_ENCOUNTER_DC,
        "latest_encounter": None,
        "level": None,
        "level_modifiers": {},
    }


SESSION = _default_session()


# ----------------------------
# ACTION HANDLING
# (this is the former POST-branch of the Flask `index()` view)
# ----------------------------

def _to_int_or_none(value):
    if value is None or value == "":
        return None
    return int(value)


def handle_action(action, depth_form=None, level_form=None):
    """
    Mirrors the POST branch of the original Flask route.

    `action` is one of "room", "check_encounter", "treasure", "reset",
    or None (None happens when only the Level dropdown changed, just
    like the original template's `onchange="this.form.submit()"`
    produced a plain POST without an `action` field).
    """
    global SESSION

    depth = SESSION.get("depth", 0)
    room = SESSION.get("room")
    treasure = SESSION.get("treasure")
    treasure_dc = SESSION.get("treasure_dc", DEFAULT_TREASURE_DC)
    encounter_dc = SESSION.get("encounter_dc", DEFAULT_ENCOUNTER_DC)
    latest_encounter = SESSION.get("latest_encounter")

    # read depth/level "from the form", same as the Flask version did
    depth_raw = _to_int_or_none(depth_form)
    if depth_raw is not None:
        depth = depth_raw

    level = _to_int_or_none(level_form)
    level_modifiers = LEVEL_MODIFIERS.get(level, {})

    if action == "room":
        used_depth = depth
        loc_roll, location = roll_table(LOCATIONS, used_depth)
        det_roll, detail = roll_table(DETAILS, used_depth)

        room = {
            "used_depth": used_depth,
            "location_roll": loc_roll,
            "location": location,
            "location_text": LOCATION_DESCRIPTIONS.get(location, "No description available."),
            "detail_roll": det_roll,
            "detail": detail,
            "detail_text": DETAIL_DESCRIPTIONS.get(detail, "No description available."),
            "treasure_result": None,
        }

        # --- Roll the treasure hidden in this location, right now.
        # Unlike the encounter check below, this is shown immediately -
        # there's no separate "search" step for treasure anymore.
        treasure_mods = collect_modifiers(room, trigger="ransack")
        treasure_mods["treasure_roll"] += level_modifiers.get("wealth", 0)
        treasure_mods["treasure_quality"] += level_modifiers.get("wealth", 0)

        treasure_dc_before = treasure_dc
        treasure_check = roll_location_treasure(
            treasure_dc, treasure_mods, dungeon_level=used_depth
        )
        treasure_dc = treasure_check["next_dc"]

        room["treasure_result"] = {
            "treasure_roll": treasure_check["roll"],
            "raw_roll": treasure_check["raw_roll"],
            "mod": treasure_check["mod"],
            "treasure_dc_before": treasure_dc_before,
            "found_treasure": treasure_check["treasure"],
            "blocked": treasure_check.get("blocked", False),
        }

        # --- Random encounter check for entering the location.
        encounter_mods = collect_modifiers(room, trigger="room")
        encounter_mods["encounter_roll"] += level_modifiers.get("population", 0)

        encounter_dc_before = encounter_dc
        encounter_check = roll_random_encounter(encounter_dc, encounter_mods)
        encounter_dc = encounter_check["next_dc"]

        monsters = (
            roll_encounter_group(level if level else 1)
            if encounter_check["success"]
            else None
        )
        monster_treasure = roll_monster_treasure(monsters, level, level_modifiers)

        latest_encounter = {
            "source": "Entering location",
            "roll": encounter_check["roll"],
            "raw_roll": encounter_check["raw_roll"],
            "mod": encounter_check["mod"],
            "dc_before": encounter_dc_before,
            "monsters": monsters,
            "treasure": monster_treasure,
            "success": encounter_check["success"],
        }

        depth = used_depth + 1

    elif action == "check_encounter":
        # A standalone risk check (e.g. searching around, listening at
        # a door, ...) - not tied to the location's own treasure at
        # all (that's already visible from the moment the location
        # was generated), but an encountered monster can still be
        # carrying loot of its own - see roll_monster_treasure().
        # Works even with no location generated yet (room is None):
        # collect_modifiers() then simply applies no location/detail
        # modifiers, just the current level's.
        mods = collect_modifiers(room, trigger="ransack")
        mods["encounter_roll"] += level_modifiers.get("population", 0)

        encounter_dc_before = encounter_dc
        encounter_check = roll_random_encounter(encounter_dc, mods)
        encounter_dc = encounter_check["next_dc"]

        monsters = (
            roll_encounter_group(level if level else 1)
            if encounter_check["success"]
            else None
        )
        monster_treasure = roll_monster_treasure(monsters, level, level_modifiers)

        latest_encounter = {
            "source": "Checking for encounter",
            "roll": encounter_check["roll"],
            "raw_roll": encounter_check["raw_roll"],
            "mod": encounter_check["mod"],
            "dc_before": encounter_dc_before,
            "monsters": monsters,
            "treasure": monster_treasure,
            "success": encounter_check["success"],
        }

    elif action == "treasure":
        treasure = generate_treasure(
            quality_mod=level_modifiers.get("wealth", 0) if level else 0,
            dungeon_level=room["used_depth"] if room else 1,
        )

    elif action == "reset":
        SESSION = _default_session()
        return

    SESSION = {
        "depth": depth,
        "room": room,
        "treasure": treasure,
        "treasure_dc": treasure_dc,
        "encounter_dc": encounter_dc,
        "latest_encounter": latest_encounter,
        "level": level,
        "level_modifiers": level_modifiers,
    }


# ----------------------------
# RENDERING
# (this replaces templates/index.html)
# ----------------------------

def _render_level_options(level):
    parts = [
        '<option value="" {} disabled>\u2014 Select Level \u2014</option>'.format(
            "selected" if level is None else ""
        )
    ]
    for lvl in range(1, 13):
        selected = "selected" if lvl == level else ""
        parts.append(f'<option value="{lvl}" {selected}>Level {lvl}</option>')
    return "\n".join(parts)


def _render_meta_badges(level_modifiers):
    parts = []
    for key, value in level_modifiers.items():
        if value != 0:
            cls = get_modifier_badge_class(key, value)
            label = key.replace("_", " ").title()
            parts.append(
                f'<span class="meta-badge {cls}">{label} {format_modifier(value)}</span>'
            )
    return "".join(parts)


def _render_item_list(item_list):
    return "".join(f"\u2022 {item}<br>" for item in item_list)


def _render_treasure_result(room):
    result = room["treasure_result"]
    if result.get("blocked"):
        return "<em>No treasure can be found here.</em>"

    badge = (
        '<span class="badge badge-success">Success</span>'
        if result["found_treasure"]
        else '<span class="badge badge-fail">Failure</span>'
    )

    html = (
        f"Rolled "
        f'<span class="recent-roll">{format_roll(result["raw_roll"], result["mod"])}</span> '
        f'vs DC {result["treasure_dc_before"]} {badge}<br><br>'
    )

    found = result["found_treasure"]
    if found:
        html += (
            "<strong>Treasure Found!</strong><br>"
            f'<strong>Quality:</strong> {found["quality"]} '
            f'<span class="recent-roll">(Rolled '
            f'{format_roll(found["raw_quality_roll"], found["quality_mod"])})</span><br>'
            f'<strong>Number of Items:</strong> {found["number_of_items"]}<br><br>'
            f'{_render_item_list(found["item_list"])}'
        )
    else:
        html += "<em>No treasure was found here.</em>"

    return html


def _render_location_section():
    room = SESSION.get("room")
    level = SESSION.get("level")
    level_modifiers = SESSION.get("level_modifiers", {})

    if not room:
        return (
            '<div class="section">'
            "<strong>Location:</strong><br>"
            "<em>Press 'Generate Location' to generate a new location.</em>"
            "</div>"
        )

    return f"""
    <div class="section">
        <div class="meta-line">
            Level {level} &middot; Depth {room['used_depth']}
            {_render_meta_badges(level_modifiers)}
        </div>

        <strong>Location ({room['location_roll']}):</strong> {room['location']}
        <div class="description">{render_md(room['location_text'])}</div>

        <strong>Detail ({room['detail_roll']}):</strong> {room['detail']}
        <div class="description">{render_md(room['detail_text'])}</div>

        <hr>

        <strong>Treasure:</strong><br>
        {_render_treasure_result(room)}
    </div>
    """


def _render_encounter_monsters(latest_encounter):
    if not latest_encounter["success"]:
        return "<em>No encounter.</em>"

    monsters = latest_encounter.get("monsters")
    groups = monsters.get("groups") if monsters else None
    if not groups:
        # Shouldn't normally happen (a successful check always rolls at
        # least one group), but render *something* sensible if it ever does.
        return "<strong>A random encounter occurs!</strong>"

    requested_level = monsters["requested_level"]
    lines = []
    for group in groups:
        cascade_note = ""
        if group["rolled_on_level"] != requested_level:
            cascade_note = (
                f' <span class="meta-badge">rolled on Level '
                f'{group["rolled_on_level"]} table</span>'
            )
        row_die, col_die = group["dice"]
        lines.append(
            f'<span class="recent-roll">{group["count"]}&times; {group["monster"]}</span>'
            f" (row d6: {row_die} \u2192 row {group['row']}, column d6: {col_die}){cascade_note}"
        )

    return "<strong>A random encounter occurs!</strong><br>" + "<br>".join(lines)


def _render_encounter_treasure(latest_encounter):
    treasure = latest_encounter.get("treasure")
    if not treasure:
        return ""

    return f"""
    <hr>
    <strong>Loot:</strong><br>
    <strong>Quality:</strong> {treasure['quality']}
    <span class="recent-roll">
        (Rolled {format_roll(treasure['raw_quality_roll'], treasure['quality_mod'])})
    </span><br>
    <strong>Number of Items:</strong> {treasure['number_of_items']}<br><br>
    {_render_item_list(treasure['item_list'])}
    """


def _render_encounter_section():
    latest_encounter = SESSION.get("latest_encounter")

    if not latest_encounter:
        return (
            '<div class="section">'
            "<strong>Random Encounter:</strong><br>"
            "<em>No encounter check yet.</em>"
            "</div>"
        )

    badge = (
        '<span class="badge badge-warning">Encounter</span>'
        if latest_encounter["success"]
        else '<span class="badge badge-fail">Safe</span>'
    )
    result_text = _render_encounter_monsters(latest_encounter)
    treasure_html = _render_encounter_treasure(latest_encounter)

    return f"""
    <div class="section">
        <strong>Random Encounter:</strong><br>
        <strong>Trigger:</strong> {latest_encounter['source']}<br>
        Rolled
        <span class="recent-roll">
            {format_roll(latest_encounter['raw_roll'], latest_encounter['mod'])}
        </span>
        vs DC {latest_encounter['dc_before']}
        {badge}
        <br><br>
        {result_text}
        {treasure_html}
    </div>
    """


def _render_treasure_section():
    treasure = SESSION.get("treasure")

    if not treasure:
        return (
            '<div class="section">'
            "<em>Press 'Generate Treasure' to generate additional treasure.</em>"
            "</div>"
        )

    return f"""
    <div class="section">
        <strong>Treasure Generated!</strong><br>
        <strong>Quality:</strong> {treasure['quality']}
        <span class="recent-roll">
            (Rolled {format_roll(treasure['raw_quality_roll'], treasure['quality_mod'])})
        </span><br>
        <strong>Number of Items:</strong> {treasure['number_of_items']}<br><br>
        {_render_item_list(treasure['item_list'])}
    </div>
    """


def render_page():
    """Builds the full inner HTML for the #app container, based on
    the current SESSION state. Equivalent to rendering
    templates/index.html with Flask/Jinja."""

    depth = SESSION.get("depth", 0)
    level = SESSION.get("level")

    form_html = f"""
    <form onsubmit="return false;">
        <div class="form-row">
            <label for="level">Level:</label>
            <select name="level" id="level" onchange="onLevelChange()">
                {_render_level_options(level)}
            </select>

            <label for="depth">Depth:</label>
            <input type="number" id="depth" name="depth" value="{depth}">
        </div>

        <div class="button-row">
            <button type="button" onclick="runAction('room')">Generate Location</button>
            <button type="button" onclick="runAction('check_encounter')">
                Check for Encounter
            </button>
            <button type="button" onclick="runAction('treasure')">Generate Treasure</button>
            <button type="button" onclick="runAction('reset')">Reset</button>
        </div>
    </form>
    """

    return (
        form_html
        + _render_encounter_section()
        + _render_location_section()
        + _render_treasure_section()
    )

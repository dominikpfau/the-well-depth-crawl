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
    (`render_page`, `_render_location_view`, ...) that build the same
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

    # --- ADD EXTRA ITEMS (paint, consumables, artifacts, ...) ---
    extra_items = generate_extra_items(quality_roll, dungeon_level)
    item_list.extend(extra_items)

    return {
        "quality_roll": quality_roll,
        "quality_mod": quality_mod,
        "raw_quality_roll": raw_roll,
        "base_item_count": count,
        "extra_item_count": len(extra_items),
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


def _roll_formula_term_detailed(term: str, level: int) -> tuple:
    """Like _roll_formula_term(), but also returns a short human-
    readable fragment describing what was rolled, e.g. "1d6\u21924" or
    "half-level\u21922"."""
    term = term.strip()

    dice_match = _DICE_RE.match(term)
    if dice_match:
        count, sides = int(dice_match.group(1)), int(dice_match.group(2))
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        if count > 1:
            return total, f"{term}\u2192{'+'.join(str(r) for r in rolls)}"
        return total, f"{term}\u2192{total}"

    range_match = _RANGE_RE.match(term)
    if range_match:
        low, high = int(range_match.group(1)), int(range_match.group(2))
        value = random.randint(low, high)
        return value, f"{term}\u2192{value}"

    normalized = term.lower().replace("_", "-").replace(" ", "-")
    if normalized == "level":
        return level, f"level\u2192{level}"
    if normalized == "half-level":
        value = _half_level(level)
        return value, f"half-level\u2192{value}"

    if _INT_RE.match(term):
        return int(term), term

    raise ValueError(f"Can't parse encounter formula term {term!r}.")


def _roll_formula_term(term: str, level: int) -> int:
    value, _ = _roll_formula_term_detailed(term, level)
    return value


def roll_monster_count_detailed(formula: str, level: int) -> tuple:
    """
    Evaluates a monster's "number formula" (e.g. "3-5 + half-level")
    for the given dungeon level, returning (count, description) - the
    resulting number (never less than 1) plus a short human-readable
    breakdown of how it was rolled, for display in the UI.
    """
    parts = re.split(r"\s+([+-])\s+", formula.strip())
    value, first_desc = _roll_formula_term_detailed(parts[0], level)
    total = value
    desc_parts = [first_desc]

    i = 1
    while i < len(parts):
        sign_str, term = parts[i], parts[i + 1]
        term_value, term_desc = _roll_formula_term_detailed(term, level)
        total += term_value if sign_str == "+" else -term_value
        desc_parts.append(f"{sign_str} {term_desc}")
        i += 2

    clamped = max(1, total)
    description = " ".join(desc_parts)
    if len(desc_parts) > 1 or clamped != total:
        description = f"{description} = {clamped}"

    return clamped, description


def roll_monster_count(formula: str, level: int) -> int:
    """
    Evaluates a monster's "number formula" (e.g. "3-5 + half-level")
    for the given dungeon level, returning how many of that monster
    appear in one group. The result is never less than 1.
    """
    value, _ = roll_monster_count_detailed(formula, level)
    return value


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

        rolls = [
            roll_monster_count_detailed(MONSTERS[entry["monster"]], current_level)
            for _ in range(entry["multiplier"])
        ]
        count = sum(value for value, _ in rolls)
        count_breakdown = (
            rolls[0][1]
            if len(rolls) == 1
            else " + ".join(f"({desc})" for _, desc in rolls) + f" = {count}"
        )
        return [{
            "rolled_on_level": current_level,
            "dice": (row_die, col_die),
            "row": row_index + 1,
            "column": col_die,
            "monster": entry["monster"],
            "multiplier": entry["multiplier"],
            "count": count,
            "count_breakdown": count_breakdown,
        }]


def roll_monster_treasure(monsters, level, level_modifiers, current_dc):
    """
    Rolls (against `current_dc` - the same running "treasure DC" a
    location's own treasure uses) whether an encountered monster
    group is carrying treasure, using only the current dungeon
    level's modifiers (LEVEL_MODIFIERS "wealth") - deliberately *not*
    the location/detail modifiers a location's own treasure uses,
    since this loot belongs to the monster(s), not the place they
    were found in.

    Returns None if there's nothing to roll for at all (no encounter,
    or every monster present is in MONSTERS_WITHOUT_TREASURE - e.g. a
    plain "Critters" swarm never carries loot, no roll even attempted).
    If an encounter mixes a treasure-less monster with one that can
    carry treasure, this still rolls (once) for the encounter as a
    whole.

    Otherwise returns a dict shaped exactly like
    roll_location_treasure()'s result: "roll", "raw_roll", "mod",
    "success", "treasure" (None on failure), "next_dc".
    """
    if not monsters:
        return None

    monster_names = {group["monster"] for group in monsters["groups"]}
    if not (monster_names - MONSTERS_WITHOUT_TREASURE):
        return None

    wealth_mod = level_modifiers.get("wealth", 0) if level else 0
    mods = {
        "treasure_roll": wealth_mod,
        "treasure_quality": wealth_mod,
        "encounter_roll": 0,
        "no_treasure": False,
    }
    raw_result = roll_location_treasure(
        current_dc, mods, dungeon_level=level if level else 1
    )

    # Normalize to the same shape room["treasure_result"] uses, so
    # _render_treasure_check_result() can render either one.
    return {
        "raw_roll": raw_result["raw_roll"],
        "mod": raw_result["mod"],
        "treasure_dc_before": current_dc,
        "found_treasure": raw_result["treasure"],
        "blocked": raw_result.get("blocked", False),
        "next_dc": raw_result["next_dc"],
    }


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
        "crawl_depth": 0,
        "crawl_history": [],
        "crawl_current_id": None,
        "treasure": None,
        "treasure_dc": DEFAULT_TREASURE_DC,
        "encounter_dc": DEFAULT_ENCOUNTER_DC,
        "encounter_check": None,
        "level": None,
        "level_modifiers": {},
        "active_view": "location",
        "roll_treasure": True,
        "roll_encounter": True,
        "encounter_roll_treasure": True,
        "forced_location": None,
        "forced_detail": None,
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


def _generate_room(
    used_depth, level, level_modifiers, roll_treasure, roll_encounter,
    treasure_dc, encounter_dc, forced_location=None, forced_detail=None,
):
    """
    Rolls a fresh location at `used_depth` - optionally its own
    treasure and an entering encounter, depending on the two flags.
    Shared by the Location Generator's "room" action (where
    roll_treasure/roll_encounter come from the person's checkboxes)
    and Crawling Mode's "go_deeper" (where both are always True - no
    checkboxes there).

    `forced_location` / `forced_detail`, if given, are used directly
    instead of rolling on LOCATIONS / DETAILS (the Location
    Generator's two dropdowns - Crawling Mode never sets these, it
    always rolls randomly). The room's "location_roll"/"detail_roll"
    are then None, since nothing was actually rolled for that part.

    Returns (room, treasure_dc, encounter_dc) - the room, plus the
    shared DC pools after whichever rolls happened.
    """
    if forced_location:
        loc_roll, location = None, forced_location
    else:
        loc_roll, location = roll_table(LOCATIONS, used_depth)

    if forced_detail:
        det_roll, detail = None, forced_detail
    else:
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
        "entering_encounter": None,
    }

    # --- Roll the treasure hidden in this location, right now. Shown
    # immediately - there's no separate "search" step for treasure
    # anymore. Skipped entirely (room["treasure_result"] stays None)
    # if roll_treasure is False - the Treasure section then just
    # isn't shown, rather than shown empty.
    if roll_treasure:
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

    # --- Random encounter check for entering the location. Skipped
    # entirely (room["entering_encounter"] stays None) if
    # roll_encounter is False.
    if roll_encounter:
        encounter_mods = collect_modifiers(room, trigger="room")
        encounter_mods["encounter_roll"] += level_modifiers.get("population", 0)

        encounter_dc_before = encounter_dc
        entering_check = roll_random_encounter(encounter_dc, encounter_mods)
        encounter_dc = entering_check["next_dc"]

        monsters = (
            roll_encounter_group(level if level else 1)
            if entering_check["success"]
            else None
        )
        # An encounter met while entering a location never carries its
        # own treasure - only the location itself does (governed by
        # roll_treasure above, shown in its own section).
        room["entering_encounter"] = {
            "raw_roll": entering_check["raw_roll"],
            "mod": entering_check["mod"],
            "dc_before": encounter_dc_before,
            "monsters": monsters,
            "treasure": None,
            "success": entering_check["success"],
        }

    return room, treasure_dc, encounter_dc


def handle_action(
    action,
    depth_form=None,
    level_form=None,
    view_form=None,
    roll_treasure_form=None,
    roll_encounter_form=None,
    encounter_roll_treasure_form=None,
    encounter_dc_form=None,
    treasure_dc_form=None,
    location_form=None,
    detail_form=None,
):
    """
    Mirrors the POST branch of the original Flask route.

    `action` is one of "room", "check_encounter", "generate_encounter",
    "treasure", "check_treasure", "switch_view", "reset", or None
    (None happens when only the Level dropdown changed, just like the
    original template's `onchange="this.form.submit()"` produced a
    plain POST without an `action` field).

    `view_form` is only used by "switch_view" - which view
    ("location" | "encounter" | "treasure") to make active.

    `roll_treasure_form` / `roll_encounter_form` are the Location
    Generator's two checkboxes (JS booleans, or None when the field
    isn't in the DOM right now - e.g. any view other than Location).
    They control whether "room" rolls for treasure / an entering
    encounter at all; when off, that part of the location isn't
    rolled - and so isn't shown - rather than being rolled and hidden.

    `encounter_roll_treasure_form` is the Encounter Generator's own
    "Roll for Treasure" checkbox (separate preference from the
    Location Generator's) - controls whether an encountered monster's
    own loot is even attempted, for both "check_encounter" and
    "generate_encounter".

    `encounter_dc_form` / `treasure_dc_form` are the two DC fields in
    the header (always present, any view) - like `depth_form`, they
    let the person directly edit the shared running DC pools instead
    of just watching them drift from rolls.

    `location_form` / `detail_form` are the Location Generator's two
    dropdowns for picking a specific location/detail by name instead
    of rolling for it - empty string (or None, meaning "field not in
    the DOM right now") means "Random", the usual roll.
    """
    global SESSION

    depth = SESSION.get("depth", 0)
    room = SESSION.get("room")
    crawl_depth = SESSION.get("crawl_depth", 0)
    crawl_history = list(SESSION.get("crawl_history", []))
    crawl_current_id = SESSION.get("crawl_current_id")
    treasure = SESSION.get("treasure")
    treasure_dc = SESSION.get("treasure_dc", DEFAULT_TREASURE_DC)
    encounter_dc = SESSION.get("encounter_dc", DEFAULT_ENCOUNTER_DC)
    encounter_check = SESSION.get("encounter_check")
    active_view = SESSION.get("active_view", "location")
    roll_treasure = SESSION.get("roll_treasure", True)
    roll_encounter = SESSION.get("roll_encounter", True)
    encounter_roll_treasure = SESSION.get("encounter_roll_treasure", True)
    forced_location = SESSION.get("forced_location")
    forced_detail = SESSION.get("forced_detail")

    # read depth/level "from the form", same as the Flask version did
    depth_raw = _to_int_or_none(depth_form)
    if depth_raw is not None:
        depth = depth_raw

    level = _to_int_or_none(level_form)
    level_modifiers = LEVEL_MODIFIERS.get(level, {})

    encounter_dc_raw = _to_int_or_none(encounter_dc_form)
    if encounter_dc_raw is not None:
        encounter_dc = encounter_dc_raw

    treasure_dc_raw = _to_int_or_none(treasure_dc_form)
    if treasure_dc_raw is not None:
        treasure_dc = treasure_dc_raw

    if location_form is not None:
        forced_location = location_form or None
    if detail_form is not None:
        forced_detail = detail_form or None

    if roll_treasure_form is not None:
        roll_treasure = bool(roll_treasure_form)
    if roll_encounter_form is not None:
        roll_encounter = bool(roll_encounter_form)
    if encounter_roll_treasure_form is not None:
        encounter_roll_treasure = bool(encounter_roll_treasure_form)

    if action == "room":
        used_depth = depth
        room, treasure_dc, encounter_dc = _generate_room(
            used_depth, level, level_modifiers, roll_treasure, roll_encounter,
            treasure_dc, encounter_dc,
            forced_location=forced_location, forced_detail=forced_detail,
        )
        depth = used_depth + 1

    elif action == "go_deeper":
        # Crawling Mode: always rolls both treasure and an entering
        # encounter (no checkboxes here) and always advances its own,
        # separate depth counter - never user-editable, unlike the
        # Location Generator's depth field.
        #
        # Every room gets an "id" and a "parent_id" (the room it was
        # reached from - None for the very first one) instead of just
        # relying on its position in crawl_history. Right now, with
        # only "go_deeper" implemented, parent_id always points at
        # whatever was current, so this can only ever produce a single
        # straight line - but once "Go Back" exists and lets someone
        # go_deeper again from an *earlier* room, the same linking
        # scheme naturally produces a second branch from that room,
        # with no changes needed to how rooms are stored. crawl_history
        # itself stays a flat, append-only list of every room ever
        # generated (across all branches) - crawl_current_id marks
        # which one is "where we are now", and _crawl_path_to_current()
        # walks parent_id links to reconstruct the active path through
        # it for display.
        new_room, treasure_dc, encounter_dc = _generate_room(
            crawl_depth, level, level_modifiers, True, True,
            treasure_dc, encounter_dc,
        )
        new_room["id"] = len(crawl_history)
        new_room["parent_id"] = crawl_current_id
        crawl_history.append(new_room)
        crawl_current_id = new_room["id"]
        crawl_depth += 1

    elif action == "check_encounter":
        # A standalone risk check (e.g. searching around, listening at
        # a door, ...) shown in its own Encounter Generator view - not
        # tied to a location's own treasure at all, but an encountered
        # monster can still be carrying loot of its own - see
        # roll_monster_treasure(). Works even with no location
        # generated yet (room is None): collect_modifiers() then simply
        # applies no location/detail modifiers, just the current level's.
        mods = collect_modifiers(room, trigger="ransack")
        mods["encounter_roll"] += level_modifiers.get("population", 0)

        encounter_dc_before = encounter_dc
        check = roll_random_encounter(encounter_dc, mods)
        encounter_dc = check["next_dc"]

        monsters = (
            roll_encounter_group(level if level else 1)
            if check["success"]
            else None
        )
        monster_treasure = (
            roll_monster_treasure(monsters, level, level_modifiers, treasure_dc)
            if encounter_roll_treasure
            else None
        )
        if monster_treasure is not None:
            treasure_dc = monster_treasure["next_dc"]

        encounter_check = {
            "mode": "rolled",
            "raw_roll": check["raw_roll"],
            "mod": check["mod"],
            "dc_before": encounter_dc_before,
            "monsters": monsters,
            "treasure": monster_treasure,
            "success": check["success"],
        }

    elif action == "generate_encounter":
        # Skips the "does an encounter even happen" DC check entirely
        # and just directly rolls a monster group - the Encounter
        # Generator's equivalent of the Treasure Generator's
        # unconditional "Generate Treasure" button. Doesn't touch
        # encounter_dc, since no check actually happened; the
        # monster's own loot (if any) is still a real DC-gated
        # treasure roll though, same as everywhere else.
        monsters = roll_encounter_group(level if level else 1)
        monster_treasure = (
            roll_monster_treasure(monsters, level, level_modifiers, treasure_dc)
            if encounter_roll_treasure
            else None
        )
        if monster_treasure is not None:
            treasure_dc = monster_treasure["next_dc"]

        encounter_check = {
            "mode": "generated",
            "raw_roll": None,
            "mod": None,
            "dc_before": None,
            "monsters": monsters,
            "treasure": monster_treasure,
            "success": True,
        }

    elif action == "check_treasure":
        # The Treasure Generator's DC-gated counterpart to "treasure"
        # below - a real check against the same shared treasure_dc
        # pool everything else uses, using only the current level's
        # wealth modifier (no location/detail context, same as
        # roll_monster_treasure()). Can fail ("nothing found").
        wealth_mod = level_modifiers.get("wealth", 0) if level else 0
        mods = {
            "treasure_roll": wealth_mod,
            "treasure_quality": wealth_mod,
            "encounter_roll": 0,
            "no_treasure": False,
        }
        treasure_dc_before = treasure_dc
        check = roll_location_treasure(
            treasure_dc, mods, dungeon_level=level if level else 1
        )
        treasure_dc = check["next_dc"]

        treasure = {
            "mode": "rolled",
            "raw_roll": check["raw_roll"],
            "mod": check["mod"],
            "treasure_dc_before": treasure_dc_before,
            "found_treasure": check["treasure"],
            "blocked": check.get("blocked", False),
        }

    elif action == "treasure":
        # Unconditional - always finds something, no DC check, no
        # treasure_dc consumption. The Treasure Generator's equivalent
        # of the Encounter Generator's "generate_encounter".
        generated = generate_treasure(
            quality_mod=level_modifiers.get("wealth", 0) if level else 0,
            dungeon_level=room["used_depth"] if room else 1,
        )
        treasure = {
            "mode": "generated",
            "raw_roll": None,
            "mod": None,
            "treasure_dc_before": None,
            "found_treasure": generated,
            "blocked": False,
        }

    elif action == "switch_view":
        if view_form in ("location", "encounter", "treasure", "crawling"):
            active_view = view_form

    elif action == "reset":
        SESSION = _default_session()
        return

    SESSION = {
        "depth": depth,
        "room": room,
        "crawl_depth": crawl_depth,
        "crawl_history": crawl_history,
        "crawl_current_id": crawl_current_id,
        "treasure": treasure,
        "treasure_dc": treasure_dc,
        "encounter_dc": encounter_dc,
        "encounter_check": encounter_check,
        "level": level,
        "level_modifiers": level_modifiers,
        "active_view": active_view,
        "roll_treasure": roll_treasure,
        "roll_encounter": roll_encounter,
        "encounter_roll_treasure": encounter_roll_treasure,
        "forced_location": forced_location,
        "forced_detail": forced_detail,
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


def _render_choice_options(names, current_value):
    """Builds <option> tags for a "pick one, or leave on Random"
    dropdown - used by the Location Generator's Location/Detail
    selects."""
    parts = [
        '<option value="" {}>Random</option>'.format(
            "selected" if not current_value else ""
        )
    ]
    for name in names:
        selected = "selected" if name == current_value else ""
        parts.append(f'<option value="{name}" {selected}>{name}</option>')
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


def _pluralize(count, singular, plural=None):
    plural = plural or f"{singular}s"
    return f"{count} {singular if count == 1 else plural}"


def _render_quality_roll_line(treasure):
    """
    Quality tier and item count both fall out of one roll, indexed
    into TREASURE_QUALITY_TABLE (see generate_treasure()). Labeled
    "Quality roll" rather than "Rolled" - this line sits right below
    a check that's *also* labeled "Rolled ... vs DC ...", and having
    two lines both start with "Rolled" read oddly stacked together.

    Base items (from the quality tier's own table) and extra treasure
    (paint, consumables, artifacts, ... from generate_extra_items())
    come from separate rolls, so they're called out separately rather
    than folded into one "number of items".
    """
    rolled = format_roll(treasure["raw_quality_roll"], treasure["quality_mod"])

    count_phrase = _pluralize(treasure["base_item_count"], "item")
    if treasure["extra_item_count"] > 0:
        count_phrase += f' + {_pluralize(treasure["extra_item_count"], "extra")}'

    return (
        f'Quality roll <span class="recent-roll">{rolled}</span> '
        f'<span class="meta-badge">= {treasure["quality_roll"]} '
        f'\u2192 {treasure["quality"]}, {count_phrase}</span>'
    )


def _render_treasure_check_result(
    result, fail_message="There doesn't seem to be anything of value here."
):
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
            f'{_render_quality_roll_line(found)}<br><br>'
            f'{_render_item_list(found["item_list"])}'
        )
    else:
        html += f"<em>{fail_message}</em>"

    return html


def _render_monster_lines(monsters):
    """Renders the "N× Monster (breakdown)" lines for an encounter's
    monster groups. Assumes `monsters` is not None and has groups."""
    requested_level = monsters["requested_level"]
    lines = []
    for group in monsters["groups"]:
        cascade_note = ""
        if group["rolled_on_level"] != requested_level:
            cascade_note = (
                f' <span class="meta-badge">rolled on Level '
                f'{group["rolled_on_level"]} table</span>'
            )

        count_note = ""
        if group["count"] > 1:
            count_note = f' <span class="meta-badge">{group["count_breakdown"]}</span>'

        lines.append(
            f'<span class="recent-roll">{group["count"]}&times; {group["monster"]}</span>'
            f"{count_note}{cascade_note}"
        )

    return "<br>".join(lines)


def _render_encounter_treasure(result):
    """`result` is a roll_monster_treasure()-shaped dict, or None if
    every monster present is one that never carries treasure."""
    if result is None:
        return (
            '<hr><strong>Treasure:</strong><br>'
            "<em>This kind of encounter never carries any treasure.</em>"
        )

    return f"""
    <hr>
    <strong>Treasure:</strong><br>
    {_render_treasure_check_result(result)}
    """


def _render_encounter_result(result, show_treasure=True):
    """
    Renders one encounter-check result - shared between a location's
    own "entering encounter" and the standalone Encounter Generator
    view, since both produce the same shape of result (see
    handle_action's "room", "check_encounter", and "generate_encounter"
    branches).

    `show_treasure=False` omits the Treasure sub-section entirely -
    used for a location's entering encounter, which never carries its
    own treasure (see handle_action's "room" branch), so there's
    nothing to explain there, not even a "carries no treasure" note.

    `result["mode"] == "generated"` (from "generate_encounter") skips
    the "Rolled ... vs DC ..." framing entirely, since no check
    actually happened there - mirrors how the Treasure Generator's
    unconditional "Generate Treasure" skips DC framing too.
    """
    if result.get("mode") == "generated":
        body = (
            _render_monster_lines(result["monsters"])
            if result["monsters"] and result["monsters"]["groups"]
            else "<em>Nothing generated.</em>"
        )
        treasure_html = _render_encounter_treasure(result["treasure"]) if show_treasure else ""
        return f"{body}\n    {treasure_html}"

    badge = (
        '<span class="badge badge-warning">Encounter</span>'
        if result["success"]
        else '<span class="badge badge-fail">Safe</span>'
    )

    if result["success"] and result["monsters"] and result["monsters"]["groups"]:
        body = _render_monster_lines(result["monsters"])
        treasure_html = _render_encounter_treasure(result["treasure"]) if show_treasure else ""
    else:
        body = "<em>No encounter.</em>"
        treasure_html = ""

    return f"""
    Rolled
    <span class="recent-roll">
        {format_roll(result['raw_roll'], result['mod'])}
    </span>
    vs DC {result['dc_before']}
    {badge}
    <br><br>
    {body}
    {treasure_html}
    """


# ----------------------------
# VIEWS
# Each view is self-contained: its own controls plus its own result -
# only one of these is shown at a time (see render_page()).
# ----------------------------

def _render_location_view():
    room = SESSION.get("room")
    depth = SESSION.get("depth", 0)
    roll_treasure = SESSION.get("roll_treasure", True)
    roll_encounter = SESSION.get("roll_encounter", True)
    forced_location = SESSION.get("forced_location")
    forced_detail = SESSION.get("forced_detail")

    treasure_checked = "checked" if roll_treasure else ""
    encounter_checked = "checked" if roll_encounter else ""

    location_names = [name for _, name in LOCATIONS]
    detail_names = [name for _, name in DETAILS]

    controls = f"""
    <div class="section">
        <div class="form-row">
            <label for="depth">Depth:</label>
            <input type="number" id="depth" name="depth" value="{depth}">
        </div>
        <div class="form-row">
            <label for="location-select">Location:</label>
            <select id="location-select">
                {_render_choice_options(location_names, forced_location)}
            </select>
            <label for="detail-select">Detail:</label>
            <select id="detail-select">
                {_render_choice_options(detail_names, forced_detail)}
            </select>
        </div>
        <div class="form-row checkbox-row">
            <label>
                <input type="checkbox" id="roll-treasure" {treasure_checked}>
                Roll for Treasure
            </label>
            <label>
                <input type="checkbox" id="roll-encounter" {encounter_checked}>
                Roll for Encounter
            </label>
        </div>
        <button type="button" class="primary-action" onclick="runAction('room')">
            Generate Location
        </button>
    </div>
    """

    if not room:
        return controls + (
            '<div class="section">'
            "<em>Press 'Generate Location' to generate a new location.</em>"
            "</div>"
        )

    entering_html = ""
    if room.get("entering_encounter"):
        entering_html = f"""
        <hr>
        <strong>Encounter:</strong><br>
        {_render_encounter_result(room["entering_encounter"], show_treasure=False)}
        """

    treasure_html = ""
    if room.get("treasure_result"):
        treasure_html = f"""
        <hr>
        <strong>Treasure:</strong><br>
        {_render_treasure_check_result(room["treasure_result"])}
        """

    location_label = (
        f"Location ({room['location_roll']})"
        if room["location_roll"] is not None
        else "Location (chosen)"
    )
    detail_label = (
        f"Detail ({room['detail_roll']})"
        if room["detail_roll"] is not None
        else "Detail (chosen)"
    )

    return controls + f"""
    <div class="section">
        <div class="meta-line">Depth {room['used_depth']}</div>

        <strong>{location_label}:</strong> {room['location']}
        <div class="description">{render_md(room['location_text'])}</div>

        <strong>{detail_label}:</strong> {room['detail']}
        <div class="description">{render_md(room['detail_text'])}</div>
        {entering_html}
        {treasure_html}
    </div>
    """


def _render_encounter_view():
    result = SESSION.get("encounter_check")
    roll_treasure = SESSION.get("encounter_roll_treasure", True)
    treasure_checked = "checked" if roll_treasure else ""

    controls = f"""
    <div class="section">
        <div class="form-row checkbox-row">
            <label>
                <input type="checkbox" id="encounter-roll-treasure" {treasure_checked}>
                Roll for Treasure
            </label>
        </div>
        <button type="button" class="primary-action" onclick="runAction('check_encounter')">
            Roll for Encounter
        </button>
        <button type="button" onclick="runAction('generate_encounter')">
            Generate Encounter
        </button>
    </div>
    """

    if not result:
        return controls + (
            '<div class="section"><em>'
            "Press 'Roll for Encounter' or 'Generate Encounter' above "
            "to get started."
            '</em></div>'
        )

    return controls + f"""
    <div class="section">
        {_render_encounter_result(result)}
    </div>
    """


def _render_treasure_view_result(result):
    """
    Renders the standalone Treasure Generator's current result -
    either a DC-gated "Roll for Treasure" outcome (can fail) or an
    unconditional "Generate Treasure" one (always finds something, no
    DC framing) - mirrors _render_encounter_result's "generated" mode.
    """
    if result.get("mode") == "generated":
        found = result["found_treasure"]
        return f"""
        {_render_quality_roll_line(found)}<br><br>
        {_render_item_list(found['item_list'])}
        """

    return _render_treasure_check_result(
        result, fail_message="Nothing turns up this time."
    )


def _render_treasure_view():
    treasure = SESSION.get("treasure")

    controls = """
    <div class="section">
        <button type="button" class="primary-action" onclick="runAction('check_treasure')">
            Roll for Treasure
        </button>
        <button type="button" onclick="runAction('treasure')">
            Generate Treasure
        </button>
    </div>
    """

    if not treasure:
        return controls + (
            '<div class="section"><em>'
            "Press 'Roll for Treasure' or 'Generate Treasure' above "
            "to get started."
            "</em></div>"
        )

    return controls + f"""
    <div class="section">
        {_render_treasure_view_result(treasure)}
    </div>
    """


def _render_crawl_entry_full(room):
    """Highlighted card for the room currently at the top of the
    trail - where the party actually is right now."""
    entering_html = ""
    if room.get("entering_encounter"):
        entering_html = f"""
        <hr>
        <strong>Encounter:</strong><br>
        {_render_encounter_result(room["entering_encounter"], show_treasure=False)}
        """

    treasure_html = ""
    if room.get("treasure_result"):
        treasure_html = f"""
        <hr>
        <strong>Treasure:</strong><br>
        {_render_treasure_check_result(room["treasure_result"])}
        """

    return f"""
    <div class="crawl-entry crawl-entry-current">
        <div class="meta-line">Depth {room['used_depth']} &middot; You are here</div>

        <strong>Location ({room['location_roll']}):</strong> {room['location']}
        <div class="description">{render_md(room['location_text'])}</div>

        <strong>Detail ({room['detail_roll']}):</strong> {room['detail']}
        <div class="description">{render_md(room['detail_text'])}</div>
        {entering_html}
        {treasure_html}
    </div>
    """


def _render_crawl_entry_summary(room):
    """Compact single-row room marker further down the trail - just
    enough to identify what was there, no descriptions or
    encounter/treasure detail."""
    return f"""
    <div class="crawl-entry crawl-entry-past">
        <span class="crawl-room-name">{room['location']} &middot; {room['detail']}</span>
        <span class="crawl-depth-badge">Depth {room['used_depth']}</span>
    </div>
    """


def _crawl_path_to_current(history, current_id):
    """
    Walks parent_id links from `current_id` back to the root, returning
    the path in root-to-current order (oldest first). This is the
    actual currently-active path through the room "tree" - once
    branching exists (a future "Go Back" followed by "go_deeper" from
    an earlier room), this is what tells apart "the path leading to
    where we are now" from "every room ever generated across every
    branch" (crawl_history, which just keeps growing and is no longer
    usable as a single ordered trail on its own).
    """
    if current_id is None:
        return []
    by_id = {room["id"]: room for room in history}
    path = []
    node_id = current_id
    while node_id is not None:
        room = by_id[node_id]
        path.append(room)
        node_id = room["parent_id"]
    path.reverse()
    return path


def _render_crawling_view():
    history = SESSION.get("crawl_history", [])
    current_id = SESSION.get("crawl_current_id")
    depth = SESSION.get("crawl_depth", 0)

    controls = f"""
    <div class="section">
        <div class="meta-line">Current Depth: {depth}</div>
        <div class="button-row">
            <button type="button" disabled title="Not implemented yet" onclick="runAction('go_back')">
                Go Back
            </button>
            <button type="button" disabled title="Not implemented yet" onclick="runAction('stay')">
                Stay
            </button>
            <button type="button" class="primary-action" onclick="runAction('go_deeper')">
                Go Deeper
            </button>
        </div>
    </div>
    """

    path = _crawl_path_to_current(history, current_id)
    if not path:
        return controls + (
            '<div class="section">'
            "<em>Press 'Go Deeper' to descend into the dungeon.</em>"
            "</div>"
        )

    # Current room first, at the top; everything before it on the
    # active path in reduced form below, each pair joined by a
    # dashed "corridor" connector segment (see style.css) - scrolls
    # naturally with the rest of the page.
    entries = [_render_crawl_entry_full(path[-1])]
    for room in reversed(path[:-1]):
        entries.append('<div class="crawl-connector"></div>')
        entries.append(_render_crawl_entry_summary(room))

    return controls + f"""
    <div class="section">
        <div class="crawl-history">
            {''.join(entries)}
        </div>
    </div>
    """


# ----------------------------
# HEADER / SIDEBAR NAVIGATION
# ----------------------------

_VIEWS = [
    ("location", "Location Generator"),
    ("encounter", "Encounter Generator"),
    ("treasure", "Treasure Generator"),
    ("crawling", "Crawling Mode"),
]


def _render_header():
    level = SESSION.get("level")
    level_modifiers = SESSION.get("level_modifiers", {})
    encounter_dc = SESSION.get("encounter_dc", DEFAULT_ENCOUNTER_DC)
    treasure_dc = SESSION.get("treasure_dc", DEFAULT_TREASURE_DC)

    modifier_badges = _render_meta_badges(level_modifiers)
    modifiers_text = modifier_badges or "<em>none</em>"

    return f"""
    <div class="header-row">
        <label for="level">Level:</label>
        <select name="level" id="level" onchange="onLevelChange()">
            {_render_level_options(level)}
        </select>
    </div>
    <div class="meta-line">Modifiers: {modifiers_text}</div>
    <div class="header-row">
        <label for="encounter-dc">Encounter DC:</label>
        <input type="number" id="encounter-dc" name="encounter-dc" value="{encounter_dc}">
        <label for="treasure-dc">Treasure DC:</label>
        <input type="number" id="treasure-dc" name="treasure-dc" value="{treasure_dc}">
    </div>
    """


def _render_sidebar():
    active_view = SESSION.get("active_view", "location")
    links = []
    for view_id, label in _VIEWS:
        cls = "sidebar-link active" if view_id == active_view else "sidebar-link"
        links.append(
            f'<button type="button" class="{cls}" '
            f'onclick="switchView(\'{view_id}\')">{label}</button>'
        )

    return f"""
    <div id="sidebar-backdrop" class="sidebar-backdrop" onclick="closeSidebar()"></div>
    <nav id="sidebar" class="sidebar">
        {''.join(links)}
    </nav>
    """


_VIEW_RENDERERS = {
    "location": _render_location_view,
    "encounter": _render_encounter_view,
    "treasure": _render_treasure_view,
    "crawling": _render_crawling_view,
}


def render_page():
    """Builds the full inner HTML for the #app container, based on
    the current SESSION state. Only one view's content is rendered at
    a time (see SESSION["active_view"]); the header/sidebar are always
    shown regardless of which view is active."""

    active_view = SESSION.get("active_view", "location")
    view_fn = _VIEW_RENDERERS.get(active_view, _render_location_view)

    return _render_sidebar() + _render_header() + view_fn()

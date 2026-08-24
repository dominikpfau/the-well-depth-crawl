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
    (`render_page`, `_render_ransack`, ...) that build the same
    markup the template used to produce. The CSS/JS shell around it
    now lives in the surrounding .html file instead of Flask.
"""

import math
import random

import markdown

from data import (
    LEVEL_MODIFIERS,
    LOCATIONS, DETAILS,
    LOCATION_MODIFIERS, DETAIL_MODIFIERS,
    LOCATION_DESCRIPTIONS, DETAIL_DESCRIPTIONS,
    TREASURE_TABLES, TREASURE_QUALITY_TABLE, TREASURE_EXTRA_ITEMS_TABLE,
    CONSUMABLE_SUBTYPES, AMPULES_TABLE, POTIONS_TABLE, MISCELLANY_TABLE, ARTIFACTS_TABLE,
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


def collect_modifiers(room: dict, trigger: str) -> dict:
    """
    trigger: "room" | "ransack"
    """

    # Safe defaults
    loc_mod = LOCATION_MODIFIERS.get(room.get("location"), {}) or {}
    det_mod = DETAIL_MODIFIERS.get(room.get("detail"), {}) or {}

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

    `action` is one of "room", "ransack", "treasure", "reset", or None
    (None happens when only the Level dropdown changed, just like the
    original template's `onchange="this.form.submit()"` produced a
    plain POST without an `action` field).
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
            "ransacked": False,
            "ransack_result": None,
        }
        mods = collect_modifiers(room, trigger="room")
        mods["treasure_roll"] += level_modifiers.get("wealth", 0)
        mods["treasure_quality"] += level_modifiers.get("wealth", 0)
        mods["encounter_roll"] += level_modifiers.get("population", 0)

        encounter_dc_before = encounter_dc
        encounter_check = roll_random_encounter(encounter_dc, mods)
        encounter_dc = encounter_check["next_dc"]

        latest_encounter = {
            "source": "Entering location",
            "roll": encounter_check["roll"],
            "raw_roll": encounter_check["raw_roll"],
            "mod": encounter_check["mod"],
            "dc_before": encounter_dc_before,
            "success": encounter_check["success"],
        }

        depth = used_depth + 1

    elif action == "ransack" and room and not room.get("ransacked"):
        mods = collect_modifiers(room, trigger="ransack")
        mods["treasure_roll"] += level_modifiers.get("wealth", 0)
        mods["treasure_quality"] += level_modifiers.get("wealth", 0)
        mods["encounter_roll"] += level_modifiers.get("population", 0)

        treasure_dc_before = treasure_dc
        treasure_check = roll_location_treasure(treasure_dc, mods)
        treasure_dc = treasure_check["next_dc"]

        encounter_dc_before = encounter_dc
        encounter_check = roll_random_encounter(encounter_dc, mods)
        encounter_dc = encounter_check["next_dc"]

        latest_encounter = {
            "source": "Ransacking location",
            "roll": encounter_check["roll"],
            "raw_roll": encounter_check["raw_roll"],
            "mod": encounter_check["mod"],
            "dc_before": encounter_dc_before,
            "success": encounter_check["success"],
        }

        room["ransacked"] = True
        room["ransack_result"] = {
            "treasure_roll": treasure_check["roll"],
            "raw_roll": treasure_check["raw_roll"],
            "mod": treasure_check["mod"],
            "treasure_dc_before": treasure_dc_before,
            "found_treasure": treasure_check["treasure"],
            "blocked": treasure_check.get("blocked", False),
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


def _render_ransack(room):
    if not room.get("ransacked"):
        return "<em>This location has not been ransacked.</em>"

    result = room["ransack_result"]
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

        <strong>Ransacking:</strong><br>
        {_render_ransack(room)}
    </div>
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
    result_text = (
        "<strong>A random encounter occurs!</strong>"
        if latest_encounter["success"]
        else "<em>No encounter.</em>"
    )

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
    room = SESSION.get("room")

    ransack_disabled = "disabled" if (not room or room.get("ransacked")) else ""

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
            <button type="button" onclick="runAction('ransack')" {ransack_disabled}>
                Ransack Location
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

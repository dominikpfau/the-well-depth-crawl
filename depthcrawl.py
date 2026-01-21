import math
import random

from flask import Flask, request, render_template_string, session

app = Flask(__name__)
app.secret_key = "replace-this-with-a-random-secret"

Table = list[tuple[int, str]]

from data import (LOCATIONS, DETAILS,
                  LOCATION_DESCRIPTIONS, DETAIL_DESCRIPTIONS,
                  TREASURE_TABLES, TREASURE_QUALITY_TABLE)


# ----------------------------
# LOGIC
# ----------------------------

def roll_table(table: Table, depth: int) -> tuple[int, str]:
    roll = random.randint(1, 20) + depth
    for max_value, result in table:
        if roll <= max_value:
            return roll, result
    raise RuntimeError("Invalid table")


def generate_treasure():
    quality_roll = random.randint(1, 6)
    count, quality = TREASURE_QUALITY_TABLE[quality_roll]

    item_list = [TREASURE_TABLES[quality][random.randint(1, 20)] for _ in range(count)]

    return {
        "quality_roll": quality_roll,
        "number_of_items": count,
        "quality": quality,
        "item_list": item_list,
    }


DEFAULT_TREASURE_DC = 8
DEFAULT_ENCOUNTER_DC = 8


def roll_location_treasure(current_dc: int):
    roll = random.randint(1, 6)
    if roll >= current_dc:
        treasure = generate_treasure()
        return {"roll": roll, "success": True, "treasure": treasure, "next_dc": DEFAULT_TREASURE_DC}
    else:
        reduction = math.ceil(roll / 2)
        next_dc = max(1, current_dc - reduction)
        return {"roll": roll, "success": False, "treasure": None, "next_dc": next_dc}


def roll_random_encounter(current_dc: int):
    roll = random.randint(1, 6)
    if roll >= current_dc:
        return {"roll": roll, "success": True, "next_dc": DEFAULT_ENCOUNTER_DC}
    else:
        reduction = math.ceil(roll / 2)
        next_dc = max(1, current_dc - reduction)
        return {"roll": roll, "success": False, "next_dc": next_dc}


# ----------------------------
# HTML TEMPLATE
# ----------------------------

from html import HTML

# ----------------------------
# ROUTE
# ----------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    # Load previous session values or initialize defaults
    depth = session.get("depth", 0)
    room = session.get("room")
    treasure = session.get("treasure")
    treasure_dc = session.get("treasure_dc", DEFAULT_TREASURE_DC)
    encounter_dc = session.get("encounter_dc", DEFAULT_ENCOUNTER_DC)
    latest_encounter = session.get("latest_encounter")

    if request.method == "POST":
        action = request.form.get("action")
        depth = int(request.form.get("depth", depth))

        if action == "room":
            used_depth = depth
            loc_roll, location = roll_table(LOCATIONS, used_depth)
            det_roll, detail = roll_table(DETAILS, used_depth)

            # roll encounter (shared DC)
            encounter_dc_before = encounter_dc
            encounter_check = roll_random_encounter(encounter_dc)
            encounter_dc = encounter_check["next_dc"]

            latest_encounter = {
                "source": "Entering location",
                "roll": encounter_check["roll"],
                "dc_before": encounter_dc_before,
                "success": encounter_check["success"],
            }

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

            depth = used_depth + 1

        elif action == "ransack" and room and not room.get("ransacked"):
            # roll treasure
            treasure_dc_before = treasure_dc
            treasure_check = roll_location_treasure(treasure_dc)
            treasure_dc = treasure_check["next_dc"]

            # roll encounter (shared DC)
            encounter_dc_before = encounter_dc
            encounter_check = roll_random_encounter(encounter_dc)
            encounter_dc = encounter_check["next_dc"]

            latest_encounter = {
                "source": "Ransacking location",
                "roll": encounter_check["roll"],
                "dc_before": encounter_dc_before,
                "success": encounter_check["success"],
            }

            room["ransacked"] = True
            room["ransack_result"] = {
                "treasure_roll": treasure_check["roll"],
                "treasure_dc_before": treasure_dc_before,
                "found_treasure": treasure_check["treasure"],
            }

        elif action == "treasure":
            treasure = generate_treasure()

        elif action == "reset":
            session.clear()
            depth = 0
            room = None
            treasure = None
            treasure_dc = DEFAULT_TREASURE_DC
            encounter_dc = DEFAULT_ENCOUNTER_DC
            latest_encounter = None

        # persist updated session
        session["depth"] = depth
        session["room"] = room
        session["treasure"] = treasure
        session["treasure_dc"] = treasure_dc
        session["encounter_dc"] = encounter_dc
        session["latest_encounter"] = latest_encounter

    return render_template_string(
        HTML,
        room=room,
        treasure=treasure,
        depth=depth,
        latest_encounter=latest_encounter,
    )


if __name__ == "__main__":
    app.run(debug=True)

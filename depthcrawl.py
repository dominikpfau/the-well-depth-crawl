import random

from flask import Flask, request, render_template_string, session
app = Flask(__name__)
app.secret_key = "replace-this-with-a-random-secret"  # needed for session

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

    item_list = []
    for _ in range(count):
        roll = random.randint(1, 20)
        item = TREASURE_TABLES[quality][roll]
        item_list.append(item)  # only store the text

    return {
        "quality_roll": quality_roll,
        "number_of_items": count,
        "quality": quality,
        "item_list": item_list,  # renamed from 'items'
    }

HTML = """
<!doctype html>
<title>Depthcrawl Generator</title>
<style>
body { font-family: serif; background:#1e1e1e; color:#e0e0e0; padding:2rem; }
input, button { font-size:1rem; padding:0.3rem; margin-right:0.5rem; }
.section { margin-top:2rem; padding:1rem; background:#2a2a2a; }
pre { white-space: pre-wrap; background:#1a1a1a; padding:0.8rem; }
</style>

<h1>Depthcrawl Generator</h1>

<form method="post">
Depth:
<input type="number" name="depth" value="{{ depth }}">
<button type="submit" name="action" value="room">Generate Room</button>
<button type="submit" name="action" value="treasure">Generate Treasure</button>
</form>

{% if room %}
<div class="result">
<b>Used Depth:</b> {{ room.used_depth }}<br><br>

<b>Location ({{ room.location_roll }}):</b> {{ room.location }}
<pre>{{ room.location_text }}</pre>

<b>Detail ({{ room.detail_roll }}):</b> {{ room.detail }}
<pre>{{ room.detail_text }}</pre>
</div>
{% endif %}

{% if treasure %}
<div class="section">
<b>Treasure Quality Roll (1d6):</b> {{ treasure.quality_roll }}<br>
<b>Number of Items:</b> {{ treasure.number_of_items }}<br>
<b>Quality:</b> {{ treasure.quality }}<br><br>

{% for item in treasure.item_list %}
• {{ item }}<br>
{% endfor %}
</div>
{% endif %}
"""

# ----------------------------
# ROUTE
# ----------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    depth = session.get("depth", 0)
    room = session.get("room")
    treasure = session.get("treasure")

    if request.method == "POST":
        action = request.form.get("action")
        depth = int(request.form.get("depth", depth))

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
            }
            depth = used_depth + 1

        elif action == "treasure":
            treasure = generate_treasure()

        # store in session to persist across requests
        session["depth"] = depth
        session["room"] = room
        session["treasure"] = treasure

    return render_template_string(
        HTML,
        room=room,
        treasure=treasure,
        depth=depth,
    )

if __name__ == "__main__":
    app.run(debug=True)


# ----------------------------
# HTML TEMPLATE
# ----------------------------

HTML = """
<!doctype html>
<title>Depthcrawl Generator</title>
<style>
body { font-family: serif; background:#1e1e1e; color:#e0e0e0; padding:2rem; }
input, button { font-size:1rem; padding:0.3rem; margin-right:0.5rem; }
.section { margin-top:2rem; padding:1rem; background:#2a2a2a; }
pre { white-space: pre-wrap; background:#1a1a1a; padding:0.8rem; }
button[disabled] { opacity: 0.5; cursor: not-allowed; }
</style>

<h1>Depthcrawl Generator</h1>

<form method="post">
Depth:
<input type="number" name="depth" value="{{ depth }}">
<button type="submit" name="action" value="room">Generate Location</button>
<button type="submit" name="action" value="ransack" {% if not room or room.ransacked %}disabled{% endif %}>Ransack Location</button>
<button type="submit" name="action" value="treasure">Generate Treasure</button>
<button type="submit" name="action" value="reset">Reset</button>
</form>

{% if room %}
<div class="section">
<b>Used Depth:</b> {{ room.used_depth }}<br><br>

<b>Location ({{ room.location_roll }}):</b> {{ room.location }}
<pre>{{ room.location_text }}</pre>

<b>Detail ({{ room.detail_roll }}):</b> {{ room.detail }}
<pre>{{ room.detail_text }}</pre>

<hr>

<b>Ransacking:</b><br>
{% if not room.ransacked %}
<em>This location has not been ransacked.</em>
{% else %}
Rolled {{ room.ransack_result.treasure_roll }} vs DC {{ room.ransack_result.treasure_dc_before }}<br><br>

{% if room.ransack_result.found_treasure %}
<b>Treasure Found!</b><br>
<b>Quality:</b> {{ room.ransack_result.found_treasure.quality }}<br>
<b>Number of Items:</b> {{ room.ransack_result.found_treasure.number_of_items }}<br><br>

{% for item in room.ransack_result.found_treasure.item_list %}
• {{ item }}<br>
{% endfor %}
{% else %}
<em>No treasure was found here.</em>
{% endif %}
{% endif %}
</div>

{% else %}
<div class="section">
<b>Location:</b><br>
<em>Press 'Generate Location' to generate a new location.</em>
</div>

{% endif %}

<!-- SINGLE ENCOUNTER SECTION -->
<div class="section">
<b>Random Encounter:</b><br>
{% if latest_encounter %}
<b>Trigger:</b> {{ latest_encounter.source }}<br>
Rolled {{ latest_encounter.roll }} vs DC {{ latest_encounter.dc_before }}<br><br>

{% if latest_encounter.success %}
<b>⚠ A random encounter occurs!</b>
{% else %}
<em>No encounter.</em>
{% endif %}
{% else %}
<em>No encounter check yet.</em>
{% endif %}
</div>

{% if treasure %}
<div class="section">
<b>Treasure Quality Roll (1d6):</b> {{ treasure.quality_roll }}<br>
<b>Number of Items:</b> {{ treasure.number_of_items }}<br>
<b>Quality:</b> {{ treasure.quality }}<br><br>

{% for item in treasure.item_list %}
• {{ item }}<br>
{% endfor %}
</div>
{% else %}
<div class="section">
<em>Press 'Generate Treasure' to generate additional treasure.</em>
</div>
{% endif %}
"""
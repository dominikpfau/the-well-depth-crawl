# ----------------------------
# LEVELS (of the Well)
# ----------------------------

LEVEL_MODIFIERS = {
    1: {"wealth": -1, "population": 0},
    2: {"wealth": 0, "population": 0, "awareness": -1, "navigation": -1},
    3: {"wealth": +1, "population": +1, "awareness": +1},
    4: {"wealth": +1, "population": 0},
    5: {"wealth": +1, "population": 0},
    6: {"wealth": +2, "population": +2},
    7: {"wealth": +1, "population": +2, "awareness": -1},
    8: {"wealth": 0, "population": 0, "navigation": -2},
    9: {"wealth": +1, "population": +1},
    10: {"wealth": +1, "population": +1, "awareness": -1},
    11: {"wealth": +3, "population": 0, "navigation": +2},
    12: {"wealth": 0, "population": +3},
}

# ----------------------------
# LOCATION GENERATOR
# ----------------------------

LOCATIONS: list[tuple[int, str]] = [
    (3, "Abandoned Shop"),
    (4, "Suites"),
    (5, "Auditorium"),
    (6, "Public Fungal Garden"),
    (7, "Market"),
    (8, "Sculpture Gallery"),
    (9, "Wellguard Station"),
    (10, "Cistern"),
    (11, "Tavern"),
    (12, "Apartments"),
    (13, "Gaming Hall"),
    (14, "Guild Hall"),
    (15, "Administrative Chambers"),
    (16, "Workshop"),
    (17, "Storehouse"),
    (18, "Manufactory"),
    (19, "Slum"),
    (20, "Ossuary"),
    (21, "Crypt"),
    (22, "Dormitories"),
    (23, "Public Rock Garden"),
    (24, "Mansion"),
    (25, "Laboratory"),
    (26, "Mausoleum"),
    (27, "Lighted Farm"),
    (28, "Library"),
    (29, "Fungal Farm"),
    (10 ** 9, "Mine"),
]

DETAILS: list[tuple[int, str]] = [
    (3, "Looted"),
    (4, "Signpost"),
    (5, "Note"),
    (6, "Inactive Rune"),
    (7, "Dead Gravedigger"),
    (8, "Signs of Recent Passage"),
    (9, "Vermin"),
    (10, "Chandelier"),
    (11, "Safe"),
    (12, "Amphoras"),
    (13, "Wet"),
    (14, "Crevice"),
    (15, "Obscured"),
    (16, "Repurposed into Crypt"),
    (17, "Lift"),
    (18, "Slime Fungus"),
    (19, "Fragile"),
    (20, "Fireplace"),
    (21, "Secret Passage"),
    (22, "Bulky Treasure"),
    (23, "Portcullis"),
    (24, "Labyrinthine"),
    (25, "Treasure Pile"),
    (26, "Mine Damp"),
    (27, "Vault"),
    (28, "Holes"),
    (29, "Blocked Exit"),
    (10 ** 9, "Dead End"),
]

LOCATION_MODIFIERS = {
    "Abandoned Shop": {
        "treasure_roll": -1,
    },
    "Crypt": {
        "treasure_quality": +1,
    },
    "Dormitories": {
        "treasure_quality": -1,
    },
    "Laboratory": {
        "treasure_quality": +2,
    },
    "Library": {
        "treasure_quality": +2,
    },
    "Mausoleum": {
        "treasure_quality": +2,
    },
    "Ossuary": {
        "encounter_roll": +2,
        "treasure_quality": -2,
    },
    "Slum": {
        "block_positive_treasure_roll": True,
        "treasure_roll": -2,
    },
    "Temple": {
        "encounter_roll": +1,
        "treasure_quality": +1,
        "scope": "ransack",
    },
}

DETAIL_MODIFIERS = {
    "Amphoras": {
        "encounter_roll": +1,
        "treasure_roll": +1,
        "scope": "ransack",
    },
    "Looted": {
        "no_treasure": True,
    },
    "Repurposed into Crypt": {
        "block_positive_treasure_quality": True,
    },
    "Treasure Pile": {
        "encounter_roll": +1,
        "scope": "ransack",
    },
    "Vault": {
        "treasure_roll": +1,
    },
}

# ----------------------------
# TREASURE GENERATOR
# ----------------------------

# 1d6 → (number_of_items, quality)
TREASURE_QUALITY_TABLE = {
    0: (1, "mundane"),
    1: (1, "minor"),
    2: (2, "minor"),
    3: (1, "moderate"),
    4: (2, "moderate"),
    5: (1, "valuable"),
    6: (2, "valuable"),
    7: (1, "excellent"),
    8: (1, "excellent"),
    9: (1, "rare"),
    10: (1, "rare"),
    11: (1, "legendary"),
    12: (1, "legendary"),
}

# Each quality has its own 1d20 table
TREASURE_TABLES = {
    "mundane": {
        1: "Broken pottery shards",
        2: "Spoilt food",
        3: "Torn cloth scraps",
        4: "Rusty iron key",
        5: "Rotten parchment",
        6: "Dull knife",
        7: "Bag full of holes",
        8: "Damp torch",
        9: "Frayed rope",
        10: "Rusty lantern with shattered glass",
        11: "Pair of worn sandals",
        12: "Rusty pickaxe",
        13: "Dusty flask filled with booze",
        14: "Incomplete set of playing cards",
        15: "Empty water skin",
        16: "Axe with a dull blade",
        17: "Flask of oil",
        18: "Bent crowbar",
        19: "Rusty chain",
        20: "Iron spikes",
    },
    "minor": {
        1: "Bronze trinket (belt buckle, brooch, button, comb)",
        2: "Brass baubles (candlestick, goblet, incense box)",
        3: "Copper ornament (bracelet, earring, hairpin)",
        4: "Brass whistle, bell or small gong",
        5: "Bronze ceremonial item (dagger, candlesnuffer, scoop)",
        6: "Copper mirror (handheld, foldable with cracked surface, set into broken comb)",
        7: "Brass weight tool (small merchants scale, set of counterweights, broken scale arm)",
        8: "Bronze idol (religious, decorative, bookend, paperweight)",
        9: "Handful of copper coins (in leather pouch, in rusted jar, wedged in floor crack)",
        10: "Brass gear with unknown function (cog wheel, unusual key, tiny hinge joint)",
        11: "Bronze container (bowl, carafe, casket, vase)",
        12: "Copper plated dice or board-game piece",
        13: "Dusty leather armor with bronze studs (brigandine, bracers, greaves)",
        14: "Brass memory keepsake (locket or tiny casket filled with buttons or dried flowers)",
        15: "Copper trinket (key, necklace, ring)",
        16: "Copper flask etched with intricate symbols (decorative runes, floral or any animal)",
        17: "Bronze weapon (shortsword, dagger, spearhead)",
        18: "Brass baubles (inkwell, lens frame, scroll case)",
        19: "Bronze artisan kit (stonecutting, woodworking, gardening, tailoring)",
        20: "Copper wire or bronze chain",
    },
    "moderate": {
        1: "Silver jewelry (chain necklace, engraved ring, filigree bracelet)",
        2: "Carved stone object (figurine, tablet, or bowl made of alabaster or serpentine)",
        3: "Iron tool (blacksmith’s tong, carpenter’s square, engraving chisel with initials)",
        4: "Silver household item (spoon set, wine cup, ornamental comb, handheld mirror)",
        5: "Silver jewelry with gem (brooch, pin or locket with garnet, onyx or agate)",
        6: "Stone relief fragment (part of a mural or stele with worn symbols related to location)",
        7: "Iron weapon (sword, hammerhead, dagger)",
        8: "Handful of silver coins (in small pouch, wrapped in old cloth, hidden in a false book)",
        9: "Flawed gemstone (rough topaz, cracked amethyst, cloudy quartz orb)",
        10: "Iron armor piece (elbow guard, gorget, greaves with etched lines)",
        11: "Silver ritual item (anointing bowl, prayer pendant, incense spoon)",
        12: "Decorative inlaid stone box (holding dried ink, wax seal kit, or folded parchment)",
        13: "Heirloom-quality tools (stone-carver’s mallet with gem inlay, jeweler’s loupe)",
        14: "Civic tokens (silver badge of office, carved stone voting marker, iron passkey)",
        15: "Stone jewelry (beaded necklace, ring or earring made of jasper, agate or lapis lazuli)",
        16: "Silver flask or snuff box (plain but elegant, engraved with initials or a crest)",
        17: "Iron mechanical part (crank, heavy pinion, gear cluster with maker’s mark)",
        18: "Stone relic or idol (family ancestor bust or figurine, broken ceremonial plinth)",
        19: "Silver writing kit (nib pen, scroll tube with silver caps, inkpot with silver lid)",
        20: "Silver ring with gem (topaz, amethyst or garnet)",
    },
    "valuable": {
        1: "Gold jewelry (signet ring, heavy chain necklace, filigree earring)",
        2: "Masterwork quality steel weapon (+1 to maneuvers)",
        3: "Black lead writing tools (engraved stylus, compact scribe’s case)",
        4: "Rare gemstone, cut (flawless opal, brilliant-cut sapphire, star ruby, diamond)",
        5: "Gold relic (sun disk, small idol, ceremonial chalice with enamel detailing)",
        6: "Gilded armor piece (vambrace, emerald-studded gorget, gold-etched helmet)",
        7: "Black lead art object (etched relief tablet, abstract idol, black-lead mask)",
        8: "Handful of gold coins (small velvet pouch, clay jar sealed with wax, hidden stack)",
        9: "Noble insignia (gold brooch with house emblem, black-lead signet, golden scepter)",
        10: "Rare mineral (chunk of fire opal, piece of starry obsidian, unusual gem cluster)",
        11: "Gold ornate container (scroll tube, casket with gemstone inlay, perfume vial)",
        12: "Steel tools (engraver’s kit, medical instruments, chisels with jeweled handles)",
        13: "Rare gemstone fragments (cracked black opal, raw alexandrite, shard of fire agate)",
        14: "Gold-plated armor piece (engraved knee guard, pauldron or ceremonial cuirass)",
        15: "Luxury grooming kit (steel shaving blade, black-lead mirror, gold comb set in velvet)",
        16: "Relic weapon (longsword with ruby in pommel, gilded hammer, gold-hilted dagger)",
        17: "Fine jewelry set (matching emerald earrings, chain, and ring in black-lead box)",
        18: "Golden statuette (mythical creature, ancestral king, or forgotten god, finely sculpted)",
        19: "Gold lined spectacles or magnifying lense",
        20: "Gold ring with gem (diamond, emerald, ruby, sapphire)",
    },
    "excellent": {
        1: "Rare wooden object (carved box, smooth mask, writing tablet bound in leather)",
        2: "Pitchblende idol (abstract figure, hooded ancestral effigy, miniature seated king)",
        3: "Hornblende-inlaid wooden object (fireproof box, weapon shaft or furnishing)",
        4: "Wooden relic (spear shaft with name carvings, silver capped cane, hide drum)",
        5: "Pitchblende weapon component (blunt mace head, pommel core, counterweight)",
        6: "Hornblende-inlaid artisan tools (carving knife, measuring rod, wood chisel)",
        7: "Decorative wooden panels (wall or furniture remnants, fragments of an ancient door)",
        8: "Pitchblende pendant (heavily worn insignia of old rank, ritual medallion on cord)",
        9: "Hornblende ceremonial mask (faceless expression, animal motif, warrior aspect)",
        10: "Wooden game board (complete set with pieces, foldable with engraved initials)",
        11: "Pitchblende container (small thick-walled bowl, empty paint pot with wooden lid)",
        12: "Wood-carved scroll case (hollow tube with latching ends, coated with hornblende)",
        13: "Proto-paint (glows faintly but otherwise non-magical)",
        14: "Wooden statuette (guardian animal, family figure trio, fragmented shrine piece)",
        15: "Pitchblende or hornblende ore (pitch black, green shimmer, silver speckles)",
        16: "Master-crafted bow or crossbow (+1 to murder)",
        17: "Pitchblende jewelry (matte ring with etched rim, bead strand, medallion on cord)",
        18: "Pitchblende tool (ceremonial hammer, burin for etching stone, anvil fragment)",
        19: "Hornblende grooming item (finely spaced comb, nail stylus, filigree hairclip)",
        20: "Wooden personal keepsake (box with family sigil, flute, carved charm)",
    },
    "rare": {
        1: "Ancient tome bound in cracked leather (religious or philosophical essay)",
        2: "Boxwood sculpture (pale, fine-grained figurine or bust that shows precise detail)",
        3: "Scholarly treatise (stone-cutting techniques, medicinal fungi or stock farming)",
        4: "Runebook (contains instructions to paint a single rune, perhaps unknown)",
        5: "Burl walnut panel fragment (carved wall or furniture piece with intricate patterns)",
        6: "Explorer's journal (expedition report with maps, perhaps copied from older source)",
        7: "Oil painting on mahogany panel (portrait, still-life or faded scenes of court or city life)",
        8: "Artist's sketch folio (plants, humans, animals or objects)",
        9: "Book of fables (told in short poetic lines, likely once read to children)",
        10: "Inscribed padauk wood plaque (deep-carved clan vows or ancient edict)",
        11: "Sample folio (swatches of woven fungus-fiber or hide with artisan annotations)",
        12: "Poetry book (verses in an archaic dialect, mirthful, romantic or sad)",
        13: "Embroidered tapestry (family tree, floral patterns, mythical creature)",
        14: "Ceremonial record book (marked with silver studs, details rites for naming or burial)",
        15: "Tome of forgotten knowledge (alchemy, medicine, mechanics, enchantment)",
        16: "Artist’s workbox (dried pigment stones and brushes, still fragrant and glossy)",
        17: "Book with historic content (town chronicle, biography)",
        18: "Rare wood grooming item (masterwork comb or makeup brush made of satinwood)",
        19: "Finely decorated piece of porcelain (vase, bowl, jug, plate, cup)",
        20: "1 dose of paint (glowing in unusual color, made from ancient forgotten recipe)",
    },
    "legendary": {
        1: "Statuette of a sleeping beast (carved from glossy petrified black mahogany)",
        2: "Funerary stele (petrified ash, inscribed with a family tree, dates, and achievements)",
        3: "Mosaic panel (hundreds of petrified olivewood tiles, depicting a historical event)",
        4: "Gallery bust (noble portrait sculpted from dense petrified rosewood on marble base)",
        5: "Regal jewelry (bracelet, necklace or ring made of amber, coral or nacre)",
        6: "Document chest (petrified ebony coffer with gold hinges for royal correspondence)",
        7: "Luxury game set (full gameboard of petrified ebony with hand-carved ivory pieces)",
        8: "Regal funeral mask (somber ivory mask with ridged brow and inset coral eyes)",
        9: "Unique gem (colorful diamond, red sapphire or giant black opal, flawless quality)",
        10: "Oil painting on petrified walnut panel (showing some overworld landscape)",
        11: "Arch keystone (carved from petrified teak, featuring faces of judges and scholars)",
        12: "Regal crown (massive gold with diamonds and other gems, ivory marquetry)",
        13: "Nacre intarsia panel (oceanic scene set into a petrified cypress mount)",
        14: "Wall frieze fragment (red coral scrollwork mounted on petrified oak, tiny gold nails)",
        15: "Intact ivory tusk (engraved or painted with complex patterns, capped with gold)",
        16: "Giant polished amber with one or more fossilized insects inside",
        17: "Ivory scroll case (etched with landscapes and gold latches in pristine condition)",
        18: "Amber figurine (meditating figure sculpted entirely from solid, cloudy amber)",
        19: "Ivory lyre (musical instrument with intricate nacre inlay along the arms)",
        20: "Regal scepter or cane (made from petrified ebony, flawless amber as headpiece)",
    },
}

# ----------------------------
# DESCRIPTIONS
# ----------------------------

LOCATION_DESCRIPTIONS = {
    "Abandoned Shop": """This place used to sell upmarket goods, but the former owner gave up on that long ago.
The rooms are now filled with dust and junk, but a thorough search might still yield something interesting.
Add -1 on rolls to find treasure here.""",

    "Administrative Chambers": """A collection of small offices and big typing pools scattered with vast amounts of loose papers.
If the PCs are looking for information about a specific location, person or event related to the history of this level,
they might find something. Doing so requires digging through chaotic, rotting documents (difficulty 10).""",

    "Apartments": """A series of small modest apartments. Whoever lived here was doing well enough to afford a home,
but their lifestyle was anything else than luxurious. Good hiding places, easy to defend,
but usually only one exit, making them potential deathtraps.""",

    "Auditorium": """A large semi-circular room with a stage at the flat side.
Around it are rings of benches, each slightly more elevated than the one in front.""",

    "Cistern": """A large basin once used to draw fresh water.
If the PCs are lucky, they can refill waterskins here.
The water may also be brackish, contaminated, or the basin dry.""",

    "Crypt": """Large stone sarcophagi are lined up, each labeled with a name.
The people who got entombed here (or their families) paid considerable fees to avoid public burial.
Add +1 to rolls on the treasure table.""",

    "Dormitories": """Sparse rooms crammed with bunk beds and little room for privacy or personal belongings.
These were the homes of the lower working class of the city.
Add -1 to rolls on the treasure table.""",

    "Fungal Farm": """A cave or former mine repurposed to grow fungi for food, drugs or other products.
The place is overgrown and jungle-like. The higher the level, the stranger and more exotic the vegetation.
PCs with farming background may search for edible or medicinal plants.""",

    "Gaming Hall": """A large room filled with gambling tables and strange gaming artifacts.
There is a good chance to find money or exotic coins here.""",

    "Guild Hall": """A central meeting chamber surrounded by storage and workrooms.
Narrow stairs lead to a mezzanine once used as an archive or office space. Faded banners show sigils of a forgotten trade guild.
Choose one of the following options or decide that the nature of the guild  remains a mystery:
- Artisans guild: Change any treasure found here into rare materials (blocks of marble, petrified woods, rolls of fine cloth) 
  or drawings of unfinished or masterful works.
- Farmers guild: Change any treasure found here into seeds, jars of pickled crops or books on farming techniques, crop rotation, or soil health.
- Mining guild: Change any treasure found here into mining equipment (hammers, pickaxes, lanterns, ropes etc.) 
  or a map leading to nearby mines.  If appropriate, the map also might contain information about dangers or secret passages there.
- Painters guild: Change any treasure found here into doses of paint or runebooks""",

    "Laboratory": """A large workshop full of strange apparatuses and exotic equipment (mostly broken). 
Whatever happened here was already a well-kept secret when the level was still inhabited. 
Ransacking this place is not without danger, for touching the broken apparatuses might trigger unknown effects, but it is usually worth it. 
Add +2 to any rolls on the treasure table. Choose one of the following options to determine the original purpose of the location:
- paint production: Change any consumables rolled on the treasure table into doses of paint. Books do always contain instructions for painting runes. While ransacking, there is a 50% chance the PCs trigger the effect of a random rune on themselves.
- golem construction (level 5 or higher): Change any consumables rolled on the treasure table into twice the amount in doses of paint. Books do always contain instructions for painting runes. While ransacking, there is a 50% chance that a half assembled construct comes to life and attacks the PCs (Treat it as a rune golem with only 1 action die and 10 resilience).
- alchemy (level 6 or higher): Any consumables rolled on the treasure table are always potions or ampules. For every generated potion or ampule there's another one still in one of the apparatuses, waiting to be bottled (The PCs can do this if they brought empty vials). While ransacking, there is a 50% chance the PCs trigger the effect of a random ampule on themselves.
- lesser thaumaturgy (level 8 or higher): Any consumables rolled on the treasure table are always miscellany. There’s a strange compass-like apparatus that will point to a nearby location 1d6 layers deeper, where more consumables can be found (difficulty 10 to navigate there). To activate it, the PCs will need a strong magnet (They can get hints at this if they experiment with it for a while). While ransacking or experimenting with the apparatus, there is a 50% chance that something blows up unexpectedly (Treat this like a “fragile” location).
- greater thaumaturgy (level 11 or higher): Rolls on the treasure table always produce at least 1 permanent artifact. Ignore anything else from the bonus column. While ransacking, there is a 50% chance that the PCs trigger some effect that attracts nearby undead (roll up a random encounter). This is in addition to any normal random encounters that would happen during this period.""",

    "Library": """Books are extremely precious and thus rarely left behind. 
Still, no gravedigger would pass the opportunity to search through the crumbled shelves, for the promise of valuable loot 
(and ancient knowledge) is too tempting. Add +2 to all rolls on the treasure table, but ignore any consumables from the bonus column (except paint).""",

    "Lighted Farm": """A large cave or former mine shaft that was used to raise valuable crops and livestock with the help of artificial light. 
In central places one can still see where the magic runes used to be. Now, without the light, it's a place of darkness and decay, 
since most light-dependent plants died long ago.""",

    "Mansion": """Entrance to a sprawling upper-class mansion.
Whoever lived here belonged to the upper class of his time. Immediately roll 1d3+1 and generate that many interconnected 
locations within the current depth, using the following special table (roll 1d6 and reroll on duplicates):
1. Cistern, with fresh water supply
2. Library, with +1 to find treasure
3. Lounge: treat like Suits location with Bulky Treasure detail
4. Mausoleum, with +1 to find treasure
5. Treasury: treat like Vault and Treasure Pile details combined. Add +3 to any rolls on the treasure table
6. Pleasure garden: treat like Public Fungal Garden with +1 to find treasure
""",

    "Manufactory": """A sprawling structure with rows of workbenches.
Storage rooms contain raw materials and finished goods.""",

    "Market": """An open area filled with the remnants of stalls—stone counters, rotting crates, and tarnished scales. 
Alcoves, where merchants once displayed their wares, are now littered with broken pottery and scraps of faded cloth.""",

    "Mausoleum": """One or several richly ornamented stone sarcophagi are placed inside a spacious chamber. 
Elaborated mural reliefs and paintings might give clues about the deceased person or family, which obviously was extremely wealthy 
to afford such a fancy last resting place. Add +2 to any rolls on the treasure table.""",

    "Mine": """Most spaces used to be mines at some point, but were extended and adjusted to a new purpose eventually. 
This one was still mined from, at the time when people abandoned this level. 
There's a 1 in 3 chance that some valuable ore vein can be found here (otherwise it's something mundane like coal). 
Roll on the treasure table and replace any improper result by larger amounts if something less valuable. 
Removing it requires time and a pickaxe.""",

    "Ossuary": """A storage room crammed with bones in every corner, maybe even up to the ceiling. 
Whoever found their final rest here was either a beggar or criminal (or both). 
Add -2 to any rolls on the treasure table, but +2 to any rolls for random encounters.""",

    "Public Fungal Garden": """An eerie expanse of bioluminescent mushrooms and twisted fungi that have been untended for decades. 
Stone pathways wind through the garden, now overgrown with moss and vines. 
There is a 50% chance that the place bears an additional detail. Choose one of the following options:
- glowing mushrooms: the area is well lit.
- hedge maze: treat like “labyrinthine” detail
- overgrown: treat like “obscured” detail
- slime fungus: treat like that very detail
- spore cloud: treat like “mine damp” detail""",

    "Public Rock Garden": """A public place elaborately decorated with rocks, stones and gravel, sometimes with additional planting in between. 
In former times (i.e. on level 6 or higher), people even mastered the art of artificial crystal growth which resulted in the most breathtaking displays. 
There's a 1 in 3 chance that something valuable can be obtained from here, with a pickaxe or similar and some time.""",

    "Sculpture Gallery": """A vast, echoing hall with high, crumbling walls, its once-pristine marble floors now cracked and uneven. 
Dust clings to the remnants of broken statues, some toppled, others half-eroded by time. 
There are 1d6 intact sculptures, just waiting to be toppled over on unwary enemies.""",

    "Slum": """A maze of narrow, crooked alleys choked with rubble and refuse. 
Only the indigent lived here. Add -2 on rolls to find treasure here and ignore any further bonuses on the roll. 
If you roll up a detail that includes treasure (bulky treasure, portcullis, treasure pile), change it into something mundane.""",

    "Storehouse": """A cavernous, dark space with rows of shelves and crates, many of them collapsed under the weight of time. 
Scattered barrels and sacks spill their long-rotted contents across the stone floor. 
There is probably not much left of value here, unless the place was left in haste. 
Choose one of the following options (or roll 1d6) for something to find while ransacking: 
1. Preserved goods: Salted or dried food in sealed barrels, possibly still edible.
2. Raw materials: Bolts of cloth, spools of rope, or planks of wood.
3. Tools: Hammers, nails, or other equipment for loading and repairs.
4. Containers: Empty barrels, crates, or sacks that could be repurposed.
5. Records: Shipping manifests or ledgers that hint on nearby locations.
6. Hidden stashes: Forgotten valuables, such as coins or luxury goods, tucked away in overlooked corners. Roll for something on the treasure table.""",

    "Suites": """A cluster of dignified dwellings, the doorways arched and adorned with faded carvings. 
A communal well sits at the center, now dry and clogged with debris. Most sites still have some degree of furniture and are usually well defensible. 
If the PCs rest here, they don't get the usual -1 on their roll for stress reduction.""",

    "Tavern": """A once-welcoming facade now marred by cracks and creeping moss. 
Inside, the stone floor is littered with broken tables and overturned chairs. 
There's a 50% chance that one of the casks still contains 1d6 doses of booze.""",

    "Temple": """Walls adorned with faded carvings of family trees and solemn faces. 
Niches hold crumbling urns and plaques etched with ancestral names, some toppled and broken on the stone floor. 
A central shrine, once the focus of rituals, stands chipped and empty, surrounded by scattered offerings of dried cave flowers, burnt incense sticks, and rusted heirlooms. 
There is a strong taboo against ransacking these sacred places of ancestral worship, but what happens upwell usually stays upwell. 
If the PCs choose to do so, they get +1 for any rolls on the treasure table, but you also add +1 on the roll for a random encounter.""",

    "Wellguard Station": """A compact, sturdy structure. Inside, the main room holds a long table, surrounded by broken chairs. 
Rusted weapon racks stand empty or with a few forgotten spears and swords, their blades dulled by time. 
Roll 1d6 for something intact to find while ransacking:
1. Sword
2. Shield
3. Spear
4. Cuirass and hauberk
5. Chain (5m)
6. Set of dice""",

    "Workshop": """A cluttered, shadow-filled space with heavy workbenches covered in rusted tools and half-finished projects. 
Shelves sag under the weight of dusty jars, while broken crates spill their contents across the floor. 
Choose one of the following options or roll 1d6 to determine what kind of craftsman had his workplace here:
1. Blacksmith
2. Carpenter
3. Stonemason
4. Weaver
5. Potter
6. Bookbinder""",
}

DETAIL_DESCRIPTIONS = {

    "Amphoras": """The location is crammed with large pieces of sealed crockery. 
They might contain organic goods (most likely rotten) or mortal remains. 
The PCs can choose to smash them while ransacking for a +1 bonus to find treasure, 
but the noise might attract something unwanted (+1 on roll for random encounter).""",

    "Blocked Exit": """The only other exit of this location is blocked. 
Choose one of the following:
- It is a light door that was barricaded, maybe even nailed up with furniture from the side the PCs are on. It can be cleared easily, but is that a good idea? If the PCs choose to go deeper from here, add +1 to the next random encounter check.
- It is a strong door with an iron lock. If the PCs want to go deeper from here, they have to find a way to open it first. While ransacking the location, they have a 1 in 6 chance to find the key.
- It is a simple passage that became overgrown with fungal weeds. The PCs can hack or burn their way through, but whatever waits in the next room might have a walk-over ambushing them. They get a -1 to awareness and stealth while going deeper from here. You should consider adding the 'obscured' detail to the next location.""",

    "Bulky Treasure": """The location contains something valuable that is hard to move. 
It might be some lavish piece of furniture, huge ornate rug or musical instrument. 
Pick something from the treasure table that is appropriate for the current level. 
If a PC wants to carry it along, they can’t take any other actions while moving between locations from now on. 
The next time the group is fleeing from a fight, they have to leave the item behind.""",

    "Chandelier": """A large chandelier is hanging from the ceiling, held up by an old rusty chain, fixed to one of the walls. 
A decent hit will cause it to fall, knocking down anything underneath, causing 1d6 damage.""",

    "Crevice": """The location is split in half. 
A PC can simply leap over it, but in the heat of a fight it might require a difficulty 5 roll to not trip. 
There's a 1 in 3 chance that something valuable lies at the bottom of the crevice (roll on the treasure table).""",

    "Dead End": """The location forms a dead end, from which the PCs have to backtrack. 
There is no way to go deeper from here.""",

    "Dead Gravedigger": """It might be someone the PCs know from Bastion (maybe they even came to search for them) or someone who's been lying here for centuries. 
If the PCs search the body, roll a d6 to see what they find: 
1. rotten food
2. two torches 
3. booze
4. half finished letter (to someone who might be long dead)
5. minor piece of treasure
6. map to a random location or some hidden treasure""",

    "Fireplace": """The location contains a large built-in fireplace, maybe with a bucket of coal nearby. 
The chimney leads to some kind of ventilation system, from which at least one other location is reachable. 
If the PCs want to climb up the chimney, they can use it to travel between any existing locations that have been generated with a fireplace. 
If no such place exists yet, instead they find a new location with a fireplace.""",

    "Fragile": """Parts of the location are structurally weak and in danger of collapsing. 
PCs who succeeded with their roll on awareness notice this. If the group ransacks the location (or interacts with it in any other way), something bad happens. 
Choose one of the following:
- Collapsing ceiling: everyone in the room suffers 1d6+1 damage from falling stones. Dodging it is difficulty 5. Halve rolls for any attempt to defend from it without a shield (or anything alike).
- Collapsing entrance: the way back is blocked. Unless the PCs have any tools to actually dig through (which takes time), they cannot go back anymore from here. Erase one of the entrances to this location.
- Collapsing floor: the PCs suffer 1d6 damage from falling (armor doesn't help) and are now effectively in another room. Unless they have climbing tools, they cannot backtrack from here and are effectively lost. Roll up a new location 1d6 layers deeper.""",

    "Holes": """The walls are perforated with small cracks and holes. 
They seem to lead to other nearby locations but are too tight for a human to squeeze through. 
Bats, Spiders, Tangles (and other small things) fit through though and can thus ambush easily. 
As long as the PCs stay here, they will automatically be surprised if encountering any of these creatures.""",

    "Inactive Rune": """The magic faded away long ago, but it is still clearly visible. With a dose of paint, it can be reactivated. 
Roll a d6 to choose the type of rune:
1. annul
2. burn
3. light
4. purify
5. reveal magic
6. scry (shows some undiscovered place. Roll up a new location 1d6 layers deeper)""",

    "Labyrinthine": """The location is part of a larger complex of maze-like corridors, intersections and secluded dead ends. 
Going deeper from here requires a difficulty 5 navigation check. On a failure, the PCs are immediately lost.""",

    "Lift": """The location contains a lift consisting of a crank, iron cage and counterweight. 
The iron chains seem to be in okayish condition but the turning mechanism is jammed. A difficulty 5 roll can fix it so it can be used again. 
The lift shaft connects to a place 1d6 layers deeper (or less deep, if the current depth is greater 5). 
If the PCs want to use the lift, they have to leave someone behind to operate the crank. Roll up a new location if they do. """,

    "Looted": "Somebody has been here before and turned the place upside down. There is no treasure to be found here.",

    "Mine Damp": """The location is filled with dangerous gas. 
A PC with a mining background will notice the signs early, others might wander into this danger carelessly. 
Choose one of the following:
- Choke damp: torches extinguish on entering and stuff like burn runes or fire ampules might not work as expected. Staying here reduces the resilience of every living thing by 2 points per full exploration round (treat this like a minor complication).
- Stink damp: the sickening smell of rotten eggs gives all living creatures a -2 penalty to all actions and causes one point of stress per full exploration round spent here.
- Fire damp: torches flare up on entering and eventually cause an explosion that deals 2d6 fire damage to everything near. The sound of the detonation will attract anything nearby. Roll for a random encounter immediately.""",

    "Note": """A previous visitor has written something. It might be a small paper note or graffiti on the wall. 
The note contains information useful for gravediggers, either about nearby threats, valuables or some general information about the current level or a specific type of monster.""",

    "Obscured": """The location is thick with cobwebs or fungi sprawling in every corner. 
The PCs get a -1 on rolls to notice threats but +1 to be stealthy while inside.""",

    "Portcullis": """The location lies behind a huge portcullis. 
PCs can see what's on the other side but have to pick the lock or break it down to be able to reach it. 
Roll on the treasure table for something that is placed inside the location, clearly visible from outside.""",

    "Repurposed into Crypt": """Whatever this location used to be, at some point it was repurposed into a public crypt. 
Dozens of corpses fill the room, mostly in cheap caskets. Ignore any bonuses to rolls on the treasure table from the location.""",

    "Safe": """A small locked safe is integrated in one of the walls. 
Picking the lock is time consuming, but brute force likely won't get you anywhere (halve rolls for that). 
If the PCs manage to open it, roll for treasure as if they were ransacking the location. If there's no treasure, put something mundane inside, like business or legal papers.""",

    "Secret Passage": """A secret passage is hidden behind some unobtrusive architectural feature (fireplace, shelf, wall relief) and can be found while ransacking the place. 
It either connects to a previously explored location (less deep than the current one) or leads to a new location 1d6 layers deeper.""",

    "Signpost": """The location contains a partially destroyed map or signpost that once gave directions for the immediate neighborhood. 
The PCs get a +1 for their next exploration roll starting from this location.""",

    "Signs of Recent Passage": """Something was here not long ago. 
Roll on the encounter table to determine who or what left its mark on the location. 
It could be footprints, an abandoned campsite (from exiles or gravediggers), webs from crypt spiders or the disfigured remains of a monster's last victim. 
The next random encounter near this location should be with that creature.""",

    "Slime Fungus": """The floor is extremely sticky, producing a smacking sound with every footstep. 
All creatures move as if suffering from a minor leg wound, unless they are flying or climbing the ceiling.""",

    "Treasure Pile": """Something valuable lies here, in plain sight, which should make every gravedigger suspicious. 
Roll on the treasure table for something that is placed inside the location. The first time you roll for a random encounter here, add +1. 
Whatever the PCs might encounter is guarding the treasure, potentially trying to lure them into an ambush.""",

    "Vault": """The location is locked behind a strong iron or stone door. 
The PCs cannot see what's inside, but there might be some weathered sign nearby, giving them a hint. 
To get in, the PCs have to pick the lock or come up with some other method. Let the players halve their rolls for any attempt that relies on brute force. 
Inside the vault, PCs get a +1 to find treasure.""",

    "Vermin": """The place is crawling with rats or bugs.""",

    "Wet": """Water drips from the ceiling, forming big puddles on the floor. Every surface is damp.""",
}

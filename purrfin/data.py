"""All game content: species, foods, toys, upgrades. Tuning knobs live here."""

# ---------------------------------------------------------------- species
# rate  = scales/sec at Lv1, neutral mood
# cost  = price of the first one (more copies get pricier)
# habitat: bottom | mid | glass | inverted
# shape: cory | pleco | long | syno | banjo
# pattern: see sprites.py
SPECIES = [
    dict(id="sunflower", name="Sunflower Catfish", shape="long", size=(13, 6),
         body=(244, 196, 48), belly=(255, 236, 150), fin=(250, 170, 40),
         pattern="sunflower", pat=(120, 70, 30), tail="fork", barbel=4,
         habitat="bottom", speed=9,
         blurb="Golden and freckled like a sunflower head. Purrs when you pet it."),
    dict(id="bronze", name="Bronze Corydoras", shape="cory", size=(9, 6),
         body=(150, 120, 70), belly=(210, 190, 140), fin=(170, 150, 110),
         pattern="sheen", pat=(80, 140, 110), tail="fork", barbel=2,
         habitat="bottom", speed=10,
         blurb="A cheerful little vacuum. Wiggles its whiskers at everything."),
    dict(id="panda", name="Panda Corydoras", shape="cory", size=(9, 6),
         body=(236, 228, 214), belly=(255, 250, 240), fin=(225, 220, 210),
         pattern="panda", pat=(30, 30, 36), tail="fork", barbel=2,
         habitat="bottom", speed=10,
         blurb="Black eye patches, zero worries."),
    dict(id="oto", name="Otocinclus", shape="pleco", size=(8, 4),
         body=(180, 160, 110), belly=(230, 220, 190), fin=(170, 160, 120),
         pattern="stripe_h", pat=(60, 50, 40), tail="fork", barbel=0,
         habitat="glass", speed=7,
         blurb="Tiny algae-eating zamboni. Loves algae wafers."),
    dict(id="pictus", name="Pictus Catfish", shape="long", size=(14, 5),
         body=(200, 205, 215), belly=(240, 242, 248), fin=(210, 210, 220),
         pattern="spots", pat=(30, 30, 40), tail="fork", barbel=9,
         habitat="mid", speed=16,
         blurb="Zoomies incarnate, with whiskers longer than its patience."),
    dict(id="bristlenose", name="Bristlenose Pleco", shape="pleco", size=(12, 6),
         body=(80, 70, 55), belly=(130, 115, 90), fin=(90, 80, 60),
         pattern="dots", pat=(190, 180, 150), tail="round", barbel=0, bristles=True,
         habitat="glass", speed=6,
         blurb="Has a face only a fish-mom could love. You love it."),
    dict(id="upside", name="Upside-down Catfish", shape="syno", size=(11, 6),
         body=(196, 170, 130), belly=(120, 95, 70), fin=(185, 160, 120),
         pattern="blotch", pat=(90, 65, 45), tail="fork", barbel=3,
         habitat="inverted", speed=8,
         blurb="Swims belly-up on purpose. Thinks YOU are the weird one."),
    dict(id="glass", name="Glass Catfish", shape="long", size=(12, 5),
         body=(200, 230, 245), belly=(220, 240, 250), fin=(210, 235, 250),
         pattern="glass", pat=(150, 170, 190), tail="fork", barbel=3,
         habitat="mid", speed=12,
         blurb="Completely see-through. Hard to find, easy to adore."),
    dict(id="julii", name="Julii Corydoras", shape="cory", size=(9, 6),
         body=(220, 220, 214), belly=(250, 248, 240), fin=(215, 215, 210),
         pattern="leopard", pat=(40, 40, 46), tail="fork", barbel=2,
         habitat="bottom", speed=11,
         blurb="Leopard print. Very fashionable. Very small."),
    dict(id="clown", name="Clown Pleco", shape="pleco", size=(10, 5),
         body=(50, 40, 34), belly=(80, 66, 50), fin=(60, 48, 38),
         pattern="bands", pat=(230, 140, 50), tail="round", barbel=0,
         habitat="glass", speed=6,
         blurb="Orange-banded wood chewer. Will eat your driftwood. Respectfully."),
    dict(id="zebra", name="Zebra Pleco", shape="pleco", size=(11, 5),
         body=(245, 245, 245), belly=(255, 255, 255), fin=(240, 240, 240),
         pattern="zebra", pat=(20, 20, 26), tail="round", barbel=0,
         habitat="glass", speed=6,
         blurb="Rare, striped, and aware of it."),
    dict(id="polka", name="Polka-dot Synodontis", shape="syno", size=(13, 7),
         body=(214, 206, 196), belly=(240, 236, 228), fin=(200, 196, 190),
         pattern="dots_big", pat=(25, 25, 30), tail="fork", barbel=4,
         habitat="bottom", speed=10,
         blurb="Covered in dots. Counted them once. Lost count at 'a lot'."),
    dict(id="raphael", name="Striped Raphael", shape="syno", size=(13, 7),
         body=(48, 40, 36), belly=(70, 60, 54), fin=(60, 52, 46),
         pattern="raphael", pat=(240, 236, 220), tail="fork", barbel=3,
         habitat="bottom", speed=8, purrs=True,
         blurb="The 'talking catfish'. Actually croaks and purrs when you pet it!"),
    dict(id="banjo", name="Banjo Catfish", shape="banjo", size=(12, 5),
         body=(120, 90, 60), belly=(150, 120, 85), fin=(110, 85, 60),
         pattern="blotch", pat=(70, 50, 34), tail="round", barbel=2,
         habitat="bottom", speed=5,
         blurb="Shaped like a banjo. Doesn't play the banjo. Yet."),
    dict(id="albino", name="Albino Bristlenose", shape="pleco", size=(12, 6),
         body=(250, 220, 170), belly=(255, 240, 210), fin=(250, 225, 180),
         pattern="none", pat=(0, 0, 0), tail="round", barbel=0, bristles=True,
         eye=(220, 40, 60), habitat="glass", speed=6,
         blurb="A sunbeam with bristles and ruby eyes."),
    dict(id="royal", name="Royal Pleco", shape="pleco", size=(15, 7),
         body=(110, 120, 110), belly=(150, 160, 150), fin=(120, 130, 120),
         pattern="royal", pat=(60, 66, 60), tail="fork", barbel=0,
         eye=(200, 50, 50), habitat="glass", speed=5,
         blurb="Pinstriped nobility. Demands driftwood tribute."),
    dict(id="redtail", name="Redtail Catfish", shape="long", size=(20, 8),
         body=(60, 62, 70), belly=(240, 236, 228), fin=(70, 70, 80),
         pattern="redtail", pat=(225, 70, 40), tail="fork", barbel=8,
         habitat="bottom", speed=9,
         blurb="A gentle giant. Mostly gentle. Definitely a giant."),
    dict(id="golden", name="Golden Sunflower", shape="long", size=(16, 7),
         body=(255, 210, 60), belly=(255, 245, 180), fin=(255, 190, 40),
         pattern="golden", pat=(160, 90, 20), tail="fork", barbel=6,
         habitat="mid", speed=11, purrs=True,
         blurb="Legend says it was born from a sunflower that fell into a river."),
    dict(id="moon", name="Moonlight Catfish", shape="long", size=(16, 7),
         body=(150, 170, 235), belly=(220, 230, 255), fin=(170, 190, 245),
         pattern="moon", pat=(250, 250, 255), tail="fork", barbel=7,
         habitat="mid", speed=10, purrs=True,
         blurb="Only shows up for keepers who have truly mastered the tank."),
    # ---------------- late game (added in 1.2): appended so earlier tiers never change
    dict(id="stone", name="Asian Stone Catfish", shape="banjo", size=(9, 4),
         body=(120, 100, 76), belly=(160, 140, 110), fin=(110, 92, 70),
         pattern="blotch", pat=(70, 56, 42), tail="round", barbel=2,
         habitat="bottom", speed=4,
         blurb="Looks exactly like a pebble. That's the whole plan."),
    dict(id="bumblebee", name="Bumblebee Catfish", shape="long", size=(12, 5),
         body=(240, 200, 60), belly=(250, 225, 120), fin=(230, 190, 60),
         pattern="zebra", pat=(40, 30, 24), tail="fork", barbel=4,
         habitat="bottom", speed=9,
         blurb="Striped like a bee. Does not sting. Does nap a lot."),
    dict(id="peppered", name="Peppered Corydoras", shape="cory", size=(9, 6),
         body=(150, 160, 130), belly=(215, 215, 195), fin=(160, 165, 140),
         pattern="spots", pat=(60, 66, 54), tail="fork", barbel=2,
         habitat="bottom", speed=10,
         blurb="A classic cory with a sprinkle of pepper."),
    dict(id="sterbai", name="Sterbai Corydoras", shape="cory", size=(9, 6),
         body=(70, 66, 70), belly=(230, 225, 215), fin=(240, 150, 60),
         pattern="dots", pat=(240, 240, 235), tail="fork", barbel=2,
         habitat="bottom", speed=11,
         blurb="Polka dots and bright orange fins. Very stylish."),
    dict(id="goldnugget", name="Gold Nugget Pleco", shape="pleco", size=(13, 6),
         body=(40, 40, 44), belly=(70, 66, 60), fin=(250, 210, 60),
         pattern="dots", pat=(250, 210, 70), tail="round", barbel=0,
         habitat="glass", speed=5,
         blurb="Covered in gold dots. Basically a walking treasure."),
    dict(id="leopardfrog", name="Leopard Frog Pleco", shape="pleco", size=(10, 5),
         body=(230, 160, 70), belly=(240, 190, 110), fin=(220, 150, 60),
         pattern="bands", pat=(30, 26, 24), tail="round", barbel=0,
         habitat="glass", speed=6,
         blurb="Orange and black bands, like a tiny tiger."),
    dict(id="featherfin", name="Featherfin Synodontis", shape="syno", size=(15, 8),
         body=(200, 190, 170), belly=(235, 230, 215), fin=(190, 180, 160),
         pattern="dots_big", pat=(60, 50, 40), tail="fork", barbel=5,
         habitat="bottom", speed=9,
         blurb="Waves its huge dorsal fin like a flag."),
    dict(id="cuckoo", name="Cuckoo Synodontis", shape="syno", size=(11, 6),
         body=(220, 205, 170), belly=(245, 235, 210), fin=(210, 195, 160),
         pattern="dots_big", pat=(30, 26, 22), tail="fork", barbel=4,
         habitat="bottom", speed=10,
         blurb="Sneaks its eggs into other fish's nests. Rude, but cute."),
    dict(id="porthole", name="Porthole Catfish", shape="long", size=(14, 6),
         body=(190, 185, 170), belly=(230, 225, 210), fin=(180, 175, 160),
         pattern="spots", pat=(40, 36, 30), tail="fork", barbel=5,
         habitat="mid", speed=11,
         blurb="Has little round 'windows' all along its side."),
    dict(id="twig", name="Twig Catfish", shape="long", size=(19, 3),
         body=(140, 110, 70), belly=(180, 150, 105), fin=(130, 100, 65),
         pattern="stripe_h", pat=(80, 60, 40), tail="fork", barbel=0,
         habitat="glass", speed=4,
         blurb="Is it a stick? Is it a fish? Yes."),
    dict(id="whiptail", name="Whiptail Catfish", shape="pleco", size=(16, 4),
         body=(170, 140, 100), belly=(210, 190, 150), fin=(160, 130, 95),
         pattern="bands", pat=(90, 70, 50), tail="fork", barbel=0,
         habitat="glass", speed=5,
         blurb="Long, flat and very good at hide and seek."),
    dict(id="sailfin", name="Sailfin Pleco", shape="pleco", size=(18, 8),
         body=(130, 110, 80), belly=(170, 150, 115), fin=(120, 100, 70),
         pattern="leopard", pat=(60, 46, 32), tail="fork", barbel=0,
         habitat="glass", speed=5,
         blurb="Raises a huge sail when it's showing off."),
    dict(id="tigershovel", name="Tiger Shovelnose", shape="long", size=(22, 6),
         body=(170, 170, 160), belly=(235, 235, 225), fin=(160, 150, 140),
         pattern="bands", pat=(40, 40, 46), tail="fork", barbel=9,
         habitat="bottom", speed=12,
         blurb="A long, striped, shovel-nosed hunter. Very dramatic."),
    dict(id="spottedraphael", name="Spotted Raphael", shape="syno", size=(12, 7),
         body=(44, 40, 38), belly=(70, 64, 58), fin=(56, 50, 46),
         pattern="dots", pat=(240, 235, 210), tail="fork", barbel=3,
         habitat="bottom", speed=7, purrs=True,
         blurb="The talking catfish's spotty cousin. Also chatty."),
    dict(id="electric", name="Electric Catfish", shape="long", size=(16, 8),
         body=(160, 150, 130), belly=(220, 210, 190), fin=(150, 140, 120),
         pattern="blotch", pat=(70, 64, 56), tail="round", barbel=6,
         habitat="bottom", speed=6,
         blurb="Gives a tiny zap when it's happy. Pet carefully!"),
    dict(id="channel", name="Channel Catfish", shape="long", size=(20, 7),
         body=(130, 140, 150), belly=(225, 230, 235), fin=(120, 130, 140),
         pattern="spots", pat=(50, 56, 66), tail="fork", barbel=8,
         habitat="bottom", speed=10,
         blurb="The river classic. Whiskers for days."),
    dict(id="bluecat", name="Blue Catfish", shape="long", size=(22, 8),
         body=(100, 130, 170), belly=(215, 225, 240), fin=(90, 120, 160),
         pattern="none", pat=(0, 0, 0), tail="fork", barbel=8,
         habitat="bottom", speed=10,
         blurb="Big, blue and very calm about it."),
    dict(id="wels", name="Wels Catfish", shape="long", size=(25, 9),
         body=(90, 100, 70), belly=(200, 200, 170), fin=(80, 90, 60),
         pattern="blotch", pat=(50, 60, 40), tail="round", barbel=10,
         habitat="bottom", speed=8,
         blurb="One of the biggest catfish in the world. A gentle submarine."),
    dict(id="mekong", name="Mekong Giant Catfish", shape="long", size=(27, 10),
         body=(150, 155, 160), belly=(230, 232, 235), fin=(140, 145, 150),
         pattern="none", pat=(0, 0, 0), tail="fork", barbel=2,
         habitat="mid", speed=8,
         blurb="A true giant of the river. Barely fits in the tank."),
    dict(id="aurora", name="Aurora Catfish", shape="long", size=(18, 8),
         body=(200, 120, 255), belly=(240, 220, 255), fin=(140, 230, 255),
         pattern="rainbow", pat=(255, 255, 255), tail="fork", barbel=7,
         habitat="mid", speed=11, purrs=True,
         blurb="Shimmers through every colour of the northern lights."),
    dict(id="galaxy", name="Galaxy Catfish", shape="long", size=(20, 9),
         body=(40, 30, 80), belly=(80, 60, 140), fin=(90, 70, 170),
         pattern="galaxy", pat=(255, 250, 220), tail="fork", barbel=8,
         habitat="mid", speed=10, purrs=True,
         blurb="Made of stardust. Folks used to say it was the last catfish. Folks were wrong."),
    # ---------------- 1.5: twenty more, for keepers who reach the very top
    dict(id="bluechannel", name="Blue Channel Catfish", shape="long", size=(24, 9), art="bluechannel",
         body=(9, 101, 213), belly=(6, 118, 255), fin=(10, 58, 117),
         pattern="none", pat=(0, 0, 0), tail="fork", barbel=6,
         habitat="mid", speed=12, purrs=True,
         blurb="Drawn by a friend of the tank. Its whiskers are longer than a school day."),
    dict(id="flathead", name="Flathead Catfish", shape="long", size=(24, 9),
         body=(150, 120, 70), belly=(220, 200, 150), fin=(130, 100, 60),
         pattern="blotch", pat=(90, 70, 40), tail="round", barbel=4,
         habitat="bottom", speed=7,
         blurb="A flat, grumpy-looking river boss. Secretly a softie."),
    dict(id="vampire", name="Vampire Catfish", shape="long", size=(13, 5),
         body=(210, 190, 200), belly=(240, 230, 235), fin=(190, 120, 140),
         pattern="none", pat=(0, 0, 0), tail="fork", barbel=4,
         habitat="mid", speed=16,
         blurb="Small, pale and dramatic. Only drinks... fish flakes."),
    dict(id="iridescent", name="Iridescent Shark Catfish", shape="long", size=(22, 8),
         body=(150, 160, 175), belly=(225, 230, 240), fin=(120, 130, 150),
         pattern="sheen", pat=(140, 200, 230), tail="fork", barbel=2,
         habitat="mid", speed=15,
         blurb="Not a shark at all. Shimmers like a soap bubble when it turns."),
    dict(id="asianredtail", name="Asian Redtail Catfish", shape="long", size=(22, 8),
         body=(110, 100, 90), belly=(220, 210, 195), fin=(220, 70, 50),
         pattern="redtail", pat=(230, 70, 50), tail="fork", barbel=8,
         habitat="mid", speed=13,
         blurb="Fiery tail, long whiskers, big appetite."),
    dict(id="lima", name="Lima Shovelnose", shape="long", size=(22, 5),
         body=(200, 205, 210), belly=(245, 245, 248), fin=(190, 195, 200),
         pattern="stripe_h", pat=(40, 40, 50), tail="fork", barbel=9,
         habitat="bottom", speed=14,
         blurb="A sleek racing stripe with whiskers to match."),
    dict(id="frogmouth", name="Chocolate Frogmouth", shape="banjo", size=(13, 7),
         body=(110, 70, 45), belly=(170, 130, 95), fin=(95, 60, 40),
         pattern="blotch", pat=(70, 45, 30), tail="round", barbel=2,
         habitat="bottom", speed=5,
         blurb="Mostly mouth. Looks like a chocolate bar that learned to swim."),
    dict(id="piraiba", name="Piraiba Catfish", shape="long", size=(28, 10),
         body=(120, 130, 135), belly=(225, 228, 230), fin=(100, 110, 115),
         pattern="dots", pat=(70, 75, 80), tail="fork", barbel=6,
         habitat="mid", speed=9,
         blurb="The Amazon's gentle giant. It has seen things."),
    dict(id="goonch", name="Goonch Catfish", shape="long", size=(26, 10),
         body=(130, 115, 90), belly=(205, 195, 170), fin=(110, 95, 75),
         pattern="blotch", pat=(80, 65, 45), tail="fork", barbel=5,
         habitat="bottom", speed=8,
         blurb="A mountain-river legend with a very serious face."),
    dict(id="bluepanaque", name="Blue-eyed Panaque", shape="pleco", size=(18, 8),
         body=(55, 60, 70), belly=(90, 95, 110), fin=(50, 55, 65),
         pattern="none", pat=(0, 0, 0), tail="round", barbel=0,
         habitat="glass", speed=6,
         blurb="Dark as night with stunning sky-blue eyes."),
    dict(id="coral", name="Coral Catfish", shape="long", size=(18, 5),
         body=(70, 60, 50), belly=(240, 230, 210), fin=(80, 70, 60),
         pattern="stripe_h", pat=(250, 240, 220), tail="round", barbel=6,
         habitat="mid", speed=13,
         blurb="Swims in a wiggly line with its friends. A tiny striped parade."),
    dict(id="ember", name="Ember Catfish", shape="long", size=(20, 8),
         body=(240, 110, 40), belly=(255, 200, 90), fin=(220, 60, 30),
         pattern="golden", pat=(255, 230, 120), tail="fork", barbel=6,
         habitat="mid", speed=12, purrs=True,
         blurb="Warm to the touch. Keeps the whole tank cozy."),
    dict(id="frost", name="Frost Catfish", shape="long", size=(20, 8),
         body=(180, 220, 245), belly=(240, 250, 255), fin=(140, 190, 235),
         pattern="moon", pat=(255, 255, 255), tail="fork", barbel=6,
         habitat="mid", speed=11, purrs=True,
         blurb="Leaves a trail of tiny snowflakes. Nobody knows how."),
    dict(id="thunder", name="Thunderwhisker Catfish", shape="syno", size=(18, 9),
         body=(90, 70, 160), belly=(170, 150, 220), fin=(250, 220, 60),
         pattern="zebra", pat=(250, 220, 60), tail="fork", barbel=8,
         habitat="bottom", speed=13, purrs=True,
         blurb="Its whiskers crackle. Pet it and your hair stands up."),
    dict(id="crystal", name="Crystal Catfish", shape="long", size=(20, 8),
         body=(240, 190, 230), belly=(255, 235, 250), fin=(220, 170, 240),
         pattern="glass", pat=(255, 255, 255), tail="fork", barbel=5,
         habitat="mid", speed=11, purrs=True,
         blurb="Clear as glass and pink as sunrise. Rings softly like a bell."),
    dict(id="jade", name="Jade Dragon Catfish", shape="long", size=(24, 9),
         body=(60, 170, 110), belly=(200, 240, 200), fin=(230, 190, 70),
         pattern="leopard", pat=(30, 100, 60), tail="fork", barbel=9,
         habitat="mid", speed=11, purrs=True,
         blurb="Carved from living jade, with golden fins. Very lucky."),
    dict(id="phoenix", name="Phoenix Catfish", shape="long", size=(22, 9),
         body=(255, 120, 60), belly=(255, 220, 120), fin=(255, 70, 110),
         pattern="rainbow", pat=(255, 255, 200), tail="fork", barbel=7,
         habitat="mid", speed=12, purrs=True,
         blurb="Every sunrise it glows a little brighter."),
    dict(id="lantern", name="Abyssal Lantern Catfish", shape="long", size=(22, 9),
         body=(20, 30, 60), belly=(40, 60, 100), fin=(60, 220, 230),
         pattern="moon", pat=(120, 255, 240), tail="fork", barbel=8,
         habitat="bottom", speed=9, purrs=True,
         blurb="From the deepest dark. Its spots glow so its friends can find it."),
    dict(id="leviathan", name="Starlight Leviathan", shape="long", size=(28, 11),
         body=(30, 25, 70), belly=(90, 70, 160), fin=(150, 120, 230),
         pattern="galaxy", pat=(255, 250, 220), tail="fork", barbel=9,
         habitat="mid", speed=8, purrs=True,
         blurb="Bigger than the Galaxy Catfish. Its whiskers trail actual comets."),
    dict(id="eternal", name="Eternal Catfish", shape="long", size=(26, 10),
         body=(255, 245, 210), belly=(255, 255, 240), fin=(255, 220, 120),
         pattern="rainbow", pat=(255, 255, 255), tail="fork", barbel=10,
         habitat="mid", speed=10, purrs=True,
         blurb="The truly final catfish. If you're reading this: you won fishkeeping."),
]

SPECIES_COST0 = 40       # cost of species #1 (#0 is the starter)
# Price growth per species tier, tuned with sim_school.py for a school day:
# fast & clicky for the first ~15 min, then roughly one new species per class period.
SPECIES_GROWTH = [(8, 9.0), (12, 13.0), (18, 7.5), (99, 6.0)]   # (up to tier, growth)
SPECIES_RATE0 = 1.0
SPECIES_RATEG = 3.0
COPY_GROWTH = 1.55       # each extra copy of the same species costs this much more

_cost = SPECIES_COST0
for _i, _s in enumerate(SPECIES):
    _s["tier"] = _i
    _s["rate"] = SPECIES_RATE0 * SPECIES_RATEG ** _i
    if _i > 1:
        _cost *= next(g for upto, g in SPECIES_GROWTH if _i <= upto)
    _s["cost"] = 10 if _i == 0 else _cost

SPECIES_BY_ID = {s["id"]: s for s in SPECIES}

# ---------------------------------------------------------------- seasons
# Seasonal things can only be bought while their season is on (by the computer's date).
# Once you've had one, you keep it - and can buy it again after Spawning Season, any time of year.
SEASONS = {
    "halloween": dict(name="Halloween", start=(10, 1), end=(11, 2)),     # (month, day), both inclusive
}

# Seasonal catfish: not part of the normal species ladder. They earn a multiple of your best
# regular species (so they stay worth having at any point of the game), one per tank.
SEASONAL_SPECIES = [
    dict(id="pumpkin", name="Pumpkin Catfish", shape="cory", size=(11, 7),
         body=(242, 128, 28), belly=(255, 186, 84), fin=(70, 130, 46),
         pattern="pumpkin", pat=(40, 18, 8), tail="round", barbel=3,
         habitat="bottom", speed=9, purrs=True, season="halloween",
         best_mult=2.0, cost_secs=900, cost_min=300,
         blurb="Carved with a spooky grin. Blows skull bubbles worth 3x!"),
]
for _s in SEASONAL_SPECIES:
    _s["tier"] = 0
    _s["rate"] = 1.0
    _s["cost"] = _s["cost_min"]
    SPECIES_BY_ID[_s["id"]] = _s
SEASONAL_BY_ID = {s["id"]: s for s in SEASONAL_SPECIES}
SKULL_POP_MULT = 3          # skull bubbles from the Pumpkin Catfish
SKULL_POP_EVERY = (14, 22)  # seconds between them

FISH_NAMES = [
    "Sunny", "Mochi", "Biscuit", "Noodle", "Whiskers", "Pickle", "Bean", "Tofu",
    "Nugget", "Pudding", "Waffles", "Sprout", "Pebble", "Barnacle", "Muffin",
    "Captain", "Sir Purrs", "Bubbles", "Zoomer", "Loaf", "Chonk", "Doodle",
    "Peanut", "Gizmo", "Toast", "Kiwi", "Marble", "Sushi", "Clover", "Mango",
    "Cheddar", "Puddle", "Dumpling", "Ziggy", "Olive", "Honey", "Fig", "Gus",
    "Mr. Mustache", "Professor", "Scoot", "Basil", "Pip", "Sesame", "Caramel",
]

# ---------------------------------------------------------------- foods
# Paid foods cost max(min, income * secs). Unlock when lifetime earnings >= unlock.
FOODS = [
    dict(id="flakes", name="Flake Food", color=(240, 170, 80), secs=0, min=0, unlock=0,
         full=22, happy=3, xp=2, cooldown=2.0, sink=6,
         desc="Free basics. +fullness."),
    dict(id="pellets", name="Sinking Pellets", color=(170, 110, 60), secs=25, min=25, unlock=150,
         full=45, happy=8, xp=8, cooldown=0.5, sink=14,
         desc="Big filling pellets that sink straight to the bottom-dwellers."),
    dict(id="bloodworms", name="Bloodworms", color=(200, 40, 50), secs=60, min=120, unlock=1500,
         full=30, happy=35, xp=15, cooldown=0.5, sink=9,
         desc="A treat! Huge happiness boost."),
    dict(id="algae", name="Algae Wafer", color=(70, 140, 60), secs=45, min=300, unlock=8000,
         full=55, happy=15, xp=10, cooldown=0.5, sink=12, pleco_bonus=3,
         desc="Plecos & otos get 3x the benefit."),
    dict(id="shrimp", name="Shrimp Pellets", color=(240, 120, 110), secs=120, min=2000, unlock=60000,
         full=35, happy=10, xp=60, cooldown=0.5, sink=11,
         desc="Protein-packed. Lots of XP."),
    dict(id="daphnia", name="Daphnia", color=(200, 120, 90), secs=90, min=1000, unlock=25000,
         full=20, happy=20, xp=40, cooldown=0.5, sink=3,
         desc="Tiny water fleas. Fish chase them all over. Good XP."),
    dict(id="seeds", name="Sunflower Seeds", color=(250, 220, 90), secs=400, min=20000, unlock=400000,
         full=25, happy=20, xp=10, cooldown=1.0, sink=8, buff=("double", 300),
         desc="Shell-on snack. 2x scales for 5 minutes!"),
    dict(id="brine", name="Brine Shrimp", color=(255, 160, 120), secs=250, min=100000, unlock=5e6,
         full=30, happy=25, xp=25, cooldown=1.0, sink=5, buff=("frenzy", 180),
         desc="Live food frenzy! Pop-bubbles appear 4x as often for 3 min."),
    dict(id="kelp", name="Catnip Kelp", color=(110, 200, 120), secs=600, min=1e6, unlock=8e7,
         full=20, happy=100, xp=30, cooldown=1.0, sink=4, buff=("bliss", 600),
         desc="It's catnip... for catfish. Max happiness for 10 min."),
    dict(id="golden", name="Golden Pellet", color=(255, 215, 40), secs=1800, min=1e7, unlock=2e9,
         full=60, happy=40, xp=0, cooldown=2.0, sink=10, levelup=1,
         desc="Whoever eats it instantly gains a level."),
]
FOODS_BY_ID = {f["id"]: f for f in FOODS}

# ---------------------------------------------------------------- toys
# bonus: +% global output per level
# pay: when a fish plays with it, scales = that fish's income x pay x level factor
TOYS = [
    dict(id="ball", name="Ping-Pong Ball", cost=60, bonus=4, pay=3, desc="Floats at the top. Fish bonk it."),
    dict(id="airstone", name="Air Stone", cost=400, bonus=3, pay=3, desc="Bubble stream. More pop-bubbles."),
    dict(id="duck", name="Rubber Duck", cost=1200, bonus=4, pay=3, desc="Bobs on the surface. Squeak!"),
    dict(id="cave", name="Driftwood Cave", cost=2500, bonus=6, pay=4, desc="A cozy hidey-hole."),
    dict(id="apple", name="Teacher's Apple", cost=8000, bonus=8, pay=4, desc="A shiny red apple for the best teacher."),
    dict(id="shells", name="Seashell Pile", cost=15000, bonus=6, pay=4, desc="Pretty shells to poke around in."),
    dict(id="sunflower", name="Sunflower Ornament", cost=30000, bonus=10, pay=5, desc="The tank's namesake. Big bonus."),
    dict(id="lilypad", name="Lily Pads", cost=120000, bonus=6, pay=4, desc="Float on the surface. Shady naps below."),
    dict(id="bamboo", name="Bamboo Shoots", cost=2.5e5, bonus=7, pay=4, desc="Tall green stalks to weave through."),
    dict(id="marimo", name="Marimo Moss Ball", cost=4e5, bonus=6, pay=4, desc="A fuzzy friend that rolls around."),
    dict(id="waterfall", name="Mini Waterfall", cost=1.5e6, bonus=9, pay=5, desc="A tiny waterfall pouring into the tank."),
    dict(id="bottle", name="Message in a Bottle", cost=3e6, bonus=7, pay=5, desc="Who sent it? Nobody knows."),
    dict(id="chest", name="Treasure Chest", cost=6e6, bonus=5, pay=4, desc="Pops open to release bubble bursts."),
    dict(id="hammock", name="Leaf Hammock", cost=2.5e7, bonus=8, pay=5, desc="Naps are productive, actually."),
    dict(id="desk", name="Little School Desk", cost=5e7, bonus=9, pay=5, desc="A tiny classroom. Class is in session!"),
    dict(id="volcano", name="Bubble Volcano", cost=1e8, bonus=9, pay=5, desc="Erupts with bubbles every so often."),
    dict(id="castle", name="Tiny Castle", cost=4e8, bonus=10, pay=6, desc="Every catfish is royalty here."),
    dict(id="snail", name="Snail Shell House", cost=8e8, bonus=10, pay=6, desc="Has a little door and a little window."),
    dict(id="log", name="Mossy Log", cost=1.6e9, bonus=10, pay=6, desc="Hollow log. Catfish love squeezing through."),
    dict(id="clam", name="Pearl Clam", cost=7e9, bonus=12, pay=6, desc="Coughs up bonus pop-bubbles."),
    dict(id="crystal", name="Rainbow Crystal", cost=1.5e10, bonus=12, pay=6, desc="Shimmers through every colour."),
    dict(id="statue", name="Catfish Statue", cost=3e10, bonus=13, pay=7, desc="A monument to the greatest catfish."),
    dict(id="ship", name="Sunken Ship", cost=1.3e11, bonus=14, pay=7, desc="Arr. Whiskers ahoy."),
    dict(id="lighthouse", name="Mini Lighthouse", cost=3e11, bonus=14, pay=7, desc="Guides lost catfish home."),
    dict(id="geyser", name="Spring Geyser", cost=6e11, bonus=15, pay=8, desc="Fresh spring water bubbling up from below."),
    dict(id="coral", name="Glow Coral", cost=3e12, bonus=16, pay=8, desc="Softly glows. Very calming."),
    dict(id="fossil", name="Ancient Fossil", cost=6e12, bonus=17, pay=8, desc="A catfish from a very long time ago."),
    dict(id="diver", name="Little Diver", cost=1.5e13, bonus=20, pay=9, desc="He's been down here a while."),
    dict(id="fountain", name="Grand Fountain", cost=8e13, bonus=25, pay=10, desc="The finest water feature money can buy."),
    dict(id="conch", name="Bubble Ring Conch", cost=4e14, bonus=30, pay=12, desc="Blows perfect bubble rings."),
    # ---------------- trillions (1.2.4): fills the gap before the late game
    dict(id="anchor", name="Old Anchor", cost=6e14, bonus=22, pay=10, desc="A rusty anchor with a long chain."),
    dict(id="sub", name="Toy Submarine", cost=1.2e15, bonus=22, pay=10, desc="A little yellow sub. Its light blinks."),
    dict(id="wheel", name="Water Wheel", cost=3e15, bonus=23, pay=10, desc="Turns slowly in the current."),
    dict(id="mushrooms", name="Glow Mushrooms", cost=8e15, bonus=24, pay=10, desc="Soft glowing mushrooms."),
    dict(id="lavalamp", name="Lava Lamp", cost=2e16, bonus=25, pay=11, desc="Groovy blobs, rising and falling."),
    dict(id="pagoda", name="Tiny Pagoda", cost=5e16, bonus=26, pay=11, desc="A peaceful little temple."),
    dict(id="organ", name="Bubble Organ", cost=1.3e17, bonus=27, pay=11, desc="Pipes that play bubbly music."),
    dict(id="icecave", name="Ice Cave", cost=3e17, bonus=28, pay=12, desc="A chilly blue cave. Catfish love it."),
    dict(id="jellies", name="Jelly Lanterns", cost=7e17, bonus=29, pay=12, desc="Glowing jellyfish lanterns on poles."),
    dict(id="throne", name="Pearl Throne", cost=1.5e18, bonus=30, pay=12, desc="A throne fit for a catfish king."),
    # ---------------- late game (1.2)
    dict(id="crystalcave", name="Crystal Cave", cost=3e+18, bonus=32, pay=12, desc="A glittering cave of purple crystals."),
    dict(id="hoard", name="Treasure Hoard", cost=3e+19, bonus=34, pay=13, desc="A mountain of gold coins. Catfish nap on it."),
    dict(id="trophy", name="Golden Catfish Trophy", cost=3e+20, bonus=36, pay=13, desc="Best Tank in the World. Obviously."),
    dict(id="tower", name="Bubble Tower", cost=3e+21, bonus=38, pay=14, desc="A tall tower that breathes out bubbles."),
    dict(id="temple", name="Sunken Temple", cost=3e+22, bonus=40, pay=15, desc="Ancient ruins from a lost catfish city."),
    dict(id="kraken", name="Friendly Kraken", cost=3e+23, bonus=42, pay=16, desc="Just a tentacle. It waves hello."),
    dict(id="rainbowfall", name="Rainbow Waterfall", cost=3e+24, bonus=45, pay=17, desc="A waterfall in every colour."),
    dict(id="moonpool", name="Moon Pool", cost=3e+25, bonus=48, pay=18, desc="A glowing pool that reflects the moon."),
    dict(id="starcoral", name="Star Coral", cost=3e+26, bonus=52, pay=19, desc="Coral that twinkles like the night sky."),
    dict(id="galaxyorb", name="Galaxy Orb", cost=3e+27, bonus=60, pay=22, desc="A swirling galaxy in a glass ball. The rarest toy of all."),
]
# seasonal toys: only for sale in their season (or again later, once you've owned one).
# They cost cost_secs of your income (at least `cost`), so they're worth having at any stage.
SEASONAL_TOYS = [
    dict(id="jackolantern", name="Jack-o'-Lantern", cost=5000, cost_secs=300, bonus=6, pay=5, season="halloween",
         desc="A grinning pumpkin that glows. Fish love the spooky light."),
    dict(id="cauldron", name="Witch's Cauldron", cost=8000, cost_secs=400, bonus=6, pay=5, season="halloween",
         desc="Bubbles green brew. Now and then it burps up a skull bubble worth 3x!"),
    dict(id="skeleton", name="Fishbone Skeleton", cost=4000, cost_secs=250, bonus=5, pay=4, season="halloween",
         desc="A friendly old fish skeleton. Its jaw clacks when fish swim by."),
    dict(id="candycorn", name="Candy Corn Pile", cost=3000, cost_secs=200, bonus=5, pay=6, season="halloween",
         desc="Sweet treats on the sand. Fish nibble them and shed extra scales."),
]
TOYS += SEASONAL_TOYS
TOY_LEVEL_GROWTH = 4.0
TOY_MAX_LEVEL = 10
TOYS_BY_ID = {t["id"]: t for t in TOYS}

# ---------------------------------------------------------------- upgrades
TANK_CAPACITY = [2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20, 22, 25]
TANK_NAMES = ["Nano Cube", "5 Gallon", "10 Gallon", "20 Long", "29 Gallon", "40 Breeder",
              "55 Gallon", "75 Gallon", "90 Gallon", "125 Gallon", "180 Gallon",
              "300 Gallon", "Living-room Wall", "Indoor Pond", "Private River"]

UPGRADES = [
    dict(id="tank", name="Bigger Tank", base=60, growth=11, max=len(TANK_CAPACITY) - 1,
         desc="Room for more catfish."),
    dict(id="filter", name="Canister Filter", base=100, growth=4.0, max=60,
         desc="+20% scales per level."),
    dict(id="conditioner", name="Water Conditioner", base=5e7, growth=6.0, max=25,
         desc="Crystal-clear water. +15% scales per level, and the water gets clearer."),
    dict(id="plants", name="Aquascaping", base=2e5, growth=6.0, max=12,
         desc="More live plants in the tank. +8% scales per level."),
    dict(id="pump", name="Current Pump", base=5e5, growth=7.0, max=20,
         desc="Gentle current. Toys pay +15% more per level."),
    dict(id="jar", name="Scale Jar", base=800, growth=5.0, max=15,
         desc="Fills with bonus scales while you're away. Click it to collect!"),
    dict(id="hatchery", name="Hatchery", base=1500, growth=7.0, max=10,
         desc="Lay free eggs. Hatchlings bring scales and level up your fish."),
    dict(id="autonest", name="Auto-Nest", base=3e6, growth=1.0, max=1,
         desc="After your eggs hatch, the same eggs are laid again for you."),
    dict(id="hands", name="Gentle Hands", base=30, growth=3.2, max=50,
         desc="Petting gives +30% more of everything."),
    dict(id="rub", name="Fin Scratches", base=150, growth=3.0, max=13,
         desc="Ability! Press Scratch! next to Shop, then hold the mouse on your fish and wiggle. Longer each level."),
    dict(id="magnet", name="Bubble Magnet", base=80, growth=3.3, max=50,
         desc="Pop-bubbles worth +35% more."),
    dict(id="lucky", name="Lucky Moss", base=1000, growth=4.0, max=12,
         desc="+1.5% chance for golden bubbles (10x value)."),
    dict(id="bubbler", name="Bubble Machine", base=150, growth=3.2, max=15,
         desc="Pop-bubbles appear more often."),
    dict(id="heater", name="Cozy Heater", base=300, growth=3.6, max=10,
         desc="Hunger & happiness drain 12% slower."),
    dict(id="light", name="Grow Light", base=200, growth=3.4, max=30,
         desc="Fish slowly gain XP on their own."),
    dict(id="feeder", name="Auto-Feeder", base=250, growth=6.0, max=5,
         desc="Feeds hungry fish while you're busy."),
    dict(id="care", name="Fish Sitter", base=2500, growth=5.0, max=8,
         desc="Earn more while the game is closed."),
    # ---------------- late game (1.2): start after the Moonlight Catfish; hidden until nearly affordable
    dict(id="abyss", name="Abyssal Filter", base=2e+18, growth=8.0, max=30,
         desc="Deep-sea filtration. +50% scales per level."),
    dict(id="school", name="Schooling Instinct", base=1e+19, growth=9.0, max=20,
         desc="Fish love company: +2% scales per fish in the tank, per level."),
    dict(id="polish", name="Scale Polish", base=3e+19, growth=6.0, max=30,
         desc="Pop-bubbles worth +100% more per level."),
    dict(id="current", name="Ocean Current", base=1e+20, growth=8.0, max=20,
         desc="Toys pay +50% more per level."),
    dict(id="timecrystal", name="Time Crystal", base=5e+20, growth=10.0, max=10,
         desc="Eggs hatch 10% faster and the jar fills 25% faster, per level."),
    dict(id="bait", name="Legendary Bait", base=3e+21, growth=12.0, max=10,
         desc="+1% shiny chance and +100% visitor gifts per level."),
    dict(id="infinity", name="Infinity Tank", base=3e+23, growth=25.0, max=10,
         desc="Room for 2 more catfish per level, beyond the biggest tank."),
]
# seasonal upgrades: same rules as seasonal toys; cost = cost_secs of income (at least base) x growth per level
UPGRADES += [
    dict(id="ghostglow", name="Ghostly Glow", base=20000, cost_secs=600, growth=3.0, max=10, season="halloween",
         desc="A spooky green shimmer. +10% scales per level."),
    dict(id="spooky", name="Spooky Bubbles", base=10000, cost_secs=400, growth=3.0, max=10, season="halloween",
         desc="Pop-bubbles and skull bubbles worth +40% per level."),
    dict(id="treats", name="Trick-or-Treat", base=30000, cost_secs=900, growth=4.0, max=5, season="halloween",
         desc="Visitors come 20% more often and bring +60% bigger gifts, per level."),
]
UPGRADES_BY_ID = {u["id"]: u for u in UPGRADES}

# ---------------------------------------------------------------- hatchery
# Laying eggs is free. When they hatch, baby fry swim around for a bit and bring:
#   gift   = scales, in seconds of your income
#   levels = level progress given to EVERY fish (1.0 = a full level)
CLUTCHES = [
    dict(id="quick", name="Small Egg", mins=10, gift=180, levels=0.25, empty=0.35, baby=0.25,
         color=(250, 240, 210),
         desc="Hatches fast. A little gift while you play."),
    dict(id="class", name="Big Blue Egg", mins=40, gift=600, levels=0.6, empty=0.10, baby=0.6,
         color=(180, 230, 250),
         desc="Takes a while. Every fish grows a good chunk of a level!"),
    dict(id="golden", name="Golden Egg", mins=120, gift=1800, levels=2.0, empty=0.0, baby=1.0,
         color=(255, 215, 80),
         desc="A long wait, but every fish grows 2 levels!"),
]
# found, not laid from the menu: golden bubbles and visitors sometimes drop one
MYSTERY_EGG = dict(id="mystery", name="Mystery Egg", mins=20, gift=1800, levels=2.0, empty=0.0, baby=0.0,
                   color=(170, 110, 240), special=True,
                   desc="Anything could hatch: scales, levels, a rare baby... or nothing at all!")
CLUTCHES_BY_ID = {c["id"]: c for c in CLUTCHES + [MYSTERY_EGG]}
MYSTERY_FROM_GOLDEN = 0.10     # chance a golden bubble drops a Mystery Egg
MYSTERY_FROM_VISITOR = 0.25    # chance a visitor leaves one
GOLDEN_EGG_SHINY = 5           # babies from Golden Eggs are this many times likelier to be shiny

# ---------------------------------------------------------------- tank themes
# water = (top, bottom) colour, sand = (top, bottom), rock = far rocks, plants = palette
THEMES = [
    dict(id="classic", name="Classic Blue", cost=0, bonus=0,
         water=((70, 160, 195), (22, 72, 110)), sand=((222, 196, 140), (176, 146, 96)), rock=(30, 78, 104),
         plants=[(46, 120, 60), (60, 140, 70), (34, 100, 64), (80, 150, 60), (110, 70, 60)],
         desc="The good old blue tank."),
    dict(id="river", name="River Stones", cost=5e4, bonus=5,
         water=((110, 175, 160), (36, 86, 80)), sand=((160, 152, 140), (104, 96, 88)), rock=(48, 88, 80),
         plants=[(70, 130, 60), (90, 150, 70), (50, 110, 70), (120, 140, 60)],
         desc="Cool river water over smooth grey pebbles."),
    dict(id="blackwater", name="Amazon Blackwater", cost=5e6, bonus=5,
         water=((156, 122, 70), (58, 38, 24)), sand=((196, 164, 112), (132, 102, 70)), rock=(72, 50, 34),
         plants=[(90, 120, 50), (110, 90, 50), (70, 100, 50), (130, 110, 60)],
         desc="Tea-coloured water, just like where wild catfish live."),
    dict(id="reef", name="Coral Reef", cost=5e8, bonus=5,
         water=((70, 205, 220), (20, 110, 160)), sand=((250, 218, 206), (222, 172, 160)), rock=(30, 124, 150),
         plants=[(230, 110, 150), (250, 150, 90), (160, 110, 220), (80, 190, 150)],
         desc="Bright tropical water and pink sand."),
    dict(id="spring", name="Crystal Spring", cost=5e10, bonus=5,
         water=((160, 230, 248), (60, 162, 212)), sand=((246, 246, 240), (206, 212, 218)), rock=(96, 166, 196),
         plants=[(80, 200, 90), (110, 220, 110), (60, 170, 100), (140, 220, 90)],
         desc="The clearest water there is. You can see every pebble."),
    # seasonal: costs cost_secs of your income (at least cost); only for sale in its season, yours forever
    dict(id="haunted", name="Haunted Lagoon", cost=5000, cost_secs=600, bonus=10, season="halloween",
         water=((88, 52, 120), (20, 10, 40)), sand=((96, 78, 70), (52, 42, 44)), rock=(46, 30, 66),
         plants=[(110, 60, 140), (230, 120, 30), (40, 70, 50), (150, 40, 60)],
         desc="Gravestones, jack-o'-lanterns and skull bubbles. Pop-bubbles become skulls worth 2x!"),
]
THEMES_BY_ID = {t["id"]: t for t in THEMES}

# ---------------------------------------------------------------- visitors
# wander through the tank now and then; click one for a gift of `secs` seconds of income
VISITORS = [
    dict(id="crab", name="Hermit Crab", secs=150, where="sand", speed=5, weight=4),
    dict(id="shrimp", name="Cherry Shrimp", secs=90, where="sand", speed=9, weight=4),
    dict(id="turtle", name="Musk Turtle", secs=300, where="mid", speed=6, weight=2),
    dict(id="axolotl", name="Axolotl", secs=600, where="mid", speed=4, weight=1),
]
VISITORS_BY_ID = {v["id"]: v for v in VISITORS}
VISIT_EVERY = (240, 480)
HAUNTED_POP_MULT = 2         # pop-bubbles are skulls worth this much in the Haunted Lagoon

# ---------------------------------------------------------------- Fin Scratches ability (id 'rub')
RUB_BASE = 2                 # seconds of scratching = RUB_BASE + level  (Lv 1 = 3s ... Lv 13 = 15s)
RUB_COOLDOWN = 60            # seconds before you can rub again
RUB_EVERY = 0.07             # fastest rub payout (about 14 a second)      # seconds between visitors

# ---------------------------------------------------------------- shiny fish
SHINY_CHANCE = 0.04          # +0.5% per Lucky Moss level; shinies earn 2x

# ---------------------------------------------------------------- prestige
SPAWN_MIN = 1e17          # lifetime-this-run earnings needed to spawn
PEARL_BONUS = 0.10        # Golden Gills: +10% per level

# ---------------------------------------------------------------- pearl tree
# Spend pearls from Spawning Season here. Level n of a node costs cost + grow * n pearls.
# req = node that needs at least Lv 1 first. col/row = where it sits in the tree.
PEARL_TREE = [
    dict(id="gills", name="Golden Gills", max=10, cost=1, grow=1, req=None, col=0, row=0,
         desc="+10% scales per level"),
    dict(id="playful", name="Playful Fish", max=5, cost=2, grow=1, req="gills", col=0, row=1,
         desc="Toys pay +25% per level"),
    dict(id="friends", name="Friendly Visitors", max=5, cost=2, grow=1, req="playful", col=0, row=2,
         desc="More visitors, and +50% visitor gifts"),
    dict(id="hatch", name="Quick Hatch", max=5, cost=1, grow=1, req=None, col=1, row=0,
         desc="Eggs hatch 10% faster per level"),
    dict(id="fertile", name="Fertile Eggs", max=5, cost=2, grow=1, req="hatch", col=1, row=1,
         desc="More baby catfish, fewer empty eggs"),
    dict(id="brood", name="Big Broods", max=2, cost=4, grow=4, req="fertile", col=1, row=2,
         desc="+1 nest slot per level"),
    dict(id="headstart", name="Head Start", max=5, cost=1, grow=1, req=None, col=2, row=0,
         desc="New seasons start with a bigger tank and scales"),
    dict(id="keeptoys", name="Toy Box", max=1, cost=5, grow=0, req="headstart", col=2, row=1,
         desc="Keep all your toys when you spawn"),
    dict(id="seasoned", name="Seasoned Keeper", max=5, cost=3, grow=2, req="keeptoys", col=2, row=2,
         desc="Seasons start with Filter +3/level"),
    dict(id="shiny", name="Shiny Scales", max=5, cost=2, grow=1, req=None, col=3, row=0,
         desc="+1% shiny catfish chance per level"),
    dict(id="lucky", name="Lucky Bubbles", max=5, cost=1, grow=1, req="shiny", col=3, row=1,
         desc="+1% golden bubbles, +25% bubble value"),
    dict(id="deepjar", name="Bottomless Jar", max=5, cost=2, grow=1, req="lucky", col=3, row=2,
         desc="Jar holds +20 min, fills 10% faster"),
]
PEARL_TREE_BY_ID = {n["id"]: n for n in PEARL_TREE}



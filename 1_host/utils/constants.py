"""constants"""

# shitty uniques
unidentified_keywords = ["Unidentified"]


INVENTORY_SLOT_CELL_SIZE = 38  # only for 1024x768

# 1024x768
CURRENCY_TAB_ITEMS_POSITIONS = {
  "divine": {"X": 433, "Y": 233},
  "fusing": {"X": 122, "Y": 283},
  "jewellers": {"X": 81, "Y": 281},
  "chaos": {"X": 391, "Y": 191},
  "vaal": {"X": 431, "Y": 361},
  "additional_slot_0_0": {"X": 115, "Y": 430},
  "additional_slot_0_1": {"X": 155, "Y": 430},
  "additional_slot_0_2": {"X": 195, "Y": 430},
  "additional_slot_0_3": {"X": 235, "Y": 430},
  "additional_slot_0_4": {"X": 275, "Y": 430},
  "additional_slot_0_5": {"X": 315, "Y": 430},
  "additional_slot_0_6": {"X": 355, "Y": 430},
  "additional_slot_1_0": {"X": 115, "Y": 475},
  "additional_slot_1_1": {"X": 155, "Y": 475},
  "additional_slot_1_2": {"X": 195, "Y": 475},
  "additional_slot_1_3": {"X": 235, "Y": 475},
  "additional_slot_1_4": {"X": 275, "Y": 475},
  "additional_slot_1_5": {"X": 315, "Y": 475},
  "additional_slot_1_6": {"X": 355, "Y": 475},
}


MAP_DEVICE_SLOTS = {  # [ [x,y], [x,y]]
  "5slot": [[228, 456], [318, 456], [228, 556], [318, 556], [275, 500]],
  "4slot": [[255, 455], [255, 495], [295, 455], [295, 495]],
  # 0 2
  # 1 3
}


SKILL_KEYS = [
  "left",
  "middle",
  "right",
  "DIK_Q",
  "DIK_W",
  "DIK_E",
  "DIK_R",
  "DIK_T",
  "CTRL+DIK_Q",
  "CTRL+DIK_W",
  "CTRL+DIK_E",
  "CTRL+DIK_R",
  "CTRL+DIK_T",
]

SKILL_KEYS_WASD = [
  "left",
  "middle",
  "right",
  "DIK_Q",
  "DIK_E",
  "DIK_R",
  "DIK_T",
  "DIK_F",
  "CTRL+DIK_Q",
  "CTRL+DIK_E",
  "CTRL+DIK_R",
  "CTRL+DIK_T",
  "CTRL+DIK_F",
]

FLASK_NAME_TO_BUFF = {
  # https://github.com/TehCheat/PoEHelper/blob/master/Plugins/Compiled/BasicFlaskRoutine/config/languages/Russian/FlaskBuffDetails.json
  # poe 2
  "Lesser Life Flask": "flask_effect_life",
  "Medium Life Flask": "flask_effect_life",
  "Greater Life Flask": "flask_effect_life",
  "Grand Life Flask": "flask_effect_life",
  "Giant Life Flask": "flask_effect_life",
  "Colossal Life Flask": "flask_effect_life",
  "Gargantuan Life Flask": "flask_effect_life",
  "Transcendent Life Flask": "flask_effect_life",
  "Ultimate Life Flask": "flask_effect_life",
  "Lesser Mana Flask": "flask_effect_mana",
  "Medium Mana Flask": "flask_effect_mana",
  "Greater Mana Flask": "flask_effect_mana",
  "Grand Mana Flask": "flask_effect_mana",
  "Giant Mana Flask": "flask_effect_mana",
  "Colossal Mana Flask": "flask_effect_mana",
  "Gargantuan Mana Flask": "flask_effect_mana",
  "Transcendent Mana Flask": "flask_effect_mana",
  "Ultimate Mana Flask": "flask_effect_mana",
}

SHITTY_UNIQUES_ARTS = set([])

DANGER_ZONE_KEYS = [
  "LightningClone",
  "Metadata/Monsters/LeagueArchnemesis/LivingCrystal",  # friendly? enemy?
  "Metadata/Monsters/VolatileCore/VolatileCoreArchnemesis",  #
  "/LeagueArchnemesis/ToxicVolatile",
]


WAYPOINTS = [
  "1_1_town",
  "1_1_2",
  "1_1_4_1",
  "1_1_5",
  "1_1_6",
  "1_1_7_1",
  "1_1_8",
  "1_1_9",
  "1_1_11_1",
  "Unknown",
  "Unknown",
  "1_2_3",
  "1_2_5_1",
  "1_2_6_1",
  "1_2_4",
  "1_2_7",
  "1_2_8",
  "1_2_9",
  "1_2_12",
  "1_2_14_2",
  "Unknown",
  "Unknown",
  "1_3_3_1",
  "1_3_5",
  "1_3_7",
  "1_3_8_1",
  "1_3_8_2",
  "1_3_9",
  "1_3_10_1",
  "1_3_13",
  "1_3_14_1",
  "1_3_15",
  "Unknown",
  "1_3_18_1",
  "Unknown",
  "Unknown",
  "1_4_3_3",
  "1_4_4_3",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "1_5_3",
  "1_5_3b",
  "1_5_4",
  "1_5_5",
  "1_5_7",
  "Unknown",
  "Unknown",
  "2_6_2",
  "2_6_6",
  "2_6_7_1",
  "Unknown",
  "2_6_9",
  "2_6_10",
  "2_6_12",
  "2_6_14",
  "2_6_15",
  "Unknown",
  "2_7_2",
  "2_7_4",
  "2_7_5_1",
  "2_7_6",
  "2_7_7",
  "Unknown",
  "2_7_10",
  "2_7_11",
  "Unknown",
  "Unknown",
  "Unknown",
  "2_8_5",
  "2_8_6",
  "2_8_7_1_",
  "2_8_9",
  "2_8_10",
  "Unknown",
  "2_8_12_1",
  "Unknown",
  "Unknown",
  "2_9_3",
  "2_9_5",
  "Unknown",
  "Unknown",
  "Unknown",
  "2_10_2",
  "2_10_4",
  "2_10_7",
  "Unknown",
  "Unknown",
  "Labyrinth_Airlock",  # 89
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
  "Unknown",
]

AURAS_SKILLS_TO_BUFFS = {
  "herald_of_ice": "herald_of_ice",
  "herald_of_thunder": "herald_of_thunder",
  "herald_of_light": "herald_of_light",
  "herald_of_ash": "herald_of_ash",
  "herald_of_agony": "herald_of_agony",
  "haste": "player_aura_speed",
  "anger": "player_aura_fire_damage",
  "spell_damage_aura": "player_aura_spell_damage",
  "damage_over_time_aura": "player_aura_damage_over_time",
  "wrath": "player_aura_lightning_damage",
  "hatred": "player_aura_cold_damage",
  "physical_damage_aura": "player_physical_damage_aura",
  "aura_accuracy_and_crits": "player_aura_accuracy_and_crits",
  "clarity": "player_aura_mana_regen",
  "vitality": "player_aura_life_regen",
  "purity": "player_aura_resists",
  "grace": "player_aura_evasion",
  "determination": "player_aura_armour",
  "discipline": "player_aura_energy_shield",
  "new_arctic_armour": "new_arctic_armour",
  "skitterbots": "skitterbots_buff",
  "banner_armour_evasion": "armour_evasion_banner_buff_aura",
  "banner_war": "bloodstained_banner_buff_aura",
  "call_to_arms": "call_to_arms",
  "automation": "automation",
}

OILS_BY_TIERS = [
  "Distilled Ire",
  "Distilled Guilt",
  "Distilled Greed",
  "Distilled Paranoia",
  "Distilled Envy",
  "Distilled Disgust",
  "Distilled Despair",
  "Distilled Fear",
  "Distilled Suffering",
  "Distilled Isolation",
]


ULTIMATUM_MODS_SAFE_KEYS = [
  # safe
  "Limited Arena",
  "Raging Dead I",
  "Raging Dead II",
  "Stormcaller Runes I",
  "Stormcaller Runes II",
  "Razor Dance I",
  "Razor Dance II",
  "Precise Monsters",
  "Hindering Flasks",
  "Unstoppable Monsters",
  "Overwhelming Monsters",
  "Random Projectiles",
  "Buffs Expire Faster",
  "Escalating Monster Speed",
  "Stormcaller Runes III",
  "Raging Dead III",
  "Stormcaller Runes IV",
  "Raging Dead IV",
  "Blistering Cold I",
  "Blistering Cold II",
  "Blistering Cold III",
  "Blistering Cold IV",
  "Razor Dance III",
  "Choking Miasma",
  "Resistant Monsters",
  "Unlucky Criticals",
  "Razor Dance IV",
  # chaos dot
  # ele dot
  "Totem of Costly Potency",
  # phys dot
  "Totem of Costly Might",
  # bloody altar
  # totems
  # mob res
  "Dexterous Monsters",
  "Ailment and Curse Reflection",
  "Deadly Monsters",
  "Treacherous Auras",
  # extra mob damage
  "Prismatic Monsters",
  # reduced cd recovery
  "Less Cooldown Recovery",
]

ULTIMATUM_MODS_RUIN_KEYS = [
  "Lightning Damage from Mana Costs",
  "Drought",
  "Ruin",
  "Reduced Recovery",
]

DOOR_KEYWORDS = [
  "Metadata/MiscellaneousObjects/Door",
  "Heist/Objects/Level/Door_Basic",
  "/Lights/ScepterDoorLight",
  "/Lights/IncaDoorLight",
  "Level/Door_NPC",
  "Metadata/Terrain/Mountain/Belly/Objects/BellyArseDoor",
]


ULTIMATUM_ALTAR_PATH = "Metadata/Terrain/Leagues/Ultimatum/Objects/UltimatumChallengeInteractable"
HIDEOUT_ALVA_METADATA_KEY = "Metadata/NPC/League/Incursion/TreasureHunterHideout"
INCURSION_CLOSED_DOOR_PATH_KEY = "Metadata/Terrain/Leagues/Incursion/Objects/ClosedDoorPast"
INCURSION_EXIT_PORTAL_PATH_KEY = "Metadata/Terrain/Leagues/Incursion/Objects/IncursionPortal2"
SMALL_RGB_ITEM_KEYS = [
  "Art/2DItems/Weapons/OneHandWeapons/Daggers/Dagger",
  "Art/2DItems/Weapons/OneHandWeapons/Wands/Wand",
  "Art/2DItems/Weapons/OneHandWeapons/Claws/Claw",
  "Art/2DItems/Armours/Helmets/Helmet",
  "Art/2DItems/Armours/Shields/ShieldInt",
  "Art/2DItems/Armours/Boots/Boots",
]

ESSENCES_KEYWORD = "Metadata/MiscellaneousObjects/Monolith"

GOLD_COIN_ART = "Art/2DItems/Currency/Ruthless/CoinPileTier2.dds"

T17_MAP_NAMES = ["Fortress Map", "Ziggurat Map", "Sanctuary Map", "Citadel Map", "Abomination Map"]


class MAPS:
  T17_MAP_NAMES = T17_MAP_NAMES


class FLASK_TYPES:
  UTILITY = "utility"
  MANA = "mana"
  LIFE = "life"


class FLASKS:
  FLASK_TYPES = FLASK_TYPES


class SKILLS_INTERNAL_NAMES:
  ABSOLUTION = "absolution"

  BLOOD_RAGE = "blood_rage"

  FLAME_DASH = "flame_dash"
  FLICKER_STRIKE = "flicker_strike"
  FROST_BLADES = "frost_blades"
  FROSTBLINK = "frostblink"

  HOLY_FLAME_TOTEM = "holy_flame_totem"

  LIGHTNING_STRIKE = "lightning_strike"

  MOLTEN_STIKE = "molten_strike"

  PURIFYING_FLAME = "purifying_flame"

  RAISE_ZOMBIE = "raise_zombie"

  SHIELD_CHARGE = "shield_charge"
  SMITE = "smite"
  SPLITTING_STEEL = "splitting_steel"
  SUMMON_RAGING_SPIRIT = "summon_raging_spirit"
  SUMMON_SKELETONS = "summon_skeletons"

  VENOM_GYRE = "venom_gyre"
  VENOM_GYRE_VAAL = "vaal_venom_gyre"

  WHIRLING_BLADES = "whirling_blades"


class SKILLS:
  INTERNAL_NAMES_KEYS = SKILLS_INTERNAL_NAMES


class CONSTANTS:
  FLASKS = FLASKS
  MAPS = MAPS
  SKILLS = SKILLS

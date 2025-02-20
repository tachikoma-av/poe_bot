from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot


class Muling:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.rules = ["t17", "beasts", "invintations"]
    self.ignore_specific = ["wild hellion alpha", "black morrigan"]

  def getPossibleToMuleList(self):
    # check it on key server or
    pass


""" constants """
# shitty uniques
unidentified_keywords = ["Unidentified"]
# if item matches any of this, itll remove it
shitty_uniques_keywords = [
  # ["", ""],
  ["Carnage Heart", "Onyx Amulet"],
  ["Sidhebreath", "Paua Amulet"],
  ["Warped Timepiece", "Turquoise Amulet"],
  ["Sibyl's Lament", "Coral Ring"],
  ["The Anvil", "Amber Amulet"],
  ["The Consuming Dark", "Fiend Dagger"],
  ["Taproot", "Ambusher"],
  ["Vis Mortis", "Necromancer Silks"],
  ["Soul Mantle", "Spidersilk Robe"],
  ["Wreath of Phrecia", "Iron Circlet"],
  ["Blunderbore", "Astral Plate"],
  ["Skirmish", "Two-Point Arrow Quiver"],
  ["Axiom Perpetuum", "Bronze Sceptre"],
  ["Voices", "Large Cluster Jewel", "Adds 7 Small Passive Skills which grant nothing"],
  ["Voices", "Large Cluster Jewel", "Adds 5 Small Passive Skills which grant nothing"],
  ["Split Personality", "+40 to Evasion Rating"],
  ["Split Personality", "+5 to maximum Mana"],
  ["Split Personality", "+40 to Accuracy Rating"],
  ["Split Personality", "+40 to Armour"],
  ["Wurm's Molt", "Leather Belt"],
  ["Belt of the Deceiver", "Heavy Belt"],
  ["Leather Belt", "Immortal Flesh"],
  ["Gluttony", "Leather Belt"],
  ["Death's Oath", "Astral Plate"],
  ["Perfidy", "Glorious Plate"],
  ["Chin Sol", "Assassin Bow"],
  ["Snakebite", "Assassin's Mitts"],
  ["The Ivory Tower", "The Ivory Tower"],
  ["Lioneye's Vision", "Crusader Plate"],
  ["Siegebreaker", "Heavy Belt"],
  ["Umbilicus Immortalis", "Leather Belt"],
  ["Victario's Acuity", "Turquoise Amulet"],
]


shitty_uniques_metadatas = [
  # qarmours
  "Metadata/Items/Armours/BodyArmours/BodyStr14",
  "Metadata/Items/Armours/BodyArmours/BodyDexInt16",
  "Metadata/Items/Armours/BodyArmours/BodyInt8",
  "Metadata/Items/Armours/BodyArmours/BodyInt11",
  "Metadata/Items/Armours/BodyArmours/BodyInt15",  # shav wrappings
  # weapons
  "Metadata/Items/Weapons/OneHandWeapons/OneHandMaces/OneHandMace18",
  "Metadata/Items/Weapons/TwoHandWeapons/Bows/Bow19",  # chin sol
  "Metadata/Items/Weapons/OneHandWeapons/OneHandMaces/Sceptre3",  # Axiom Perpetuum
  "Metadata/Items/Weapons/OneHandWeapons/Daggers/Dagger18",  # Taproot
  "Metadata/Items/Weapons/OneHandWeapons/OneHandThrustingSwords/Rapier21",  # Cospri's Malice
  "Metadata/Items/Rings/Ring2",
  "Metadata/Items/Amulets/Amulet3",  # The Anvil
  "Metadata/Items/Amulets/Amulet8",
  "Metadata/Items/Belts/Belt3",
  "Metadata/Items/Belts/Belt4",
  "Metadata/Items/Armours/Gloves/GlovesStr9",
  "Metadata/Items/Armours/BodyArmours/BodyInt14",
  "Metadata/Items/Armours/BodyArmours/BodyInt8",
  "Metadata/Items/Weapons/OneHandWeapons/Claws/Claw20",
  "Metadata/Items/Rings/Ring4",
  "Metadata/Items/Rings/Ring15",
  "Metadata/Items/Armours/Boots/BootsDex8",
  "Metadata/Items/Armours/Boots/BootsDex8",
  "Metadata/Items/Rings/Ring15",
  "Metadata/Items/Armours/Boots/BootsDex8",
  "Metadata/Items/Weapons/OneHandWeapons/Daggers/Dagger15",
  "Metadata/Items/Weapons/OneHandWeapons/Wands/Wand3",
  "Metadata/Items/Weapons/OneHandWeapons/Daggers/Dagger21",
  "Metadata/Items/Flasks/FlaskUtility12",
  "Metadata/Items/Weapons/OneHandWeapons/Daggers/Dagger15",
  "Metadata/Items/Amulets/Amulet7",
  "Metadata/Items/Amulets/Amulet7",
  "Metadata/Items/Rings/Ring4",
  "Metadata/Items/Rings/Ring9",
  "Metadata/Items/Rings/Ring9",
  "Metadata/Items/Rings/Ring9",
  "Metadata/Items/Armours/Shields/ShieldStr14",
  "Metadata/Items/Amulet/AmuletAtlas1",
  "Metadata/Items/Armours/BodyArmours/BodyDexInt11",
  "Metadata/Items/Armours/Helmets/HelmetInt2",
  "Metadata/Items/Armours/Shields/ShieldStrInt10",
  "Metadata/Items/Armours/Gloves/GlovesStrDex6",
  "Metadata/Items/Armours/BodyArmours/BodyStr17",
  "Metadata/Items/Weapons/OneHandWeapons/Wands/Wand6",
  "Metadata/Items/Weapons/OneHandWeapons/Wands/Wand6",
  "Metadata/Items/Weapons/TwoHandWeapons/Staves/Staff12Metadata/Items/Armours/BodyArmours/BodyStrInt16",
  "Metadata/Items/Armours/Gloves/GlovesDexInt8",
  "Metadata/Items/Rings/Ring6",
  "Metadata/Items/Rings/Ring6",
]

# TO GET LIST OF ITEMS IN INVENTORY AND PARSE THEIR RENDER ART
# items_in_inventory = []
# for item in poe_bot.getOpenedInventoryInfo()['items']:
#   items_in_inventory.append(item['RenderArt'])

# new_str = ''
# for item in items_in_inventory:
#   new_str += "'"
#   new_str += item
#   new_str += "',"
# print(new_str)

KEYWORDSTOSEARCH = ["Rusted", "Polished", "Screaming", "Shrieking", "Catalyst", "Oil"]
IGNOREKEYWORDSTOSEARCH = ["Golden", "Prismatic", "Unstable"]


# zone where we will drop the loot from inventory to the ground
DROP_ITEMS_ZONE = [488, 545, 413, 615]  # x1, x2, y1, y2

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

MAP_DEVICE_ACTIVATE_BUTTON = {
  "5slot": (272, 633),
  "4slot": (280, 590),
}

FRIENDLY_ENTITIES_PATH_KEYWORDS = [
  "/NPCAllies/",  # heist npc helpers
  "Metadata/Monsters/RockGolem/RockGolemSummoned",  # stone golem
  "Metadata/Monsters/Mirage/RangerMirage",  # mirage archer
  "Metadata/Monsters/Totems/ShotgunTotem",  # ballista totem,
  "Metadata/Monsters/BoneGolem/BoneGolem@72",  # carrion golem
  "Metadata/Monsters/SummonedSkull/SummonedSkull@72",  # srs minion
  "Metadata/Monsters/Masters/Einhar",
]

DELIRIUM_TRASH_ON_MAPS = [
  "Metadata/Monsters/LeagueAffliction/DoodadDaemons/DoodadDaemonEyes",  # some delirium mob on map
  "Metadata/Monsters/LeagueAffliction/DoodadDaemons/DoodadDaemonPimple",
  "Metadata/Monsters/LeagueAffliction/DoodadDaemons/DoodadDaemonSpikes",  # some delirium mob on map
]

UNKNOWN_ENTITIES = [
  "Metadata/Monsters/LeagueAffliction/DoodadDaemons/DoodadDaemonEyes",  # some delirium mob on map
  "Metadata/Monsters/LeagueAffliction/DoodadDaemons/DoodadDaemonPimple",
  "Metadata/Monsters/LeagueAffliction/DoodadDaemons/DoodadDaemonSpikes",  # some delirium mob on map
]

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

FLASK_NAME_TO_BUFF = {
  # https://github.com/TehCheat/PoEHelper/blob/master/Plugins/Compiled/BasicFlaskRoutine/config/languages/Russian/FlaskBuffDetails.json
  "Small Life Flask": "flask_effect_life",
  "Medium Life Flask": "flask_effect_life",
  "Large Life Flask": "flask_effect_life",
  "Greater Life Flask": "flask_effect_life",
  "Grand Life Flask": "flask_effect_life",
  "Giant Life Flask": "flask_effect_life",
  "Colossal Life Flask": "flask_effect_life",
  "Sacred Life Flask": "flask_effect_life",
  "Hallowed Life Flask": "flask_effect_life",
  "Sanctified Life Flask": "flask_effect_life",
  "Divine Life Flask": "flask_effect_life",
  "Eternal Life Flask": "flask_effect_life",
  "Small Mana Flask": "flask_effect_mana",
  "Medium Mana Flask": "flask_effect_mana",
  "Large Mana Flask": "flask_effect_mana",
  "Greater Mana Flask": "flask_effect_mana",
  "Grand Mana Flask": "flask_effect_mana",
  "Giant Mana Flask": "flask_effect_mana",
  "Colossal Mana Flask": "flask_effect_mana",
  "Sacred Mana Flask": "flask_effect_mana",
  "Hallowed Mana Flask": "flask_effect_mana",
  "Sanctified Mana Flask": "flask_effect_mana",
  "Divine Mana Flask": "flask_effect_mana",
  "Eternal Mana Flask": "flask_effect_mana",
  "Small Hybrid Flask": "flask_effect_life",
  "Medium Hybrid Flask": "flask_effect_life",
  "Large Hybrid Flask": "flask_effect_life",
  "Colossal Hybrid Flask": "flask_effect_life",
  "Sacred Hybrid Flask": "flask_effect_life",
  "Hallowed Hybrid Flask": "flask_effect_life",
  "Diamond Flask": "flask_utility_critical_strike_chance",
  "Ruby Flask": "flask_utility_resist_fire",
  "Sapphire Flask": "flask_utility_resist_cold",
  "Topaz Flask": "flask_utility_resist_lightning",
  "Granite Flask": "flask_utility_ironskin",
  "Quicksilver Flask": "flask_utility_sprint",
  "Amethyst Flask": "flask_utility_resist_chaos",
  "Quartz Flask": "flask_utility_phase",
  "Jade Flask": "flask_utility_evasion",
  "Basalt Flask": "flask_utility_stone",
  "Aquamarine Flask": "flask_utility_aquamarine",
  "Stibnite Flask": "flask_utility_smoke",
  "Sulphur Flask": "flask_utility_consecrate",
  "Silver Flask": "flask_utility_haste",
  "Bismuth Flask": "flask_utility_prismatic",
}

SHITTY_UNIQUES_ARTS = set(
  [
    "Art/2DItems/Belts/PyroshockClasp.dds",
    "Art/2DItems/Belts/Gluttony.dds",
    "Art/2DItems/Belts/BeltOfTheDeciever.dds",
    "Art/2DItems/Belts/ImmortalFlesh.dds",
    "Art/2DItems/Belts/BiscosLeash.dds",
    "Art/2DItems/Belts/PyroshockClasp.dds",
    "Art/2DItems/Belts/UmbilicusImmortalis.ddsArt/2DItems/Belts/Belt6Unique.dds",  # "Wurm's Molt"
    "Art/2DItems/Belts/85482.dds",  # Siegebreaker
    "Art/2DItems/Belts/Belt7Unique.dds",  # "Meginord's Girdle"
    "Art/2DItems/Belts/KaomBelt.dds",
    "Art/2DItems/Belts/MotherDyadus.dds",
    "Art/2DItems/Belts/MothersEmbrace.dds",
    "Art/2DItems/Belts/LeashOfOblation.dds",
    "Art/2DItems/Belts/PyroshockClasp.dds",
  ]
)

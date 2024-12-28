import time
import random
from .base_strategy import Strategy

class CleanInventoryStrategy(Strategy):
    def __init__(self, prefer_high_tier):
        self.prefer_high_tier = prefer_high_tier
        
    def __call__(self, poe_bot) -> None:
        poe_bot.ui.inventory.update()
        empty_slots = poe_bot.ui.inventory.getEmptySlots()
        if len(empty_slots) < 40:
            poe_bot.ui.stash.open()
            items_to_keep = []
            poe_bot.ui.inventory.update()
            waystones_to_keep = list(filter(lambda i: i.map_tier, poe_bot.ui.inventory.items))
            waystones_to_keep.sort(key=lambda i: i.map_tier, reverse=self.prefer_high_tier)
            items_to_keep.extend(waystones_to_keep[:4])
            alchemy_orbs = list(filter(lambda i: i.name == "Orb of Alchemy", poe_bot.ui.inventory.items))
            items_to_keep.extend(alchemy_orbs[:1])
            items_can_stash = list(filter(lambda i: i not in items_to_keep, poe_bot.ui.inventory.items))
            poe_bot.ui.clickMultipleItems(items_can_stash)
            poe_bot.ui.closeAll()
            time.sleep(random.uniform(0.3, 1.4)) 
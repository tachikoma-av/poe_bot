import time
import random
from .base_strategy import Strategy
from utils.gamehelper import Poe2Bot
from config import Config
class PlaceMapStrategyAndActivate(Strategy):
    # dont activate is for debugging only
    def __init__(self, config: Config):
        self.config = config
        
    def __call__(self, poe_bot: Poe2Bot) -> None:
        poe_bot.ui.inventory.update()
        maps_in_inventory = list(filter(lambda i: i.map_tier, poe_bot.ui.inventory.items))
        # select only maps which tier is not higher then config.max_map_lvl
        maps_in_inventory = list(filter(lambda i: i.map_tier <= self.config.max_map_lvl, maps_in_inventory))

        maps_in_inventory.sort(key=lambda i: i.map_tier, reverse=self.config.prefer_high_tier)
        map_to_run = maps_in_inventory[0]
        print(f'placing map {map_to_run.raw}')

        if self.config.alch_map_if_possible:
            for _i in range(1):
                if map_to_run.rarity != "Normal":
                    break
                alchemy_orbs = list(filter(lambda i: i.name == "Orb of Alchemy", poe_bot.ui.inventory.items))
                if len(alchemy_orbs) == 0:
                    break
                alchemy_orb = alchemy_orbs[0]
                alchemy_orb.click(button="right")
                time.sleep(random.uniform(0.4, 1.2))
                map_to_run.click()
                time.sleep(random.uniform(0.8, 1.2))

        map_to_run.click(hold_ctrl=True)
        poe_bot.ui.map_device.update()
        poe_bot.ui.map_device.checkIfActivateButtonIsActive()

        poe_bot.ui.map_device.activate() 

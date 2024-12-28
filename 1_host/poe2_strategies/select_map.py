import time
import random
from .base_strategy import Strategy, HideoutStrategyError

class SelectSuitableMapAndOpenDropdownStrategy(Strategy):
    def __init__(self, map_selection_strategy):
        self.map_selection_strategy = map_selection_strategy
        
    def __call__(self, poe_bot) -> None:
        poe_bot.ui.map_device.update()
        
        map_obj = self.map_selection_strategy.select_map(poe_bot.ui.map_device)
        print(f'Selected map: {map_obj.raw}')
        poe_bot.ui.map_device.moveScreenTo(map_obj)
        time.sleep(random.uniform(0.15, 0.35))
        
        for i in range(3):
            updated_map_obj = next(
                (m for m in poe_bot.ui.map_device.avaliable_maps if m.id == map_obj.id)
            )
            time.sleep(random.uniform(0.15, 0.35))
            updated_map_obj.hover()
            time.sleep(random.uniform(0.15, 0.35))
            updated_map_obj.click(hover=False)
            time.sleep(random.uniform(0.15, 0.35))
            poe_bot.ui.map_device.update()

            if poe_bot.ui.map_device.place_map_window_opened:
                break
                
        if not poe_bot.ui.map_device.place_map_window_opened:
            raise HideoutStrategyError("can't open dropdown for map device") 
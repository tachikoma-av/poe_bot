
from .base_strategy import Strategy
from .open_map_device import OpenMapDeviceStrategy
from .select_map import SelectSuitableMapAndOpenDropdownStrategy
from .place_map import PlaceMapStrategyAndActivate


class OpenNewMapStrategy(Strategy):
    def __init__(self, config, map_selection_strategy):
        self.config = config
        self.map_selection_strategy = map_selection_strategy
        
    def __call__(self, poe_bot) -> None:
        # First check if map device is open
        poe_bot.ui.map_device.update()
        
        if not poe_bot.ui.map_device.is_opened:
            # Need to open map device
            OpenMapDeviceStrategy()(poe_bot)
            poe_bot.ui.map_device.update()
        
        # Check if map dropdown is already open
        if not poe_bot.ui.map_device.place_map_window_opened:
            # Need to select map and open dropdown
            SelectSuitableMapAndOpenDropdownStrategy(self.map_selection_strategy)(poe_bot)
            poe_bot.ui.map_device.update()
            
        # Place map and activate if not already done
        if not poe_bot.ui.map_device.checkIfActivateButtonIsActive():
            # Need to place map
            PlaceMapStrategyAndActivate(self.config)(poe_bot) 
        else:
            poe_bot.ui.map_device.activate() 

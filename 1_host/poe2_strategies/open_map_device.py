import time
import random
from .base_strategy import Strategy, HideoutStrategyError

class OpenMapDeviceStrategy(Strategy):

    class MapDeviceEntityNotFoundError(HideoutStrategyError):
        pass

    PORTAL_MAP_DEVICE_PATH =  "Metadata/Terrain/Missions/Hideouts/Objects/MapDeviceVariants/ZigguratMapDevice"

    def is_map_device_entity(self, entity):
        return entity.path == self.PORTAL_MAP_DEVICE_PATH
    

    def get_map_device_entity(self, poe_bot):
        entity = next(
            (e for e in poe_bot.game_data.entities.all_entities 
             if self.is_map_device_entity(e)),
            None
        )
        if entity is None:
            raise self.MapDeviceEntityNotFoundError("couldn't target map device, restart or debug")
        return entity
    
    def __call__(self, poe_bot) -> None:
        poe_bot.refreshInstanceData()
        map_device_entity = self.get_map_device_entity(poe_bot)
        map_device_entity.hover()
        poe_bot.refreshInstanceData()
        map_device_entity = self.get_map_device_entity(poe_bot)
        
        if map_device_entity.is_targeted:
            print('targeted')
            map_device_entity.click()
            _i = 0
            while True:
                _i += 1
                if _i == 100:
                    raise HideoutStrategyError('cannot open map device')

                poe_bot.ui.map_device.update()
                if poe_bot.ui.map_device.is_opened:
                    break
                time.sleep(random.uniform(1.3, 1.4))
            time.sleep(random.uniform(1.3, 1.4))
        else:
            raise self.MapDeviceEntityNotFoundError("couldn't target map device, restart or debug") 
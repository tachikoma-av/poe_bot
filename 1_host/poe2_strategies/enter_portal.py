import time
import random

from utils.gamehelper import Poe2Bot
from .base_strategy import Strategy, HideoutStrategyError


class EnterPortalStrategy(Strategy):
    def __call__(self, poe_bot: Poe2Bot ) -> None:
        try:
            poe_bot.helper_functions.getToPortal(check_for_map_device=False)
        except Exception as e:
            if str(e) == 'Portal is too far away':
                print('portal became too far away')
                original_area_name = poe_bot.game_data.area_raw_name
                _i = 0
                while True:
                    _i += 1
                    if _i == 100:
                        raise HideoutStrategyError('could not get to portal')
                    poe_bot.refreshAll()

                    if poe_bot.game_data.area_raw_name != original_area_name:
                        break
            else:
                print(str(e))
                raise HideoutStrategyError('something happened on getToPortal') 
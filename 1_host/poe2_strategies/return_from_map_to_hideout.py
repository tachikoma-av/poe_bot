from typing import TYPE_CHECKING
import random
import time

from poe2_strategies.base_strategy import Strategy

if TYPE_CHECKING:
    from utils.gamehelper import Poe2Bot

class ReturnFromMapToHideoutStrategy(Strategy):
    def __call__(self, poe_bot: 'Poe2Bot') -> None:
        """Execute the strategy to return from map to hideout"""
        self._open_portal(poe_bot)
        poe_bot.helper_functions.waitForPortalNearby()
        poe_bot.helper_functions.getToPortal(check_for_map_device=False, refresh_area=False)

    def _open_portal(self, poe_bot: 'Poe2Bot') -> None:
        """Open a portal at current location"""
        poe_bot.bot_controls.releaseAll()

        time.sleep(random.randint(40,80)/100)
        pos_x, pos_y = random.randint(709,711), random.randint(694,696)
        pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y, safe=False)
        poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
        time.sleep(random.randint(40,80)/100)
        poe_bot.bot_controls.mouse.click()
        time.sleep(random.randint(30,60)/100) 
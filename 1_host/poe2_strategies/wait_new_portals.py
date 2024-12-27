import time
import random

from utils.gamehelper import Poe2Bot
from .base_strategy import Strategy


class WaitNewPortalsStrategy(Strategy):
    def __call__(self, poe_bot: Poe2Bot ) -> None:
        time.sleep(random.uniform(0.8, 1.6))
        poe_bot.helper_functions.waitForNewPortals()
        poe_bot.refreshInstanceData()
        
from poe2_strategies.open_new_map import OpenNewMapStrategy
from poe2_strategies.wait_new_portals import WaitNewPortalsStrategy


class OpenNewMapIfRequiredStrategy(OpenNewMapStrategy):
    def __init__(self, config, map_selection_strategy):
        super().__init__(config, map_selection_strategy)
        
    def __call__(self, poe_bot) -> None:
        print(f'len(poe_bot.helper_functions.getPortals()) {len(poe_bot.helper_functions.getPortals())}')
        if len(poe_bot.helper_functions.getPortals()) == 6:
            # already opened 6 portals, skipping hideout preparations
            print("DEBUG: already opened 6 portals")
            return
        else:
            super().__call__(poe_bot)
            WaitNewPortalsStrategy()(poe_bot)
            

from config import Config
from utils.gamehelper import Poe2Bot


class RunnerBreaker:
    def __init__(self, poe_bot: Poe2Bot, config: Config):
        self.poe_bot = poe_bot
        self.config = config
      

    def runnerBreakFunction(self, *args, **kwargs):
        switch_nearby = next( (e for e in self.poe_bot.game_data.entities.all_entities if e.is_targetable and e.path == "Metadata/Terrain/Maps/Crypt/Objects/CryptSecretDoorSwitch" and e.distance_to_player < 30), None)
        if switch_nearby:
            self.poe_bot.mover.goToEntitysPoint(switch_nearby)
            self.poe_bot.combat_module.clearAreaAroundPoint(switch_nearby.grid_position.toList())
            switch_nearby.clickTillNotTargetable()
            return True

        if self.config.rares_detection_radius != 0:
            rares_nearby = list(filter(lambda e: e.distance_to_player < self.config.rares_detection_radius, self.poe_bot.game_data.entities.attackable_entities_rares))
            for rare_mob in rares_nearby:
                updated_entity = list(filter(lambda e: e.id == rare_mob.id, self.poe_bot.game_data.entities.attackable_entities_rares))
                if len(updated_entity) != 0:
                    updated_entity = updated_entity[0]
                    self.poe_bot.mover.goToEntitysPoint(updated_entity, min_distance=50)
                    self.poe_bot.combat_module.killUsualEntity(updated_entity)
                    return True

        loot_collected = self.poe_bot.loot_picker.collectLoot()
        if loot_collected is True:
            return loot_collected
        return False

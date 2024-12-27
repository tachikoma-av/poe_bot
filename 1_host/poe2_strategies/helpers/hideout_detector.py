
class HideoutDetector:
  # TODO: add more hideout area names
  HIDEOUT_AREA_NAMES = ["HideoutShrine"]
  def __init__(self, poe_bot):
    self.poe_bot = poe_bot

  def is_hideout(self):
    return self.poe_bot.area_raw_name in self.HIDEOUT_AREA_NAMES

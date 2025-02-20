from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
  from .gamehelper import PoeBot
import random
import time


class PosXY:
  x: int
  y: int

  def __init__(self, x: int, y: int) -> None:
    self.x = x
    self.y = y

  def __str__(self) -> str:
    return str(f"x:{self.x} y: {self.y}")

  def toList(self):
    return [self.x, self.y]


class PosXYZ:
  x: int
  y: int

  def __init__(self, x: int, y: int, z: int) -> None:
    self.x = x
    self.y = y
    self.z = z

  def __str__(self) -> str:
    return str(f"x:{self.x} y: {self.y} z: {self.z}")

  def toList(self):
    return [self.x, self.y, self.z]


class Posx1x2y1y2:
  def __init__(self, x1: int, x2: int, y1: int, y2: int) -> None:
    self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2

  def toList(self):
    return [self.x1, self.x2, self.y1, self.y2]

  def getCenter(self):
    return [int((self.x2 + self.x1) / 2), int((self.y1 + self.y2) / 2)]

  def getCorners(self):
    return [[self.x1, self.y1], [self.x2, self.y1], [self.x2, self.y2], [self.x1, self.y2]]


class TotalCurrentReserved:
  total: int
  current: int
  reserved: int

  def getPercentage(self):
    if self.total == 0:
      return 1.0
    return self.current / self.total


class Life:
  health: TotalCurrentReserved
  mana: TotalCurrentReserved
  energy_shield: TotalCurrentReserved

  def __init__(self, raw_json) -> None:
    if raw_json is None:
      raw_json = [0, 0, 0, 0, 0, 0, 0, 0, 0]

    health = TotalCurrentReserved()
    health.total = raw_json[0]
    health.current = raw_json[1]
    health.reserved = raw_json[2]
    self.health = health

    mana = TotalCurrentReserved()
    mana.total = raw_json[3]
    mana.current = raw_json[4]
    mana.reserved = raw_json[5]
    self.mana = mana

    energy_shield = TotalCurrentReserved()
    energy_shield.total = raw_json[6]
    energy_shield.current = raw_json[7]
    self.energy_shield = energy_shield


class PoeBotComponent:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot


class UiElement(PoeBotComponent):
  def __init__(self, poe_bot: PoeBot, screen_zone: Posx1x2y1y2 | None = None, screen_pos: PosXY | None = None) -> None:
    super().__init__(poe_bot)
    if screen_zone is None and screen_pos is None:
      poe_bot.raiseLongSleepException("screen_zone == None and screen_pos == None on init ui element")
    self.screen_zone = screen_zone
    self.screen_pos = screen_pos

  def getScreenPos(self):
    if self.screen_pos:
      pos_x = self.screen_pos.x
      pos_y = self.screen_pos.y
    else:
      pos_x = int((self.screen_zone.x1 + self.screen_zone.x2) / 2)
      pos_y = int((self.screen_zone.y1 + self.screen_zone.y2) / 2)
    return pos_x, pos_y

  def hover(self, mouse_speed_mult=1):
    pos_x, pos_y = self.getScreenPos()
    screen_pos_x, screen_pos_y = self.poe_bot.convertPosXY(pos_x, pos_y, safe=False)
    self.poe_bot.bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, mouse_speed_mult=mouse_speed_mult)

  def click(self, hold_ctrl=False, hold_shift=False, can_click_multiple_times=0, button="left", hover=True, mouse_speed_mult=1):
    bot_controls = self.poe_bot.bot_controls

    if hold_ctrl is True:
      bot_controls.keyboard_pressKey("DIK_LCONTROL")
    if hold_shift is True:
      bot_controls.keyboard_pressKey("DIK_LSHIFT")

    if hover is True:
      self.hover(mouse_speed_mult=mouse_speed_mult)
      time.sleep(random.randint(10, 25) / 100)
    iterations = 1
    for i in range(can_click_multiple_times):
      if random.randint(1, 10) == 1:
        iterations += 1
    for i in range(iterations):
      bot_controls.mouse.press(button=button)
      if random.randint(0, 2) != 0:
        self.hover()
      bot_controls.mouse.release(button=button)

    if hold_ctrl is True or hold_shift is True:
      time.sleep(random.randint(5, 7) / 100)
      if hold_ctrl is True:
        bot_controls.keyboard_releaseKey("DIK_LCONTROL")
      if hold_shift is True:
        bot_controls.keyboard_releaseKey("DIK_LSHIFT")

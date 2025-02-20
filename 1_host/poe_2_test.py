#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import sys
import time
from ast import literal_eval

from utils.gamehelper import Poe2Bot


# In[ ]:





# In[3]:


notebook_dev = False
# readability
poe_bot_class = Poe2Bot
poe_bot: poe_bot_class


# In[ ]:


default_config = {
  "REMOTE_IP": "192.168.47.51",  # z2
  "unique_id": "poe_2_test",
  "force_reset_temp": False,
}


try:
  i = sys.argv[1]
  print(i)
  parsed_config = literal_eval(i)
  print("successfully parsed cli config")
  print(f"parsed_config: {parsed_config}")
except:
  print("cannot parse config from cli, using default\dev one")
  notebook_dev = True
  parsed_config = default_config

config = {}

for key in default_config.keys():
  config[key] = parsed_config.get(key, default_config[key])

print(f"config to run {config}")


# In[ ]:


REMOTE_IP = config["REMOTE_IP"]  # REMOTE_IP
UNIQUE_ID = config["unique_id"]  # unique id
force_reset_temp = config["force_reset_temp"]
print(f"running test using: REMOTE_IP: {REMOTE_IP} unique_id: {UNIQUE_ID}  force_reset_temp: {force_reset_temp}")


# In[ ]:


poe_bot = Poe2Bot(unique_id=UNIQUE_ID, remote_ip=REMOTE_IP)
poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()
# TODO move it to poe_bot.refreshAll() refreshed_data["c_t"] ## "c_t":0 - mouse || "c_t":1 - wasd
poe_bot.mover.setMoveType("wasd")


# In[ ]:





# In[7]:


raise 404


# In[ ]:


from utils.combat import TempestFlurryBuild

poe_bot.combat_module.build = TempestFlurryBuild(poe_bot)
poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine


# In[ ]:


poe_bot.refreshInstanceData()
alva_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Alva"))
poe_bot.mover.goToEntitysPoint(alva_entity, release_mouse_on_end=False)
danning_entity = next((e for e in poe_bot.game_data.entities.all_entities if e.render_name == "Dannig"))
poe_bot.mover.goToEntitysPoint(danning_entity, release_mouse_on_end=True)


# In[ ]:


raise 404


# In[ ]:


poe_bot.ui.auction_house.open()


# In[ ]:


poe_bot.ui.auction_house.update()


# In[ ]:





# In[8]:


from utils.constants import OILS_BY_TIERS

stash = poe_bot.ui.stash
auction_house = poe_bot.ui.auction_house

oil_items = [item for item in poe_bot.ui.stash.getAllItems() if item.name in OILS_BY_TIERS]
stash_tab_indexes_with_oils = list({item.tab_index for item in oil_items})

poe_bot.ui.stash.open()
for i in stash_tab_indexes_with_oils:
  poe_bot.ui.stash.openTabIndex(i)
poe_bot.ui.closeAll()


# In[ ]:


poe_bot.ui.auction_house.open()
auction_house.i_have_button.click()
while auction_house.currency_picker.visible is False:
  time.sleep(0.3)
  auction_house.update()
  print("waiting till auction_house.currency_picker.visible == False")
auction_house.currency_picker.openCategory("Delirium")
time.sleep(1)
auction_house.update()

list_of_oils_we_can_get = list(filter(lambda el: el.text in OILS_BY_TIERS, auction_house.currency_picker.presented_elements))


# In[ ]:





# In[ ]:


# auction_house.i_have_button.click()
auction_house.currency_picker.openCategory("Currency")
auction_house.currency_picker.clickElementWithText("Exalted Orb")
# TODO currencypicker supposed to be not visible


# In[ ]:


def getMarketRatios():
  for i in range(10):
    time.sleep(0.3)
    auction_house.update()
    if auction_house.market_ratios != []:
      break
  return auction_house.market_ratios


ok_decimals = [0.0, 0.1, 0.25, 0.5, 0.75]
multipliers = [1, 10, 4, 2, 4]


def findNearestDecimal(rate, limit):
  frac_part = rate % 1
  num_part = int(rate)
  ok_decimals_inner = list(filter(lambda el: num_part + el < limit, ok_decimals))
  closest = min(ok_decimals_inner, key=lambda x: abs(x - frac_part))
  closest_index = ok_decimals.index(closest)
  return [num_part + closest, closest_index]


min_ex_trade = 40
# for each oil we can sell
for oil_type in list_of_oils_we_can_get:
  # for oil_type in list_of_oils_we_can_get[1:2]:
  # check if orderbook is full, if full -> collect all orderesbreak
  if oil_type.count < 10:
    print(f"skipping {oil_type.name} cos < 10 count")
    continue

  auction_house.i_want_button.click()
  auction_house.currency_picker.openCategory("Delirium")
  auction_house.currency_picker.clickElementWithText(oil_type.text)
  # TODO currencypicker supposed to be not visible
  price_ratios_buy = getMarketRatios()
  auction_house.i_want_button.click(hold_ctrl=True)  # reverse our trading
  price_ratios_sell = getMarketRatios()

  # TODO find average ratio to sell, its supposed to be avg around the market
  # basically we are going to sell for the cheapest price
  print(f"ratios are {price_ratios_buy} {price_ratios_sell}")
  give_oil_rate = price_ratios_buy[0][0]
  take_ex_rate = price_ratios_buy[0][1]
  give_oil_rate, take_ex_rate
  oils_to_give = oil_type.count
  ex_to_take = 0
  if give_oil_rate > 1:
    opt_rate, closest_index = findNearestDecimal(give_oil_rate, price_ratios_sell[0][1])
    bulk_size = opt_rate * multipliers[closest_index]
    bulks_count = int(oil_type.count / bulk_size)
    oils_to_give = int(bulk_size * bulks_count)
    ex_to_take = int(bulks_count * multipliers[closest_index])

  else:
    ex_to_take = int(oil_type.count * take_ex_rate)
  print(f"gonna sell {oil_type.text}, {oils_to_give} for {ex_to_take} ex")
  if ex_to_take < min_ex_trade:
    print(f"skipping  {oil_type.text} cos income less than 40")
    auction_house.i_want_button.click(hold_ctrl=True)  # reverse our trading
    continue
  # set values
  # check if values are correct
  # auction_house.setFieldValue(auction_house.i_have_field, oils_to_give)
  # auction_house.setFieldValue(auction_house.i_want_field, ex_to_take)
  auction_house.setHaveValue(oils_to_give)
  auction_house.setWantValue(ex_to_take)

  # check if we have enough gold, else break
  if auction_house.gold < auction_house.deal_price:
    break
  # place order
  auction_house.i_want_field.click()
  input("test")
  auction_house.place_order_button.click()

  auction_house.i_want_button.click(hold_ctrl=True)  # reverse our trading back


# In[ ]:


raise 404


# In[ ]:


price_ratios_sell[0][1]


# In[ ]:


ok_decimals = [0.0, 0.1, 0.25, 0.50, 0.75]
give_oil_rate = 3.38


# In[ ]:


give_oil_rate


# In[ ]:


ok_decimals = [0.0, 0.1, 0.25, 0.5, 0.75]
multipliers = [1, 10, 4, 2, 4]


def findNearestDecimal(rate, limit):
  frac_part = rate % 1
  num_part = int(rate)
  ok_decimals_inner = list(filter(lambda el: num_part + el < limit, ok_decimals))
  closest = min(ok_decimals_inner, key=lambda x: abs(x - frac_part))
  closest_index = ok_decimals.index(closest)
  return [num_part + closest, closest_index]


findNearestDecimal(3.38, 3.5)
opt_rate, closest_index = findNearestDecimal(give_oil_rate, price_ratios_sell[0][1])
bulk_size = opt_rate * multipliers[closest_index]
bulks_count = int(oil_type.count / bulk_size)
oils_to_give = int(bulk_size * bulks_count)
ex_to_take = int(bulks_count * multipliers[closest_index])


# In[ ]:





# In[ ]:


oils_to_give = int(oils_to_give * multipliers[closest_index])
ex_to_take = int(oil_type.count // multipliers[closest_index])


# In[ ]:


opt_rate


# In[ ]:


485 // multipliers[closest_index]
# 121 * multipliers[closest_index]


# In[ ]:


batches_count = int(285 / multipliers[closest_index])
oils_to_give = batches_count * multipliers[closest_index]
280 / 1.1


# In[ ]:


285 // 1.1


# In[ ]:


259 / 1.1


# In[ ]:


oil_type.count


# In[ ]:


600 // opt_rate


# In[ ]:


184 * opt_rate


# In[ ]:


# List of acceptable decimal values
ok_decimals = [0.0, 0.1, 0.25, 0.5, 0.75]

# Given oil rate
give_oil_rate = 3.38


# Function to find the closest decimal value
def closest_decimal_rate(rate, decimals):
  # Find the fractional part of the given rate
  frac_part = rate % 1
  # Find the closest decimal value
  closest = min(decimals, key=lambda x: abs(x - frac_part))
  return closest


# Calculate the closest decimal value
closest_decimal = closest_decimal_rate(give_oil_rate, ok_decimals)

# Output the closest decimal oil rate
closest_oil_rate = int(give_oil_rate) + closest_decimal
closest_oil_rate


# In[ ]:


oil_type.count


# In[ ]:


time.sleep(0.3)
auction_house.update()


# In[ ]:


price_ratios_buy, price_ratios_sell


# In[ ]:





# In[ ]:


num_is_integer = False
oil_count = oil_type.count
while num_is_integer is False and oil_count > 0:
  oils_can_sell = oil_count / give_oil_rate
  num_is_integer = oils_can_sell.is_integer()
  oil_count -= 1


# In[ ]:


oil_type.count


# In[ ]:





# In[ ]:


num_is_integer = False
oil_count = oil_type.count
while num_is_integer is False and oil_count > 0:
  oils_can_sell = oil_count / give_oil_rate
  print(f"{oil_count} / {give_oil_rate} = {oils_can_sell}")
  num_is_integer = oils_can_sell.is_integer()
  oil_count -= 1


# In[ ]:


oils_can_sell


# In[ ]:


oils_can_sell = 14.5


# In[ ]:


oils_can_sell.is_integer()


# In[ ]:


give_oil_rate


# In[ ]:


take_ex_rate


# In[ ]:


oil_type.count, give_oil_rate


# In[ ]:


(251, 2.85)


# In[ ]:


oil_type.count % 2.85


# In[ ]:





# In[ ]:


88 * 2.85


# In[ ]:


oil_type.count - oil_type.count % give_oil_rate


# In[ ]:


price_ratios_sell


# In[ ]:


price_ratios_buy


# In[ ]:


(3.17 * 2 + 2.9) / 3


# In[ ]:


raise 404


# In[ ]:


poe_bot.refreshInstanceData()
poe_bot.ui.stash.open()
poe_bot.ui.stash.updateStashTemp()


# In[ ]:





# In[ ]:


arr = ["  1 : 3", "85", "  1 : 3.33", "200", "  1 : 3.40", "200", "  1 : 3.50", "26,602", "  1 : 3.55", "2,000", "< 1 : 3.55", "321,151"]
arr[::2]

for index in range(0, len(arr), 2):
  ratio = arr[index]
  if "<" in ratio:
    continue
  amount = int(arr[index + 1].replace(",", ""))
  take = float(ratio.split(":")[0])
  give = float(ratio.split(":")[1])
  print(f"{take} {give} {amount}")


# In[ ]:


class Dummy:
  def a(self):
    print("a")


d = Dummy()
d.a()


def b():
  d.a()
  print("b")


d.a = b

d.a()


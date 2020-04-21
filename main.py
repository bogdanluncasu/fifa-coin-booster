import time
from fifa_items import items

from trader import Trader

trader = Trader("")
while True:
    time.sleep(2)
    trader.buy_and_sell(items["health"])

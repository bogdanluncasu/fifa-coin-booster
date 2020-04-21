import http.client
import json
import random
import time

FIFA_VERSION = "fifa20"
ITEM_ENDPOINT = "/ut/game/%s/item" % FIFA_VERSION
SELL_ENDPOINT = "/ut/game/%s/auctionhouse" % FIFA_VERSION


def get_connection():
    return http.client.HTTPSConnection("utas.external.s3.fut.ea.com")


def get_trade_pile_payload(item_id):
    return "{\"itemData\": [{\"id\": " + str(item_id) + ", \"pile\": \"trade\"}]}"


class Trader:
    def __init__(self, token):
        self.headers = {
            'x-ut-sid': token,
            'content-type': "application/json",
            'Cache-Control': "no-store",
            "Pragma": "no-cache"
        }
        self.invest = 0
        self.expected_profit = 0
        self.counter = 0

    def put_on_transfer_list(self, item_id: int, resource: str = "") -> int:
        """
        Puts an item on trade pile

        :param item_id: The id of the item which will be put on the trade pile
        :param resource: resource endpoint - the trade pile endpoint is different when it comes to consumables
            - e.g. "../resource"
        :return: id of the item put on the trade pile
        """
        payload = get_trade_pile_payload(item_id)
        print("Put on transfer list request payload:", payload)
        conn = get_connection()
        conn.request("PUT", ITEM_ENDPOINT + resource, payload, headers=self.headers)

        res = conn.getresponse()
        data = res.read()
        data = json.loads(data.decode("utf-8"))
        print("Put on transfer list response:", data)

        _id = data["itemData"][0]["id"]
        conn.close()
        return _id

    def sell_item(self, starting_bid, buy_now, item_id):
        """
        Sell an item

        :param starting_bid: the starting bid price for the item
        :param buy_now: the buy now price for the item
        :param item_id: id of the item going to be sold
        :return:
        """
        conn = get_connection()
        sell_payload = "{\"itemData\":{\"id\":" + str(item_id) + "},\"startingBid\":" + str(
            starting_bid) + ",\"duration\":3600,\"buyNowPrice\":" + str(buy_now) + "}"
        print("Sell payload:", sell_payload)
        conn.request("POST", SELL_ENDPOINT, sell_payload, self.headers)
        response = conn.getresponse()
        print("Sell response status code", response.status)
        conn.close()

    def buy_and_sell(self, _item):
        print("request number", self.counter + 1)
        if self.counter > 100:
            print("stop")
            print("Invest: ", self.invest)
            print("Potential profit: ", self.expected_profit)
            self.counter = 0
            return

        conn = get_connection()
        url = "/ut/game/%s/transfermarket?cb=%s" % (
            FIFA_VERSION, str(random.randint(0, 100000))) + "&start=0&num=21&type=" + _item["typ"] + "&maxb=%s" % str(
            _item["max_bid"] + self.counter)

        self.counter += 1

        conn.request("GET", url, headers=self.headers)

        res = conn.getresponse()
        data = res.read()
        conn.close()
        if res.status == 200:
            auctions = json.loads(data.decode("utf-8"))
            for auction in auctions["auctionInfo"]:
                try:
                    trade_id = auction["tradeId"]
                    payload = "{\"bid\":" + str(auction["buyNowPrice"]) + "}"

                    conn = get_connection()
                    conn.request("PUT", "/ut/game/%s/trade/" % FIFA_VERSION + str(trade_id) + "/bid",
                                 payload, self.headers)
                    trade_response = conn.getresponse()
                    data = trade_response.read()
                    if trade_response.status == 200:
                        self.invest += auction["buyNowPrice"]
                        self.expected_profit += _item["end_bn"] - auction["buyNowPrice"]
                        conn.close()
                        time.sleep(0.5)
                        bought = json.loads(data.decode("utf-8"))

                        player_id = bought["auctionInfo"][0]["itemData"]["id"]
                        print("Bought ", str(player_id), " for: " + payload)

                        self.put_on_transfer_list(player_id)
                        time.sleep(0.5)
                        self.sell_item(_item["start_bn"], _item["end_bn"], player_id)
                        time.sleep(0.5)
                    else:
                        print("trade response:", trade_response.status)
                        if trade_response.status != 200:
                            trade_response.close()
                            conn.close()
                            return
                except Exception as e:
                    print(str(e))
        else:
            time.sleep(2)
            print("Something went wrong - Status code", res.status)

from pycoingecko import CoinGeckoAPI
cg = CoinGeckoAPI()
import datetime

# print(cg.get_price(ids='bitcoin', vs_currencies='usd'))
# coin_list = cg.get_coins_list()
# for coin in coin_list:
#     if coin["symbol"] == "eth" or coin["symbol"] == "ada":
#         print(coin)
#         print(cg.get_price(coin["id"], "usd"))
# print(cg.get_price("bitcoin", "usd"))
    
market_data = cg.get_coin_market_chart_by_id("bitcoin", "usd", "1", interval="hourly")
print(market_data["prices"])

for l in market_data["prices"]:
    s = l[0] /1000
    date = datetime.datetime.fromtimestamp(s) # .strftime('%Y-%m-%d %H:%M:%S.%f')
    print(date)
    if date.hour == 0:
        print(date, l[1])
    
print(type(market_data["prices"][-1][1]))
s = market_data["prices"][-1][0] /1000
print(datetime.datetime.fromtimestamp(s))

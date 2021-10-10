from requests.api import head
import boto3
import requests
from math import isclose
from pycoingecko import CoinGeckoAPI
import datetime
import json
cg = CoinGeckoAPI()


dynamoClient = boto3.client("dynamodb")

RETURN_HEADER = { 
    'Access-Control-Allow-Origin' : '*',
    'Access-Control-Allow-Headers':'*',
    'Access-Control-Allow-Credentials' : True,
    'Access-Control-Allow-Methods' : "OPTIONS, POST",
    'Content-Type': 'application/json',
    'X-Requested-With' : '*'
}

def getAttribute(dbItem, attributeName, attributeType):
    """
    INPUT
    dbItem: the databse item returned => {'headers' : {'S': 'some string'}, ...}
    attribtueName: name of the item
    attributeType: one of the dynamoDb datatypes => {'S', 'N'...}
    OUTPUT
    return database attribute 
    """
    return dbItem.get(attributeName, {}).get(attributeType, "")

def getJsonStrAttribute(dbItem, attributeName):
    """
    INPUT
    dbItem: the database item
    attributeName: name of the column in the table
    OUTPUT:
    return dictionary item of the attribute
    """
    json_str = dbItem.get(attributeName, {}).get('S', "{}").replace("\'", "\"")
    return json.loads(json_str)
    

def insertAttributeItem(dbItem, attributeName, attributeVal, attributeType):
    """
    INPUT
    dbItem: the database item
    attributeName: name of attribute in table
    attributeVal: value of attribute to put
    attributeType: type of attribute in {'S', 'N', 'BOOL'}
    OUTPUT
    return updated dbItem
    """
    dbItem[attributeName] = {attributeType : attributeVal}
    return dbItem

def insertJsonAttributeItem(dbItem, attributeName, attributeVal):
    dbItem[attributeName] = {"S" : json.dumps(attributeVal)}
    return dbItem

def lambda_handler(event, context):
    api_key = event.get("queryStringParameters", {}).get("api_key", "")
    userId = event.get("queryStringParameters", {}).get("userId", "")
    print("api_key: {}".format(api_key))
    print("userId: {}".format(userId))
    # db_item = dynamoClient.get_item(
    #     Key={
    #         'api_key' : {
    #             'S' : api_key
    #         }
    #     },
    #     TableName='celsiusAccount'
    # ).get("Item")

    # get wallets now
    headers = {
        'X-Cel-Partner-Token' : 'ff4152bf-ec69-40cd-932b-783767dbb921',
        'X-Cel-Api-Key': api_key
    }
    base_endpoint = "https://wallet-api.celsius.network/wallet/"
    wallets_endpoint = "balance/"
    try:
        wallet_response = requests.get(url=base_endpoint+wallets_endpoint, headers=headers)
        if wallet_response.status_code != 200:
            raise Exception("Could not hit wallet request")
        print("got wallet resposne")
        wallet_response_json = wallet_response.json()
        total_account_value = 0
        assets = []
        total_daily_change = 0
        pct_changes = []
        total_all_time_change = 0
        for coin, coin_amount_total in wallet_response_json.get("balance", {}).items():
            # balance is a dictionary: {"eth" : ".11", "btc" : "0"}

            # [TICKER, Name, Daily Change, Current Value, Quantity, Share Price, Purcahsed Price]
            if float(coin_amount_total) > 0:
                print("Calculating for coin : {}".format(coin))
                ticker = coin
                name = coin
                coin_map = cg.get_coins_list()
                print("got coin list from goin gecko")
                coin_id = None
                for c in coin_map:
                    if c["symbol"] == ticker.lower():
                        name = c["name"]
                        coin_id = c["id"]
                market_data = cg.get_coin_market_chart_by_id(coin_id, "usd", "1", interval="hourly")
                print("got market data from goin gecko")
                price_data = market_data["prices"]
                start_price = 0
                for [mili_time, price] in price_data:
                    s = mili_time /1000
                    date = datetime.datetime.fromtimestamp(s)
                    print("Regular date: {}".format(date))
                    if date.hour == 7:
                        print("Got start price: {}".format(price))
                        print("date: {}".format(date))
                        start_price = price
                float_current_price = price_data[-1][1]
                pct_daily_change = (float_current_price - start_price) / start_price
                pct_daily_change_str = "{:.2f}".format(pct_daily_change* 100)

                value = float_current_price * float(coin_amount_total)
                value_str = "{:.2f}".format(value)
                total_account_value += value
                amount_str = "{:.2f}".format(float(coin_amount_total))
                current_price_str = "{:.2f}".format(float_current_price)
                if start_price == 0:
                    raise Exception("Could not get start price")
                print("current price: {}".format(float_current_price))
                print("start price: {}".format(start_price))
                print("pct daily change: {}".format(pct_daily_change))
                print("amount: {}".format(amount_str))
                # GET ALL TIME
                upper_ticker = coin.upper()
                transaction_url = base_endpoint + upper_ticker + "/transactions?per_page=100"
                transaction_response = requests.get(url=transaction_url, headers=headers)
                if transaction_response.status_code != 200:
                    raise Exception("Could not get transactions")

                transaction_response_json = transaction_response.json()
                txs = transaction_response_json.get("record", [])
                remaining_amount = float(coin_amount_total)
                bought_price = 0
                for tx in txs:

                    if tx.get("nature") != "deposit":
                        continue
                    print("Checking order for buy: {}".format(tx))

                    coin_amount = float(tx.get("amount_precise", "0"))
                    tx_value = float(tx.get("amount_usd", "0"))
                    current_buy_price = tx_value/coin_amount 
                    if isclose(remaining_amount, coin_amount, abs_tol=10**-2) or coin_amount > remaining_amount:
                        coin_amount = remaining_amount
                        pct = coin_amount / float(coin_amount_total)
                        print("pct: {}".format(pct))
                        print("coin_amount: {}".format(coin_amount))
                        bought_price += current_buy_price * pct
                        remaining_amount = 0
                    
                    elif coin_amount <= remaining_amount:
                        pct = coin_amount / float(coin_amount_total)
                        print("pct: {}".format(pct))
                        print("coin_amount: {}".format(coin_amount))
                        bought_price += current_buy_price * pct
                        remaining_amount -= coin_amount
                # DONE WITH ALL TIME
                print("Bought price: {}".format(bought_price))
                pct_all_time_change = 0.00
                bought_price_str = "0"
                if bought_price != 0:
                    bought_price_str = "{:.2f}".format(bought_price)
                    pct_all_time_change = ((float_current_price - bought_price) / bought_price) * 100
                pct_all_time_change_str = "{:.2f}".format(pct_all_time_change)
                assets.append([ticker, name, pct_daily_change_str, value_str, amount_str, current_price_str,\
                                pct_all_time_change_str, bought_price_str])
                pct_changes.append((pct_daily_change, value, pct_all_time_change))

        for i in range(len(pct_changes)):
            pct_daily_change = pct_changes[i][0]
            value = pct_changes[i][1]
            pct_all_time_change = pct_changes[i][2]
            print("daily change: {}, value: {}, account_value: {}, pct_all_time_change: {}".format(pct_daily_change, value, total_account_value, pct_all_time_change))
            total_daily_change += pct_daily_change * (value/total_account_value)
            total_all_time_change += pct_all_time_change * (value/total_account_value)
            print("total all time change: {}".format(total_all_time_change))   


        return_dict = {
                'total_pct_change' : "{:.2f}".format(total_daily_change* 100),
                'assets' : assets,
                'account_total' : "{:.2f}".format(total_account_value),
                'name' : "Celsius",
                'total_all_time_pct_change' : "{:.2f}".format(total_all_time_change)
            }

    except Exception as e:
        print("Erroed out with: {}".format(e))
        return {
            'statusCode' : 400,
            'body': json.dumps("Error: {}".format(e)),
            'headers' : RETURN_HEADER
        }


    try:
        # insert the account data into userAccounts table
        user_account = dynamoClient.get_item(
            Key={
                'userId' : {
                    'S' : userId
                },
                'AccountName' : {
                    'S' : 'Celsius'
                }
            },
            TableName='UserAccounts'
        )
        print("user account: {}".format(user_account))
        if "Item" in user_account:
            # user account already exists
            print("user account found")
            user_account = user_account.get("Item")
            account_data_str = json.dumps(return_dict)
            update_response = dynamoClient.update_item(
                ExpressionAttributeNames={
                    '#AD': 'AccountData',
                },
                ExpressionAttributeValues={
                    ':ad': {
                        'S': account_data_str,
                    },
                },
                Key={
                    'userId': {
                        'S': userId,
                    },
                    'AccountName': {
                        'S': "Celsius",
                    },
                },
                ReturnValues='ALL_NEW',
                TableName='UserAccounts',
                UpdateExpression='SET #AD = :ad',
            )
            print("Updated item: {}".format(update_response))
        else:
            # user account doesn't exist
            print("no user account")
            user_account = {
                'userId' :
                    {'S' : userId},
                'AccountName' :
                    {'S' : 'Celsius'},
            }
            user_account = insertJsonAttributeItem(user_account, 'AccountData', return_dict)
            print("final account: {}".format(user_account))
            dynamoClient.put_item(
                Item=user_account,
                TableName="UserAccounts"
            )
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps("Error: {}".format(e)),
            'headers' : RETURN_HEADER
        }
    return {
        'statusCode': 200,
        'body': json.dumps(return_dict),
        'headers' : RETURN_HEADER
    }
from requests import api
from requests.api import head
import boto3
import json
import requests

dynamoClient = boto3.client("dynamodb")

RETURN_HEADER = { 
    'Access-Control-Allow-Origin' : '*',
    'Access-Control-Allow-Headers':'*',
    'Access-Control-Allow-Credentials' : True,
    'Access-Control-Allow-Methods' : "OPTIONS, POST",
    'Content-Type': 'application/json',
    'X-Requested-With' : '*'
}


def lambda_handler(event, context):
    api_key = event.get("queryStringParameters", {}).get("api_key", "")
    user_id = event.get("queryStringParameters", {}).get("userId", "")

    print("api_key: {}".format(api_key))
    print("user_id: {}".format(user_id))

    headers = {
        'X-Cel-Partner-Token' : 'ff4152bf-ec69-40cd-932b-783767dbb921',
        'X-Cel-Api-Key': api_key
    }
    base_endpoint = "https://wallet-api.celsius.network/wallet/"
    wallets_endpoint = "balance/"
    try:
        wallet_request = requests.get(url=base_endpoint+wallets_endpoint, headers=headers)

        if wallet_request.status_code != 200 :
            print("Error when accessing wallet endpoint")
            raise Exception("Could not get data from wallet endpoint")
        print("api key was successfull")
        new_account = {
            'api_key' : 
                {'S' : api_key},
            'userId' :
                {'S' : user_id},
        }
        print("inserting new DB item: {}".format(new_account))
        dynamoClient.put_item(
                    Item = new_account,
                    TableName='celsiusAccount'
        )
    except Exception as e:
        print("Erroring out: {}".format(e))
        return {
            'statusCode' : 400,
            'body' : json.dumps("Error {}".format(e)),
            'headers' : RETURN_HEADER
        }

    print("Succesfully added account to celsiusAccount table")

    return {
        'statusCode': 200,
        'body': json.dumps({'loggedIn' : True}),
        'headers' : RETURN_HEADER
    }
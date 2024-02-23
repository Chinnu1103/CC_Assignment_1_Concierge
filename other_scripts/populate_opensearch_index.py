import json
import boto3
import requests
from requests_aws4auth import AWS4Auth

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
aws_auth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

dynamodb = boto3.resource('dynamodb')
es_endpoint = 'search-restaurants-domain-5bburyrdx3v4w25dtexgn6pgdm.us-east-1.es.amazonaws.com'

def lambda_handler(event, context):
    table = dynamodb.Table('yelp-restaurants')
    response = table.scan()

    for item in response['Items']:
        index_document(item)

    return {
        'statusCode': 200,
        'body': json.dumps('Data indexed successfully!')
    }

def index_document(item):
    url = f'https://{es_endpoint}/restaurants/_doc/{item["id"]}'
    headers = {'Content-Type': 'application/json'}
    data = {
        'cuisineType': item['cuisineType'],
        'insertedAtTimestamp': str(item['insertedAtTimestamp'])
    }
    response = requests.put(url, auth=aws_auth, headers=headers, data=json.dumps(data))
    print(response)

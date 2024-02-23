import json
import boto3
import requests
from requests_aws4auth import AWS4Auth
from datetime import datetime

#Send the html body to the given email
def send_email(sub, body, email):
    client = boto3.client('ses')
    client.send_email(
        Source = 'cdb9649@nyu.edu',
        Destination = {
            'ToAddresses': [email]
        },
        Message = {
            'Subject': {
                'Data': sub
            },
            'Body': {
                'Html': {
                    'Data': body
                }
            }
        }
    )

#Format date into readable Month, Day Year string
def get_formatted_date(date):
    return datetime.strptime(date, "%Y-%m-%d").strftime("%B, %d %Y")

#Format address into a single string
def get_formatted_address(addr):
    try:
        addr = json.loads(addr)
        formatted_addr = ""
        for part in addr["display_address"]["L"]:
            formatted_addr += part["S"]
            formatted_addr += " "   
    except:
        formatted_addr = ""
    
    return formatted_addr

#Convert an array of 3 restaurants into a HTML string to be sent to the user as email
def get_formatted_restaurants(res, pref: dict):    
    body = ""
    formatted_date = get_formatted_date(pref["date"])
    body += "<html><body><p>Hello,<br>I hope this email finds you well!<br><br>"
    body += f"Based on your preferences for {pref["cuisine"].title()} restaurants in {pref["location"].title()}, I've carefully curated three fantastic recommendations for your party of {pref["party_size"]}, that are perfect for dining at {pref["time"]} on {formatted_date}.<br><br>"
    
    body += "<ol>"
    for i in range(3):
        name = res[i]["name"]["S"]
        phone = res[i]["phone"]["S"] if "phone" in res[i] else ""
        price = res[i]["price"]["S"] if "price" in res[i] else ""
        rating = res[i]["rating"]["S"] if "rating" in res[i] else ""
        yelp_link = res[i]["url"]["S"] if "url" in res[i] else ""
        address = get_formatted_address(res[i]["location"])
        
        body += "<li>"
        body += f"<a href=\"{yelp_link}\">{name}</a><br>"
        body += f"Phone: {phone}<br>" if phone else ""
        body += f"Price: {price}<br>" if price else ""
        body += f"Rating: {rating}<br>" if rating else ""
        body += f"Address: {address}<br>" if address else ""
        body += "<br>"
        body += "</li>"
    
    body += "</ol><br>"    
    body += "Wishing you a delightful dining experience!"
    body += "</p></body></html>"
    
    return body

#Fetch restaurant details from dynamo db given the restaurant id from opensearch
def get_restaurants_details(ts_list):
    client = boto3.client('dynamodb')
    res = []
    
    for ts in ts_list:
        item = client.get_item(
            TableName='yelp-restaurants', 
            Key={ 
                'insertedAtTimestamp':{
                    'N': ts
                }
            }
        )
        
        res.append(item["Item"])
    
    return res

#Fetch 3 random restaurant ids by cuisine from opensearch
def get_restaurants_by_cuisine(cuisine, seed):
    region = 'us-east-1'
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    search_url = "https://search-restaurants-domain-5bburyrdx3v4w25dtexgn6pgdm.us-east-1.es.amazonaws.com"
    search_url = search_url + '/' + "restaurants" + '/_search'
    
    query = {
        "size": 3,
        "query": {
            "function_score": {
                "query": {
                    "match": {
                        "cuisineType": cuisine.title()
                    }
                },
                "random_score" : {
                    "seed": seed
                }
            }
        }
    }
    
    headers = { "Content-Type": "application/json" }
    res = requests.get(search_url, auth=awsauth, headers=headers, data=json.dumps(query))
    
    res = json.loads(res.text)
    
    ts_list = []
    ts_list.append(res["hits"]["hits"][0]["_source"]["insertedAtTimestamp"])
    ts_list.append(res["hits"]["hits"][1]["_source"]["insertedAtTimestamp"])
    ts_list.append(res["hits"]["hits"][2]["_source"]["insertedAtTimestamp"])
    
    return get_restaurants_details(ts_list)

#Pop the front of the SQS queue with the restaurant details
def get_queue_request():
    sqs = boto3.client('sqs')
    queue_url = "https://sqs.us-east-1.amazonaws.com/533267091586/DiningPreferenceQueue.fifo"
    
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'All'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ]
    )
    
    if ("Messages" in response) and (len(response["Messages"]) != 0):
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        return message
    
    return None

#Main Function 
def lambda_handler(event, context):
    
    msg = get_queue_request()
    
    if msg:
        
        attr = msg["MessageAttributes"]
        
        preferences = {
            "cuisine": attr["Cuisine"]["StringValue"],
            "date": attr["Date"]["StringValue"],
            "email": attr["Email"]["StringValue"],
            "location": attr["Location"]["StringValue"],
            "party_size": attr["PartySize"]["StringValue"],
            "time": attr["Time"]["StringValue"]
        }
        
        res = get_restaurants_by_cuisine(preferences["cuisine"], int(attr["Seed"]["StringValue"]))
        email_body = get_formatted_restaurants(res, preferences)
        email_sub = "Restaurant Suggestions"
        
        send_email(email_sub, email_body, preferences["email"])

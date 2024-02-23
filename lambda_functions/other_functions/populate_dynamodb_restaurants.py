import requests
import time
import boto3
from tqdm import tqdm
import json

cuisines = ["Chinese", "Italian", "Indian", "Mexican", "French", "Japanese", "American", "Thai", "Cuban", "Greek", "Korean"]

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('yelp-restaurants')

for cuisine in cuisines:
    print(f"Parsing Cuisine: {cuisine}")
    for offset in range(0, 1000, 50):
        print(f"Parsing Offset: {offset}")
        url = f"https://api.yelp.com/v3/businesses/search?location=NYC&term={cuisine}%20restaurants&categories=&sort_by=best_match&limit=50&offset={offset}"

        headers = {
            "accept": "application/json",
            "Authorization": "BEARER"
        }

        response = requests.get(url, headers=headers)
        businesses = json.loads(response.text)["businesses"]
        for restaurant in tqdm(businesses):
            ts = time.time_ns()
            restaurant["insertedAtTimestamp"] = ts 
            restaurant["cuisineType"] = cuisine
            restaurant["coordinates"]["latitude"] = str(restaurant["coordinates"]["latitude"])
            restaurant["coordinates"]["longitude"] = str(restaurant["coordinates"]["longitude"]) 
            restaurant["rating"] = str(restaurant["rating"])
            del restaurant["distance"]
                  
            table.put_item(Item=restaurant)
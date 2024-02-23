from datetime import datetime, timezone, timedelta
from lf1_response_messages import get_message
import re
import boto3
import json

#Pre-definition of some response structures
messages = [{
    "content": "",
    "contentType": "PlainText"
}]

dialogAction = {
    "type": "ElicitSlot"
}

#Get the state of the previous user session
def get_prev_suggestion(sessionId):
    client = boto3.client('dynamodb')
    item = client.get_item(
        TableName='restaurant_suggestion_session', 
        Key={ 
            'session_id':{
                'S': sessionId
            }
        }
    )
    
    if "Item" in item:
        return item["Item"]    
    else:
        return None

#Get the next empty slot in the sequence
def get_next_slot(slots):
    if not ("Location" in slots and slots["Location"] != None):
        return "Location"
    elif not ("Cuisine" in slots and slots["Cuisine"] != None):
        return "Cuisine"
    elif not ("Date" in slots and slots["Date"] != None):
        return "Date"
    elif not ("Time" in slots and slots["Time"] != None):
        return "Time"
    elif not ("PartySize" in slots and slots["PartySize"] != None):
        return "PartySize"
    elif not ("Email" in slots and slots["Email"] != None):
        return "Email"
    
    return None

#Handle the response when the user triggers the Greeting intent
def handle_greeting_event(event):
    
    slots = event["sessionState"]["intent"]["slots"]
    
    if "PreviousSuggestion" in slots and slots["PreviousSuggestion"] != None:
    
        if slots["PreviousSuggestion"]["value"]["interpretedValue"] == "Yes":
            item = get_prev_suggestion(event["sessionId"])
            event["previous_session_info"] = {
                "Cuisine": item["Cuisine"]["S"],
                "Date": item["Date"]["S"],
                "Email": item["Email"]["S"],
                "Time": item["Time"]["S"],
                "Location": item["Location"]["S"],
                "PartySize": item["PartySize"]["S"],
                "session_id": item["session_id"]["S"],
                "Seed": item["Seed"]["N"]
            }
            messages[0]["content"] = "Gotcha! I'll be sending the recommendations right away. Have a great day!"
            event["messages"] = messages
            dialogAction["type"] = "Close"
            event["sessionState"]["dialogAction"] = dialogAction
        else:
            messages[0]["content"] = "Alright, how can I help you today?"
            event["messages"] = messages
            dialogAction["type"] = "ElicitIntent"
            event["sessionState"]["dialogAction"] = dialogAction
    else:
        
        item = get_prev_suggestion(event["sessionId"])
        if not item:
            dialogAction["type"] = "Close"
            event["sessionState"]["dialogAction"] = dialogAction
            messages[0]["content"] = "Hello! How can I help you today?"
            event["messages"] = messages
            return (False, event)
        else:
            dialogAction["type"] = "ElicitSlot"
            dialogAction["slotToElicit"] = "PreviousSuggestion"
            event["sessionState"]["dialogAction"] = dialogAction
            messages[0]["content"] = "Hi, welcome back! I still have your previous restaurant recommendations. Do you want me to send it again to your email?"
            event["messages"] = messages
    
    return (True, event)

#Handle the response when the user triggers the DiningSuggestion intent
def handle_dining_event(event):
    ret, msg, slot = validate_slots(event["sessionState"]["intent"]["slots"])
    if not ret:
        msg = get_message(msg)
        event["sessionState"]["intent"]["slots"][slot] = None
        dialogAction["slotToElicit"] = slot
        event["sessionState"]["dialogAction"] = dialogAction
        event["sessionState"]["intent"]["state"] = "InProgress"
        messages[0]["content"] = msg
        event["messages"] = messages
        return (False, event)
    
    if "dialogAction" not in event["sessionState"]:
        dialogAction["slotToElicit"] = get_next_slot(event["sessionState"]["intent"]["slots"])
        if(dialogAction["slotToElicit"] == None):
            dialogAction["type"] = "Close"
            slots = event["sessionState"]["intent"]["slots"]
            location = slots["Location"]["value"]["interpretedValue"].title()
            date = slots["Date"]["value"]["interpretedValue"]
            psize = int(slots["PartySize"]["value"]["interpretedValue"])
            messages[0]["content"] = f"Great! You're all set for a fantastic dining experience in {location} on {date} for a party of {psize}. You can expect the recommendations shortly. Have a nice day!"
            event["messages"] = messages
        else:
            dialogAction["type"] = "ElicitSlot"
        event["sessionState"]["dialogAction"] = dialogAction
    
    return (True, event)

#Handle the lex response sent by the user
def handle_response(event):
    ret, msg = validate_intent(event)
    if not ret:
        msg = get_message(msg)
        dialogAction["type"] = "Close"
        event["sessionState"]["dialogAction"] = dialogAction
        messages[0]["content"] = msg
        event["messages"] = messages
        return (False, event)
    
    if(event["sessionState"]["intent"]["name"] == "GreetingIntent"):
        print("Greeting Event")
        return handle_greeting_event(event)
    else:
        print("Dining Event")
        return handle_dining_event(event)
    
#Validate if the intent is within the scope of our expectations
def validate_intent(event):
    if(event["sessionState"]["intent"]["name"] != "DiningSuggestionsIntent" and event["sessionState"]["intent"]["name"] != "GreetingIntent"):
        return (False, "wrong_intent")
    elif (event["sessionState"]["intent"]["state"] == "Failed"):
        return (False, "failed_intent")
    
    return (True, "")

#Validate the slot values
def validate_slots(slots):
    if("Location" in slots and slots["Location"] != None):
        location = slots["Location"]["value"]["interpretedValue"].title()
        valid_locations = ["Manhattan", "New York", "New York City", ]
        if location not in valid_locations:
            return (False, "invalid_location", "Location")
    
    if("Cuisine" in slots and slots["Cuisine"] != None):
        cuisine = slots["Cuisine"]["value"]["interpretedValue"].title()
        valid_cuisines = ["Chinese", "Italian", "Indian", "Mexican", "French", "Japanese", "American", "Thai", "Cuban", "Greek", "Korean"]
        if cuisine not in valid_cuisines:
            return (False, "invalid_cuisine", "Cuisine")
    
    if("Date" in slots and slots["Date"] != None):
        try:
            date_str = slots["Date"]["value"]["interpretedValue"]
            et = timezone(timedelta(hours=-5))
            given_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=et)
            difference = given_date - datetime.today().astimezone(et).replace(hour=0, minute=0, second=0, microsecond=0)
            if not (0 <= difference.days <= 30):
                return (False, "invalid_date_duration", "Date")
        except ValueError:
            return (False, "invalid_date_format", "Date")
        
    if("Time" in slots and slots["Time"] != None):
        try:
            time_str = slots["Time"]["value"]["interpretedValue"]
            et = timezone(timedelta(hours=-5))
            today = datetime.today().astimezone(et)
            given_time = datetime.combine(today, datetime.strptime(time_str, '%H:%M').time()).replace(tzinfo=et)
            if(difference.days == 0 and today > given_time):
                print("Booop")
                return (False, "invalid_time_duration", "Time")
        except ValueError:
            return (False, "invalid_time_format", "Time")
    
    if("PartySize" in slots and slots["PartySize"] != None):
        try:
            psize = int(slots["PartySize"]["value"]["interpretedValue"])
            if (psize > 50):
                return (False, "large_partysize", "PartySize")
            elif (psize < 1):
                return (False, "small_partysize", "PartySize")
        except ValueError:
            return (False, "invalid_partysize", "PartySize")
    
    if("Email" in slots and slots["Email"] != None):
        given_email = slots["Email"]["value"]["originalValue"]
        email_pattern = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
        if(email_pattern.match(given_email) == None):
            return (False, "invalid_email", "Email")
    
    return (True, "", "")
import json
import boto3
import uuid
import time
from lf1_validate_response import handle_response

#Save the session to a dynamo db table
def save_session(session_info):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('restaurant_suggestion_session')
    
    table.put_item(Item=session_info)

#Send the message to SQS queue to be handled by LF2 later
def send_message_to_sqs(session_info):
    sqsURL = "https://sqs.us-east-1.amazonaws.com/533267091586/DiningPreferenceQueue.fifo"
    sqs = boto3.client('sqs')
    
    sqs.send_message(
        QueueUrl=sqsURL,
        MessageGroupId=str(uuid.uuid1()),
        MessageAttributes={
            'Email': {
                'DataType': 'String',
                'StringValue': session_info["Email"]
            },
            'Cuisine': {
                'DataType': 'String',
                'StringValue': session_info["Cuisine"]
            },
            'Date': {
                'DataType': 'String',
                'StringValue': session_info["Date"]
            },
            'Time': {
                'DataType': 'String',
                'StringValue': session_info["Time"]
            },
            'Location': {
                'DataType': 'String',
                'StringValue': session_info["Location"]
            },
            'PartySize': {
                'DataType': 'Number',
                'StringValue': session_info["PartySize"]
            },
            'Seed': {
                'DataType': 'Number',
                'StringValue': str(session_info["Seed"])
            }
        },
        MessageBody=(
            f"Restaurant Suggestion request for {session_info['Email']}"
        )
    )

#Main function
def lambda_handler(event, context):
    
    try:
        ret, event = handle_response(event)
        
        if(ret and event["sessionState"]["dialogAction"]["type"] == "Close"):
            print("Sending Request to SQS")
            
            if event["sessionState"]["intent"]["name"] == "GreetingIntent":
                session_info = event["previous_session_info"]
                del event["previous_session_info"]
            else:
                slots = event["sessionState"]["intent"]["slots"]
                session_info = {
                    "Cuisine": slots["Cuisine"]["value"]["interpretedValue"],
                    "Date": slots["Date"]["value"]["interpretedValue"],
                    "Email": slots["Email"]["value"]["interpretedValue"],
                    "Time": slots["Time"]["value"]["interpretedValue"],
                    "Location": slots["Location"]["value"]["interpretedValue"],
                    "PartySize": slots["PartySize"]["value"]["interpretedValue"],
                    "session_id": event["sessionId"],
                    "Seed": time.time_ns()
                }
                
            save_session(session_info)
            send_message_to_sqs(session_info)
        
    except Exception as e:
        print("Error: ", e)
        event["messages"] = [{"content": "Sorry I didn't get that, can you please try again?", "contentType": "PlainText"}]
        event["sessionState"]["dialogAction"] = {"type": "Delegate"}
    
    return event
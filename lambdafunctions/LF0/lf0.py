import json
import uuid
from datetime import datetime
import boto3

#Main function to send user message to lex and return the response back to the user
def lambda_handler(event, context):
    session_id = event["messages"][0]["unstructured"]["id"]
    text = event["messages"][0]["unstructured"]["text"]
    
    client = boto3.client('lexv2-runtime')
    response = client.recognize_text(
        botId="Q2VQRHSXYA",
        botAliasId="TSTALIASID",
        localeId="en_US",
        sessionId=session_id,
        text=text
    )
    
    messages = []
    for msg in response["messages"]:
        message = {
            'type': "unstructured",
            'unstructured': {
                'id': str(uuid.uuid1()),
                'text': msg["content"],
                'timestamp': datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
        messages.append(message)
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin' : "*",
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'messages': messages,
        'body': "{}"
        
    }

messages = {
    "wrong_intent": "I'm sorry, I do not understand your request. Can you please try again?",
    "failed_intent": "I'm sorry, but I failed to gather enough information to suggest restaurants. Can you please try again?",
    "invalid_location": "Currently, I only support these locations: New York, New York City, Manhattan. Can you please select a location from these options?",
    "invalid_cuisine": "Currently, I do not support the cuisine you requested for. Can you please enter another cuisine?",
    "invalid_date_duration": "I'm sorry, please enter a date within 30 days from today.",
    "invalid_date_format": "I'm sorry, I could not understand the date format. Can you please try again?",
    "invalid_time_duration": "I'm sorry, the time you entered has already passed. Can you please enter a time in the future?",
    "invalid_time_format": "I'm sorry, I could not understand the time format. Can you please try again?",
    "large_partysize": "Unfortunately I do not support party sizes larger than 50. Can you please enter a smaller size?",
    "small_partysize": "Please enter a valid party size which is more than 1.",
    "invalid_partysize": "I'm sorry I could not understand your party size. Can you please try again?",
    "invalid_email": "I'm sorry, I could not understand your email format. Can you please try again."
}

def get_message(message_type):
    if message_type in messages:
        return messages[message_type]
    else:
        return message_type
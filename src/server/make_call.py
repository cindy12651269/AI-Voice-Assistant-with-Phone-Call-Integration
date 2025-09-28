import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()  # Load TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, etc.

# Your Twilio credentials from .env
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")  # e.g. +19566920691
my_number = os.getenv("MY_PHONE_NUMBER")  

client = Client(account_sid, auth_token)

call = client.calls.create(
    to=my_number,
    from_=twilio_number,
    # Twilio will request TwiML from your deployed server:
    url="https://ai-voice-assistant-with-phone-call.onrender.com/twilio/voice"
)

print(f"✅ Call initiated. SID: {call.sid}")

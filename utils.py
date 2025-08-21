import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",           
    "https://www.googleapis.com/auth/calendar.events"     
]

messages = []

def setup_calendar_service():
    """Create an token file with authenticated Google Calendar service using OAuth tokens."""
    try:
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
            
        service = build("calendar", "v3", credentials=creds)
        
        return service
    except Exception as e:
        print(f"⚠️ Wystąpił błąd podczas konfigurowania usługi Kalendarza Google: {e}")
        return None


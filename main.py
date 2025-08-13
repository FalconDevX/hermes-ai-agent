import os
import json
import datetime as dt
from typing import Dict
from zoneinfo import ZoneInfo  

from dotenv import load_dotenv
import google.generativeai as genai

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Load environment variables
load_dotenv()
# Configure Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Set model name
MODEL_NAME = "gemini-2.5-flash"  
# Define Google Calendar API scopes
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
# Define timezone
TZ = ZoneInfo("Europe/Warsaw")

def get_calendar_service():
    """Create an token file with authenticated Google Calendar service using OAuth tokens."""
    try:
        creds = None
        # if token.json exists, load it, limited by SCOPES
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        # if no creds or valid creds, run OAuth on web to get new token
        if not creds or not creds.valid:
            # if creds and they are expired create new token from refresh token
            if creds and creds.expired and creds.refresh_token:
                # sending refresh request to Google
                creds.refresh(Request())
            else:
                # if no valid creds, run OAuth on web to get new token limited by SCOPES
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                # run webserver, after authentication store the token
                creds = flow.run_local_server(port=0)
            #saving token to .json file 
            with open("token.json", "w", encoding="utf-8") as file:
                file.write(creds.to_json())
        # Build the Google Calendar service with the credentials
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Error creating calendar service and authentication: {e}")
        return None

def parse_iso_local(google_date: str) -> dt.datetime:
    """Parse ISO string to python datetime, if no timezone (tz) then assume Europe/Warsaw"""

    #if there is no time in date -> date is all day, assume start of day
    if "T" not in google_date:
        parsed_date = dt.datetime.strptime(google_date, "%Y-%m-%d").replace(tzinfo=TZ)
        return parsed_date
    #if there is UTC (Zulu time at the end of date) replace with +00:00
    if  google_date.endswith("Z"): 
        google_date = google_date.replace("Z", "+00:00")
    #parse the date from iso - google to datetime - python
    parsed_date = dt.datetime.fromisoformat(google_date)
    #if parsed date has no timezone, assume Europe/Warsaw
    if parsed_date.tzinfo is None:
        parsed_date = parsed_date.replace(tzinfo=TZ)
    return parsed_date

def convert_date_to_local(date: dt.datetime) -> str:
    """Return iso date (with no tz) in local Warsaw time for Google API with timeZone field."""
    return date.astimezone(TZ).replace(tzinfo=None).isoformat(timespec="seconds")

def move_date_to_future(start_dt: dt.datetime, now: dt.datetime) -> dt.datetime:
    """If start_dt is in the past, move to the nearest sensible future moment."""
    #if start date is in the future return date
    if start_dt >= now:
        return start_dt

    #if start date is today but time already passed move on tomorrow same time
    if start_dt.date() == now.date() and start_dt.time() < now.time():
        return start_dt + dt.timedelta(days=1)

    #date in the past year try same month/day in current year
    projected_dt = start_dt.astimezone(TZ)
    try:
        #attempt to replace year with current year
        projected_dt = projected_dt.replace(year=now.year)
    except ValueError:
        #handle error e.g. 29 Feb etc.
        projected_dt = projected_dt + dt.timedelta(days=365)

    #if projected date is still in the past (past month) try next year
    if projected_dt < now:
        try:
            #attempt to replace year with next year
            projected_dt = projected_dt.replace(year=projected_dt.year + 1)
        except ValueError:
            #handle error 
            projected_dt = projected_dt + dt.timedelta(days=365)

    return projected_dt

def prompt_to_event(user_prompt: str) -> Dict:
    """
    Ask Gemini to convert a argument - short Polish instruction into JSON:
    { "title": str, "start_iso": str, "end_iso": str | null, "timezone": str | null }
    Always adjust to future date if model returns past.
    """
    #create variable with current time - e.g. in iso format 2025-08-13T14:25:37.123456+02:00
    today = dt.datetime.now(TZ)
    #instructions for Gemini llm model   
    gemini_instructions = (
        "You convert Polish natural language into ONE Google Calendar event.\n"
        f"Today is {today.date().isoformat()} and the current local time is {today.time().strftime('%H:%M')} in Europe/Warsaw.\n"
        "Return ONLY valid JSON with EXACT keys: title, start_iso, end_iso, timezone.\n"
        "Dates must be fully qualified ISO 8601 (e.g. 2025-08-13T15:00:00).\n"
        "Assume Europe/Warsaw when timezone is not specified.\n"
        "If only start is given and no duration, set end_iso to empty string.\n"
        "Prefer the nearest future date if ambiguous."
    )
    #creating an instance of the Gemini model
    gemini_model = genai.GenerativeModel(
        #name
        MODEL_NAME,
        #system prompt
        system_instruction=gemini_instructions,
        #force to return json file type
        generation_config={"response_mime_type": "application/json"},
    )

    # Generate content using the model and saving it to variable
    response = gemini_model.generate_content(user_prompt)

    #Checking if model answer is valid JSON
    try:
        event_data = json.loads(response.text)
    except Exception as e:
        raise RuntimeError(f"Model did not return JSON: {e}\nRaw: {getattr(response, 'text', '')}")

    #Validate required fields
    missing_field = [key for key in ["title", "start_iso"] if not event_data.get(key)]
    if missing_field:
        raise ValueError(f"Missing required fields from model: {missing_field}. Got: {event_data}")

    #set default timezone if event_data is missing one
    if not event_data.get("timezone"):
        event_data["timezone"] = "Europe/Warsaw"

    # Parse and normalize date to local Warsaw time
    start_dt = parse_iso_local(event_data["start_iso"]).astimezone(TZ)

    #Checking if date is in the past
    now = dt.datetime.now(TZ)
    start_dt = move_date_to_future(start_dt, now)

    # Default duration +1h if end missing/empty
    if not event_data.get("end_iso"):
        end_dt = start_dt + dt.timedelta(hours=1)
    else:
        end_dt = parse_iso_local(event_data["end_iso"]).astimezone(TZ)
        if end_dt <= start_dt:
            end_dt = start_dt + dt.timedelta(hours=1)

    # Store back as local iso
    event_data["start_iso"] = convert_date_to_local(start_dt)
    event_data["end_iso"]   = convert_date_to_local(end_dt)

    return event_data

def create_event(event_info: Dict, calendar_id: str = "primary") -> str:
    """Insert event into Google Calendar and return the HTML link."""
    #create event body with provided data
    event_body = {
        "summary": event_info["title"],
        "start": {"dateTime": event_info["start_iso"], "timeZone": event_info["timezone"]},
        "end":   {"dateTime": event_info["end_iso"],   "timeZone": event_info["timezone"]},
    }
    #initialize calendar service
    calendar_service = get_calendar_service()
    #insert event into calendar, providing event with calendar id and event body
    event = calendar_service.events().insert(calendarId=calendar_id, body=event_body).execute()
    #return event link
    return event.get("htmlLink", "")

def main():
    #Showing user formatted current time
    today_str = dt.datetime.now(TZ).strftime("%Y-%m-%d (%A) %H:%M")
    print(f"📅 Dziś: {today_str}")

    # Get user input for event details
    user_text = input("🗣️ Polecenie: ").strip()
    gemini_answer= prompt_to_event(user_text)

    # Echo parsed times for clarity
    print(f"⏰ Start: {gemini_answer['start_iso']}  (strefa: {gemini_answer['timezone']})")
    print(f"⏱️  Koniec: {gemini_answer['end_iso']}  (strefa: {gemini_answer['timezone']})")

    link = create_event(gemini_answer)
    print(f"✔️ Dodano: {gemini_answer['title']}")
    print(f"🔗 Link: {link}")

if __name__ == "__main__":
    main()
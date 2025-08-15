import os
import datetime as dt
from zoneinfo import ZoneInfo
from google import genai
import json
from dotenv import load_dotenv

from typing import List, Optional, Literal
from pydantic import BaseModel

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"  

# add new event from Google Calendar API example
# https://developers.google.com/workspace/calendar/api/guides/create-events?hl=pl#python
# https://ai.google.dev/gemini-api/docs/function-calling?example=meeting
# event = {
#   'summary': 'Google I/O 2015',
#   'location': '800 Howard St., San Francisco, CA 94103',
#   'description': 'A chance to hear more about Google\'s developer products.',
#   'start': {
#     'dateTime': '2015-05-28T09:00:00-07:00',
#     'timeZone': 'America/Los_Angeles',
#   },
#   'end': {
#     'dateTime': '2015-05-28T17:00:00-07:00',
#     'timeZone': 'America/Los_Angeles',
#   },
#   'recurrence': [
#     'RRULE:FREQ=DAILY;COUNT=2'
#   ],
#   'attendees': [
#     {'email': 'lpage@example.com'},
#     {'email': 'sbrin@example.com'},
#   ],
#   'reminders': {
#     'useDefault': False,
#     'overrides': [
#       {'method': 'email', 'minutes': 24 * 60},
#       {'method': 'popup', 'minutes': 10},
#     ],
#   },
# }


#Sub models
class EventDateTime(BaseModel):
    dateTime: Optional[str] = None
    date: Optional[str] = None
    timeZone: Optional[str] = None

class Attendee(BaseModel):
    email: str
    
class RemiderOverride(BaseModel):
    method: Literal["email", "popup"]
    minutes: int

class Reminders(BaseModel):
    useDefault: bool = True
    overrides: Optional[List[RemiderOverride]] = None

#Main model
class CalendarEvent(BaseModel):
    summary: str
    location: Optional[str] = None
    description: Optional[str] = None
    start: EventDateTime
    end: EventDateTime
    attendees: List[Attendee]
    reminders: Optional[Reminders] = None
    attendees: Optional[List[Attendee]] = None
    reminders: Optional[Reminders] = None

def create_event_prompt(user_prompt: str) -> str:
    """Create a prompt for the ai model to generate calendar event in formatted way"""

    today = dt.datetime.now(tz=dt.timezone.utc).astimezone(tz=ZoneInfo("Europe/Warsaw"))

    gemini_instructions = (
        f"Today is {today.date().isoformat()} and the current local time is "
        f"{today.time().strftime('%H:%M')} in Europe/Warsaw.\n"
        "Convert the following Polish natural language request into a valid Google Calendar event "
        "matching the provided function schema.\n"
        "If the user specifies only a date or a relative day (e.g., 'za dwa dni', 'jutro'), "
        "assume a default start time of 10:00 and set the end time to 1 hour later.\n"
        "Prefer the nearest future date if ambiguous.\n"
        "Return only the JSON object, no extra text."
    )

    with open("./ai_tools_definitions/google_event.json", "r", encoding="utf-8") as f:
        ai_tool_google_calendar_object = json.load(f)

    tools = genai.types.Tool(function_declarations=[ai_tool_google_calendar_object])

    config = genai.types.GenerateContentConfig(
        tools=[tools],
        system_instruction=gemini_instructions,
        response_mime_type="application/json"
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=config
    )

    return response

if __name__ == "__main__":
    user_prompt = "Chcę umówić spotkanie z zespołem na jutro o 10:00."
    response = create_event_prompt(user_prompt)


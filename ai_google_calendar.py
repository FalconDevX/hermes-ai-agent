import os
import datetime as dt
from zoneinfo import ZoneInfo
from google import genai
import json
from dotenv import load_dotenv

from utils import setup_calendar_service

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"  

def create_event_api(event: json):
    service = setup_calendar_service()

    if "colorId" not in event:
        event["colorId"] = "5"

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Event created: %s" % (event.get('htmlLink')))

def list_events_api(time_min, time_max):
    service = setup_calendar_service()
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    events = events_result.get("items", [])

    if not events:
        print("Brak nadchodzących wydarzeń.")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(f"📅 {event['summary']} (Start: {start})")

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
        "If the user specifies an event color (e.g., red, green, blue, purple), "
        "choose the appropriate colorId according to the following mapping:\n"
        "Use the following color mapping:\n"
        "- red → \"11\" \n"
        "- green → \"2\"\n"
        "- blue → \"9\"\n"
        "- purple → \"3\"\n"
        "- yellow → \"5\"\n"
        "- orange → \"6\"\n"
        "- turquoise → \"7\"\n"
        "- gray → \"8\"\n"
        "- light blue → \"1\"\n"
        "- light green → \"10\"\n"
        "- pink → \"4\"\n"
        "If the user does not specify a color, do NOT include the colorId field in the response.\n"
        "Return the event as function_call, not plain JSON."
    )

    with open("./ai_tools_definitions/google_event.json", "r", encoding="utf-8") as file:
        ai_tool_google_calendar_object = json.load(file)

    tools = genai.types.Tool(function_declarations=[ai_tool_google_calendar_object])

    config = genai.types.GenerateContentConfig(
        tools=[tools],
        system_instruction=gemini_instructions
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=config
    )

    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        print(f"Function to call {function_call.name}")
        print(f"Arguments: {function_call.args}")
    else:
        print("No function call found in the response.")
        print(f"Response text: {response.text}")

    if function_call:
        create_event_api(function_call.args)
    else:
        raise ValueError("No function call found in the response. Please check the input prompt.")

def list_events_prompt(user_prompt: str):
    """Create prompt for ai model to list events from user input and returns two date interval"""
    today = dt.datetime.now(tz=dt.timezone.utc).astimezone(tz=ZoneInfo("Europe/Warsaw"))

    gemini_instructions = (
        f"Today is {today.date().isoformat()} and the current local time is "
        f"{today.time().strftime('%H:%M')} in Europe/Warsaw.\n"
        "Convert the following Polish natural language request into a date interval.\n"
        "Always return a function_call with two arguments: timeMin and timeMax.\n"
        "Rules:\n"
        "- 'dzisiaj' → timeMin = today 00:00, timeMax = today 23:59.\n"
        "- 'jutro' → timeMin = tomorrow 00:00, timeMax = tomorrow 23:59.\n"
        "- 'ten tydzień' → timeMin = Monday of this week 00:00, timeMax = Sunday of this week 23:59.\n"
        "- 'przyszły tydzień' → Monday next week → Sunday next week.\n"
        "- 'ten miesiąc' → first day of this month → last day of this month.\n"
        "- 'przyszły miesiąc' → first day of next month → last day of next month.\n"
        "- If user specifies a range (e.g., 'od 1 września do 10 września'), use it directly.\n"
        "- If only one date is given, use it as both timeMin (00:00) and timeMax (23:59).\n"
        "- Always return ISO 8601 format with timezone Europe/Warsaw.\n"
        "Never return plain text, only function_call."
    )

    with open("./ai_tools_definitions/google_list_events.json", "r", encoding="utf-8") as file:
        ai_tool_google_calendar_object = json.load(file)
    
    tools = genai.types.Tool(function_declarations=[ai_tool_google_calendar_object])

    config = genai.types.GenerateContentConfig(
        tools=[tools],
        system_instruction=gemini_instructions
    )   

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=config
    )

    if response.candidates[0].content.parts[0].function_call:
        function_call = response.candidates[0].content.parts[0].function_call
        print(f"Function to call {function_call.name}")
        print(f"Arguments: {function_call.args}")
    else:
        print("No function call found in the response.")
        print(f"Response text: {response.text}")

    if function_call:
        list_events_api(function_call.args["timeMin"], function_call.args["timeMax"])
    else:
        raise ValueError("No function call found in the response. Please check the input prompt.")

# def list_available_colors():
#     service = setup_calendar_service()
#     colors = service.colors().get().execute()
#     print("Available event colors:")
#     for color_id, color_info in colors["event"].items():
#         print(f"{color_id}: background={color_info['background']}, foreground={color_info['foreground']}")



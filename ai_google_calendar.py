import os
import datetime as dt
from zoneinfo import ZoneInfo
from google import genai
import json
from dotenv import load_dotenv
from utils import setup_calendar_service

from utils import messages

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"  

def create_event_api(event: json):
    service = setup_calendar_service()

    COLOR_MAP = {
        "red": "11",
        "green": "2",
        "blue": "9",
        "purple": "3",
        "yellow": "5",
        "orange": "6",
        "turquoise": "7",
        "gray": "8",
        "light blue": "1",
        "light green": "10",
        "pink": "4"
    }

    gemini_new_color_instructions = (
        "Convert the user's color name input to one of the following canonical names, handling synonyms and misspellings:\n"
        "red, green, blue, purple, yellow, orange, turquoise, gray, light blue, light green, pink.\n"
        "If the input does not match any of these colors, return the exact phrase 'no_color'."
    )
    
    config = genai.types.GenerateContentConfig(
        system_instruction=gemini_new_color_instructions,
        response_mime_type="text/plain",
        temperature=0.0,
        max_output_tokens=5
    )

    if event.get("no_color", False):
        print("❌ Podano kolor, który nie jest obsługiwany. Wybierz poprawny kolor. Wydarzenie nie zostało utworzone.")
        event.pop("colorId", None)

        while True:
            is_new_color = input("Ustawić nowy kolor (jeśli nie domyślnie niebieski)? T,t/N,n: ").lower()

            if is_new_color == "t":
                new_color = input("Podaj nowy kolor: ").lower()
                
                try:
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=new_color,
                        temperature=0.0,
                        max_output_tokens=5,
                        config=config
                    )
                    ai_message = response.text.strip()

                except Exception as e:
                    print(f"❌ Wystąpił błąd llm podczas generowania koloru: {e}")
                    continue

                if ai_message == "no_color":
                    print("❌ Podano kolor, który nie jest obsługiwany. Wybierz poprawny kolor.")
                    continue
                else:
                    event["colorId"] = COLOR_MAP.get(ai_message)
                    print(f"✅ Ustawiono nowy kolor: {ai_message} dla wydarzenia {event['summary']}.")
                    break
            elif is_new_color == "n":
                event["colorId"] = "9"  # Default to blue
                print("✅ Ustawiono domyślny kolor (niebieski) dla wydarzenia.")
                break
            else:
                print("❌ Nieprawidłowy wybór. Proszę wpisać T lub N.")

    if "reminders" not in event or event.get("reminders", {}).get("useDefault", True):
        event["reminders"] = {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30}
            ]
        }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"✅ Utworzono wydarzenie: {event.get('htmlLink')}")

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
        print("📭 Brak nadchodzących wydarzeń.")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(f"📅 {event['summary']} (🕒 Początek: {start})")

def delete_event_api(event_name: str, time_min: str, time_max: str):
    """Delete event by searching its name in a given date range."""
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

    matches = [
        event for event in events 
        if event_name.strip().lower() in event.get("summary", "").strip().lower()
    ]

    if not matches:
        print("❌ Nie znaleziono pasujących wydarzeń.")
        return

    if len(matches) == 1:
        event = matches[0]
        print(f"🗑️ Usuwanie wydarzenia: {event['summary']} "
              f"({event['start'].get('dateTime', event['start'].get('date'))})")

        confirm = input("Usunąć? (T/N): ").lower()
        if confirm in ("t", "y"):
            service.events().delete(calendarId='primary', eventId=event["id"]).execute()
            print(f"✅ Usunięto: {event['summary']}")
        else:
            print("❎ Usuwanie anulowane.")
    else:
        print("⚠️ Znaleziono kilka pasujących wydarzeń:")
        for num, event in enumerate(matches, start=1):
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"{num}. 📅 {event['summary']} (🕒 Początek: {start})")

        while True:
            choice = input("Wybierz numer wydarzenia do usunięcia (lub Enter aby anulować): ")
            
            if choice.strip() == "":
                print("❎ Usuwanie anulowane.")
                break

            if choice.isdigit():
                choice_num = int(choice) - 1
                if 0 <= choice_num < len(matches):
                    event = matches[choice_num]
                    print(f"🗑️ Usuwanie wydarzenia: {event['summary']} "
                          f"({event['start'].get('dateTime', event['start'].get('date'))})")

                    confirm = input("Usunąć? (T/N): ").lower()
                    if confirm in ("t", "y"):
                        service.events().delete(calendarId='primary', eventId=event["id"]).execute()
                        print(f"✅ Usunięto: {event['summary']}")
                    else:
                        print("❎ Usuwanie anulowane.")
                    break
                else:
                    print("❌ Nieprawidłowy numer, spróbuj ponownie.")
            else:
                print("❌ Podaj poprawny numer albo naciśnij Enter, aby anulować.")
                    
def create_event_prompt(user_prompt: str) -> str:
    """Create a prompt for the ai model to generate calendar event in formatted way"""

    messages.append(
        genai.types.Content(
            role="user",
            parts=[genai.types.Part.from_text(text=user_prompt)]
        )
    )

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
        "important - If the user specifies a color which is NOT included in the mapping return: no_color\n"
        "For reminders:\n"
        "- If the user specifies custom reminders, always return them inside 'overrides' \n"
        "and set 'useDefault' to false.\n"
        "- If the user requests to use default reminders, set 'useDefault' to true and do not include overrides.\n"
        "- Never include both 'useDefault: true' and 'overrides' together.\n"
        "Return ONLY as function_call with args, NEVER plain JSON or text."
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
        contents=messages[-10:],
        config=config
    )

    function_call = None

    ai_message = response.candidates[0].content.parts[0]

    if ai_message.function_call:
        function_call = ai_message.function_call

        print(f"🛠️ Wywołanie funkcji: {function_call.name}")
        print(f"🧩 Argumenty: {function_call.args}")

    else:
        print("❌ Nie znaleziono wywołania funkcji w odpowiedzi.")
        print(f"📝 Tekst odpowiedzi: {response.text}")

    if function_call:
        create_event_api(function_call.args)
    else:
        raise ValueError("Nie znaleziono wywołania funkcji w odpowiedzi. Sprawdź dane wejściowe.")

def list_events_prompt(user_prompt: str):
    """Create prompt for ai model to list events from user input and returns two date interval"""
    
    messages.append(
        genai.types.Content(
            role="user",
            parts=[genai.types.Part.from_text(text=user_prompt)]
        )
    )

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
        contents=messages[-10:],
        config=config
    )

    function_call = None

    ai_message = response.candidates[0].content.parts[0]

    if ai_message.function_call:
        function_call = ai_message.function_call

        print(f"🛠️ Wywołanie funkcji: {function_call.name}")
        print(f"🧩 Argumenty: {function_call.args}")

    else:
        print("❌ Nie znaleziono wywołania funkcji w odpowiedzi.")
        print(f"📝 Tekst odpowiedzi: {response.text}")

    if function_call:
        list_events_api(function_call.args["timeMin"], function_call.args["timeMax"])
    else:
        raise ValueError("Nie znaleziono wywołania funkcji w odpowiedzi. Sprawdź dane wejściowe.")

def delete_event_prompt(user_prompt: str):
    """Create prompt for ai model to delete an event from user input."""

    messages.append(
        genai.types.Content(
            role="user",
            parts=[genai.types.Part.from_text(text=user_prompt)]
        )
    )

    today = dt.datetime.now(tz=dt.timezone.utc).astimezone(tz=ZoneInfo("Europe/Warsaw"))

    gemini_instructions = (
        f"Today is {today.date().isoformat()} and the current local time is "
        f"{today.time().strftime('%H:%M')} in Europe/Warsaw.\n"
        "Convert the following Polish natural language request into a function_call "
        "for deleting a Google Calendar event.\n"
        "Always return a function_call with three arguments: eventName, timeMin, timeMax.\n"
        "Rules:\n"
        "- eventName → extract directly from the user request (string).\n"
        "- 'dzisiaj' → timeMin = today 00:00, timeMax = today 23:59.\n"
        "- 'jutro' → timeMin = tomorrow 00:00, timeMax = tomorrow 23:59.\n"
        "- 'ten tydzień' → Monday this week → Sunday this week.\n"
        "- 'przyszły tydzień' → Monday next week → Sunday next week.\n"
        "- 'ten miesiąc' → first day of this month → last day of this month.\n"
        "- 'przyszły miesiąc' → first day of next month → last day of next month.\n"
        "- If user specifies a range (e.g. 'od 1 września do 10 września'), use it directly.\n"
        "- If only one date is given, use it as both timeMin (00:00) and timeMax (23:59).\n"
        "- Always return ISO 8601 format with timezone Europe/Warsaw.\n"
        "- If no date is given check the whole week.\n"
        "Never return plain text, only function_call."
    )

    with open("./ai_tools_definitions/google_delete_event.json", "r", encoding="utf-8") as file:
        ai_tool_google_calendar_object = json.load(file)

    tools = genai.types.Tool(function_declarations=[ai_tool_google_calendar_object])

    config = genai.types.GenerateContentConfig(
        tools=[tools],
        system_instruction=gemini_instructions
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=messages[-10:],
        config=config
    )

    function_call = None

    ai_message = response.candidates[0].content.parts[0]

    if ai_message.function_call:
        function_call = ai_message.function_call
        print(f"🛠️ Wywołanie funkcji: {function_call.name}")
        print(f"🧩 Argumenty: {function_call.args}")
    else:
        print("❌ Nie znaleziono wywołania funkcji w odpowiedzi.")
        print(f"📝 Tekst odpowiedzi: {response.text}")

    if function_call:
        delete_event_api(
            function_call.args["eventName"],
            function_call.args["timeMin"],
            function_call.args["timeMax"]
        )
    else:
        raise ValueError("No function call found in the response. Please check the input prompt.")


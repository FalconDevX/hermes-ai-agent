from zoneinfo import ZoneInfo
from google import genai
import os
from dotenv import load_dotenv

from ai_google_calendar import create_event_prompt, list_events_prompt, delete_event_prompt, change_calendar_prompt    

from utils import messages

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"  

TZ = ZoneInfo("Europe/Warsaw")

COMMANDS = ["add_event", "list_events", "remove_event", "clarification_needed", "change_calendar"]

schema = {
    "type" : "string",
    "enum": COMMANDS
}

def choose_specified_model(user_prompt: str) -> str:
    """Function which choose a specified ai model using gemini based on user input."""
    
    messages.append(
        genai.types.Content(
            role="user",
            parts=[genai.types.Part.from_text(text=user_prompt)]
        )
    )

    gemini_instructions = (
        "You act as a command classifier.\n"
        "Convert the user's request (in Polish) into exactly ONE of these strings:\n"
        "add_event, list_events, remove_event, change_calendar.\n"
        "Return ONLY the string, with no punctuation, no explanation, no quotes.\n"
        "If the request is unclear, return: clarification_needed\n"
        "Examples:\n"
        "Dodaj spotkanie na jutro o 15 lubtest jutro 15-16 -> add_event\n"
        "Pokaż mi nadchodzące wydarzenia -> list_events\n"
        "Usuń wydarzenie jutro o 12 -> remove_event\n"
        "Coś o wydarzeniu, ale nie wiem jak -> clarification_needed \n"
        "Przełącz kalendarz na inny -> change_calendar ."
    )

    config = genai.types.GenerateContentConfig(
        system_instruction=gemini_instructions,
        response_mime_type="text/plain"
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=messages[-10:],  
        config=config
    )

    result = response.text.strip()

    if result == "add_event":
        create_event_prompt(user_prompt)
    elif result == "list_events":
        list_events_prompt(user_prompt)
    elif result == "remove_event":
        delete_event_prompt(user_prompt)
    elif result == "edit_event":
        print("✏️ Funkcja edytowania wydarzeń nie jest jeszcze zaimplementowana.")
    elif result == "change_calendar":
        change_calendar_prompt(user_prompt)
    elif result == "clarification_needed":
        print("❓ Doprecyzuj swoje polecenie.")


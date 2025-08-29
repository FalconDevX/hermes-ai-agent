import os

from dotenv import load_dotenv
from zoneinfo import ZoneInfo  

from google import genai

from ai_router import choose_specified_model
from ai_google_calendar import change_calendar_api
from utils import setup_calendar_service
import utils

load_dotenv()

genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"  

TZ = ZoneInfo("Europe/Warsaw")

if __name__ == "__main__":
    service = setup_calendar_service()
    utils.cur_calendar = service.calendarList().get(calendarId="primary").execute()

    while True:
        user_prompt = input(change_calendar_api(utils.cur_calendar["id"])).strip()
        if user_prompt.lower() in ["exit", "quit"]:
            print("👋 Do widzenia!")
            break
        else:
            choose_specified_model(user_prompt)
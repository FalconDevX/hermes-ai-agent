import os

from dotenv import load_dotenv
from zoneinfo import ZoneInfo  

from google import genai

from ai_router import choose_specified_model

load_dotenv()

genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"  

TZ = ZoneInfo("Europe/Warsaw")

if __name__ == "__main__":
    while True:
        user_prompt = input("💬 Wpisz swoje polecenie: ")
        if user_prompt.lower() in ["exit", "quit"]:
            print("👋 Do widzenia!")
            break
        else:
            choose_specified_model(user_prompt)
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"  

def choose_specified_model(user_prompt: str) -> str:
    """Function which choose a specified ai model using gemini based on user input."""
    
    gemini_instructions = (
        "You act as a command classifier.\n"
        "Convert the user's request (in Polish) into exactly ONE of these strings:\n"
        "add_event, list_events, remove_event.\n"
        "Return ONLY the string, with no punctuation, no explanation, no quotes.\n"
        "If the request is unclear, return: clarification_needed\n"
        "Examples:\n"
        "Dodaj spotkanie na jutro o 15 -> add_event\n"
        "Pokaż mi nadchodzące wydarzenia -> list_events\n"
        "Usuń wydarzenie jutro o 12 -> remove_event\n"
        "Coś o wydarzeniu, ale nie wiem jak -> clarification_needed \n"
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config={
                "system_instruction": gemini_instructions,
                "response_mime_type": "application/json"
            }
    )
    return response.text

if __name__ == "__main__":
    user_input = "zmien nazwe użytkownika"
    model_response = choose_specified_model(user_input)
    print(f"Model response: {model_response}")
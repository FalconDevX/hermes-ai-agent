import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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

    gemini_model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=gemini_instructions,
        generation_config={
            "temperature": 0.0,
            "max_output_tokens": 6
        }
    )

    response = gemini_model.generate_content(user_prompt)
    
    return response.text

if __name__ == "__main__":
    user_input = "pokaż moje ustawienia użytkownika"
    model_response = choose_specified_model(user_input)
    print(f"Model response: {model_response}")
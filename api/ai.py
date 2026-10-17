import os
from dotenv import load_dotenv

load_dotenv()

def ask_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Gemini API key missing. Open the project's .env file and set GEMINI_API_KEY."
        )
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        response = client.models.generate_content(model=model, contents=prompt)
        answer = getattr(response, "text", None)
        if not answer:
            raise RuntimeError("The AI returned an empty response. Please try again.")
        return answer.strip()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"AI request failed: {exc}") from exc

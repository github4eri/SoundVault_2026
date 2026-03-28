import os
from google import genai
from google.genai import types
from mutagen.mp3 import MP3
from dotenv import load_dotenv

load_dotenv()

# 1. Setup the Gemini Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def get_audio_duration(file_path):
    """Automatically find out how long the audio is."""
    try:
        audio = MP3(file_path)
        length = audio.info.length # This is in seconds
        minutes = int(length // 60)
        seconds = int(length % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except Exception:
        return "Unknown"

async def analyze_audio_with_gemini(file_path):
    """The 'Ears': Using the stable 2.5 Flash Lite model."""
    
    # 1. Upload to Gemini's workspace
    file_upload = client.files.upload(file=file_path)

    prompt = """
    Listen to this audio. Provide a JSON response:
    {
      "title": "catchy name",
      "mood": "one word vibe",
      "instruments": "list of sounds",
      "energy": 1-10,
      "description": "1-sentence summary",
      "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
      "license_guess": "royalty-free or commercial"
    }
    """

    # 2. Call the 2.5 version
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[file_upload, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    
    
    print(f"AI RESPONSE: {response.text}")

    # 3. Clean and return
    return response.text.replace("```json", "").replace("```", "").strip()
    
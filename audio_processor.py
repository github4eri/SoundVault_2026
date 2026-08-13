import os
import time
from google import genai
from google.genai import types
import mutagen
from dotenv import load_dotenv

load_dotenv()

# 1. Setup the Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_audio_duration(file_path):
    """Automatically find out how long the audio is (works for any format mutagen supports)."""
    try:
        audio = mutagen.File(file_path)
        length = audio.info.length # This is in seconds
        minutes = int(length // 60)
        seconds = int(length % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except Exception:
        return "Unknown"

async def analyze_audio_with_gemini(file_path):
    """The 'Ears': Using the Gemini 2.5 Flash model."""

    # 1. Upload to Gemini's workspace
    file_upload = client.files.upload(file=file_path)

    # Gemini processes audio asynchronously (PROCESSING -> ACTIVE). Wait for it
    # to finish before analyzing, otherwise the model may read incomplete audio.
    max_attempts = 30
    attempts = 0
    while file_upload.state.name == "PROCESSING" and attempts < max_attempts:
        time.sleep(2)
        file_upload = client.files.get(name=file_upload.name)
        attempts += 1

    if file_upload.state.name != "ACTIVE":
        raise RuntimeError(f"Gemini file processing did not complete (state: {file_upload.state.name})")

    prompt = """
    ROLE: Professional Sound Librarian.
    TASK: Analyze the audio and provide technical metadata.
    
    GUIDELINES:
    - tempo_rhythm: Describe speed and pattern (e.g., 'Fast/Driving', 'Slow/Steady').
    - is_orchestrated: true if it's a full band/orchestra, false if it's a single instrument.
    - main_instrument: Identify the dominant sound (e.g., 'Electric Guitar', 'Violin', 'Nature Sounds').
    - has_vocals: true if any human singing or speaking is detected.
    
    SOURCE CATEGORIZATION:
    1. If the sound is synthetic or AI-synthesized: set is_ai_generated to true.
    2. If it is a recording of nature (wind, birds, water): set is_ai_generated to false AND is_environmental to true.
    3. If it is a human performance (instruments, voice, footsteps): set is_ai_generated to false AND is_environmental to false.
    4. "If the primary sound source is organic (Wind, Water, Animals), you MUST set is_environmental to true, even if a human is holding the microphone. Human Made is strictly for intentional human sounds like music, speech, or footsteps."
    
    Provide JSON:
    {
      "mood": "Mood",
      "instruments": ["list"],
      "main_instrument": "Specific dominant instrument",
      "is_orchestrated": true/false,
      "has_vocals": true/false,
      "tempo_rhythm": "Speed/Pattern",
      "acoustic_type": "Type",
      "is_ai_generated": true/false,
      "is_environmental": true/false,
      "music_genre": "Genre",
      "origin_country": "Country",
      "description": "Summary",
      "tags": ["tag1", "tag2"]
    }
    """

    # 2. Call the 2.5 version
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[file_upload, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    
    
    print(f"AI RESPONSE: {response.text}")

    # 3. Clean and return
    return response.text.replace("```json", "").replace("```", "").strip()
    
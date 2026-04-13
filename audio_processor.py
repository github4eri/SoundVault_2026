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
      "is_ai_generated": true/false,
      "description": "Summary",
      "tags": ["tag1", "tag2"]
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
    
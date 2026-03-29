from sqlalchemy import Column, Integer, String, Boolean, Text
from database import Base

class Sound(Base):
    __tablename__ = "sounds"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    file_path = Column(String)
    duration = Column(String)
    is_royalty_free = Column(Boolean, default=True)
    
    # --- New Architectural Additions ---
    acoustic_type = Column(String) # e.g., Alarm, Bar, Traffic
    is_environmental = Column(Boolean, default=False) # True if Nature/Ambient
    music_genre = Column(String) # e.g., Pop, Jazz, Cinematic
    origin_country = Column(String) # Country of origin
    is_ai_generated = Column(Boolean, default=False) # The Transparency Tag
    tempo_rhythm = Column(String) # e.g., "Fast/Steady" or "Slow/Ambient"
    is_orchestrated = Column(Boolean, default=False) # True if multiple instruments, False if solo
    main_instrument = Column(String) # e.g., "Piano", "Synthesizer", "None"
    has_vocals = Column(Boolean, default=False) # True if there is a human voice
    # -----------------------------------

    ai_mood = Column(String)
    ai_instruments = Column(String)
    ai_description = Column(String)
    ai_tags = Column(String)
    
    # ⚖️ The "Legal Safety Net"
    is_royalty_free = Column(Boolean, default=True)
    license_type = Column(String) # e.g., "CC0", "Personal", "Purchased"

    # 🧠 Gemini's Analysis
    ai_mood = Column(String)      # e.g., "Energetic"
    ai_instruments = Column(Text) # List of instruments
    ai_description = Column(Text) # Detailed AI summary
    ai_tags = Column(String)      # SEO-style tags

    # 🎹 Musical Metadata
    bpm = Column(Integer, nullable=True)
    is_loop = Column(Boolean, default=False)

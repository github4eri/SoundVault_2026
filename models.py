from sqlalchemy import Column, Integer, String, Boolean, Text
from database import Base

class Sound(Base):
    __tablename__ = "sounds"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    file_path = Column(String)  # Where the file is stored
    duration = Column(String)   # e.g., "02:45"
    
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

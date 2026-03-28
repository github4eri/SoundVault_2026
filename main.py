import os
from fastapi import FastAPI, UploadFile, File, Depends, Request, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, database, audio_processor
import json

# 1. Initialize the App
app = FastAPI()
models.Base.metadata.create_all(bind=database.engine)

# 2. Setup Folders
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# 3. ROUTES
@app.get("/")
async def home(request: Request, db: Session = Depends(database.get_db)):
    sounds = db.query(models.Sound).all()
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"sounds": sounds}
    )

@app.post("/upload")
async def upload_sound(
    request: Request,
    file: UploadFile = File(...),
    is_free: bool = Form(True),
    db: Session = Depends(database.get_db)
):
    # Save file locally
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 🧠 The Magic: AI Analysis
    ai_data_json = await audio_processor.analyze_audio_with_gemini(file_path)
    ai_data = json.loads(ai_data_json)
    
    # 🎹 Get Technical Metadata
    duration = audio_processor.get_audio_duration(file_path)

    # 💾 Save to Database
    instruments_raw = ai_data.get("instruments", "")
    if isinstance(instruments_raw, list):
        instruments_str = ", ".join(instruments_raw)
    else:
        instruments_str = str(instruments_raw)

    # For tags: convert ['nature', 'morning'] -> "nature, morning"
    tags_raw = ai_data.get("tags", "")
    if isinstance(tags_raw, list):
        tags_str = ", ".join(tags_raw)
    else:
        tags_str = str(tags_raw)

    new_sound = models.Sound(
        title=ai_data.get("title", file.filename),
        file_path=file_path,
        duration=duration,
        is_royalty_free=is_free,
        ai_mood=ai_data.get("mood"),
        ai_instruments=instruments_str, # Now a safe string!
        ai_description=ai_data.get("description"),
        ai_tags=tags_str # Now a safe string!
    )
    db.add(new_sound)
    db.commit()

    # This kicks the user back to the home page to see their new sound!
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/delete/{sound_id}")
async def delete_sound(sound_id: int, db: Session = Depends(database.get_db)):
    # 1. Find the sound in the database
    sound = db.query(models.Sound).filter(models.Sound.id == sound_id).first()
    
    if sound:
        # 2. Delete the actual file from the 'uploads' folder
        if os.path.exists(sound.file_path):
            os.remove(sound.file_path)
        
        # 3. Remove the record from the database
        db.delete(sound)
        db.commit()
        
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
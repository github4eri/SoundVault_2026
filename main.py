import os
from fastapi import FastAPI, UploadFile, File, Depends, Request, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, database, audio_processor
import json
from sqlalchemy import or_ # This allows to search "Title OR Genre OR Country"

# 🌎 THE BILINGUAL MAP
TRANSLATIONS = {
    "en": {
        "title": "SoundVault",
        "search": "🔍 Search",
        "search_placeholder": "Search keywords...",
        "filter_origin": "Origin",
        "ai_gen": "🤖 AI Synthesized",
        "nature_made": "🌿 Nature Made",
        "human_made": "👤 Human Made",
        "audio_type": "🎧 Audio Type",
        "instrumental": "🎸 Instrumental",
        "vocals": "🎤 Vocals Present",
        "artifacts_found": "Artifacts Found",
        "artifact_singular": "Artifact Found",
        "apply_btn": "Apply Filters",
        "clear_link": "CLEAR ALL",
        "upload_btn": "Upload New Sound",
    },
    "jp": {
        "title": "サウンド・ボルト",
        "search": "🔍 検索",
        "search_placeholder": "キーワードで検索...",
        "filter_origin": "起源",
        "ai_gen": "🤖 AI生成",
        "nature_made": "🌿 自然音",
        "human_made": "👤 ヒューマンメイド",
        "audio_type": "🎧 オーディオタイプ",
        "instrumental": "🎸 楽器音",
        "vocals": "🎤 ボーカルあり",
        "artifacts_found": "個の素材が見つかりました",
        "artifact_singular": "個の素材が見つかりました",
        "apply_btn": "フィルターを適用",
        "clear_link": "すべてクリア",
        "upload_btn": "素材をアップロード",
    }
}

# 1. Initialize the App
app = FastAPI()
models.Base.metadata.create_all(bind=database.engine)

# 2. Setup Folders
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# 3. ROUTES
@app.get("/")
async def home(
    request: Request, 
    q: str = None, 
    lang: str = "en", # <--- Default language is English
    ai_only: bool = False, 
    human_only: bool = False,
    nature_only: bool = False,
    instrumental: bool = False,
    vocals: bool = False,
    db: Session = Depends(database.get_db)
):
    query_obj = db.query(models.Sound)

    # 1. Text Search
    if q:
        search_term = f"%{q}%"
        query_obj = query_obj.filter(
            or_(
                models.Sound.title.ilike(search_term),
                models.Sound.ai_mood.ilike(search_term),
                models.Sound.music_genre.ilike(search_term),
                models.Sound.origin_country.ilike(search_term)
            )
        )

    # 2. AI vs Human Filter
    if ai_only:
        query_obj = query_obj.filter(models.Sound.is_ai_generated == True)
    
    if nature_only:
        query_obj = query_obj.filter(
            models.Sound.is_ai_generated == False, 
            models.Sound.is_environmental == True
        )
        
    if human_only:
        query_obj = query_obj.filter(
            models.Sound.is_ai_generated == False, 
            models.Sound.is_environmental == False
        )

    # 3. Vocals vs Instrumental Filter
    if instrumental:
        query_obj = query_obj.filter(models.Sound.has_vocals == False)
    if vocals:
        query_obj = query_obj.filter(models.Sound.has_vocals == True)

    sounds = query_obj.all()
    
    # 🎨 Selection Logic: Pick the correct dictionary labels
    labels = TRANSLATIONS.get(lang, TRANSLATIONS["en"])

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "sounds": sounds, 
            "query": q,
            "labels": labels,        # <--- Pass the labels to the HTML
            "current_lang": lang,    # <--- So the buttons know which is active
            "ai_only": ai_only,
            "human_only": human_only,
            "nature_only": nature_only,
            "instrumental": instrumental,
            "vocals": vocals,
            "is_filtering_origin": any([ai_only, nature_only, human_only])
        }
    )

# 🤫 THE LOG SILENCER: Add this near your other routes
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def silence_chrome_ghost():
    return {"status": "Not using automatic workspaces"}

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

    # 💾 Save to Database
    new_sound = models.Sound(
        title=ai_data.get("title", file.filename),
        file_path=file_path,
        duration=duration,
        is_royalty_free=is_free,
        
        # New Fields
        tempo_rhythm=ai_data.get("tempo_rhythm"),
        is_orchestrated=ai_data.get("is_orchestrated"),
        main_instrument=ai_data.get("main_instrument"),
        has_vocals=ai_data.get("has_vocals"),

        acoustic_type=ai_data.get("acoustic_type"),
        is_environmental=ai_data.get("is_environmental"),
        music_genre=ai_data.get("music_genre"),
        origin_country=ai_data.get("origin_country"),
        is_ai_generated=ai_data.get("is_ai_generated"),
        # Original Fields
        ai_mood=ai_data.get("mood"),
        ai_instruments=", ".join(ai_data.get("instruments", [])),
        ai_description=ai_data.get("description"),
        ai_tags=", ".join(ai_data.get("tags", []))
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
    
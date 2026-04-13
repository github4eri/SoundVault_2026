import os
from fastapi import FastAPI, UploadFile, File, Depends, Request, Form, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, database, audio_processor
import json
from sqlalchemy import or_ # This allows to search "Title OR Genre OR Country"
from starlette.middleware.sessions import SessionMiddleware
import boto3


# Connect to AWS S3 using your environment variables
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

# 🌎 THE BILINGUAL MAP
TRANSLATIONS = {
    "en": {
        "title": "SoundVault",
        "search": "🔍 Search",
        "search_placeholder": "Search keywords...",
        "filter_origin": "Filter",
        "ai_gen": "🤖 AI Made",
        "nature_made": "🌿 Nature Sound",
        "human_made": "🎶Sound",
        "audio_type": "🎧 Audio Type",
        "instrumental": "🎸 Instrumental",
        "vocals": "🎤 Vocals Present",
        "artifacts_found": "SoundArtifacts Found",
        "artifact_singular": "Artifact Found",
        "apply_btn": "Apply Filters",
        "clear_link": "Clear All",
        "upload_btn": "Upload New Sound",
        "apply_filters": "Apply Filters",
        "clear_all": "Clear All",
        "library_title": "Sound Library",
        "collection_title": "Your Collection",
        "select_artifact": "Select Audio File",
        "upload_btn": "Deposit Sound",
        "sound_library": "Sound Library",
        "modal_title": "Upload Section",
        # Dropdown options
        "origin_label": "Sound",
        "origin_ai": "AI Generated Sound",
        "origin_nature": "Nature Sound",
        "origin_human": "Sound",
        "choose_category": "-- Select Category --",
        "copyright_label": "Copyright Status",
        "copyright_free": "Royalty Free / Cleared",
        "copyright_protected": "Copyright Protected",
        "choose_copyright": "-- Select Status --",
        "filter_all": "All"
        },
    "jp": {
        "apply_filters": "フィルターを適用",
        "clear_all": "すべてクリア",
        "library_title": "サウンドライブラリ",
        "collection_title": "あなたのコレクション",
        "select_artifact": "サウンドを選択",
        "upload_btn": "サウンドをアップロード",
        "sound_library": "サウンドライブラリー",
        "title": "サウンド・ボルト",
        "search": "🔍 検索",
        "search_placeholder": "キーワードで検索...",
        "filter_origin": "フィルター",
        "ai_gen": "🤖 AI生成",
        "nature_made": "🌿 自然音",
        "human_made": "🎶音源",
        "audio_type": "🎧 オーディオタイプ",
        "instrumental": "🎸 楽器音",
        "vocals": "🎤 ボーカルあり",
        "artifacts_found": "個の素材が見つかりました",
        "artifact_singular": "個の素材が見つかりました",
        "apply_btn": "フィルターを適用",
        "clear_link": "すべてクリア",
        "upload_btn": "アップロード",
        "modal_title": "アップロードセクション",
        # Dropdown options
        "origin_label": "音源",
        "origin_ai": "AI生成音",
        "origin_nature": "自然音",
        "origin_human": "音源",
        "choose_category": "-- カテゴリーを選択 --",
        "copyright_label": "著作権",
        "copyright_free": "ロイヤリティフリー / クリア済",
        "copyright_protected": "著作権保護あり",
        "choose_copyright": "-- ステータスを選択 --",
        "filter_all": "全て"
    }
}

# 1. Initialize the App
app = FastAPI()
models.Base.metadata.create_all(bind=database.engine)

# This is the engine that handles login cookies!
app.add_middleware(SessionMiddleware, secret_key="PutSomeRandomLongStringHereForSecurity")

# Ensure the uploads directory exists before mounting
os.makedirs("uploads", exist_ok=True)

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
    copyright_all: bool = False,
    copyright_free: bool = False,
    copyright_protected: bool = False,
    db: Session = Depends(database.get_db)
    
):
    query_obj = db.query(models.Sound)

# 🕵️ Check if the visitor has the Master Key!
    is_admin = request.session.get("is_admin", False)

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

    # 4. Copyright Filter
    if copyright_free and not copyright_protected:
        query_obj = query_obj.filter(models.Sound.is_royalty_free == True)
    elif copyright_protected and not copyright_free:
        query_obj = query_obj.filter(models.Sound.is_royalty_free == False)

    # THE FETCH COMMAND (Must be at the very bottom of all filters!)
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
            "copyright_all": copyright_all,
            "copyright_free": copyright_free,
            "copyright_protected": copyright_protected,
            "is_filtering_origin": any([ai_only, nature_only, human_only]),
            "is_admin": is_admin
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
    title: str = Form(...),      # <--- Your new catcher's glove!
    origin: str = Form(...),     # Catches the Origin dropdown
    copyright: str = Form(...),
    db: Session = Depends(database.get_db)
):

    # 🛑 THE INVISIBLE VAULT DOOR
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/", status_code=303)

    # 1. Save file locally FIRST so Gemini can listen to it
    safe_filename = file.filename.replace(" ", "_") # Clean name for URLs
    local_file_path = f"uploads/{safe_filename}"
    with open(local_file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 🧠 2. The Magic: AI Analysis (Using the local file)
    ai_data_json = await audio_processor.analyze_audio_with_gemini(local_file_path)
    ai_data = json.loads(ai_data_json)
    
    # 🎹 3. Get Technical Metadata (Using the local file)
    duration = audio_processor.get_audio_duration(local_file_path)

    # ☁️ 4. NEW: Upload to AWS S3!
    s3_client.upload_file(
        local_file_path,
        AWS_BUCKET_NAME,
        safe_filename,
        ExtraArgs={"ContentType": file.content_type}
    )
    
    # Create the public Amazon URL
    s3_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{safe_filename}"
    
    # 🧹 5. NEW: Delete the temporary local file (Keep the server clean!)
    os.remove(local_file_path)

    # 💾 Formatting for Database
    instruments_raw = ai_data.get("instruments", "")
    if isinstance(instruments_raw, list):
        instruments_str = ", ".join(instruments_raw)
    else:
        instruments_str = str(instruments_raw)

    tags_raw = ai_data.get("tags", "")
    if isinstance(tags_raw, list):
        tags_str = ", ".join(tags_raw)
    else:
        tags_str = str(tags_raw)

    # Convert HTML dropdowns to Database booleans
    user_is_free = (copyright == "free")
    user_is_ai = (origin == "ai")
    user_is_nature = (origin == "nature")

    # 💾 6. Save to Database (USING THE NEW S3 URL!)
    new_sound = models.Sound(
        title=title,    # <--- Now it uses the text you typed in the modal!
        file_path=s3_url,   # 👈 CHANGED THIS: Now saves the Amazon link!
        duration=duration,
        is_royalty_free=user_is_free,

        # New Fields
        tempo_rhythm=ai_data.get("tempo_rhythm"),
        is_orchestrated=ai_data.get("is_orchestrated"),
        main_instrument=ai_data.get("main_instrument"),
        has_vocals=ai_data.get("has_vocals"),

        acoustic_type=ai_data.get("acoustic_type"),
        is_environmental=user_is_nature,
        music_genre=ai_data.get("music_genre"),
        origin_country=ai_data.get("origin_country"),
        is_ai_generated=user_is_ai,

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
async def delete_sound(request: Request, sound_id: int, db: Session = Depends(database.get_db)):
    
    # 1. Find the sound in the database
    sound = db.query(models.Sound).filter(models.Sound.id == sound_id).first()
    
    # 🛑 THE INVISIBLE VAULT DOOR
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/", status_code=303)
    
    if sound:
        # 2. Delete the actual file from the 'uploads' folder
        if os.path.exists(sound.file_path):
            os.remove(sound.file_path)
        
        # 3. Remove the record from the database
        db.delete(sound)
        db.commit()
        
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login")
async def login_page(request: Request):
    # If already logged in, redirect to home
    if request.session.get("is_admin"):
        return RedirectResponse(url="/", status_code=303)
        
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"error": None}
    )

@app.post("/login")
async def process_login(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...)
):
    # 1. Grab the real credentials from the .env file
    env_user = os.getenv("ADMIN_USERNAME", "admin")
    env_pass = os.getenv("ADMIN_PASSWORD", "changeme")

    # 2. Check if what the user typed matches the .env file
    if username == env_user and password == env_pass:
        # Success! Give them the master key (cookie)
        request.session["is_admin"] = True
        return RedirectResponse(url="/", status_code=303)
    
    # 3. Failed login! Send them back with an error message
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"error": "Invalid username or password."}
    )

@app.get("/logout")
async def logout(request: Request):
    # Destroy the master key
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


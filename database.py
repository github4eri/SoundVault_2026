import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Grab the cloud URL from your .env file
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Create the engine (SQLite specific arguments are removed!)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# The Database session generator
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()    
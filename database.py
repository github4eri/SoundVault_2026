from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Name the database file
SQLALCHEMY_DATABASE_URL = "sqlite:///./soundvault.db"

# 2. Create the "Engine" (The motor that drives the data)
# 'check_same_thread' is only needed for SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Create a Session Factory (The phone line to the DB)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. The Base class (What our models in models.py will inherit from)
Base = declarative_base()

# 5. Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
       
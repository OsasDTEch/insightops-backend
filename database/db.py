from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
load_dotenv()
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
DATABASE_URL=os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

SessionLocal=sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db

    finally:
        db.close()
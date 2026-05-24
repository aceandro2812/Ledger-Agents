import os
import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Local SQLite DB path in the project workspace root
DATABASE_URL = "sqlite:///forensic_audit.db"

Base = declarative_base()

class AuditRecord(Base):
    __tablename__ = 'audits'
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="queued") # queued, running, completed, failed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    results_json = Column(Text, nullable=True)       # Full final state JSON
    extra_files_json = Column(Text, nullable=True)   # JSON list of {file_path, ledger_type}

# Create SQLite engine and session factory
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

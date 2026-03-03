import os
import sys
import redis
from sqlalchemy import create_engine, Column, Integer, String, text, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from dotenv import load_dotenv
load_dotenv()

DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
VT_API_KEY = os.getenv("VT_API_KEY")

if not (DB_USERNAME and DB_PASSWORD and DB_HOST and DB_PORT and DB_NAME and VT_API_KEY):
    sys.exit(".env file missing or fields missing. Refer .env.example for creating proper .env file")

DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
Base = declarative_base()

# reports - table
class Report(Base):
    __tablename__ = "reports"
    identifier = Column(String, primary_key=True)
    identifier_type = Column(Integer, default=1)
    data = Column(JSON)
    

# reports - table utility methods
class Reports:
    def upsert(self, report: Report, session: Session):
        session.merge(report)
        session.commit()
        return {"added":True, "report":report}
    def get(self, identifier: str, identifier_type: int, session):
        report: Report = session.query(Report).filter(Report.identifier == identifier).filter(Report.identifier_type == identifier_type).first()
        if not report:
            return {"error": "Not found"}
        return report.data


class Database:
    def __init__(self):
        # Postgresql
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        # Redis
        self._redis = redis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True
        )
    def get_db(self):
        db_session = self.Session()
        try:
            yield db_session
        finally:
            db_session.close()

db = Database()
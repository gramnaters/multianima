# Database for slug-to-IMDB mapping (same as original)
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime, timedelta
from config import Config

Base = declarative_base()

class Mapping(Base):
    __tablename__ = 'mappings'
    slug = Column(String, primary_key=True)
    tmdb_id = Column(String)
    imdb_id = Column(String, index=True)
    provider = Column(String, default='')

class FailedMapping(Base):
    __tablename__ = 'failed_mappings'
    imdb_id = Column(String, primary_key=True)
    checked_at = Column(DateTime, default=datetime.utcnow)

class Database:
    def __init__(self):
        if Config.DB_TYPE == 'postgresql':
            engine = create_engine(Config.DATABASE_URL, pool_size=3, max_overflow=5, pool_pre_ping=True, pool_recycle=1800, connect_args={'sslmode': 'require'})
        else:
            engine = create_engine(f'sqlite:///{Config.DB_PATH}', pool_size=3, max_overflow=5)
        Base.metadata.create_all(engine)
        self.Session = scoped_session(sessionmaker(bind=engine))

    def get_mapping(self, slug: str) -> tuple:
        session = self.Session()
        try:
            m = session.query(Mapping).filter_by(slug=slug).first()
            return (m.tmdb_id, m.imdb_id, m.provider) if m else None
        finally: session.close()

    def get_slug_by_imdb(self, imdb_id: str) -> tuple:
        session = self.Session()
        try:
            m = session.query(Mapping).filter_by(imdb_id=imdb_id).first()
            return (m.slug, m.provider) if m else None
        finally: session.close()

    def set_mapping(self, slug: str, tmdb_id: str, imdb_id: str, provider: str = ''):
        session = self.Session()
        try:
            m = session.query(Mapping).filter_by(slug=slug).first()
            if m:
                m.tmdb_id, m.imdb_id, m.provider = tmdb_id, imdb_id, provider
            else:
                session.add(Mapping(slug=slug, tmdb_id=tmdb_id, imdb_id=imdb_id, provider=provider))
            session.commit()
        finally: session.close()

    def is_failed(self, imdb_id: str, ttl_days: int = 30) -> bool:
        session = self.Session()
        try:
            f = session.query(FailedMapping).filter_by(imdb_id=imdb_id).first()
            if not f: return False
            if datetime.utcnow() - f.checked_at > timedelta(days=ttl_days):
                session.delete(f); session.commit()
                return False
            return True
        finally: session.close()

    def add_failed(self, imdb_id: str):
        session = self.Session()
        try:
            f = session.query(FailedMapping).filter_by(imdb_id=imdb_id).first()
            if f: f.checked_at = datetime.utcnow()
            else: session.add(FailedMapping(imdb_id=imdb_id))
            session.commit()
        finally: session.close()

db = Database()

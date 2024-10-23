from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Указываем путь к базе данных (локальная SQLite)
DATABASE_URL = "sqlite:///./test.db"  # Пример URL для базы данных

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Функция для инициализации базы данных
def init_db():
    Base.metadata.create_all(bind=engine)

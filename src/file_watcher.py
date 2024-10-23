import logging
import os
import time

from sqlalchemy.orm import Session
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from src.crud import create_file_record
from src.models import File
from src.schemas import FileCreate


import datetime


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.root_dir = "src/files"  # Указываем корневую директорию для хранения файлов

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            relative_file_path = os.path.relpath(file_path, self.root_dir)  # Приводим путь к относительному
            file_name = os.path.basename(file_path)
            file_base_name, file_extension = os.path.splitext(file_name)
            file_size = os.path.getsize(file_path)

            time.sleep(1)
            # Проверка на существование файла в базе данных
            existing_file = self.db_session.query(File).filter(File.name == file_base_name,
                                                               File.extension == file_extension).first()
            if existing_file:
                logging.info(f"Файл {file_base_name} уже существует в базе данных.")
                return

            # Если файла нет в БД, создаем новую запись
            new_file = FileCreate(
                name=file_base_name,
                extension=file_extension,
                size=file_size,
                path=f"src/files/{file_name}",  # Здесь добавляем корректный путь
                created_at=datetime.datetime.utcnow()  # Время создания
            )
            create_file_record(self.db_session, new_file)
            logging.info(f"Файл {file_base_name} добавлен в базу данных с расширением {file_extension}.")




def start_watching(directory, db_session):
    event_handler = FileEventHandler(db_session)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    observer.start()
    print(f"Monitoring directory: {directory}")

    try:
        while True:
            pass  # Оставляем наблюдатель активным
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

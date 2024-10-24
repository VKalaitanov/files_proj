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
    """
    Обработчик событий для файловой системы, который реагирует на события создания новых файлов
    и добавляет их в базу данных.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.root_dir = "src/files"

    def on_created(self, event):
        """
        Метод, вызываемый при создании файла в отслеживаемой директории.
        """
        if not event.is_directory:
            file_path = event.src_path
            relative_file_path = os.path.relpath(file_path, self.root_dir)
            file_name = os.path.basename(file_path)
            file_base_name, file_extension = os.path.splitext(file_name)
            file_size = os.path.getsize(file_path)

            time.sleep(1)  # Даем системе время на завершение копирования файла

            # Проверка на существование файла в базе данных
            existing_file = self.db_session.query(File).filter(
                File.name == file_base_name,
                File.extension == file_extension
            ).first()

            if existing_file:  # Если файл уже есть в базе данных, выходим
                logging.info(f"Файл {file_base_name} уже существует в базе данных.")
                return

            # Если файла нет в базе данных, создаем новую запись
            new_file = FileCreate(
                name=file_base_name,
                extension=file_extension,
                size=file_size,
                path=f"src/files/{file_name}",
                created_at=datetime.datetime.utcnow()
            )

            # Сохраняем новую запись файла в базе данных
            create_file_record(self.db_session, new_file)
            logging.info(f"Файл {file_base_name} добавлен в базу данных с расширением {file_extension}.")


def start_watching(directory, db_session):
    """
    Функция для запуска наблюдателя за изменениями в директории.
    """
    event_handler = FileEventHandler(db_session)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    observer.start()
    logging.info(f"Мониторинг директории: {directory}")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()

    observer.join() 

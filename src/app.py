import datetime
import logging
import os
from threading import Thread
from typing import List

import aiofiles
from fastapi import Depends, UploadFile, HTTPException
from fastapi import FastAPI
from fastapi import File as F
from fastapi import Response
from sqlalchemy.orm import Session

from src.crud import get_files, create_file, update_file, delete_file, download_file
from src.database import SessionLocal, init_db
from src.file_watcher import start_watching
from src.models import File
from src.schemas import FileCreate, FileUpdate, FileResponse

# Инициализация базы данных
init_db()

app = FastAPI()

# Настройка логирования
logging.basicConfig(level=logging.INFO)


# Зависимость для работы с базой данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Фоновая задача для наблюдения за директорией
def start_file_monitoring():
    directory_to_watch = "src/files"
    db_session = SessionLocal()

    # Запускаем мониторинг с помощью watchdog
    start_watching(directory_to_watch, db_session)


# Фоновая задача для запуска мониторинга
@app.on_event("startup")
def startup_event():
    observer_thread = Thread(target=start_file_monitoring, daemon=True)
    observer_thread.start()
    logging.info("Мониторинг директории запущен.")


@app.get("/files/", response_model=List[FileResponse])
def list_files(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Получить список файлов с возможностью пагинации.
    """
    return get_files(db, skip=skip, limit=limit)


@app.get("/file/{file_name}", response_model=FileResponse)
def get_file_by_name(file_name: str, db: Session = Depends(get_db)):
    """
    Получить файл по имени.
    """
    db_file = db.query(File).filter(File.name == file_name).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    return db_file


@app.post("/upload/", response_model=FileResponse)
async def upload_file(uploaded_file: UploadFile = F(...), comment: str = None, db: Session = Depends(get_db)):
    """
    Загрузить новый файл. Запрещено загружать файл с уже существующим именем.
    """
    try:
        # Получаем имя файла и расширение
        file_base_name, file_extension = os.path.splitext(uploaded_file.filename)
        directory = "src/files"  # Директория для хранения файлов
        file_location = os.path.join(directory, uploaded_file.filename)

        # Проверка на существование файла с таким именем в базе данных
        existing_file = db.query(File).filter(File.name == file_base_name).first()
        if existing_file:
            raise HTTPException(status_code=400, detail="Файл с таким именем уже существует.")

        os.makedirs(directory, exist_ok=True)

        # Сохраняем файл на диск
        async with aiofiles.open(file_location, "wb") as f:
            await f.write(await uploaded_file.read())

        # Создаем запись о файле в базе данных
        file_data = FileCreate(
            name=file_base_name,
            extension=file_extension,
            size=uploaded_file.size,
            path=directory,  # Сохраняем только директорию
            comment=comment,
            created_at=datetime.datetime.utcnow()
        )
        file_record = create_file(db, file_data, file_path=file_location)
        logging.info(f"Файл '{file_record.name}{file_record.extension}' загружен и сохранен в базе данных.")
        return file_record

    except HTTPException as http_ex:
        raise http_ex

    except Exception as e:
        logging.error(f"Ошибка при загрузке файла: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")


@app.put("/file/{file_name}", response_model=FileResponse)
def update_file_by_name(file_name: str, file_update: FileUpdate, db: Session = Depends(get_db)):
    """
    Обновить информацию о файле. Запрещено изменять имя файла на уже существующее.
    """
    db_file = db.query(File).filter(File.name == file_name).first()

    if db_file is None:
        raise HTTPException(status_code=404, detail="Файл не найден")

    # Проверка на наличие файла с таким именем в базе данных (кроме самого обновляемого файла)
    if file_update.name and file_update.name != db_file.name:
        existing_file = db.query(File).filter(File.name == file_update.name).first()
        if existing_file:
            raise HTTPException(status_code=400, detail="Файл с таким именем уже существует.")

    updated_file = update_file(db, db_file, file_update)  # Передаем обновленные данные файла
    logging.info(f"Файл '{db_file.name}' обновлён.")
    return updated_file


@app.delete("/file/{file_name}", response_model=dict)
def delete_file_by_name(file_name: str, db: Session = Depends(get_db)):
    """
    Удалить файл по имени.
    """
    db_file = db.query(File).filter(File.name == file_name).first()

    if db_file:
        # Формируем полный путь к файлу
        file_path = os.path.join(db_file.path)

        # Логируем полный путь к файлу
        logging.info(f"Попытка удалить файл по пути: {file_path}")

        # Проверяем существование файла на диске
        if os.path.exists(file_path):
            try:
                os.remove(file_path)  # Удаляем файл с диска
                logging.info(f"Файл {file_path} успешно удалён.")
            except Exception as e:
                logging.error(f"Ошибка при удалении файла {file_path}: {e}")
                raise HTTPException(status_code=500, detail="Ошибка при удалении файла с диска.")
        else:
            logging.warning(f"Файл {file_path} не найден на диске. Удаление записи из базы данных продолжается.")

        # Удаление записи из базы данных
        delete_file(db, db_file.id)
        logging.info(f"Запись о файле '{file_name}' была удалена из базы данных.")
        return {"message": f"Файл '{file_name}' был успешно удалён"}

    # Если файл не найден в базе данных
    raise HTTPException(status_code=404, detail="Файл не найден")


@app.get("/search/", response_model=List[FileResponse])
def search_files(directory: str, db: Session = Depends(get_db)):
    """
    Поиск файлов в базе данных по указанной директории.
    """
    found_files = db.query(File).filter(File.path.like(f"%{directory}%")).all()

    if not found_files:
        raise HTTPException(status_code=404, detail="Файлы в указанной директории не найдены")

    logging.info(f"Найдено {len(found_files)} файлов в директории '{directory}'.")
    return found_files


@app.get("/download/{file_name}", response_class=Response)
def download_file_endpoint(file_name: str, db: Session = Depends(get_db)):
    """
    Скачивание файла по имени.
    """
    return download_file(db, file_name)

import logging
import os
from datetime import datetime
from typing import List

from fastapi import HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.models import File
from src.schemas import FileCreate, FileUpdate


def create_file_record(db_session: Session, file_data: FileCreate) -> File:
    """Создаёт запись о файле в базе данных."""
    db_file = File(
        name=file_data.name,
        extension=file_data.extension,
        size=file_data.size,
        path=file_data.path
    )
    db_session.add(db_file)
    db_session.commit()
    db_session.refresh(db_file)
    return db_file


def get_file(db: Session, file_name: str) -> File:
    """Получает файл из базы данных по имени."""
    db_file = db.query(File).filter(File.name == file_name).first()

    if db_file:
        # Проверяем существование файла на диске
        if not os.path.exists(db_file.path):
            # Если файл отсутствует, удаляем запись из БД
            db.delete(db_file)
            db.commit()
            logging.info(f"Файл {file_name} был удалён из базы данных, так как его не существует на диске.")
            raise HTTPException(status_code=404, detail="Файл не найден на диске, запись удалена из базы данных")

    if not db_file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    return db_file


def get_files(db: Session, skip: int = 0, limit: int = 10) -> List[File]:
    """Получает список файлов с возможностью пагинации."""
    files = db.query(File).offset(skip).limit(limit).all()

    # Проверка всех файлов на наличие на диске
    for file in files:
        if not os.path.exists(file.path):
            # Если файла нет, удаляем запись из БД
            db.delete(file)
            db.commit()
            logging.info(f"Файл с ID {file.id} был удалён из базы данных, так как его не существует на диске.")

    return files


def create_file(db: Session, file: FileCreate, file_path: str) -> File:
    """Создание файла в базе данных с использованием транзакции."""
    db_file = File(
        name=file.name,
        extension=file.extension,
        size=file.size,
        path=file_path,
        comment=file.comment,
        created_at=datetime.utcnow(),
    )
    try:
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Ошибка при создании записи о файле в базе данных: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при сохранении информации о файле в базе данных")


def update_file(db: Session, db_file: File, file_update: FileUpdate) -> File:
    """Обновляет информацию о файле в базе данных и на диске."""
    old_path = db_file.path  # Сохраняем старый путь для перемещения файла

    # Если нужно изменить имя файла
    if file_update.name:
        # Обрабатываем новое имя файла
        new_name = file_update.name
        if new_name.endswith(db_file.extension):
            new_name = new_name[:-(len(db_file.extension))]  # Убираем расширение из имени

        # Если нужно изменить директорию файла
        new_path = handle_file_path_change(file_update.path, new_name, db_file.extension, old_path)

        # Переименовываем и перемещаем файл на уровне файловой системы
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

        # Обновляем путь и имя в базе данных
        db_file.name = new_name  # Имя без расширения
        db_file.path = new_path  # Новый путь

    # Если только директория была изменена (без изменения имени)
    elif file_update.path and not file_update.name:
        new_path = handle_file_path_change(file_update.path, db_file.name, db_file.extension, old_path)

        # Перемещаем файл
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

        # Обновляем путь в базе данных
        db_file.path = new_path

    # Обновляем комментарий, если предоставлен
    if file_update.comment:
        db_file.comment = file_update.comment

    db_file.updated_at = datetime.utcnow()  # Обновляем дату изменения
    db.commit()
    db.refresh(db_file)

    return db_file


def handle_file_path_change(new_dir: str, file_name: str, extension: str, old_path: str) -> str:
    """Обрабатывает изменение пути и имени файла."""
    if new_dir:
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)  # Создаём директорию, если она не существует
        return os.path.join(new_dir, file_name + extension)  # Возвращаем новый путь
    else:
        # Если директория не изменена, сохраняем в текущей директории
        return os.path.join(os.path.dirname(old_path), file_name + extension)


def delete_file(db: Session, file_name: str) -> dict:
    """Удаляет файл и запись о нём из базы данных."""
    deleted_file = db.query(File).filter(File.name == file_name).first()

    if not deleted_file:
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_path = deleted_file.path  # Получаем путь к файлу

    # Логируем попытку удаления
    logging.info(f"Попытка удаления файла по пути: {file_path}")

    # Удаляем файл с диска, если он существует
    if os.path.exists(file_path):
        try:
            os.remove(file_path)  # Удаляем файл
            logging.info(f"Файл {file_path} успешно удалён")
        except (PermissionError, OSError) as e:
            logging.error(f"Ошибка при удалении файла: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка при удалении файла: {e}")

    # Удаляем информацию о файле из базы данных
    db.delete(deleted_file)
    db.commit()
    logging.info(f"Запись о файле {file_name} удалена из базы данных")

    return {"message": f"Файл {file_name} был успешно удалён"}


def download_file(db: Session, file_name: str) -> Response:
    """Скачивает файл из базы данных по имени."""
    db_file = db.query(File).filter(File.name == file_name).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="Файл не найден в базе данных.")

    file_path = db_file.path  # Получаем полный путь к файлу

    # Проверяем существование файла на диске
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден на диске.")

    # Открываем файл для чтения в бинарном режиме
    with open(file_path, 'rb') as file:
        content = file.read()

    # Возвращаем файл в качестве ответа
    return Response(
        content=content,  # Указываем content как именованный параметр
        media_type='application/octet-stream',
        headers={
            "Content-Disposition": f"attachment; filename={db_file.name}{db_file.extension}"
        }
    )


def find_files_in_directory(directory: str) -> List[dict]:
    """Находит все файлы в заданной директории и возвращает информацию о них."""
    found_files = []
    for root, _, files in os.walk(directory):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            found_files.append({
                'name': file_name,
                'path': file_path,
                'extension': os.path.splitext(file_name)[1],
                'size': os.path.getsize(file_path),
                'created_at': datetime.fromtimestamp(os.path.getctime(file_path)),
                'updated_at': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    return found_files

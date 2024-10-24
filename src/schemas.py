import os

from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class FileBase(BaseModel):
    name: str
    extension: str
    size: int
    path: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    comment: Optional[str] = None


class FileCreate(BaseModel):
    name: str
    extension: str
    size: int
    path: str
    comment: Optional[str] = None


class FileUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    comment: Optional[str] = None


class FileResponse(FileBase):
    class Config:
        orm_mode = True

    @validator('path', pre=True, always=True)
    def remove_filename_from_path(cls, v, values):
        # Удаляем имя файла из пути
        return os.path.dirname(v)

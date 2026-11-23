from pydantic import BaseModel, ConfigDict
from typing import Optional


class SongDownloadSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    progress: int = 0
    title: str = ""
    duration: float = 0.0
    filesize: int = 0
    link: Optional[str] = None

from pydantic import BaseModel, ConfigDict
from typing import Optional


class SongDetailVideoDetailsSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    author: str = ""
    videoId: str = ""


class SongDetailSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    videoDetails: Optional[SongDetailVideoDetailsSchema] = None

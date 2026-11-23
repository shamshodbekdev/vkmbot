from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ShazamImagesSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    background: Optional[str] = None
    coverart: Optional[str] = None
    coverarthq: Optional[str] = None


class ShazamGenresSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    primary: Optional[str] = None


class ShazamShareSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subject: Optional[str] = None


class ShazamTrackSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    url: Optional[str] = None
    images: Optional[ShazamImagesSchema] = None
    genres: Optional[ShazamGenresSchema] = None
    share: Optional[ShazamShareSchema] = None


class ShazamMatchSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: Optional[str] = None
    offset: Optional[float] = None


class ShazamSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    matches: List[ShazamMatchSchema] = []
    track: Optional[ShazamTrackSchema] = None

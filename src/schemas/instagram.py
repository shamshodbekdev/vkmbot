from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class InstagramMediaItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    url: str
    thumbnail: Optional[str] = None


class InstagramResponseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    medias: List[InstagramMediaItemSchema] = []

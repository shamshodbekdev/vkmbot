from pydantic import BaseModel, ConfigDict
from typing import List


class MoodItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    params: str = ""


class MoodPlaylistItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    playlistId: str = ""
    description: str = ""

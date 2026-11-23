from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TranscriptionWordSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    word: str
    start: float
    end: float


class TranscriptionSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    task: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    words: Optional[List[TranscriptionWordSchema]] = None

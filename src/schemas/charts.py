from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ChartsCountrySelectedSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    text: str = ""


class ChartsCountriesSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    selected: Optional[ChartsCountrySelectedSchema] = None
    options: List[str] = []


class ChartsVideoSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    playlistId: str = ""


class ChartsArtistSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    browseId: str = ""
    subscribers: str = ""
    rank: str = ""
    trend: str = ""


class ChartsGenreSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = ""
    playlistId: str = ""


class ChartsSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    countries: Optional[ChartsCountriesSchema] = None
    videos: List[ChartsVideoSchema] = []
    artists: List[ChartsArtistSchema] = []
    genres: List[ChartsGenreSchema] = []

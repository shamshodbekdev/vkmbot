from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class PlaylistAuthorSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    id: Optional[str] = None


class PlaylistArtistSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    id: Optional[str] = None


class PlaylistAlbumSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = ""
    id: Optional[str] = None


class PlaylistTrackSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    videoId: str = ""
    title: str = ""
    duration: str = ""
    duration_seconds: int = 0
    isAvailable: bool = True
    isExplicit: bool = False
    artists: List[PlaylistArtistSchema] = []
    album: Optional[PlaylistAlbumSchema] = None


class PlaylistSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = ""
    title: str = "Playlist"
    privacy: str = ""
    description: str = ""
    year: str = ""
    duration: str = ""
    duration_seconds: int = 0
    trackCount: int = 0
    author: Optional[PlaylistAuthorSchema] = None
    tracks: List[PlaylistTrackSchema] = []

from .statistics import StatisticsReportSchema
from .analytics import AnalyticsReportSchema
from .health import HealthSchema
from .youtube_search import SongAlbumSchema, SongArtistSchema, SongThumbnailSchema, SongSchema
from .song_detail import SongDetailVideoDetailsSchema, SongDetailSchema
from .youtube_download import SongDownloadSchema
from .charts import (
    ChartsCountrySelectedSchema,
    ChartsCountriesSchema,
    ChartsVideoSchema,
    ChartsArtistSchema,
    ChartsGenreSchema,
    ChartsSchema,
)
from .shazam import ShazamMatchSchema, ShazamTrackSchema, ShazamImagesSchema, ShazamGenresSchema, ShazamSchema
from .playlist import (
    PlaylistAuthorSchema,
    PlaylistArtistSchema,
    PlaylistAlbumSchema,
    PlaylistTrackSchema,
    PlaylistSchema,
)

__all__ = [
    "StatisticsReportSchema",
    "AnalyticsReportSchema",
    "HealthSchema",
    "SongAlbumSchema",
    "SongArtistSchema",
    "SongThumbnailSchema",
    "SongSchema",
    "SongDetailVideoDetailsSchema",
    "SongDetailSchema",
    "SongDownloadSchema",
    "ChartsCountrySelectedSchema",
    "ChartsCountriesSchema",
    "ChartsVideoSchema",
    "ChartsArtistSchema",
    "ChartsGenreSchema",
    "ChartsSchema",
    "PlaylistAuthorSchema",
    "PlaylistArtistSchema",
    "PlaylistAlbumSchema",
    "PlaylistTrackSchema",
    "PlaylistSchema",
    "ShazamMatchSchema",
    "ShazamTrackSchema",
    "ShazamImagesSchema",
    "ShazamGenresSchema",
    "ShazamSchema",
]

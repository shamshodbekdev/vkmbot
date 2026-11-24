from aiogram.utils.i18n import lazy_gettext as __

# YouTube Music returns its mood and genre categories in English only. Each known
# title is a translation key; a title YouTube adds later (seasonal ones come and
# go) is shown as it is. Buttons carry YouTube's ``params``, never the title, so
# translating the text does not change what a button does.
MOOD_TITLES = {
    title: __(title)
    for title in (
        # Moods & moments
        "Autumn", "Chill", "Commute", "Energize", "Feel good", "Focus", "Gaming",
        "Hanukkah", "Party", "Romance", "Sad", "Sleep", "Summer", "Winter", "Workout",
        # Seasonal moods YouTube shows at times
        "Spring", "Christmas", "Holiday", "Halloween", "Valentine's Day", "New Year's Eve",
        "Ramadan", "Travel", "Love", "Throwback",
        # Genres
        "African", "Arabic", "Blues", "Bollywood & Indian", "Classical", "Country & Americana",
        "Dance & electronic", "Decades", "Family", "Folk & acoustic", "German hip-hop",
        "German pop", "Hip-hop", "Indie & alternative", "J-Pop", "Jazz", "K-Pop", "Latin",
        "Mandopop & cantopop", "Metal", "Pop", "R&B & soul", "Reggae & caribbean", "Rock",
        "Schlager", "Soundtracks & musicals",
    )
}


def mood_title(title: str) -> str:
    """``title`` from YouTube Music in the user's language (unchanged if unknown)."""
    lazy = MOOD_TITLES.get(title)
    return str(lazy) if lazy is not None else title


__all__ = ["MOOD_TITLES", "mood_title"]

# 🎵 VKM Bot

**VKM Bot** is a Telegram music and media downloader. Send it a link from YouTube, Instagram or TikTok and it sends the video back without a watermark. Send it a voice message, a video note or an audio clip and it tells you which song is playing. Then you can download the track as MP3 in one tap.

Everything runs on your own server with free, open-source libraries: no paid third-party APIs.

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## ✨ Features

**Downloads**
- **YouTube**: videos and Shorts (MP4), plus any track as MP3
- **Instagram**: posts, Reels, IGTV and carousels
- **TikTok**: videos without watermark (H.264, plays everywhere)

**Music recognition (Shazam)**
- Recognize songs from **voice messages, video notes, audio and video files**
- Find a song by **singing or saying its lyrics** (local Whisper speech-to-text)
- Search by **song title or artist name**, with spelling suggestions
- Inline mode: search music from any chat

**Music discovery**
- **Top charts** per country and **daily charts** delivered on schedule
- **Mood & genre playlists**
- Personal **playlists** (`/my`), bulk download of a whole playlist

**Administration**
- Statistics and growth analytics with charts
- **Broadcasts**: immediate or delayed, filtered by language / chat type / premium, with pause, resume and stop
- User management (ban, temporary ban), admin roles
- **Mandatory subscription** to channels before using the bot
- Throttling, i18n in 4 languages (🇺🇿 Uzbek Latin & Cyrillic, 🇷🇺 Russian, 🇬🇧 English)

---

## 🛠 Tech stack

| Component        | Technology                                    |
| ---------------- | --------------------------------------------- |
| Bot framework    | [aiogram 3](https://docs.aiogram.dev/)        |
| Database / ORM   | PostgreSQL + Tortoise ORM (asyncpg)           |
| Cache / FSM      | Redis (aiocache, aiogram RedisStorage)        |
| Scheduler        | APScheduler (jobs persisted in Redis)         |
| Media download   | yt-dlp + ffmpeg                               |
| YouTube Music    | ytmusicapi                                    |
| Song recognition | ShazamIO                                      |
| Speech-to-text   | faster-whisper (runs locally on CPU)          |
| Config           | pydantic-settings                             |
| Charts           | matplotlib                                    |

---

## 🏗 Architecture

```mermaid
flowchart LR
    U[Telegram user] <--> TG[Telegram Bot API]
    TG <--> D[aiogram Dispatcher]

    subgraph Bot["VKM Bot (this server)"]
        D --> MW["Middlewares<br/>Register → I18n → Throttler → Blocked → Subscription"]
        MW --> H[Handlers<br/>users · admin · inline · common]
        H --> S[Services]
        S --> YT[youtube_api<br/>ytmusicapi + yt-dlp]
        S --> IG[instagram_api<br/>yt-dlp]
        S --> TT[tiktok_api<br/>yt-dlp]
        S --> SZ[shazam_api<br/>ShazamIO]
        S --> WH[transcription_api<br/>faster-whisper]
        SCH[APScheduler<br/>broadcasts · daily charts] --> S
    end

    H <--> DB[(PostgreSQL<br/>users · media cache · playlists)]
    H <--> R[(Redis<br/>FSM · cache · jobs)]
    YT & IG & TT --> FF[ffmpeg]
```

Downloaded files are cached by Telegram `file_id` in PostgreSQL, so the same video or track is only downloaded once and later requests are answered instantly.

---

## 🚀 Installation

### Requirements
- Python **3.12+** and [Poetry](https://python-poetry.org/)
- PostgreSQL and Redis
- **ffmpeg** (`apt install ffmpeg` / `dnf install ffmpeg`)
- ~1 GB of free RAM if you use lyrics recognition (the Whisper `small` model)

### Steps

```bash
git clone https://github.com/shamshodbekdev/vkmbot.git
cd vkmbot
poetry install
cp .env.example .env     # then edit .env
poetry run python src/main.py
```

Database tables are created automatically on startup, and translations are compiled automatically.

### Configuration (`.env`)

| Variable             | Description                                                     |
| -------------------- | --------------------------------------------------------------- |
| `TELEGRAM_TOKEN`     | Bot token from [@BotFather](https://t.me/BotFather)             |
| `TELEGRAM_USERNAME`  | Bot username, e.g. `@my_music_bot` (shown in captions)          |
| `TELEGRAM_ID`        | Telegram ID of the super-admin                                  |
| `TELEGRAM_API_URL`   | Optional. Self-hosted Bot API server URL                        |
| `TELEGRAM_API_LOCAL` | `true` for a local Bot API server (raises upload limit to 2 GB) |
| `REDIS_URL`          | e.g. `redis://localhost:6379/0`                                 |
| `DATABASE_URL`       | e.g. `postgres://user:password@localhost:5432/vkm_bot`          |

Optional: to download Instagram posts that require a login, export the cookies of a logged-in browser in Netscape format to `cookies/instagram.txt` (the folder is git-ignored).

### Run as a systemd service

```ini
# /etc/systemd/system/vkm-bot.service
[Unit]
Description=VKM Telegram Bot
After=network.target postgresql.service redis.service

[Service]
WorkingDirectory=/opt/vkmbot
ExecStart=/usr/local/bin/poetry run python src/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now vkm-bot
journalctl -u vkm-bot -f
```

---

## 💬 Usage

| You send                                     | Bot replies                                        |
| -------------------------------------------- | -------------------------------------------------- |
| `https://youtube.com/shorts/...`             | The video as MP4                                   |
| `https://www.instagram.com/reel/...`         | The Reel / post media                              |
| `https://www.tiktok.com/@user/video/...`     | The video without watermark                        |
| `Shape of You`                               | A list of matching tracks; tap one to get the MP3  |
| 🎤 Voice message / video note / audio file   | The recognized song and download buttons           |
| `@your_bot query` in any chat                | Inline music search                                |

Commands: `/start` · `/top` (charts) · `/mood` (mood playlists) · `/my` (your playlist) · `/lang` · `/settings` · `/manage` (admins)

The bot also works in groups: add it to a group and send links there.

---

## 📁 Project structure

```
vkmbot/
├── i18n/                    # Translations: en, ru, uz, uzc (.po)
├── src/
│   ├── main.py              # Entry point
│   ├── core/                # Bot bootstrap, config, cache, i18n, scheduler, commands
│   ├── database/            # Tortoise ORM connection, models, enums
│   ├── filters/             # Callback-data and message filters (URL filters, admin...)
│   ├── handlers/
│   │   ├── admin/           # Statistics, broadcasts, user/admin/subscription management
│   │   ├── users/           # Commands, callbacks, messages, inline search
│   │   └── common/          # Join requests, chat membership, errors, fallback
│   ├── keyboard/            # Inline and reply keyboards
│   ├── middlewares/         # Register → I18n → Throttler → Blocked → Subscription
│   ├── schemas/             # Pydantic / dataclass schemas
│   ├── services/
│   │   ├── youtube_api.py        # ytmusicapi + yt-dlp
│   │   ├── instagram_api.py      # yt-dlp
│   │   ├── tiktok_api.py         # yt-dlp
│   │   ├── shazam_api.py         # ShazamIO
│   │   ├── transcription_api.py  # faster-whisper
│   │   ├── media_downloader.py   # Shared yt-dlp / ffmpeg helpers
│   │   ├── broadcast/            # Broadcast engine
│   │   ├── charts/               # Statistics charts (matplotlib)
│   │   └── repositories/         # Analytics & statistics queries
│   ├── states/              # FSM states
│   └── utils/               # Constants, formatters, helpers, validators
├── tests/                   # pytest test suite
├── .env.example
├── pyproject.toml
└── LICENSE
```

---

## 🧪 Tests

```bash
poetry run pytest
```

---

## 🤝 Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## ⚠️ Disclaimer

This project is for personal and educational use. Respect the terms of service of each platform and the rights of content creators.

## 📄 License

Released under the [MIT License](LICENSE).

## 👤 Author

**Shamshodbek** · [GitHub @shamshodbekdev](https://github.com/shamshodbekdev) · shamshodbekdev@gmail.com

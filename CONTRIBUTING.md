# Contributing to VKM Bot

Thanks for taking the time to contribute! Bug reports, feature ideas and pull requests are all welcome.

## Getting started

1. Fork the repository and clone your fork.
2. Install dependencies: `poetry install`
3. Copy `.env.example` to `.env` and fill in a **test** bot token.
4. Make sure PostgreSQL, Redis and `ffmpeg` are available.
5. Run the bot: `poetry run python src/main.py`

## Workflow

- Create a branch from `main`: `git checkout -b feat/short-description`
- Keep pull requests focused: one feature or fix per PR.
- Run the tests before pushing: `poetry run pytest`
- Describe **what** changed and **why** in the PR description.

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Pinterest downloader
fix(tiktok): prefer H.264 formats
docs: update installation guide
```

Common types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`.

## Code style

- Python 3.12+, type hints on public functions.
- No user-facing text inline in handlers: wrap it in `_()` and add it to every
  `.po` file in `i18n/` (`en`, `ru`, `uz`, `uzc`).
- Blocking work (yt-dlp, ffmpeg, Whisper) must run in a worker thread or subprocess,
  never directly on the event loop.
- Services return `None` / empty results on failure and log a warning; handlers
  decide what to tell the user.

## Reporting bugs

Open an issue with steps to reproduce, the expected and actual behaviour, and the
relevant log lines (`journalctl -u vkm-bot`). **Never paste your bot token or `.env`.**

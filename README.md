# Setlist Manager

A lightweight Flask web app for building and managing band setlists. Keep a library of songs, generate a setlist that fits your show length, and fine-tune the running order before you hit the stage.

## Features

- Song library with title, artist, duration, optional genre, and energy level.
- Automatic setlist generation that fits (or comes close to) a target duration without repeating songs.
- Manual curation tools to reorder, add, or remove songs from a setlist.
- Quick overview of running time vs. target time for each show.

## Getting Started

1. **Install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the development server**
   ```bash
   flask --app app run --debug
   ```

   The app listens on `http://127.0.0.1:5000/` by default. The SQLite database (`setlists.db`) is created in the project root the first time the server runs.

## Usage Notes

- Enter durations as `mm:ss` (e.g. `4:30`) or as minutes in decimal form (e.g. `4.5`).
- Automatic generation shuffles your library and chooses the combination of songs that most closely matches the requested target without exceeding it. If no target is supplied it simply shuffles the available songs.
- Removing a song from your library removes it from any setlists that use it.
- Regenerate an existing setlist any time if it has a target duration, or continue adjusting manually.

## Project Layout

- `app.py` – Flask entrypoint.
- `setlist_manager/` – Application package (database models, routes, templates, static assets).
- `requirements.txt` – Runtime dependencies.

Feel free to tailor the data model or generator logic to match your band's workflow, rehearsal notes, or show pacing preferences.

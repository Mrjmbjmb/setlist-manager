# Setlist Manager

A lightweight Flask web app for building and managing band setlists. Keep a library of songs, generate a setlist that fits your show length, and fine-tune the running order before you hit the stage.

## Features

- Song library with title, artist, duration, optional genre, and energy level.
- Automatic setlist generation that fits (or comes close to) a target duration without repeating songs.
- Manual curation tools to reorder, add, or remove songs from a setlist.
- Quick overview of running time vs. target time for each show.
- Optional song alias that prints on setlists if it differs from the library name.
- Optional song tags for Multitrack (M), Cover (CVR), and Vocals Only (VO) to highlight special arrangements.
- Edit song details any time to keep titles, aliases, tags, and durations in sync.
- Stats dashboard that surfaces most-played songs, recent setlists, and library-wide metrics.

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
- Bulk import songs from the Songs page using a CSV file when you already have a spreadsheet of your catalog.
- Provide an alias (print name) if you want the setlist to show a shortened or alternate title while keeping the library name intact.
- Tag songs as Multitrack (`M`), Cover (`CVR`), or Vocals Only (`VO`) so you can spot production-specific tracks while building setlists.
- Open the Stats page to review top songs, unused tracks, and pacing insights before planning your next show.
- Drop an encore break anywhere in a setlist to separate the main set from the finale.
- Generate a stage-friendly PDF of any setlist with bold, easy-to-read titles.

### CSV Import Format

Upload a UTF-8 encoded CSV file with a header row. The required columns are `title`, `artist`, and `duration`. Optional columns include `alias`, `genre`, `energy`, and `tags`.\
`tags` accepts any mix of `M`, `CVR`, and `VO` separated by commas, semicolons, slashes, or pipes. For compatibility with older sheets you can also include boolean columns named `multitrack`, `cover`, or `vocals_only` (values like `true`, `yes`, or `1` are treated as checked).

```csv
title,artist,alias,duration,genre,energy,tags
Song One,The Example Band,Intro Jam,3:45,Rock,7,M
Song Two,Another Artist,,4,Pop,5,"CVR,VO"
```

Durations accept the same formats as the add-song form: `mm:ss` (e.g. `4:30`) or minutes in decimal form (e.g. `4.5`). Energy should be a whole number if supplied. Rows with missing required data, invalid durations, duplicate title/artist pairs, unknown tag codes, or non-numeric energy values are skipped and reported after the import.

## Project Layout

- `app.py` – Flask entrypoint.
- `setlist_manager/` – Application package (database models, routes, templates, static assets).
- `requirements.txt` – Runtime dependencies.

Feel free to tailor the data model or generator logic to match your band's workflow, rehearsal notes, or show pacing preferences.

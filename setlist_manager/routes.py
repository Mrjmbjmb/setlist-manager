import csv
import io
import re
from typing import Optional

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from .database import db
from .models import Setlist, SetlistSong, Song
from .services import generate_setlist

bp = Blueprint("setlists", __name__)
VALID_TAG_CODES = {"M", "CVR", "VO"}
TAG_ATTRIBUTE_MAP = {
    "M": "is_multitrack",
    "CVR": "is_cover",
    "VO": "is_vocals_only",
}


def _apply_tags_to_song(song: Song, selected_tags: set[str]) -> None:
    for code, attribute in TAG_ATTRIBUTE_MAP.items():
        setattr(song, attribute, code in selected_tags)


def _collect_song_form_data(form) -> tuple[Optional[dict], Optional[str]]:
    title = (form.get("title") or "").strip()
    artist = (form.get("artist") or "").strip()
    alias = (form.get("alias") or "").strip() or None
    duration_raw = (form.get("duration") or "").strip()
    genre = (form.get("genre") or "").strip() or None
    energy_raw = (form.get("energy") or "").strip()
    selected_tags = {tag.upper() for tag in form.getlist("tags")}

    duration_seconds = _parse_duration(duration_raw)
    energy = None

    if energy_raw:
        try:
            energy = int(energy_raw)
        except ValueError:
            return None, "Energy must be a whole number."

    if not title or not artist or duration_seconds is None:
        return None, "Title, artist, and duration are required (format mm:ss or minutes)."

    unknown_tags = selected_tags - VALID_TAG_CODES
    if unknown_tags:
        return None, f"Unknown tag(s): {', '.join(sorted(unknown_tags))}."

    return (
        {
            "title": title,
            "artist": artist,
            "alias": alias,
            "duration_seconds": duration_seconds,
            "genre": genre,
            "energy": energy,
            "selected_tags": selected_tags,
        },
        None,
    )


def _format_seconds(total_seconds: Optional[int]) -> str:
    if not total_seconds:
        return "0:00"

    minutes, seconds = divmod(int(total_seconds), 60)
    return f"{minutes}:{seconds:02d}"


def _parse_duration(value: str) -> Optional[int]:
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    try:
        if ":" in value:
            minutes_part, seconds_part = value.split(":", 1)
            minutes = int(minutes_part)
            seconds = int(seconds_part)
            if seconds < 0 or seconds >= 60:
                raise ValueError
            return minutes * 60 + seconds

        minutes_float = float(value)
        return int(minutes_float * 60)
    except (TypeError, ValueError):
        return None


@bp.route("/")
def index():
    setlists = Setlist.query.order_by(Setlist.created_at.desc()).all()
    total_songs = Song.query.count()
    return render_template("index.html", setlists=setlists, total_songs=total_songs)


@bp.route("/songs", methods=["GET", "POST"])
def songs():
    if request.method == "POST":
        form_data, error_message = _collect_song_form_data(request.form)
        if error_message:
            flash(error_message, "error")
            return redirect(url_for("setlists.songs"))

        song = Song(
            title=form_data["title"],
            artist=form_data["artist"],
            alias=form_data["alias"],
            duration_seconds=form_data["duration_seconds"],
            genre=form_data["genre"],
            energy=form_data["energy"],
        )
        _apply_tags_to_song(song, form_data["selected_tags"])
        db.session.add(song)
        db.session.commit()

        flash(f"Added “{song.title}” by {song.artist}.", "success")
        return redirect(url_for("setlists.songs"))

    songs_list = Song.query.order_by(Song.title).all()
    return render_template("songs.html", songs=songs_list)


@bp.route("/songs/<int:song_id>/edit", methods=["GET", "POST"])
def edit_song(song_id: int):
    song = Song.query.get_or_404(song_id)

    if request.method == "POST":
        form_data, error_message = _collect_song_form_data(request.form)
        if error_message:
            flash(error_message, "error")
            return redirect(url_for("setlists.edit_song", song_id=song.id))

        song.title = form_data["title"]
        song.artist = form_data["artist"]
        song.alias = form_data["alias"]
        song.duration_seconds = form_data["duration_seconds"]
        song.genre = form_data["genre"]
        song.energy = form_data["energy"]
        _apply_tags_to_song(song, form_data["selected_tags"])

        db.session.commit()
        flash(f"Updated “{song.print_title}”.", "success")
        return redirect(url_for("setlists.songs"))

    selected_tags = set(song.tag_codes)
    return render_template(
        "song_form.html",
        song=song,
        selected_tags=selected_tags,
        tag_definitions=Song.TAG_DEFINITIONS,
    )


@bp.route("/stats")
def stats():
    total_songs = Song.query.count()
    total_library_seconds = (
        db.session.query(func.coalesce(func.sum(Song.duration_seconds), 0)).scalar() or 0
    )

    setlists = (
        Setlist.query.options(
            joinedload(Setlist.entries).joinedload(SetlistSong.song)
        )
        .order_by(Setlist.created_at.desc())
        .all()
    )

    total_setlists = len(setlists)
    total_plays = sum(len(item.entries) for item in setlists)
    latest_setlist_at = setlists[0].created_at if setlists else None

    avg_songs_per_setlist = 0.0
    avg_setlist_duration_seconds = 0.0
    longest_setlist = None

    if total_setlists:
        total_song_counts = sum(len(item.entries) for item in setlists)
        total_setlist_duration_seconds = sum(
            item.total_duration_seconds for item in setlists
        )
        avg_songs_per_setlist = total_song_counts / total_setlists
        avg_setlist_duration_seconds = (
            total_setlist_duration_seconds / total_setlists
        )

        longest_obj = max(setlists, key=lambda item: item.total_duration_seconds)
        longest_setlist = {
            "name": longest_obj.name,
            "created_at": longest_obj.created_at,
            "song_count": len(longest_obj.entries),
            "duration_seconds": longest_obj.total_duration_seconds,
            "duration_label": _format_seconds(longest_obj.total_duration_seconds),
        }

    most_played_rows = (
        db.session.query(
            Song,
            func.count(SetlistSong.id).label("play_count"),
            func.max(Setlist.created_at).label("last_played"),
        )
        .join(SetlistSong, SetlistSong.song_id == Song.id)
        .join(Setlist, SetlistSong.setlist_id == Setlist.id)
        .group_by(Song.id)
        .order_by(func.count(SetlistSong.id).desc(), func.max(Setlist.created_at).desc())
        .limit(10)
        .all()
    )
    most_played_songs = [
        {
            "song": song,
            "play_count": play_count,
            "last_played": last_played,
        }
        for song, play_count, last_played in most_played_rows
    ]

    unused_song_query = Song.query.filter(~Song.setlist_entries.any())
    unused_song_total = unused_song_query.count()
    unused_songs = unused_song_query.order_by(Song.title).limit(10).all()

    tag_counts = [
        {
            "code": code,
            "label": label,
            "count": Song.query.filter(getattr(Song, attribute)).count(),
        }
        for code, label, attribute in Song.TAG_DEFINITIONS
    ]

    recent_setlists = [
        {
            "name": item.name,
            "created_at": item.created_at,
            "song_count": len(item.entries),
            "duration_label": _format_seconds(item.total_duration_seconds),
        }
        for item in setlists[:5]
    ]

    context = {
        "total_songs": total_songs,
        "total_setlists": total_setlists,
        "total_plays": total_plays,
        "total_library_seconds": total_library_seconds,
        "library_duration_label": _format_seconds(total_library_seconds),
        "avg_songs_per_setlist": round(avg_songs_per_setlist, 1) if total_setlists else 0.0,
        "avg_setlist_duration_label": _format_seconds(
            int(round(avg_setlist_duration_seconds))
        )
        if total_setlists
        else "0:00",
        "longest_setlist": longest_setlist,
        "most_played_songs": most_played_songs,
        "unused_songs": unused_songs,
        "unused_song_total": unused_song_total,
        "tag_counts": tag_counts,
        "recent_setlists": recent_setlists,
        "latest_setlist_at": latest_setlist_at,
    }

    return render_template("stats.html", **context)


@bp.post("/songs/import")
def import_songs():
    uploaded_file = request.files.get("csv_file")
    if uploaded_file is None or not uploaded_file.filename:
        flash("Choose a CSV file to import.", "error")
        return redirect(url_for("setlists.songs"))

    try:
        raw_bytes = uploaded_file.read()
    except OSError:
        flash("Could not read the uploaded file.", "error")
        return redirect(url_for("setlists.songs"))

    if not raw_bytes:
        flash("The uploaded file is empty.", "error")
        return redirect(url_for("setlists.songs"))

    try:
        decoded_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        flash("CSV files must be saved with UTF-8 encoding.", "error")
        return redirect(url_for("setlists.songs"))

    reader = csv.DictReader(io.StringIO(decoded_text, newline=""))
    if reader.fieldnames is None:
        flash("CSV file must include a header row.", "error")
        return redirect(url_for("setlists.songs"))

    field_map = {header.strip().lower(): header for header in reader.fieldnames if header}
    required_headers = {"title", "artist", "duration"}
    missing_headers = [header for header in required_headers if header not in field_map]
    if missing_headers:
        flash("CSV must include the columns: title, artist, duration.", "error")
        return redirect(url_for("setlists.songs"))

    added_count = 0
    skipped_rows: list[tuple[int, str]] = []

    truthy_values = {"1", "true", "yes", "y", "on", "t"}

    def _is_truthy(value: str) -> bool:
        if not value:
            return False
        return value.strip().lower() in truthy_values

    def _parse_tags(value: str) -> set[str]:
        if not value:
            return set()
        parts = re.split(r"[;,/|\s]+", value)
        normalized = {part.strip().upper() for part in parts if part.strip()}
        return normalized

    try:
        for row_number, row in enumerate(reader, start=2):
            if row is None:
                continue

            def _get(field_name: str) -> str:
                column = field_map.get(field_name)
                if column is None:
                    return ""
                return (row.get(column) or "").strip()

            title = _get("title")
            artist = _get("artist")
            alias = _get("alias") or None
            duration_raw = _get("duration")
            genre = _get("genre") or None
            energy_raw = _get("energy")
            tags_raw = _get("tags")

            if not any([title, artist, alias, duration_raw, genre, energy_raw, tags_raw]):
                continue

            if not title or not artist or not duration_raw:
                skipped_rows.append((row_number, "Missing title, artist, or duration"))
                continue

            duration_seconds = _parse_duration(duration_raw)
            if duration_seconds is None:
                skipped_rows.append((row_number, "Invalid duration"))
                continue

            energy = None
            if energy_raw:
                try:
                    energy = int(energy_raw)
                except ValueError:
                    skipped_rows.append((row_number, "Energy must be a whole number"))
                    continue

            tag_codes = _parse_tags(tags_raw)
            if not tag_codes:
                if _is_truthy(_get("multitrack")):
                    tag_codes.add("M")
                if _is_truthy(_get("cover")):
                    tag_codes.add("CVR")
                if _is_truthy(_get("vocals_only")):
                    tag_codes.add("VO")

            unknown_tags = tag_codes - VALID_TAG_CODES
            if unknown_tags:
                skipped_rows.append((row_number, f"Unknown tag(s): {', '.join(sorted(unknown_tags))}"))
                continue

            existing = Song.query.filter_by(title=title, artist=artist).first()
            if existing:
                skipped_rows.append((row_number, "Song already exists"))
                continue

            song = Song(
                title=title,
                artist=artist,
                alias=alias,
                duration_seconds=duration_seconds,
                genre=genre,
                energy=energy,
            )
            _apply_tags_to_song(song, tag_codes)
            db.session.add(song)
            added_count += 1
    except csv.Error as error:
        db.session.rollback()
        flash(f"Could not read the CSV file: {error}", "error")
        return redirect(url_for("setlists.songs"))

    if added_count:
        db.session.commit()
        song_word = "song" if added_count == 1 else "songs"
        flash(f"Imported {added_count} {song_word}.", "success")
    else:
        db.session.rollback()
        flash("No songs were imported. Check the file and try again.", "error")

    if skipped_rows:
        preview = "; ".join(
            f"row {row_number}: {reason}" for row_number, reason in skipped_rows[:3]
        )
        if len(skipped_rows) > 3:
            preview += f"; … {len(skipped_rows) - 3} more"
        flash(f"Skipped {len(skipped_rows)} row(s): {preview}", "warning")

    return redirect(url_for("setlists.songs"))


@bp.post("/songs/<int:song_id>/delete")
def delete_song(song_id: int):
    song = Song.query.get_or_404(song_id)
    affected_setlists = {entry.setlist_id for entry in song.setlist_entries}
    db.session.delete(song)
    db.session.commit()
    for setlist_id in affected_setlists:
        _normalize_positions(setlist_id)
    flash(f"Removed “{song.title}”.", "success")
    return redirect(url_for("setlists.songs"))


@bp.route("/setlists/new", methods=["GET", "POST"])
def create_setlist():
    songs = Song.query.order_by(Song.title).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        duration_raw = request.form.get("target_duration", "")
        action = request.form.get("action", "create")

        if not name:
            flash("Setlist name is required.", "error")
            return redirect(url_for("setlists.create_setlist"))

        target_duration = _parse_duration(duration_raw)

        setlist = Setlist(
            name=name,
            description=description or None,
            target_duration_seconds=target_duration,
        )
        db.session.add(setlist)
        db.session.flush()

        if action == "generate":
            if not songs:
                flash("Add some songs before generating a setlist.", "error")
                db.session.rollback()
                return redirect(url_for("setlists.create_setlist"))

            generated_songs = generate_setlist(
                target_duration or 0,
                songs,
            )

            if generated_songs:
                for index, song in enumerate(generated_songs, start=1):
                    entry = SetlistSong(
                        setlist_id=setlist.id,
                        song_id=song.id,
                        position=index,
                    )
                    db.session.add(entry)

        db.session.commit()

        flash("Setlist created successfully.", "success")
        return redirect(url_for("setlists.view_setlist", setlist_id=setlist.id))

    return render_template("setlist_form.html", songs=songs)


@bp.route("/setlists/<int:setlist_id>")
def view_setlist(setlist_id: int):
    setlist = Setlist.query.get_or_404(setlist_id)
    available_songs = (
        Song.query.filter(~Song.setlist_entries.any(SetlistSong.setlist_id == setlist.id))
        .order_by(Song.title)
        .all()
    )
    return render_template(
        "setlist_detail.html",
        setlist=setlist,
        available_songs=available_songs,
    )


@bp.get("/setlists/<int:setlist_id>/print")
def print_setlist(setlist_id: int):
    setlist = (
        Setlist.query.options(
            joinedload(Setlist.entries).joinedload(SetlistSong.song)
        )
        .get_or_404(setlist_id)
    )
    segments: list[dict] = []
    current_entries: list[SetlistSong] = []
    current_type = "set"
    set_counter = 1
    encore_counter = 1

    def build_segment(entries_group: list[SetlistSong], segment_type: str, set_number: int, encore_number: int) -> dict:
        if not entries_group:
            return {}

        entries_copy = list(entries_group)
        total_seconds = sum(
            entry.song.duration_seconds for entry in entries_copy if entry.song
        )
        label = f"Set {set_number}" if segment_type == "set" else f"Encore {encore_number}"

        segment = {
            "type": segment_type,
            "label": label,
            "entries": entries_copy,
            "song_count": len(entries_copy),
            "total_duration_seconds": total_seconds,
            "total_duration_label": _format_seconds(total_seconds),
            "encore_index": encore_number if segment_type == "encore" else None,
        }
        segment["per_song"] = []
        for index, song_entry in enumerate(entries_copy):
            if song_entry.song is None:
                continue
            is_last = index == len(entries_copy) - 1
            segment["per_song"].append(
                {
                    "entry": song_entry,
                    "is_last": is_last,
                    "duration_label": song_entry.song.duration_label if is_last else None,
                }
            )
        return segment

    for entry in setlist.entries:
        if entry.starts_encore and current_entries:
            segment = build_segment(current_entries, current_type, set_counter, encore_counter)
            if segment:
                segments.append(segment)
            if current_type == "set":
                set_counter += 1
            else:
                encore_counter += 1
            current_entries = []
            current_type = "encore"

        current_entries.append(entry)

    if current_entries:
        segment = build_segment(current_entries, current_type, set_counter, encore_counter)
        if segment:
            segments.append(segment)

    return render_template("setlist_print.html", setlist=setlist, segments=segments)


@bp.post("/setlists/<int:setlist_id>/add-song")
def add_song_to_setlist(setlist_id: int):
    setlist = Setlist.query.get_or_404(setlist_id)
    try:
        song_id = int(request.form.get("song_id", "").strip())
    except ValueError:
        flash("Select a song to add.", "error")
        return redirect(url_for("setlists.view_setlist", setlist_id=setlist.id))

    song = Song.query.get(song_id)
    if song is None:
        flash("Song not found.", "error")
        return redirect(url_for("setlists.view_setlist", setlist_id=setlist.id))

    position = len(setlist.entries) + 1
    entry = SetlistSong(
        setlist_id=setlist.id,
        song_id=song.id,
        position=position,
    )
    db.session.add(entry)
    db.session.commit()

    flash(f"Added “{song.title}” to {setlist.name}.", "success")
    return redirect(url_for("setlists.view_setlist", setlist_id=setlist.id))


@bp.post("/setlists/<int:setlist_id>/reorder")
def reorder_setlist(setlist_id: int):
    Setlist.query.get_or_404(setlist_id)
    payload = request.get_json(silent=True) or {}
    order = payload.get("order")

    if not isinstance(order, list):
        return {"status": "error", "message": "Invalid order payload."}, 400

    try:
        order_ids = [int(item) for item in order]
    except (TypeError, ValueError):
        return {"status": "error", "message": "Order must contain numeric IDs."}, 400

    entries = (
        SetlistSong.query.filter_by(setlist_id=setlist_id)
        .order_by(SetlistSong.position)
        .all()
    )

    if len(order_ids) != len(entries):
        return {"status": "error", "message": "Order length mismatch."}, 400

    entry_map = {entry.id: entry for entry in entries}
    if set(order_ids) != set(entry_map.keys()):
        return {"status": "error", "message": "Unknown entry IDs supplied."}, 400

    for index, entry_id in enumerate(order_ids, start=1):
        entry = entry_map[entry_id]
        entry.position = index

    db.session.commit()
    return {"status": "ok"}


@bp.post("/setlists/<int:setlist_id>/entries/<int:entry_id>/remove")
def remove_setlist_entry(setlist_id: int, entry_id: int):
    entry = (
        SetlistSong.query.filter_by(setlist_id=setlist_id, id=entry_id)
        .first()
    )
    if entry is None:
        abort(404)

    db.session.delete(entry)
    db.session.commit()
    _normalize_positions(setlist_id)

    flash("Removed song from setlist.", "success")
    return redirect(url_for("setlists.view_setlist", setlist_id=setlist_id))


@bp.post("/setlists/<int:setlist_id>/entries/<int:entry_id>/toggle-encore")
def toggle_encore_entry(setlist_id: int, entry_id: int):
    entry = (
        SetlistSong.query.filter_by(setlist_id=setlist_id, id=entry_id)
        .first()
    )
    if entry is None:
        abort(404)

    entries = (
        SetlistSong.query.filter_by(setlist_id=setlist_id)
        .order_by(SetlistSong.position)
        .all()
    )

    was_enabled = entry.starts_encore

    for item in entries:
        item.starts_encore = False

    if not was_enabled:
        entry.starts_encore = True
        flash(f"Encore now starts with “{entry.song.print_title}”.", "success")
    else:
        flash("Encore break removed.", "success")

    db.session.commit()
    return redirect(url_for("setlists.view_setlist", setlist_id=setlist_id))


@bp.post("/setlists/<int:setlist_id>/entries/<int:entry_id>/move")
def move_setlist_entry(setlist_id: int, entry_id: int):
    direction = request.form.get("direction")
    if direction not in {"up", "down"}:
        abort(400)

    entries = (
        SetlistSong.query.filter_by(setlist_id=setlist_id)
        .order_by(SetlistSong.position)
        .all()
    )

    entry_index = next((i for i, item in enumerate(entries) if item.id == entry_id), None)
    if entry_index is None:
        abort(404)

    if direction == "up" and entry_index > 0:
        entries[entry_index].position, entries[entry_index - 1].position = (
            entries[entry_index - 1].position,
            entries[entry_index].position,
        )
    elif direction == "down" and entry_index < len(entries) - 1:
        entries[entry_index].position, entries[entry_index + 1].position = (
            entries[entry_index + 1].position,
            entries[entry_index].position,
        )

    db.session.commit()
    return redirect(url_for("setlists.view_setlist", setlist_id=setlist_id))


@bp.post("/setlists/<int:setlist_id>/regenerate")
def regenerate_setlist(setlist_id: int):
    setlist = Setlist.query.get_or_404(setlist_id)
    songs = Song.query.order_by(Song.title).all()
    target_duration = setlist.target_duration_seconds or 0

    for entry in list(setlist.entries):
        db.session.delete(entry)
    db.session.flush()

    generated_songs = generate_setlist(target_duration, songs)
    for index, song in enumerate(generated_songs, start=1):
        entry = SetlistSong(
            setlist_id=setlist.id,
            song_id=song.id,
            position=index,
        )
        db.session.add(entry)

    db.session.commit()
    flash("Setlist regenerated.", "success")
    return redirect(url_for("setlists.view_setlist", setlist_id=setlist.id))


@bp.post("/setlists/<int:setlist_id>/delete")
def delete_setlist(setlist_id: int):
    setlist = Setlist.query.get_or_404(setlist_id)
    db.session.delete(setlist)
    db.session.commit()
    flash("Setlist deleted.", "success")
    return redirect(url_for("setlists.index"))


def _normalize_positions(setlist_id: int) -> None:
    entries = (
        SetlistSong.query.filter_by(setlist_id=setlist_id)
        .order_by(SetlistSong.position)
        .all()
    )
    encore_found = False
    for index, entry in enumerate(entries, start=1):
        entry.position = index
        if entry.starts_encore:
            if encore_found:
                entry.starts_encore = False
            else:
                encore_found = True
    db.session.commit()

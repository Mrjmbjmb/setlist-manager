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

from .database import db
from .models import Setlist, SetlistSong, Song
from .services import generate_setlist

bp = Blueprint("setlists", __name__)


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
        title = request.form.get("title", "").strip()
        artist = request.form.get("artist", "").strip()
        duration_raw = request.form.get("duration", "").strip()
        genre = request.form.get("genre", "").strip() or None
        energy_raw = request.form.get("energy", "").strip()

        duration_seconds = _parse_duration(duration_raw)
        energy = None
        if energy_raw:
            try:
                energy = int(energy_raw)
            except ValueError:
                flash("Energy must be a whole number.", "error")
                return redirect(url_for("setlists.songs"))

        if not title or not artist or duration_seconds is None:
            flash("Title, artist, and duration are required (format mm:ss or minutes).", "error")
            return redirect(url_for("setlists.songs"))

        song = Song(
            title=title,
            artist=artist,
            duration_seconds=duration_seconds,
            genre=genre,
            energy=energy,
        )
        db.session.add(song)
        db.session.commit()

        flash(f"Added “{song.title}” by {song.artist}.", "success")
        return redirect(url_for("setlists.songs"))

    songs_list = Song.query.order_by(Song.title).all()
    return render_template("songs.html", songs=songs_list)


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
    for index, entry in enumerate(entries, start=1):
        entry.position = index
    db.session.commit()

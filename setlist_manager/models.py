from datetime import datetime

from .database import db


class Song(db.Model):
    __tablename__ = "songs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    artist = db.Column(db.String(120), nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=False)
    genre = db.Column(db.String(80))
    energy = db.Column(db.Integer)

    setlist_entries = db.relationship(
        "SetlistSong", back_populates="song", cascade="all, delete"
    )

    @property
    def duration_minutes(self) -> float:
        return round(self.duration_seconds / 60, 2)

    @property
    def duration_label(self) -> str:
        minutes, seconds = divmod(self.duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"


class Setlist(db.Model):
    __tablename__ = "setlists"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    target_duration_seconds = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    entries = db.relationship(
        "SetlistSong",
        back_populates="setlist",
        order_by="SetlistSong.position",
        cascade="all, delete-orphan",
    )

    @property
    def total_duration_seconds(self) -> int:
        return sum(
            entry.song.duration_seconds
            for entry in self.entries
            if entry.song is not None
        )

    @property
    def total_duration_label(self) -> str:
        minutes, seconds = divmod(self.total_duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def target_duration_label(self) -> str:
        if self.target_duration_seconds:
            minutes, seconds = divmod(self.target_duration_seconds, 60)
            return f"{minutes}:{seconds:02d}"
        return "-"


class SetlistSong(db.Model):
    __tablename__ = "setlist_songs"

    id = db.Column(db.Integer, primary_key=True)
    setlist_id = db.Column(db.Integer, db.ForeignKey("setlists.id"), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey("songs.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(255))

    setlist = db.relationship("Setlist", back_populates="entries")
    song = db.relationship("Song", back_populates="setlist_entries", lazy="joined")

from datetime import datetime

from .database import db


class Song(db.Model):
    __tablename__ = "songs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    artist = db.Column(db.String(120), nullable=False)
    alias = db.Column(db.String(120))
    duration_seconds = db.Column(db.Integer, nullable=False)
    genre = db.Column(db.String(80))
    energy = db.Column(db.Integer)
    is_multitrack = db.Column(db.Boolean, nullable=False, default=False)
    is_cover = db.Column(db.Boolean, nullable=False, default=False)
    is_vocals_only = db.Column(db.Boolean, nullable=False, default=False)

    setlist_entries = db.relationship(
        "SetlistSong", back_populates="song", cascade="all, delete"
    )

    TAG_DEFINITIONS = (
        ("M", "Multitrack", "is_multitrack"),
        ("CVR", "Cover", "is_cover"),
        ("VO", "Vocals Only", "is_vocals_only"),
    )

    @property
    def duration_minutes(self) -> float:
        return round(self.duration_seconds / 60, 2)

    @property
    def duration_label(self) -> str:
        minutes, seconds = divmod(self.duration_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def tag_codes(self) -> list[str]:
        return [code for code, _, attribute in self.TAG_DEFINITIONS if getattr(self, attribute)]

    @property
    def tag_labels(self) -> list[str]:
        return [label for _, label, attribute in self.TAG_DEFINITIONS if getattr(self, attribute)]

    @property
    def tag_summary(self) -> str:
        return ", ".join(self.tag_codes)

    @property
    def print_title(self) -> str:
        return self.alias or self.title


class Setlist(db.Model):
    __tablename__ = "setlists"

    BETWEEN_SONG_SECONDS = 30
    ENCORE_BREAK_SECONDS = 240

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
    def has_encore_break(self) -> bool:
        return any(
            index > 0 and entry.starts_encore
            for index, entry in enumerate(self.entries)
        )

    @property
    def total_song_duration_seconds(self) -> int:
        return sum(
            entry.song.duration_seconds
            for entry in self.entries
            if entry.song is not None
        )

    @property
    def transition_buffer_seconds(self) -> int:
        if not self.entries:
            return 0

        buffer = 0
        for index in range(len(self.entries) - 1):
            next_entry = self.entries[index + 1]
            if next_entry.starts_encore and index + 1 > 0:
                buffer += self.ENCORE_BREAK_SECONDS
            else:
                buffer += self.BETWEEN_SONG_SECONDS
        return buffer

    @property
    def total_duration_seconds(self) -> int:
        return self.total_song_duration_seconds + self.transition_buffer_seconds

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
    starts_encore = db.Column(db.Boolean, nullable=False, default=False)

    setlist = db.relationship("Setlist", back_populates="entries")
    song = db.relationship("Song", back_populates="setlist_entries", lazy="joined")

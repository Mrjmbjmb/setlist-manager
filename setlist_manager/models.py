from datetime import datetime, timedelta

from .database import db


# Move Setting class to top to avoid circular imports
class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key, value, description=None):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.updated_at = datetime.utcnow()
        else:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting


def get_setting_value(key, default=None):
    """Helper function to get setting value"""
    return Setting.get(key, default)


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
        """Format duration as hh:mm:ss"""
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
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
    show_date = db.Column(db.Date, nullable=True)  # Add this line
    show_start_time = db.Column(db.Time, nullable=True)
    show_end_time = db.Column(db.Time, nullable=True)

    entries = db.relationship(
        "SetlistSong",
        back_populates="setlist",
        order_by="SetlistSong.position",
        cascade="all, delete-orphan",
    )

    @property
    def has_encore_break(self) -> bool:
        return self.encore_break_count > 0

    @property
    def encore_break_count(self) -> int:
        return sum(
            1
            for index, entry in enumerate(self.entries)
            if index > 0 and entry.starts_encore
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
                buffer += self.encore_break_seconds
            else:
                buffer += self.between_song_seconds
        return buffer

    @property
    def total_duration_seconds(self) -> int:
        return self.total_song_duration_seconds + self.transition_buffer_seconds

    @property
    def total_duration_label(self) -> str:
        """Format total duration as hh:mm:ss"""
        hours = self.total_duration_seconds // 3600
        minutes = (self.total_duration_seconds % 3600) // 60
        seconds = self.total_duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @property
    def song_duration_label(self) -> str:
        """Format song duration only (without transitions) as hh:mm:ss"""
        hours = self.total_song_duration_seconds // 3600
        minutes = (self.total_song_duration_seconds % 3600) // 60
        seconds = self.total_song_duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    @property
    def target_duration_label(self) -> str:
        """Format target duration as hh:mm:ss"""
        if self.target_duration_seconds:
            hours = self.target_duration_seconds // 3600
            minutes = (self.target_duration_seconds % 3600) // 60
            seconds = self.target_duration_seconds % 60

            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        return "-"

    @property
    def between_song_seconds(self) -> int:
        """Get the configurable transition time between songs"""
        transition_setting = get_setting_value('transition_time_seconds')
        try:
            return int(transition_setting) if transition_setting else self.BETWEEN_SONG_SECONDS
        except (ValueError, TypeError):
            return self.BETWEEN_SONG_SECONDS

    @property
    def encore_break_seconds(self) -> int:
        """Get the configurable encore break time"""
        encore_setting = get_setting_value('encore_break_seconds')
        try:
            return int(encore_setting) if encore_setting else self.ENCORE_BREAK_SECONDS
        except (ValueError, TypeError):
            return self.ENCORE_BREAK_SECONDS

    @property
    def show_duration_seconds(self) -> int:
        """Calculate the total show duration in seconds"""
        if self.show_start_time and self.show_end_time:
            start = datetime.combine(datetime.min.date(), self.show_start_time)
            end = datetime.combine(datetime.min.date(), self.show_end_time)

            # Handle case where end time is after midnight
            if end < start:
                end = datetime.combine(datetime.min.date() + timedelta(days=1), self.show_end_time)

            return int((end - start).total_seconds())
        return 0

    @property
    def show_duration_label(self) -> str:
        """Format show duration as mm:ss or hh:mm:ss"""
        if self.show_duration_seconds:
            hours = self.show_duration_seconds // 3600
            minutes = (self.show_duration_seconds % 3600) // 60
            seconds = self.show_duration_seconds % 60

            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        return "-"

    @property
    def duration_difference_seconds(self) -> int:
        """Difference between show duration and setlist duration"""
        return self.show_duration_seconds - self.total_duration_seconds

    @property
    def duration_difference_label(self) -> str:
        """Format duration difference"""
        diff = self.duration_difference_seconds

        if diff == 0:
            return "Perfect fit!"

        abs_diff = abs(diff)
        sign = "+" if diff > 0 else "-"

        if abs_diff >= 3600:
            hours = abs_diff // 3600
            minutes = (abs_diff % 3600) // 60
            return f"{sign}{hours}h {minutes}m"
        else:
            minutes = abs_diff // 60
            seconds = abs_diff % 60
            return f"{sign}{minutes}m {seconds}s"

    @property
    def exceeds_show_duration(self) -> bool:
        """Check if setlist exceeds the show duration"""
        return self.duration_difference_seconds < 0

    @property
    def show_duration_warning(self) -> str:
        """Generate warning message if setlist exceeds show duration"""
        if not self.show_start_time or not self.show_end_time:
            return None

        if self.exceeds_show_duration:
            diff_label = self.duration_difference_label
            setlist_duration = self.total_duration_label
            show_duration = self.show_duration_label

            return (f"⚠️ Setlist ({setlist_duration}) exceeds show duration ({show_duration}) "
                   f"by {diff_label.replace('-', '')}")

        return None


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

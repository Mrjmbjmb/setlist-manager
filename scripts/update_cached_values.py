#!/usr/bin/env python3
"""Script to update cached values for all existing setlists."""

import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setlist_manager import create_app
from setlist_manager.models import Setlist

def update_all_cached_values():
    """Update cached values for all setlists in the database."""
    app = create_app()

    with app.app_context():
        setlists = Setlist.query.all()
        print(f"Updating cached values for {len(setlists)} setlists...")

        for i, setlist in enumerate(setlists, 1):
            try:
                # Force load of entries to ensure we have the data
                _ = len(setlist.entries)

                # Update cached values
                setlist.cached_song_count = len(setlist.entries)
                setlist.cached_total_duration_seconds = setlist.total_duration_seconds

                print(f"  {i}/{len(setlists)}: Updated '{setlist.name}' - {setlist.cached_song_count} songs, {setlist.cached_total_duration_label}")
            except Exception as e:
                print(f"  Error updating setlist {setlist.id}: {e}")

        # Commit all changes at once
        try:
            from setlist_manager.database import db
            db.session.commit()
            print("✅ All cached values updated successfully!")
        except Exception as e:
            print(f"❌ Error committing changes: {e}")
            return 1

    return 0

if __name__ == "__main__":
    sys.exit(update_all_cached_values())
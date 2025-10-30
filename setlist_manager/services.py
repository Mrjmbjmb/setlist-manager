import random
from typing import List

from .models import Song


def generate_setlist(target_duration_seconds: int, songs: List[Song]) -> List[Song]:
    """Return an ordered list of songs that best fits the target duration."""
    if not songs:
        return []

    if not target_duration_seconds or target_duration_seconds <= 0:
        shuffled = songs[:]
        random.shuffle(shuffled)
        return shuffled

    shuffled = songs[:]
    random.shuffle(shuffled)

    best_fit = {0: []}

    for song in shuffled:
        snapshot = list(best_fit.items())
        for total, selection in snapshot:
            new_total = total + song.duration_seconds
            if new_total > target_duration_seconds:
                continue

            updated_selection = selection + [song]
            existing = best_fit.get(new_total)

            if existing is None:
                best_fit[new_total] = updated_selection
                continue

            existing_total = sum(track.duration_seconds for track in existing)
            updated_total = sum(track.duration_seconds for track in updated_selection)

            if updated_total > existing_total:
                best_fit[new_total] = updated_selection

    viable_totals = [total for total in best_fit.keys() if total > 0]
    if viable_totals:
        best_total = max(viable_totals)
        return best_fit[best_total]

    shortest_song = min(shuffled, key=lambda item: item.duration_seconds)
    return [shortest_song]

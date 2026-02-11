"""
Track selection module.

Provides functionality to analyze MIDI tracks and select the best track
for monophonic conversion (typically the melody track).
"""

from typing import Any, Dict, List, Optional

from .midi_parser import MidiMeta, MidiNote


def compute_track_stats(notes: List[MidiNote], track_idx: int) -> Dict[str, Any]:
    """
    Compute basic statistics for a track.

    Args:
        notes: List of all MIDI notes
        track_idx: Index of the track to analyze

    Returns:
        Dictionary containing track statistics:
        - track_index: The track index
        - note_count: Number of notes in the track
        - max_simul: Maximum simultaneous notes (polyphony measure)
        - min_pitch: Minimum pitch value
        - max_pitch: Maximum pitch value
        - avg_pitch: Average pitch value
    """
    tr_notes = [n for n in notes if n.track_index == track_idx and n.channel != 9]  # exclude drum channel(10)
    if not tr_notes:
        return {"track_index": track_idx, "note_count": 0, "max_simul": 999}

    events = []
    for n in tr_notes:
        events.append((n.start_tick, 1))
        events.append((n.end_tick, -1))
    events.sort()

    active = 0
    max_active = 0
    for _, d in events:
        active += d
        if active > max_active:
            max_active = active

    pitches = [n.pitch for n in tr_notes]
    return {
        "track_index": track_idx,
        "note_count": len(tr_notes),
        "max_simul": max_active,
        "min_pitch": min(pitches),
        "max_pitch": max(pitches),
        "avg_pitch": sum(pitches) / len(pitches),
    }


def select_best_track(
    metas: List[MidiMeta],
    notes: List[MidiNote],
    track_index: Optional[int] = None,
    track_name_contains: Optional[str] = None
) -> int:
    """
    Pick the best track for monophonic conversion.

    Selection strategy:
    1. If track_index is specified, use it
    2. If track_name_contains is specified, find matching track
    3. Otherwise, select track with lowest polyphony and most notes

    Args:
        metas: List of track metadata
        notes: List of all MIDI notes
        track_index: Optional specific track index to use
        track_name_contains: Optional substring to search in track names

    Returns:
        Index of the selected track

    Raises:
        ValueError: If no valid track is found
    """
    if track_index is not None:
        return track_index

    if track_name_contains:
        key = track_name_contains.lower()
        for i, m in enumerate(metas):
            if m.track_name and key in m.track_name.lower():
                if any(n.track_index == i and n.channel != 9 for n in notes):
                    return i

    stats = [compute_track_stats(notes, i) for i in range(len(metas))]
    stats = [s for s in stats if s["note_count"] > 0]

    if not stats:
        raise ValueError("No note events found in MIDI.")

    # prefer: lower polyphony, then more notes
    stats.sort(key=lambda s: (s["max_simul"], -s["note_count"]))
    return stats[0]["track_index"]

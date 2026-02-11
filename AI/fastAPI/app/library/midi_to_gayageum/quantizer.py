"""
Quantization and monophonic extraction module.

Provides functionality to quantize MIDI notes and extract a monophonic
event stream suitable for solo instrument notation.
"""

from typing import List, Optional, Tuple

from .midi_parser import MidiNote


def ticks_to_units(ticks: int, tpq: int, divisions_per_quarter: int) -> int:
    """
    Convert absolute ticks to quantized MusicXML 'units'.

    Args:
        ticks: MIDI tick value
        tpq: Ticks per quarter note
        divisions_per_quarter: MusicXML divisions per quarter note

    Returns:
        Quantized unit value
    """
    unit_ticks = tpq / divisions_per_quarter
    return int(round(ticks / unit_ticks))


def extract_monophonic_events(
    notes: List[MidiNote],
    tpq: int,
    track_idx: int,
    divisions_per_quarter: int,
) -> List[Tuple[str, int, int, Optional[int]]]:
    """
    Extract a monophonic event stream from MIDI notes.

    Returns a list of events:
      ("rest", start_unit, dur_unit, None)
      ("note", start_unit, dur_unit, pitch)

    Strategy:
    - quantize note start/end to grid
    - group notes with same start_unit, keep one (highest velocity, then highest pitch)
    - clamp overlaps to keep monophonic line

    Args:
        notes: List of all MIDI notes
        tpq: Ticks per quarter note
        track_idx: Index of track to extract
        divisions_per_quarter: MusicXML divisions per quarter note

    Returns:
        List of events as tuples (kind, start_unit, dur_unit, pitch)
    """
    tr_notes = [n for n in notes if n.track_index == track_idx and n.channel != 9]
    if not tr_notes:
        return []

    # quantize
    q = []
    for n in tr_notes:
        s = ticks_to_units(n.start_tick, tpq, divisions_per_quarter)
        e = ticks_to_units(n.end_tick, tpq, divisions_per_quarter)
        if e <= s:
            e = s + 1
        q.append((s, e, n.pitch, n.velocity))

    # group by start time
    by_start: dict[int, List[Tuple[int, int, int]]] = {}
    for s, e, p, v in q:
        by_start.setdefault(s, []).append((e, p, v))

    starts = sorted(by_start.keys())
    chosen = []
    for s in starts:
        # choose by velocity then pitch
        cand = by_start[s]
        cand.sort(key=lambda x: (x[2], x[1]))  # (vel, pitch)
        e, p, v = cand[-1]
        chosen.append((s, e, p))

    chosen.sort(key=lambda x: x[0])

    # build monophonic event stream with rests and clamping
    events: List[Tuple[str, int, int, Optional[int]]] = []
    cur = 0
    for s, e, p in chosen:
        if s > cur:
            events.append(("rest", cur, s - cur, None))
            cur = s
        if s < cur:
            s = cur
        dur = e - s
        if dur <= 0:
            continue
        events.append(("note", s, dur, p))
        cur = s + dur

    return events

"""
MIDI file parser module.

Provides functionality to parse Standard MIDI Files (SMF) and extract
note events and metadata.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple


def read_varlen(data: bytes, idx: int) -> Tuple[int, int]:
    """Read MIDI variable-length quantity."""
    value = 0
    while True:
        b = data[idx]
        idx += 1
        value = (value << 7) | (b & 0x7F)
        if (b & 0x80) == 0:
            break
    return value, idx


@dataclass
class MidiMeta:
    """Metadata extracted from a MIDI track."""
    tempo_us_per_quarter: Optional[int] = None  # microseconds per quarter
    time_sig: Optional[Tuple[int, int]] = None  # (numerator, denominator)
    track_name: Optional[str] = None


@dataclass
class MidiNote:
    """A note event from a MIDI file."""
    pitch: int
    start_tick: int
    end_tick: int
    velocity: int
    channel: int          # 0-15 (MIDI ch1 == 0)
    track_index: int


def parse_midi(path: str) -> Tuple[int, List[MidiMeta], List[MidiNote]]:
    """
    Parse a Standard MIDI File.

    Args:
        path: Path to the MIDI file

    Returns:
        Tuple containing:
        - tpq: ticks per quarter note
        - metas: per-track metadata (track name, first tempo, first time signature)
        - notes: all note events across all tracks

    Raises:
        ValueError: If the file is not a valid MIDI file
    """
    with open(path, "rb") as f:
        data = f.read()

    idx = 0
    if data[idx:idx + 4] != b"MThd":
        raise ValueError("Not a MIDI file: missing MThd")
    idx += 4
    header_len = struct.unpack(">I", data[idx:idx + 4])[0]
    idx += 4
    header = data[idx:idx + header_len]
    idx += header_len

    fmt, ntrks, division = struct.unpack(">HHH", header[:6])
    if division & 0x8000:
        raise ValueError("SMPTE time division is not supported in this script.")
    tpq = division

    metas: List[MidiMeta] = []
    notes: List[MidiNote] = []

    for t in range(ntrks):
        if data[idx:idx + 4] != b"MTrk":
            raise ValueError(f"Not a valid MIDI: missing MTrk at track {t}")
        idx += 4
        trk_len = struct.unpack(">I", data[idx:idx + 4])[0]
        idx += 4
        trk_end = idx + trk_len

        abs_tick = 0
        running_status: Optional[int] = None
        meta = MidiMeta()

        # key: (channel, pitch) -> list of (start_tick, velocity) (stack for overlaps)
        active: dict[Tuple[int, int], List[Tuple[int, int]]] = {}

        while idx < trk_end:
            delta, idx = read_varlen(data, idx)
            abs_tick += delta

            b = data[idx]
            if b < 0x80:
                # running status
                if running_status is None:
                    raise ValueError("Running status encountered without previous status.")
                status = running_status
            else:
                status = b
                idx += 1
                running_status = status

            if status == 0xFF:  # meta event
                meta_type = data[idx]
                idx += 1
                length, idx = read_varlen(data, idx)
                payload = data[idx:idx + length]
                idx += length

                # Running status is cancelled by system/common messages (incl. meta)
                running_status = None

                if meta_type == 0x03:  # track name
                    try:
                        meta.track_name = payload.decode(errors="replace")
                    except Exception:
                        meta.track_name = None
                elif meta_type == 0x51 and length == 3:  # tempo
                    tempo_us = payload[0] << 16 | payload[1] << 8 | payload[2]
                    if meta.tempo_us_per_quarter is None:
                        meta.tempo_us_per_quarter = tempo_us
                elif meta_type == 0x58 and length >= 2:  # time signature
                    nn = payload[0]
                    dd_pow = payload[1]
                    dd = 2 ** dd_pow
                    if meta.time_sig is None:
                        meta.time_sig = (nn, dd)
                continue

            if status in (0xF0, 0xF7):  # SysEx
                length, idx = read_varlen(data, idx)
                idx += length
                running_status = None
                continue

            evt_type = status & 0xF0
            ch = status & 0x0F

            if evt_type in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                d1 = data[idx]
                d2 = data[idx + 1]
                idx += 2

                if evt_type == 0x90:  # note on
                    pitch = d1
                    vel = d2
                    if vel == 0:
                        # note off (running note-on with vel 0)
                        key = (ch, pitch)
                        if key in active and active[key]:
                            start, svel = active[key].pop(0)
                            notes.append(MidiNote(pitch, start, abs_tick, svel, ch, t))
                    else:
                        key = (ch, pitch)
                        active.setdefault(key, []).append((abs_tick, vel))

                elif evt_type == 0x80:  # note off
                    pitch = d1
                    key = (ch, pitch)
                    if key in active and active[key]:
                        start, svel = active[key].pop(0)
                        notes.append(MidiNote(pitch, start, abs_tick, svel, ch, t))

                # other 2-byte events are ignored

            elif evt_type in (0xC0, 0xD0):  # program change / channel pressure
                idx += 1
            else:
                raise ValueError(f"Unknown MIDI status byte: 0x{status:02X}")

        # close any still-active notes at end of track
        for (ch, pitch), lst in active.items():
            for start, vel in lst:
                notes.append(MidiNote(pitch, start, abs_tick, vel, ch, t))

        metas.append(meta)
        idx = trk_end

    return tpq, metas, notes

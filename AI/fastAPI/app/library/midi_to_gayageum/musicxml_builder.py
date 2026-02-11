"""
MusicXML generation module.

Provides functionality to build MusicXML documents from monophonic
event streams.
"""

import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple


# MIDI pitch class to MusicXML step/alter mapping
STEP_ALTER = {
    0: ("C", 0),
    1: ("C", 1),
    2: ("D", 0),
    3: ("D", 1),
    4: ("E", 0),
    5: ("F", 0),
    6: ("F", 1),
    7: ("G", 0),
    8: ("G", 1),
    9: ("A", 0),
    10: ("A", 1),
    11: ("B", 0),
}

# Note type base durations (in quarter note units)
TYPE_BASE_UNITS = [
    ("whole", 4.0),
    ("half", 2.0),
    ("quarter", 1.0),
    ("eighth", 0.5),
    ("16th", 0.25),
    ("32nd", 0.125),
    ("64th", 0.0625),
    ("128th", 0.03125),
]


def midi_pitch_to_xml(pitch: int) -> Tuple[str, int, int]:
    """
    Convert MIDI pitch number to MusicXML step, alter, octave.

    Args:
        pitch: MIDI pitch number (0-127)

    Returns:
        Tuple of (step, alter, octave)
    """
    pc = pitch % 12
    step, alter = STEP_ALTER[pc]
    octave = (pitch // 12) - 1  # MIDI 60 -> C4
    return step, alter, octave


def duration_to_type_and_dots(units: int, divs: int) -> Tuple[Optional[str], int]:
    """
    Try to express duration as type + dots.

    If it doesn't match, return (None, 0) and we'll omit <type>.

    Args:
        units: Duration in MusicXML units
        divs: Divisions per quarter note

    Returns:
        Tuple of (note_type, dots) or (None, 0) if no match
    """
    for typ, qlen in TYPE_BASE_UNITS:
        base = divs * qlen
        for dots in range(3):
            mult = 1.0
            add = 0.5
            for _ in range(dots):
                mult += add
                add *= 0.5
            if abs(base * mult - units) < 1e-6:
                return typ, dots
    return None, 0


def build_musicxml(
    events: List[Tuple[str, int, int, Optional[int]]],
    divisions_per_quarter: int,
    tempo_bpm: float,
    time_sig: Tuple[int, int],
    title: str,
    instrument_name: str,
) -> ET.Element:
    """
    Build a MusicXML document from monophonic events.

    Args:
        events: List of events (kind, start_unit, dur_unit, pitch)
        divisions_per_quarter: MusicXML divisions per quarter note
        tempo_bpm: Tempo in beats per minute
        time_sig: Time signature as (numerator, denominator)
        title: Work title
        instrument_name: Name of the instrument

    Returns:
        XML ElementTree root element
    """
    beats, beat_type = time_sig
    measure_units = int(round(divisions_per_quarter * beats * (4 / beat_type)))
    if measure_units <= 0:
        measure_units = divisions_per_quarter * 4  # fallback 4/4

    score = ET.Element("score-partwise", version="3.1")

    work = ET.SubElement(score, "work")
    ET.SubElement(work, "work-title").text = title

    part_list = ET.SubElement(score, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = instrument_name

    score_inst = ET.SubElement(score_part, "score-instrument", id="P1-I1")
    ET.SubElement(score_inst, "instrument-name").text = instrument_name
    midi_inst = ET.SubElement(score_part, "midi-instrument", id="P1-I1")
    ET.SubElement(midi_inst, "midi-channel").text = "1"
    ET.SubElement(midi_inst, "midi-program").text = "0"

    part = ET.SubElement(score, "part", id="P1")

    measure_no = 1
    pos = 0
    measure = ET.SubElement(part, "measure", number=str(measure_no))

    # first measure: attributes
    attrs = ET.SubElement(measure, "attributes")
    ET.SubElement(attrs, "divisions").text = str(divisions_per_quarter)

    time_el = ET.SubElement(attrs, "time")
    ET.SubElement(time_el, "beats").text = str(beats)
    ET.SubElement(time_el, "beat-type").text = str(beat_type)

    clef = ET.SubElement(attrs, "clef")
    ET.SubElement(clef, "sign").text = "G"
    ET.SubElement(clef, "line").text = "2"

    # tempo direction
    direction = ET.SubElement(measure, "direction", placement="above")
    dir_type = ET.SubElement(direction, "direction-type")
    metro = ET.SubElement(dir_type, "metronome")
    ET.SubElement(metro, "beat-unit").text = "quarter"
    ET.SubElement(metro, "per-minute").text = str(int(round(tempo_bpm)))
    ET.SubElement(direction, "sound", tempo=str(tempo_bpm))

    def start_new_measure() -> None:
        nonlocal measure_no, measure, pos
        measure_no += 1
        measure = ET.SubElement(part, "measure", number=str(measure_no))
        pos = 0

    def add_rest(dur_units: int) -> None:
        n_el = ET.SubElement(measure, "note")
        ET.SubElement(n_el, "rest")
        ET.SubElement(n_el, "duration").text = str(dur_units)
        typ, dots = duration_to_type_and_dots(dur_units, divisions_per_quarter)
        if typ:
            ET.SubElement(n_el, "type").text = typ
            for _ in range(dots):
                ET.SubElement(n_el, "dot")

    def add_note(pitch: int, dur_units: int, tie_start: bool, tie_stop: bool) -> None:
        n_el = ET.SubElement(measure, "note")
        pitch_el = ET.SubElement(n_el, "pitch")
        step, alter, octave = midi_pitch_to_xml(pitch)
        ET.SubElement(pitch_el, "step").text = step
        if alter != 0:
            ET.SubElement(pitch_el, "alter").text = str(alter)
        ET.SubElement(pitch_el, "octave").text = str(octave)

        if tie_start:
            ET.SubElement(n_el, "tie", type="start")
        if tie_stop:
            ET.SubElement(n_el, "tie", type="stop")

        ET.SubElement(n_el, "duration").text = str(dur_units)

        typ, dots = duration_to_type_and_dots(dur_units, divisions_per_quarter)
        if typ:
            ET.SubElement(n_el, "type").text = typ
            for _ in range(dots):
                ET.SubElement(n_el, "dot")

        if tie_start or tie_stop:
            notations = ET.SubElement(n_el, "notations")
            if tie_start:
                ET.SubElement(notations, "tied", type="start")
            if tie_stop:
                ET.SubElement(notations, "tied", type="stop")

    # write events with measure splitting
    for kind, _start, dur, pitch in events:
        remaining = dur
        first_seg = True
        while remaining > 0:
            space = measure_units - pos
            if space == 0:
                start_new_measure()
                space = measure_units
            seg = min(remaining, space)

            if kind == "rest":
                add_rest(seg)
            else:
                # tie if split
                tie_start = remaining > seg
                tie_stop = not first_seg
                add_note(int(pitch), seg, tie_start=tie_start, tie_stop=tie_stop)

            pos += seg
            remaining -= seg
            first_seg = False

    # final barline
    barline = ET.SubElement(measure, "barline", location="right")
    ET.SubElement(barline, "bar-style").text = "light-heavy"
    return score


def to_pretty_xml(elem: ET.Element) -> str:
    """
    Pretty-print XML element (no external libs).

    Args:
        elem: XML ElementTree element

    Returns:
        Pretty-printed XML string
    """
    rough = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

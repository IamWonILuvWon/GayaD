#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
midi_to_gayageum_solo.py

의존성 없이(표준 라이브러리만) MIDI 파일을 읽어서
가야금 솔로용 "오선보 뼈대" MusicXML(.musicxml)로 변환합니다.

- 기본값: 4/4, 120 BPM, 1/32(32분) 격자 퀀타이즈
- MIDI 안에 템포/박자표가 있으면(메타 이벤트) 그 값을 우선 사용합니다.
  (단, 템포/박자표 변화가 여러 번 있는 복잡한 MIDI는 이 스크립트가 완벽히 표기하지 못할 수 있습니다.)
- 여러 트랙이 있을 때는 "가장 단선율(폴리포니가 적은) + 노트가 많은" 트랙을 자동 선택합니다.
  필요하면 --track-name 또는 --track-index로 직접 선택하세요.

출력된 .musicxml은 MuseScore / Dorico 등에서 열어서 PDF로 뽑으면 됩니다.
"""

import argparse
import os
import sys
from typing import Tuple

# Add the AI directory to the path so we can import the package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from midi_to_gayageum import (
    build_musicxml,
    parse_midi,
    select_best_track,
    extract_monophonic_events,
    to_pretty_xml,
)


def parse_time_sig(s: str) -> Tuple[int, int]:
    """Parse time signature string like '4/4' into tuple."""
    if "/" not in s:
        raise argparse.ArgumentTypeError("Time signature must look like '4/4'.")
    a, b = s.split("/", 1)
    return int(a.strip()), int(b.strip())


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Convert MIDI -> Gayageum solo MusicXML (staff notation)."
    )
    ap.add_argument("midi", help="input .mid/.midi file")
    ap.add_argument("-o", "--out", default=None, help="output .musicxml path")
    ap.add_argument(
        "--track-index",
        type=int,
        default=None,
        help="force track index (0-based)"
    )
    ap.add_argument(
        "--track-name",
        type=str,
        default=None,
        help="choose track whose name contains this substring"
    )
    ap.add_argument(
        "--tempo",
        type=float,
        default=None,
        help="tempo BPM (override MIDI; default 120 if missing)"
    )
    ap.add_argument(
        "--time",
        type=parse_time_sig,
        default=None,
        help="time signature like 4/4 (override MIDI; default 4/4 if missing)"
    )
    ap.add_argument(
        "--grid",
        type=int,
        default=32,
        help="quantize grid as note denominator (default 32 => 1/32 note). Must be divisible by 4."
    )
    ap.add_argument("--title", type=str, default=None, help="work title")
    ap.add_argument(
        "--instrument",
        type=str,
        default="Gayageum (solo)",
        help="instrument name to show in score"
    )

    args = ap.parse_args()

    if args.grid % 4 != 0:
        raise SystemExit("--grid must be divisible by 4 (e.g., 16, 32, 64).")

    divisions_per_quarter = args.grid // 4  # 32nd grid -> 8 divisions per quarter

    tpq, metas, notes = parse_midi(args.midi)

    # tempo/time signature: first found in any track, else defaults
    found_tempo = None
    found_time = None
    for m in metas:
        if found_tempo is None and m.tempo_us_per_quarter is not None:
            found_tempo = m.tempo_us_per_quarter
        if found_time is None and m.time_sig is not None:
            found_time = m.time_sig

    if args.tempo is not None:
        tempo_bpm = args.tempo
    elif found_tempo is not None:
        tempo_bpm = 60_000_000.0 / found_tempo
    else:
        tempo_bpm = 120.0

    if args.time is not None:
        time_sig = args.time
    elif found_time is not None:
        time_sig = found_time
    else:
        time_sig = (4, 4)

    track_idx = select_best_track(
        metas,
        notes,
        track_index=args.track_index,
        track_name_contains=args.track_name,
    )
    track_name = metas[track_idx].track_name or f"Track {track_idx}"

    events = extract_monophonic_events(notes, tpq, track_idx, divisions_per_quarter)
    if not events:
        raise SystemExit("Selected track has no notes.")

    # pitch range stats
    pitches = [p for (k, _, _, p) in events if k == "note" and p is not None]
    min_pitch = min(pitches)
    max_pitch = max(pitches)

    def midi_to_name(m: int) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (m // 12) - 1
        return f"{names[m % 12]}{octave}"

    title = args.title or f"Gayageum solo (from MIDI) — {os.path.basename(args.midi)}"

    xml_root = build_musicxml(
        events=events,
        divisions_per_quarter=divisions_per_quarter,
        tempo_bpm=tempo_bpm,
        time_sig=time_sig,
        title=title,
        instrument_name=args.instrument,
    )
    xml_text = to_pretty_xml(xml_root)

    out_path = args.out
    if out_path is None:
        base, _ = os.path.splitext(args.midi)
        out_path = base + "_gayageum.musicxml"

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml_text)

    print("=== MIDI -> MusicXML (Gayageum solo) ===")
    print(f"Input MIDI        : {args.midi}")
    print(f"Chosen track      : {track_idx} ({track_name})")
    print(f"Tempo / Time      : {tempo_bpm:.2f} BPM, {time_sig[0]}/{time_sig[1]}")
    print(f"Quantize grid     : 1/{args.grid} (divisions_per_quarter={divisions_per_quarter})")
    print(f"Pitch range       : {min_pitch}({midi_to_name(min_pitch)}) .. {max_pitch}({midi_to_name(max_pitch)})")
    print(f"Output MusicXML   : {out_path}")
    print("Open the .musicxml in MuseScore and export to PDF if needed.")


if __name__ == "__main__":
    main()

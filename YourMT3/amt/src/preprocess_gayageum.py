"""preprocess_gayageum.py

Preprocess Gayageum dataset into YourMT3 format (16k WAV + note events).
"""
import json
import os
import random
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import torchaudio

from utils.audio import get_audio_file_info, write_wav_file
from utils.midi import midi2note
from utils.note2event import note2note_event
from utils.utils import note_event2token2note_event_sanity_check

DEFAULT_FORCE_PROGRAM = 107  # GM "Koto" as a closest single-instrument proxy


def _resolve_raw_root(data_home: os.PathLike, raw_subdir: str) -> Path:
    raw_root = Path(raw_subdir)
    if not raw_root.is_absolute():
        raw_root = Path(data_home) / raw_subdir
    if (raw_root / "Training").exists():
        return raw_root
    candidate = raw_root / "Gayageum_dataset"
    if (candidate / "Training").exists():
        return candidate
    raise ValueError(f"Raw dataset root not found under: {raw_root}")


def _collect_pairs(split_root: Path) -> List[Tuple[Path, Path]]:
    pairs = []
    for wav_file in sorted(split_root.rglob("*.wav")):
        midi_file = wav_file.with_suffix(".mid")
        if not midi_file.exists():
            midi_file = wav_file.with_suffix(".midi")
        if not midi_file.exists():
            raise FileNotFoundError(f"Missing MIDI for: {wav_file}")
        pairs.append((wav_file, midi_file))
    return pairs


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resample_to_16k(src_wav: Path, dst_wav: Path, force: bool) -> None:
    if dst_wav.exists() and not force:
        return
    _ensure_dir(dst_wav)
    audio, sr = torchaudio.load(str(src_wav))
    if audio.ndim > 1:
        audio = audio.mean(dim=0, keepdim=True)
    if sr != 16000:
        audio = torchaudio.functional.resample(audio, sr, 16000)
    audio = audio.squeeze(0).numpy()
    write_wav_file(str(dst_wav), audio, samplerate=16000)


def _process_midi(src_midi: Path,
                  dst_midi: Path,
                  force_program: Optional[int],
                  force: bool,
                  sanity_check: bool) -> Tuple[Dict, Dict]:
    if dst_midi.exists() and not force:
        pass
    else:
        _ensure_dir(dst_midi)
        shutil.copy2(src_midi, dst_midi)

    notes, dur_sec = midi2note(
        str(dst_midi),
        binary_velocity=True,
        ch_9_as_drum=False,
        force_all_drum=False,
        force_all_program_to=force_program if force_program is not None else None,
        trim_overlap=True,
        fix_offset=True,
        quantize=True,
        verbose=0,
        minimum_offset_sec=0.01,
        drum_offset_sec=0.01,
        ignore_pedal=False)

    if force_program is not None:
        for note in notes:
            note.program = int(force_program)
            note.is_drum = False

    programs = sorted({note.program for note in notes})
    is_drum = [1 if program == 128 else 0 for program in programs]

    notes_dict = {
        "gayageum_id": dst_midi.stem,
        "program": programs,
        "is_drum": is_drum,
        "duration_sec": dur_sec,
        "notes": notes,
    }
    note_events_dict = {
        "gayageum_id": dst_midi.stem,
        "program": programs,
        "is_drum": is_drum,
        "duration_sec": dur_sec,
        "note_events": note2note_event(notes),
    }

    if sanity_check:
        note_event2token2note_event_sanity_check(note_events_dict["note_events"], notes_dict["notes"])

    return notes_dict, note_events_dict


def _split_pairs(pairs: List[Tuple[Path, Path]],
                 val_ratio: float,
                 test_ratio: float,
                 seed: int) -> Tuple[List[Tuple[Path, Path]], List[Tuple[Path, Path]], List[Tuple[Path, Path]]]:
    rng = random.Random(seed)
    pairs = pairs[:]
    rng.shuffle(pairs)
    n_total = len(pairs)
    n_val = int(n_total * val_ratio)
    n_test = int(n_total * test_ratio)
    val_pairs = pairs[:n_val]
    test_pairs = pairs[n_val:n_val + n_test]
    train_pairs = pairs[n_val + n_test:]
    return train_pairs, val_pairs, test_pairs


def preprocess_gayageum_16k(
    data_home: os.PathLike,
    dataset_name: str = "gayageum",
    raw_subdir: str = "raw",
    manifest_name: str = "manifest.json",
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
    force: bool = False,
    force_program: Optional[int] = DEFAULT_FORCE_PROGRAM,
    sanity_check: bool = False,
) -> None:
    """
    Preprocess Gayageum dataset to 16k WAV and YourMT3 index format.

    Writes:
        - {data_home}/{dataset_name}_yourmt3_16k/**: resampled audio + copied MIDI
        - {data_home}/yourmt3_indexes/{dataset_name}_{split}_file_list.json
    """
    base_dir = Path(data_home) / f"{dataset_name}_yourmt3_16k"
    output_index_dir = Path(data_home) / "yourmt3_indexes"
    output_index_dir.mkdir(parents=True, exist_ok=True)

    raw_root = _resolve_raw_root(data_home, raw_subdir)
    train_root = raw_root / "Training"
    val_root = raw_root / "Validation"

    train_pairs = _collect_pairs(train_root)
    val_pairs = _collect_pairs(val_root) if val_root.exists() else []

    splits: Dict[str, List[Tuple[Path, Path]]] = {"train": train_pairs}
    if val_pairs:
        splits["validation"] = val_pairs
    else:
        train_pairs, val_pairs, test_pairs = _split_pairs(train_pairs, val_ratio, test_ratio, seed)
        splits["train"] = train_pairs
        if val_pairs:
            splits["validation"] = val_pairs
        if test_pairs:
            splits["test"] = test_pairs

    manifest_entries = []

    for split, pairs in splits.items():
        file_list = {}
        for i, (wav_file, midi_file) in enumerate(pairs):
            rel_path = wav_file.relative_to(raw_root)
            out_wav = base_dir / split / rel_path
            out_mid = out_wav.with_suffix(".mid")

            _resample_to_16k(wav_file, out_wav, force=force)
            notes_dict, note_events_dict = _process_midi(midi_file,
                                                         out_mid,
                                                         force_program=force_program,
                                                         force=force,
                                                         sanity_check=sanity_check)

            notes_file = out_mid.with_suffix("")
            notes_file = notes_file.with_name(notes_file.name + "_notes.npy")
            note_events_file = out_mid.with_suffix("")
            note_events_file = note_events_file.with_name(note_events_file.name + "_note_events.npy")

            if force or not notes_file.exists():
                _ensure_dir(notes_file)
                np.save(notes_file, notes_dict, allow_pickle=True, fix_imports=False)
            if force or not note_events_file.exists():
                _ensure_dir(note_events_file)
                np.save(note_events_file, note_events_dict, allow_pickle=True, fix_imports=False)

            fs, n_frames, n_channels = get_audio_file_info(str(out_wav))
            if fs != 16000 or n_channels != 1:
                raise ValueError(f"Expected 16k mono WAV, got fs={fs}, ch={n_channels}: {out_wav}")

            file_list[i] = {
                "gayageum_id": out_mid.stem,
                "n_frames": n_frames,
                "mix_audio_file": str(out_wav),
                "notes_file": str(notes_file),
                "note_events_file": str(note_events_file),
                "midi_file": str(out_mid),
                "program": notes_dict["program"],
                "is_drum": notes_dict["is_drum"],
            }

            manifest_entries.append({
                "split": split,
                "id": out_mid.stem,
                "raw_wav": str(wav_file),
                "raw_midi": str(midi_file),
                "wav_16k": str(out_wav),
                "midi_16k": str(out_mid),
                "notes": str(notes_file),
                "note_events": str(note_events_file),
            })

        output_index_file = output_index_dir / f"{dataset_name}_{split}_file_list.json"
        with open(output_index_file, "w") as f:
            json.dump(file_list, f, indent=4)
        print(f"Created {output_index_file}")

    if manifest_name:
        manifest_path = base_dir / manifest_name
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, "w") as f:
            json.dump(manifest_entries, f, indent=2)
        print(f"Created {manifest_path}")
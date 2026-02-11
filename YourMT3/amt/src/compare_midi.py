# compare_midi.py
import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pretty_midi
import matplotlib.pyplot as plt
from mir_eval.transcription import precision_recall_f1_overlap
from mir_eval.util import midi_to_hz

INDEX_RE = re.compile(r"^(?P<dataset>.+)_(?P<split>[^_]+)_file_list\.json$")
SPLIT_RANK = {"test": 0, "validation": 1, "val": 1, "train": 2}


def resolve_repo_root():
    return Path(__file__).resolve().parents[2]


def resolve_path(path_str, base):
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def pick_data_home(args, repo_root):
    if args.data_home:
        return resolve_path(args.data_home, repo_root)
    env = os.environ.get("DATA_HOME")
    if env:
        return resolve_path(env, repo_root)
    return repo_root / "data"


def pick_logs_roots(args, repo_root):
    roots = []
    if args.logs_root:
        roots.append(resolve_path(args.logs_root, repo_root))
    env = os.environ.get("WANDB_SAVE_DIR")
    if env:
        roots.append(resolve_path(env, repo_root))
    roots.append(repo_root / "amt" / "logs")
    roots.append(repo_root / "logs")
    uniq = []
    for root in roots:
        if root not in uniq:
            uniq.append(root)
    return [root for root in uniq if root.exists()]


def collect_pred_midis(logs_roots):
    candidates = []
    for root in logs_roots:
        candidates.extend(root.rglob("model_output/**/*.mid"))
    return candidates


def pick_pred_midi(candidates, track_id=None):
    if track_id:
        candidates = [p for p in candidates if p.stem == track_id]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def extract_track_id(meta):
    for key, value in meta.items():
        if key.endswith("_id"):
            return str(value)
    return None


def build_index_map(index_dir):
    index_map = defaultdict(list)
    if not index_dir.exists():
        return index_map
    for path in index_dir.glob("*_file_list.json"):
        match = INDEX_RE.match(path.name)
        if not match:
            continue
        dataset = match.group("dataset")
        split = match.group("split")
        with open(path, "r") as f:
            data = json.load(f)
        for meta in data.values():
            track_id = extract_track_id(meta)
            midi_file = meta.get("midi_file")
            if track_id and midi_file:
                index_map[track_id].append({
                    "midi_file": midi_file,
                    "dataset": dataset,
                    "split": split,
                })
    return index_map


def guess_dataset_for_track(index_map, track_id):
    datasets = {m["dataset"] for m in index_map.get(track_id, [])}
    if len(datasets) == 1:
        return next(iter(datasets))
    return None


def find_ref_midi(track_id, index_map, dataset_hint=None):
    matches = index_map.get(track_id, [])
    if dataset_hint:
        matches = [m for m in matches if m["dataset"] == dataset_hint]
    if not matches:
        return None, None
    matches.sort(key=lambda m: SPLIT_RANK.get(m["split"], 99))
    best = matches[0]
    return Path(best["midi_file"]), best


def fallback_ref_midi(track_id, data_home):
    if not data_home or not data_home.exists():
        return None
    candidates = list(data_home.rglob(f"{track_id}.mid"))
    if not candidates:
        return None
    preferred = [p for p in candidates if "_yourmt3_16k" in str(p)]
    return preferred[0] if preferred else candidates[0]


def load_midi(path, shift_to_zero=True):
    pm = pretty_midi.PrettyMIDI(path)
    if shift_to_zero:
        notes = [n for inst in pm.instruments for n in inst.notes]
        if notes:
            t0 = min(n.start for n in notes)
            if t0 > 0:
                for n in notes:
                    n.start -= t0
                    n.end -= t0
    return pm


def notes_from_pm(pm, ignore_drums=True):
    notes = []
    for inst in pm.instruments:
        if ignore_drums and inst.is_drum:
            continue
        for n in inst.notes:
            notes.append((n.pitch, n.start, n.end))
    return notes


def to_arrays(notes):
    if not notes:
        return np.array([]), np.zeros((0, 2))
    pitches = np.array([midi_to_hz(p) for p, s, e in notes])
    intervals = np.array([[s, e] for p, s, e in notes])
    return pitches, intervals


def note_f1(est_notes, ref_notes, onset_tol=0.05, offset_ratio=0.2):
    est_p, est_i = to_arrays(est_notes)
    ref_p, ref_i = to_arrays(ref_notes)
    if len(ref_p) == 0 and len(est_p) == 0:
        return np.nan, np.nan, np.nan
    p, r, f, _ = precision_recall_f1_overlap(
        ref_i, ref_p, est_i, est_p,
        onset_tolerance=onset_tol,
        pitch_tolerance=50.0,
        offset_ratio=offset_ratio
    )
    return p, r, f


def plot_rolls(pm_ref, pm_est, output_path, fs=100):
    roll_ref = pm_ref.get_piano_roll(fs=fs)
    roll_est = pm_est.get_piano_roll(fs=fs)
    max_len = max(roll_ref.shape[1], roll_est.shape[1])
    if roll_ref.shape[1] < max_len:
        roll_ref = np.pad(roll_ref, ((0, 0), (0, max_len - roll_ref.shape[1])))
    if roll_est.shape[1] < max_len:
        roll_est = np.pad(roll_est, ((0, 0), (0, max_len - roll_est.shape[1])))

    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.imshow(roll_ref, aspect="auto", origin="lower")
    plt.title("Reference MIDI Piano Roll")
    plt.ylabel("MIDI pitch")

    plt.subplot(2, 1, 2)
    plt.imshow(roll_est, aspect="auto", origin="lower")
    plt.title("Estimated MIDI Piano Roll")
    plt.xlabel("Time (frames)")
    plt.ylabel("MIDI pitch")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--est", help="predicted MIDI path (auto if omitted)")
    parser.add_argument("--ref", help="reference MIDI path (auto if omitted)")
    parser.add_argument("--track_id", help="force track id (stem name)")
    parser.add_argument("--dataset", help="dataset name for lookup")
    parser.add_argument("--data_home", help="override data home")
    parser.add_argument("--logs_root", help="override logs root")
    parser.add_argument("--fs", type=int, default=100)
    parser.add_argument("--onset_tol", type=float, default=0.05)
    parser.add_argument("--offset_ratio", type=float, default=0.2)
    parser.add_argument("--save_fig", help="save plot to path (default: alongside est midi)")
    parser.add_argument("--no_plot", action="store_true", help="skip plot generation")
    args = parser.parse_args()

    repo_root = resolve_repo_root()
    data_home = pick_data_home(args, repo_root)
    logs_roots = pick_logs_roots(args, repo_root)

    if args.est:
        est_path = Path(args.est)
    else:
        candidates = collect_pred_midis(logs_roots)
        est_path = pick_pred_midi(candidates, track_id=args.track_id)

    if not est_path or not est_path.exists():
        raise FileNotFoundError(
            "No predicted MIDI found. Run test with -w true and check logs under amt/logs."
        )

    track_id = args.track_id or est_path.stem
    index_map = build_index_map(data_home / "yourmt3_indexes")
    dataset_hint = args.dataset or guess_dataset_for_track(index_map, track_id)

    ref_info = None
    if args.ref:
        ref_path = Path(args.ref)
    else:
        ref_path, ref_info = find_ref_midi(track_id, index_map, dataset_hint=dataset_hint)
        if ref_path is None:
            ref_path = fallback_ref_midi(track_id, data_home)

    if not ref_path or not Path(ref_path).exists():
        raise FileNotFoundError(
            f"No reference MIDI found for track_id={track_id}. "
            "Pass --ref or set DATA_HOME."
        )

    print(f"Estimated MIDI: {est_path}")
    if ref_info:
        print(f"Reference MIDI: {ref_path} (dataset={ref_info['dataset']}, split={ref_info['split']})")
    else:
        print(f"Reference MIDI: {ref_path}")

    pm_ref = load_midi(ref_path, shift_to_zero=True)
    pm_est = load_midi(est_path, shift_to_zero=True)

    ref_notes = notes_from_pm(pm_ref, ignore_drums=True)
    est_notes = notes_from_pm(pm_est, ignore_drums=True)

    p, r, f = note_f1(est_notes, ref_notes, args.onset_tol, args.offset_ratio)
    print(f"Note F1 (onset+offset): P={p:.3f} R={r:.3f} F1={f:.3f}")

    if not args.no_plot:
        if args.save_fig:
            output_path = Path(args.save_fig)
        else:
            output_path = est_path.with_suffix(".png")
        plot_rolls(pm_ref, pm_est, output_path=output_path, fs=args.fs)
        print(f"Saved plot: {output_path}")


if __name__ == "__main__":
    main()

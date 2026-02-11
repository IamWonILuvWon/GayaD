from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent / "amt" / "src"))

import os
from model_helper import load_model_checkpoint, transcribe

#exp_id = "ptf_all_cross_rebal5_mirst_xk2_edr005_attend_c_full_plus_b100@model.ckpt"  # or "my_exp@epoch=2-step=12345.ckpt"
exp_id = "gayageum_ft_001@last.ckpt"
project = "gayageum"
task = "mt3_full_plus"
audio_path = "examples/Slakh_test_1884.wav"

ckpt_args = [exp_id, "-p", project, "-tk", task]
model = load_model_checkpoint(args=ckpt_args, device="cuda")

audio_info = {
    "filepath": audio_path,
    "track_name": os.path.splitext(os.path.basename(audio_path))[0],
}
midi_path = transcribe(model, audio_info)
print("Saved MIDI:", midi_path)

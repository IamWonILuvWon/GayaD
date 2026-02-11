export CUDA_VISIBLE_DEVICES=1

EXP_ID="${1:-gayageum_ft_001}"
PROJECT="gayageum"

# default ckpt for gayageum init (override by env if needed)
CKPT_MODE="${CKPT_MODE:-init}"
CKPT_PATH="${CKPT_PATH:-/workspace/code/YourMT3/amt/logs/2024/notask_all_cross_v6_xk2_amp0811_gm_ext_plus_nops_b72/checkpoints/model.ckpt}"
CKPT_ARGS=()
if [ -n "${CKPT_MODE:-}" ]; then
  CKPT_ARGS+=(--ckpt-mode "${CKPT_MODE}")
fi
if [ -n "${CKPT_PATH:-}" ]; then
  CKPT_ARGS+=(--ckpt-path "${CKPT_PATH}")
fi


export DATA_HOME="/workspace/code/YourMT3/data"     # ✅ 전처리 출력 위치 = 학습이 찾는 위치
export RAW_SUBDIR="/workspace/code/YourMT3/Gayageum_dataset"  # ✅ 원본 데이터 절대경로
export PYTHONPATH="/workspace/code/YourMT3/amt/src"

python - <<'PY'
import os
from preprocess_gayageum import preprocess_gayageum_16k

preprocess_gayageum_16k(
    data_home=os.environ["DATA_HOME"],
    raw_subdir=os.environ["RAW_SUBDIR"],
    dataset_name="gayageum",
    force_program=46,
    force=False,
)
PY

python /workspace/code/YourMT3/amt/src/train.py "${EXP_ID}" \
  -p "${PROJECT}" \
  -d gayageum \
  -tk gm_ext_plus \
  -wb disabled \
  -xk 0 \
  -bsz 15 30 \
  -e 50 \
  -se 12000 \
  "${CKPT_ARGS[@]}"

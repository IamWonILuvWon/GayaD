import json, shutil
from pathlib import Path

IN_ROOT = Path("/path/to/dataset_root")   # 전체 데이터 폴더
OUT_ROOT = Path("/path/to/out_gayageum")  # 가야금만 모을 폴더
OUT_ROOT.mkdir(parents=True, exist_ok=True)

# 악기 코드(문서 기준)
GAYAGEUM_CODE = "SP01"  # 가야금 :contentReference[oaicite:4]{index=4}

# JSON에서 악기코드를 찾아내는 유틸(필드명이 제각각일 수 있어 방어적으로)
CODE_KEYS = ["instrument_code", "inst_code", "악기코드", "악기_코드", "instrumentId", "instrument"]
NAME_KEYS = ["instrument_name", "inst_name", "악기명", "악기", "instrumentName"]

def is_gayageum(meta: dict, json_path: Path) -> bool:
    # 1) 코드 키로 탐색
    for k in CODE_KEYS:
        if k in meta and str(meta[k]).strip() == GAYAGEUM_CODE:
            return True

    # 2) 모든 키를 훑으면서 값이 SP01인 곳이 있는지(방어 로직)
    for k, v in meta.items():
        if isinstance(v, (str, int)) and str(v).strip() == GAYAGEUM_CODE:
            if any(x in k.lower() for x in ["inst", "instrument", "code", "악기"]):
                return True

    # 3) 악기명 텍스트로 탐색
    for k in NAME_KEYS:
        if k in meta and isinstance(meta[k], str) and ("가야금" in meta[k]):
            return True

    # 4) 백업: 파일 경로/이름에 SP01 포함
    if GAYAGEUM_CODE in str(json_path):
        return True

    return False

def paired_paths(json_path: Path):
    stem = json_path.with_suffix("")  # .json 제거
    # 흔한 케이스: 같은 폴더에 stem.wav, stem.mid
    wav = stem.with_suffix(".wav")
    mid = stem.with_suffix(".mid")
    return wav, mid

cnt = 0
for json_path in IN_ROOT.rglob("*.json"):
    try:
        meta = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        continue

    if not is_gayageum(meta, json_path):
        continue

    wav_path, mid_path = paired_paths(json_path)

    # 페어링 검증
    if not (wav_path.exists() and mid_path.exists()):
        continue

    # 복사(또는 용량 절약하려면 symlink 추천)
    out_dir = OUT_ROOT / json_path.parent.name
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(json_path, out_dir / json_path.name)
    shutil.copy2(wav_path, out_dir / wav_path.name)
    shutil.copy2(mid_path, out_dir / mid_path.name)
    cnt += 1

print("exported:", cnt)

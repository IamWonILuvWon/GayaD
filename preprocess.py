import json, shutil
from pathlib import Path

IN_ROOT = Path("KoranMusicData")   # 전체 데이터 폴더
TRAINING_DIR = IN_ROOT / "Training"
VALIDATION_DIR = IN_ROOT / "Validation"
OUT_ROOT = Path("Gayageum_dataset")  # 가야금만 모을 폴더
OUT_ROOT.mkdir(parents=True, exist_ok=True)

# 악기 코드(문서 기준)
GAYAGEUM_CODE = "SP01"  # 가야금

# JSON에서 악기코드를 찾아내는 유틸(필드명이 제각각일 수 있어 방어적으로)
CODE_KEYS = ["instrument_code", "inst_code", "악기코드", "악기_코드", "instrumentId", "instrument", "instrument_cd"]
NAME_KEYS = ["instrument_name", "inst_name", "악기명", "악기", "instrumentName"]

def is_gayageum(meta: dict, json_path: Path) -> bool:
    # 1) music_type_info.instrument_cd 확인 (가장 정확한 방법)
    if "music_type_info" in meta:
        music_type = meta["music_type_info"]
        if isinstance(music_type, dict) and "instrument_cd" in music_type:
            if str(music_type["instrument_cd"]).strip() == GAYAGEUM_CODE:
                return True
    
    # 2) 코드 키로 탐색
    for k in CODE_KEYS:
        if k in meta and str(meta[k]).strip() == GAYAGEUM_CODE:
            return True

    # 3) 모든 키를 훑으면서 값이 SP01인 곳이 있는지(방어 로직)
    for k, v in meta.items():
        if isinstance(v, (str, int)) and str(v).strip() == GAYAGEUM_CODE:
            if any(x in k.lower() for x in ["inst", "instrument", "code", "악기"]):
                return True

    # 4) 악기명 텍스트로 탐색
    for k in NAME_KEYS:
        if k in meta and isinstance(meta[k], str) and ("가야금" in meta[k]):
            return True

    # 5) 백업: 파일 경로/이름에 SP01 포함
    if GAYAGEUM_CODE in str(json_path):
        return True

    return False

def find_paired_files(json_path: Path, search_dir: Path):
    """
    JSON 파일명을 기반으로 01.원천데이터 폴더에서 .wav와 .mid 파일을 찾습니다.
    """
    stem = json_path.stem  # 파일명에서 확장자 제거 (예: AP_C09_02194)
    
    # 01.원천데이터 폴더 경로 찾기
    source_data_dir = search_dir / "01.원천데이터"
    
    if not source_data_dir.exists():
        return None, None
    
    # 01.원천데이터 폴더 전체에서 파일명으로 검색
    wav_files = list(source_data_dir.rglob(f"{stem}.wav"))
    mid_files = list(source_data_dir.rglob(f"{stem}.mid"))
    
    wav_path = wav_files[0] if wav_files else None
    mid_path = mid_files[0] if mid_files else None
    
    return wav_path, mid_path

cnt = 0
# Training과 Validation 폴더만 탐색
search_dirs = []
if TRAINING_DIR.exists():
    search_dirs.append(TRAINING_DIR)
if VALIDATION_DIR.exists():
    search_dirs.append(VALIDATION_DIR)

if not search_dirs:
    print("Error: Training 또는 Validation 폴더를 찾을 수 없습니다.")
    exit(1)

for search_dir in search_dirs:
    print(f"Processing {search_dir.name} folder...")
    for json_path in search_dir.rglob("*.json"):
        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Warning: Failed to parse {json_path}: {e}")
            continue

        if not is_gayageum(meta, json_path):
            continue

        wav_path, mid_path = find_paired_files(json_path, search_dir)

        # 페어링 검증
        if wav_path is None or mid_path is None or not (wav_path.exists() and mid_path.exists()):
            print(f"Warning: Missing paired files for {json_path.name}")
            continue

        # 출력 디렉토리 구조 유지 (Training/Validation 구분)
        relative_path = json_path.relative_to(search_dir)
        out_dir = OUT_ROOT / search_dir.name / relative_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 복사
        shutil.copy2(json_path, out_dir / json_path.name)
        shutil.copy2(wav_path, out_dir / wav_path.name)
        shutil.copy2(mid_path, out_dir / mid_path.name)
        cnt += 1
        print(f"  Copied: {json_path.name}")

print(f"\nTotal exported: {cnt} files")

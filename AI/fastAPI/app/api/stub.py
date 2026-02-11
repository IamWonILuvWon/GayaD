from __future__ import annotations

import os
import uuid
import shutil
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from intergrations.next_callback import notify_next

from library.midi_to_gayageum import (
    parse_midi,
    select_best_track,
    extract_monophonic_events,
    build_musicxml,
    to_pretty_xml,
)

router = APIRouter()

# 백엔드에 넣어둔 테스트 악보
ASSET_TEST_SCORE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "test_score.pdf")
)

class StubRequest(BaseModel):
    jobId: str
    inputPath: str  # Next.js에서 넘어오는 음원 경로 (MIDI 파일 또는 오디오)
    callbackUrl: str
    # callbackToken: str

class StubResponse(BaseModel):
    job_id: str
    score_key: str

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def _convert_audio_to_midi(
    audio_path: Path,
    out_midi_path: Path,
) -> None:
    """
    음원 파일(오디오)을 MIDI 파일로 변환하는 파이프라인.
    
    TODO: 음원 → MIDI 변환 로직 구현 필요
    현재는 placeholder 함수로, 실제 구현 시 음성 인식/분석 로직이 들어갈 예정.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # TODO: 음원 파일을 MIDI로 변환하는 로직 구현
    # 예: Librosa, Madmom, Essentia 등의 라이브러리를 사용하여 음원 분석
    # 그 결과를 MIDI 파일로 생성
    raise NotImplementedError(
        f"Audio to MIDI conversion is not yet implemented. "
        f"Received: {audio_path.name}"
    )


def _convert_midi_to_musicxml(
    midi_path: Path,
    out_path: Path,
    tempo_bpm: Optional[float] = None,
    time_sig: Optional[Tuple[int, int]] = None,
) -> None:
    """
    MIDI 파일을 가야금 솔로 MusicXML로 변환하는 파이프라인.

    1) MIDI 파싱
    2) 트랙 선택
    3) 단선 이벤트 추출
    4) MusicXML 생성 및 저장
    """
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    tpq, metas, notes = parse_midi(str(midi_path))

    # tempo/time signature: 첫 번째 값 사용, 필요시 요청에서 override
    found_tempo = None
    found_time = None
    for m in metas:
        if found_tempo is None and m.tempo_us_per_quarter is not None:
            found_tempo = m.tempo_us_per_quarter
        if found_time is None and m.time_sig is not None:
            found_time = m.time_sig

    if tempo_bpm is not None:
        tempo = tempo_bpm
    elif found_tempo is not None:
        tempo = 60_000_000.0 / found_tempo
    else:
        tempo = 120.0

    if time_sig is not None:
        ts = time_sig
    elif found_time is not None:
        ts = found_time
    else:
        ts = (4, 4)

    track_idx = select_best_track(metas, notes)

    # 1/32 그리드 기준 (기존 CLI와 동일)
    divisions_per_quarter = 8
    events = extract_monophonic_events(
        notes,
        tpq,
        track_idx,
        divisions_per_quarter,
    )
    if not events:
        raise RuntimeError("Selected track has no notes.")

    title = f"Gayageum solo — {midi_path.name}"

    xml_root = build_musicxml(
        events=events,
        divisions_per_quarter=divisions_per_quarter,
        tempo_bpm=tempo,
        time_sig=ts,
        title=title,
        instrument_name="Gayageum (solo)",
    )
    xml_text = to_pretty_xml(xml_root)
    _ensure_dir(out_path.parent)
    out_path.write_text(xml_text, encoding="utf-8")

@router.post("/stub/submit", response_model=StubResponse)
async def submit_job(req: StubRequest):
    """
    통합 음악 처리 엔드포인트.
    
    처리 흐름:
    1. 음원 파일(오디오) → MIDI 파일로 변환
    2. MIDI 파일 → MusicXML로 변환
    3. 완료 후 콜백 알림
    
    입력: LOCAL_STORAGE_ROOT 기준 파일 경로 (req.inputPath)
    출력: LOCAL_STORAGE_ROOT 아래 output/{jobId}/score.musicxml
    완료 후: callbackUrl로 상태를 알림
    """
    storage_root = os.getenv("LOCAL_STORAGE_ROOT")
    
    if not storage_root:
        raise HTTPException(status_code=500, detail="LOCAL_STORAGE_ROOT is not set in env")
    
    job_id = req.jobId
    try:
        # 입력 파일 경로 확인
        input_path = Path(storage_root + "/" + req.inputPath)
        if not input_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Input file not found at LOCAL_STORAGE_ROOT/{req.inputPath}",
            )
        
        # 출력 디렉토리 준비
        out_dir = storage_root + "/storage/output/" + job_id
        _ensure_dir(Path(out_dir))
        
        # 파일 확장자에 따라 처리 분기
        file_ext = input_path.suffix.lower()
        
        # Step 1: 음원 → MIDI 변환 또는 MIDI 파일 직접 사용
        if file_ext == ".mid" or file_ext == ".midi":
            # MIDI 파일: 직접 사용
            midi_path = input_path
        else:
            # 오디오 파일: MIDI로 변환
            midi_path = Path(out_dir) / f"intermediate_{job_id}.mid"
            _convert_audio_to_midi(input_path, midi_path)
        
        # Step 2: MIDI → MusicXML 변환
        out_musicxml = Path(out_dir + "/" + "score.musicxml")
        _convert_midi_to_musicxml(midi_path, out_musicxml)
        score_key = f"output/{job_id}/score.musicxml"
        
    except HTTPException:
        # HTTPException은 그대로 전파
        raise
    except Exception as e:
        # 기타 예외는 콜백으로 실패 알리고 HTTP 에러 반환
        await notify_next(job_id, req.callbackUrl, {
            "status": "failed",
            "outputPath": None,
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
    
    # 성공 콜백
    await notify_next(job_id, req.callbackUrl, {
        "status": "completed",
        "outputPath": score_key,
        "error": None,
    })

    return StubResponse(
        job_id=job_id,
        score_key=score_key,
    )

@router.post("/test")
async def test():
    return {"status": "ok"}
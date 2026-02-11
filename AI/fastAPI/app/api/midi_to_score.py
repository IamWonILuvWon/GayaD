from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from midi_to_gayageum import (
    parse_midi,
    select_best_track,
    extract_monophonic_events,
    build_musicxml,
    to_pretty_xml,
)

from intergrations.next_callback import notify_next


router = APIRouter()


class MidiJobRequest(BaseModel):
    jobId: str
    inputPath: str  # LOCAL_STORAGE_ROOT 기준 MIDI 파일 경로 (예: "input/xxx/file.mid")
    callbackUrl: str


class MidiJobResponse(BaseModel):
    job_id: str
    score_key: str  # LOCAL_STORAGE_ROOT 기준 MusicXML 경로 (예: "output/{job_id}/score.musicxml")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _convert_midi_to_musicxml(
    midi_path: Path,
    out_path: Path,
    tempo_bpm: Optional[float] = None,
    time_sig: Optional[Tuple[int, int]] = None,
) -> None:
    """
    Blocking 변환 함수.

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


@router.post("/midi/submit", response_model=MidiJobResponse)
async def submit_midi_job(req: MidiJobRequest):
    """
    MIDI 파일을 가야금 솔로 MusicXML로 변환하는 작업을 제출하는 엔드포인트.

    - 입력: LOCAL_STORAGE_ROOT 기준 MIDI 경로 (req.inputPath)
    - 출력: LOCAL_STORAGE_ROOT 아래 output/{jobId}/score.musicxml
    - 완료 후: callbackUrl로 상태를 알림
    """
    storage_root = os.getenv("LOCAL_STORAGE_ROOT")
    if not storage_root:
        raise HTTPException(status_code=500, detail="LOCAL_STORAGE_ROOT is not set in env")

    storage_root_path = Path(storage_root)

    midi_path = storage_root_path / req.inputPath
    if not midi_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"MIDI file not found at LOCAL_STORAGE_ROOT/{req.inputPath}",
        )

    # output/{jobId}/score.musicxml 형태로 저장
    job_id = req.jobId
    out_rel = Path("output") / job_id / "score.musicxml"
    out_abs = storage_root_path / out_rel

    try:
        # 동기 변환 (필요시 to_thread.run_sync로 옮길 수 있음)
        _convert_midi_to_musicxml(midi_path, out_abs)
    except Exception as e:
        # 실패 시 Next에 실패 상태 알리고 HTTP 에러 반환
        await notify_next(job_id, req.callbackUrl, {
            "status": "failed",
            "outputPath": None,
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Failed to convert MIDI: {e}")

    score_key = str(out_rel).replace(os.sep, "/")

    # 성공 콜백
    await notify_next(job_id, req.callbackUrl, {
        "status": "completed",
        "outputPath": score_key,
        "error": None,
    })

    return MidiJobResponse(
        job_id=job_id,
        score_key=score_key,
    )


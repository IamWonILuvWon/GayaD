# midi_to_gayageum Package

MIDI 파일을 가야금 솔로용 MusicXML로 변환하는 모듈러 패키지입니다.

## 구조

```
midi_to_gayageum/
├── __init__.py          # 패키지 초기화 및 공개 API
├── midi_parser.py       # MIDI 파일 파싱
├── track_selector.py    # 트랙 선택 및 통계 계산
├── quantizer.py         # 퀀타이제이션 및 단선화
└── musicxml_builder.py  # MusicXML 생성
```

## 모듈 설명

### `midi_parser.py`
- `MidiMeta`: 트랙 메타데이터 (템포, 박자표, 트랙명)
- `MidiNote`: MIDI 노트 이벤트
- `parse_midi()`: Standard MIDI File 파싱

### `track_selector.py`
- `compute_track_stats()`: 트랙 통계 계산
- `select_best_track()`: 단선율 트랙 자동 선택

### `quantizer.py`
- `ticks_to_units()`: MIDI ticks를 MusicXML units로 변환
- `extract_monophonic_events()`: 단선 이벤트 스트림 추출

### `musicxml_builder.py`
- `build_musicxml()`: MusicXML 문서 생성
- `to_pretty_xml()`: XML 포맷팅
- `midi_pitch_to_xml()`: MIDI 피치를 MusicXML 형식으로 변환
- `duration_to_type_and_dots()`: 음표 길이를 표준 음표 타입으로 변환

## 사용 예시

```python
from midi_to_gayageum import (
    parse_midi,
    select_best_track,
    extract_monophonic_events,
    build_musicxml,
    to_pretty_xml,
)

# MIDI 파일 파싱
tpq, metas, notes = parse_midi("input.mid")

# 최적 트랙 선택
track_idx = select_best_track(metas, notes)

# 단선 이벤트 추출
events = extract_monophonic_events(notes, tpq, track_idx, divisions_per_quarter=8)

# MusicXML 생성
xml_root = build_musicxml(
    events=events,
    divisions_per_quarter=8,
    tempo_bpm=120.0,
    time_sig=(4, 4),
    title="My Song",
    instrument_name="Gayageum (solo)",
)

# XML 문자열로 변환
xml_text = to_pretty_xml(xml_root)
```

## 장점

1. **모듈화**: 각 기능이 독립적인 모듈로 분리되어 유지보수가 쉬움
2. **재사용성**: 각 모듈을 독립적으로 사용 가능
3. **테스트 용이성**: 각 모듈을 개별적으로 테스트 가능
4. **확장성**: 새로운 기능 추가가 용이

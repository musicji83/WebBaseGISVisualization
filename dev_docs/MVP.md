# MVP (Minimum Viable Product)

## Burwood Station 3D Buildings Visualization

---

## 1. MVP 정의

### 1.1 MVP 범위

> **한 문장 요약**: Burwood Station 반경 500m 건물을 자동으로 수집 → QGIS 프로젝트 구성 → 브라우저에서 3D 인터랙티브 시각화

| 항목 | 내용 |
|------|------|
| **핵심 가치** | 비개발자도 터미널 한 줄로 3D 건물 시각화 완성 |
| **MVP 버전** | v1.0 |
| **목표 완료** | 2026-03-02 |
| **상태** | ✅ 완료 |

### 1.2 MVP에 포함된 것 vs 제외된 것

| ✅ 포함 (MVP) | ❌ 제외 (향후) |
|---------------|---------------|
| Burwood Station 고정 좌표 | 사용자 좌표 입력 |
| 500m 고정 반경 | 가변 반경 |
| 기존 GeoJSON 재사용 | 실시간 API 호출 |
| 높이별 6단계 색상 | 사용자 커스텀 색상 |
| 마우스 회전/확대/이동 | 키보드 단축키 |
| 건물 hover 툴팁 | 건물 검색/필터링 |
| 다크 테마 배경지도 | 테마 전환 |
| 로컬 HTTP 서버 | 클라우드 배포 |

---

## 2. MVP 아키텍처

### 2.1 시스템 구성도

```
┌─────────────────────────────────────────────────┐
│                    사용자                         │
│         python3 run_all_steps.py 실행             │
└──────────────────┬──────────────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    ▼                             ▼
┌─────────────┐          ┌──────────────────┐
│  QGIS 경로  │          │  웹 3D 경로       │
│  (자동화)   │          │  (시각화)         │
├─────────────┤          ├──────────────────┤
│             │          │                  │
│ run_all_    │  같은    │ burwood_3d_      │
│ steps.py    │ GeoJSON  │ viewer.html      │
│    ↓        │ ◄──────► │    ↓             │
│ QGIS MCP    │  공유    │ deck.gl          │
│    ↓        │          │    ↓             │
│ PyQGIS      │          │ WebGL 렌더링     │
│    ↓        │          │    ↓             │
│ PNG + QGZ   │          │ 인터랙티브 3D    │
└─────────────┘          └──────────────────┘
```

### 2.2 파일 구조

```
QGIS_MCP/
├── dev_docs/                    # 개발 문서
│   ├── PRD.md
│   ├── CRM.md
│   ├── MVP.md
│   └── BUILD_PROCESS.md
│
├── qgis_mcp/                    # MCP 서버 + QGIS 플러그인 (upstream)
│   ├── src/qgis_mcp/
│   │   ├── qgis_mcp_server.py   # FastMCP 서버 (15개 도구)
│   │   └── qgis_socket_client.py
│   └── qgis_mcp_plugin/
│       └── qgis_mcp_plugin.py   # QGIS 플러그인 (소켓 서버)
│
├── burwood_3d_step1_setup.py    # Step 1: 프로젝트 초기 설정
├── burwood_3d_step2_buildings.py # Step 2: Overpass API 건물 수집
├── burwood_3d_step3_style.py    # Step 3: 높이별 그라데이션 스타일
├── burwood_3d_step4_3dview.py   # Step 4: 3D Extrusion 설정
├── burwood_3d_step5_render.py   # Step 5: PNG 렌더링 + QGZ 저장
│
├── run_all_steps.py             # 원클릭 자동화 스크립트
├── auto_start_mcp.py            # QGIS --code MCP 자동 시작
├── burwood_3d_viewer.html       # 웹 3D 뷰어 (deck.gl)
│
├── burwood_buildings.geojson    # 건물 데이터 (513개)
├── burwood_2d_map.png           # 2D 렌더링 이미지
├── burwood_3d.qgz              # QGIS 프로젝트 파일
└── CLAUDE.md                    # 프로젝트 가이드
```

---

## 3. MVP 핵심 기능 상세

### 3.1 자동화 파이프라인 (`run_all_steps.py`)

```
실행: python3 run_all_steps.py

[1] QGIS 실행 확인 → 꺼져있으면 --code 플래그로 자동 시작
[2] MCP 서버 대기 (최대 30초, 1초 간격 ping)
[3] Step 1: 프로젝트 초기 설정 (OSM + 핀 + 버퍼)
[4] Step 2: 건물 GeoJSON 로드 (513개 피처)
[5] Step 3: 높이별 6단계 그라데이션 스타일 적용
[6] Step 5: 2D PNG 렌더링 + .qgz 프로젝트 저장  ← 순서 주의!
[7] Step 4: 3D Extrusion 렌더러 설정              ← 마지막에 실행
```

**실행 순서가 1→2→3→5→4인 이유**:
`setRenderer3D()`가 QGIS 내부 상태를 오염시켜 이후 `exec()` 명령이 segfault를 일으킴.
렌더링/저장을 먼저 완료한 뒤, 3D 설정은 마지막에 실행하여 크래시 영향을 최소화.

### 3.2 웹 3D 뷰어 (`burwood_3d_viewer.html`)

| 기능 | 구현 방법 |
|------|----------|
| 3D 건물 렌더링 | deck.gl `GeoJsonLayer` (extruded: true) |
| 높이별 돌출 | `getElevation: feature.properties.height * 1.5` |
| 높이별 색상 | `getColorByHeight()` 함수 (6단계 RdBu 팔레트) |
| 마우스 인터랙션 | deck.gl `controller: true` (회전/확대/이동/기울기) |
| 건물 툴팁 | `onHover` 이벤트 → DOM tooltip 업데이트 |
| 배경지도 | MapLibre GL + CARTO dark-matter 타일 |
| 조명 | deck.gl `LightingEffect` (ambient + sun) |
| Burwood 핀 | `ScatterplotLayer` (빨간 점) |

**실행 방법**:
```bash
cd /Users/link4eeg/Desktop/QGIS_MCP
python3 -m http.server 8080 --bind 127.0.0.1 &
open http://localhost:8080/burwood_3d_viewer.html
```

### 3.3 QGIS MCP 통신

```
run_all_steps.py                    QGIS 플러그인
     │                                    │
     │  TCP 연결 (localhost:9876)          │
     ├───────────────────────────────────►│
     │                                    │
     │  {"type":"execute_code",           │
     │   "params":{"code":"..."}}         │
     ├───────────────────────────────────►│
     │                                    │  exec(code) 실행
     │                                    │  ↓
     │  {"status":"success",              │
     │   "result":{"stdout":"..."}}       │
     │◄───────────────────────────────────┤
     │                                    │
```

---

## 4. MVP 검증 결과

### 4.1 기능 검증

| 테스트 항목 | 기대 결과 | 실제 결과 | 판정 |
|------------|----------|----------|------|
| `run_all_steps.py` 실행 | 5개 Step 모두 성공 | 5개 모두 ✅ | PASS |
| QGIS 자동 시작 | --code로 MCP 서버 자동 시작 | 6~7초 내 연결 | PASS |
| 건물 레이어 로드 | 513개 피처 | 513개 확인 | PASS |
| PNG 렌더링 | 파일 생성 + 2,657KB | 정상 생성 | PASS |
| QGZ 저장 | 프로젝트 파일 생성 | 정상 저장 | PASS |
| 웹 3D 뷰어 | 건물 3D 표시 | 513개 모두 렌더링 | PASS |
| 마우스 회전 | 오른쪽 드래그로 회전 | 정상 동작 | PASS |
| 건물 hover 툴팁 | 이름 + 높이 표시 | 정상 표시 | PASS |

### 4.2 알려진 제한사항

| 제한사항 | 영향 | 해결 방안 |
|---------|------|----------|
| Burwood 좌표 하드코딩 | 다른 지역 분석 불가 | v1.1에서 파라미터화 |
| QGIS 3D Map View 불가 | macOS segfault | 웹 뷰어로 대체 (현재 동작) |
| 로컬 HTTP 서버 필요 | 추가 실행 단계 | v2.0에서 정적 호스팅 |
| CDN 의존 | 오프라인 불가 | 로컬 번들링 고려 |

---

## 5. MVP → v1.1 개선 계획

| 개선 항목 | 현재 (v1.0) | 목표 (v1.1) |
|----------|------------|------------|
| 좌표 입력 | Burwood 하드코딩 | CLI 파라미터 또는 입력 폼 |
| 반경 설정 | 500m 고정 | 100m ~ 2km 선택 |
| 데이터 소스 | 기존 GeoJSON 파일 | Overpass API 실시간 호출 |
| 배포 | 로컬 HTTP 서버 | GitHub Pages 또는 Vercel |
| 테마 | 다크 테마 고정 | 다크/라이트 전환 |

# BUILD PROCESS (구축 프로세스)

## Burwood 3D 웹 뷰어 구축 과정

---

## 1. 전체 프로세스 개요

```
📡 1단계: 데이터 수집        →  Overpass API → GeoJSON
     ↓
🗺️ 2단계: QGIS 프로젝트 구성  →  MCP 서버 경유 자동화
     ↓
🌐 3단계: 웹 3D 시각화        →  deck.gl + MapLibre
```

**소요 시간**: 전체 파이프라인 약 90초 (QGIS 시작 포함)

---

## 2. 1단계: 건물 데이터 수집

### 2.1 데이터 소스

| 항목 | 내용 |
|------|------|
| **API** | OpenStreetMap Overpass API |
| **엔드포인트** | `https://overpass-api.de/api/interpreter` |
| **쿼리 방식** | Overpass QL (영역 내 building 태그 검색) |
| **좌표** | Burwood Station: 위도 -33.8773, 경도 151.1043 |
| **반경** | 500m |

### 2.2 Overpass 쿼리

```
[out:json][timeout:30];
(
  way["building"](around:500, -33.8773, 151.1043);
  relation["building"](around:500, -33.8773, 151.1043);
);
out body;
>;
out skel qt;
```

### 2.3 데이터 처리 흐름

```
Overpass API 응답 (OSM JSON)
    ↓ osm_id, coordinates, tags 추출
    ↓ building:levels → height 변환 (1층 = 3m)
    ↓ 이미 height 태그가 있으면 그대로 사용
GeoJSON FeatureCollection 생성
    ↓
burwood_buildings.geojson 저장 (221KB)
```

### 2.4 결과 데이터 구조

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[151.1027, -33.8780], ...]]
      },
      "properties": {
        "osm_id": 19183152,
        "building": "yes",
        "name": "Burwood Plaza",
        "height": 9.0,
        "levels": "3"
      }
    }
  ]
}
```

| 필드 | 설명 | 예시 |
|------|------|------|
| `osm_id` | OpenStreetMap 고유 ID | 19183152 |
| `building` | 건물 유형 태그 | "yes", "residential", "commercial" |
| `name` | 건물 이름 (없으면 빈 문자열) | "Burwood Plaza" |
| `height` | 건물 높이 (미터) | 9.0 |
| `levels` | 층수 (문자열) | "3" |

### 2.5 데이터 통계

| 항목 | 값 |
|------|-----|
| 총 건물 수 | 513개 |
| 파일 크기 | 221KB |
| 높이 범위 | 3m ~ 60m+ |
| 좌표계 | WGS84 (EPSG:4326) |

---

## 3. 2단계: QGIS 프로젝트 자동 구성

### 3.1 통신 아키텍처

```
┌────────────────┐    TCP Socket     ┌──────────────────┐
│  run_all_       │    (JSON)         │  QGIS 플러그인    │
│  steps.py      │ ◄──────────────► │  (QTimer 100ms)   │
│                │    localhost:9876  │                   │
│  send_command()│                   │  process_server() │
│       ↓        │                   │       ↓           │
│  소켓 전송     │   ──────────►    │  exec(code)       │
│       ↓        │                   │       ↓           │
│  응답 수신     │   ◄──────────    │  PyQGIS 실행      │
└────────────────┘                   └──────────────────┘
```

### 3.2 QGIS 자동 시작 메커니즘

```
python3 run_all_steps.py
    │
    ├─ QGIS 실행 중? (pgrep -f QGIS)
    │   ├─ Yes → 바로 MCP 서버 대기
    │   └─ No  → QGIS 시작:
    │           /Applications/QGIS.app/Contents/MacOS/QGIS --code auto_start_mcp.py
    │                                                           │
    │           auto_start_mcp.py 내부:                          │
    │           QTimer.singleShot(3000ms) ─────────────────────►│
    │                                                           │
    │           3초 후:                                          │
    │           QgisMCPServer(port=9876, iface=iface).start()   │
    │           builtins._mcp_auto_server = server  (GC 방지)   │
    │
    ├─ MCP 서버 대기 (최대 30초, 1초 간격 ping)
    │   └─ {"type": "ping"} → {"status": "success", "result": {"pong": true}}
    │
    └─ Step 실행 시작
```

### 3.3 Step 실행 순서 및 상세

#### Step 1: 프로젝트 초기 설정 (`burwood_3d_step1_setup.py`)

```
새 QGIS 프로젝트 생성
    ↓
QgsRasterLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    → OpenStreetMap 배경지도 추가
    ↓
QgsVectorLayer("Point") + QgsPointXY(151.1043, -33.8773)
    → Burwood Station 핀 마커 (빨간 별)
    ↓
native:buffer (500m, segments=72)
    → 500m 반경 버퍼 (파란 점선 원)
    ↓
iface.mapCanvas().setExtent(buffer_extent)
    → 맵 뷰를 버퍼 영역으로 줌
```

#### Step 2: 건물 레이어 로드

```
QgsVectorLayer(GEOJSON_PATH, "Buildings", "ogr")
    → burwood_buildings.geojson을 QGIS 벡터 레이어로 로드
    → 513개 폴리곤 피처 확인
    → QgsProject.instance().addMapLayer(layer)
```

#### Step 3: 높이별 그라데이션 스타일 (`burwood_3d_step3_style.py`)

```
QgsGraduatedSymbolRenderer 설정:
    ┌────────────┬────────────────┬────────────┐
    │  범위       │  색상 (RGB)    │  라벨       │
    ├────────────┼────────────────┼────────────┤
    │  0 ~ 6m    │  #2166ac 파랑  │  1-2층      │
    │  6 ~ 12m   │  #67a9cf 연파랑│  2-4층      │
    │  12 ~ 20m  │  #d1e5f0 하늘  │  4-7층      │
    │  20 ~ 35m  │  #fddbc7 연주황│  7-12층     │
    │  35 ~ 60m  │  #ef8a62 주황  │  12-20층    │
    │  60m+      │  #b2182b 빨강  │  20층 이상  │
    └────────────┴────────────────┴────────────┘

레이어 순서: Pin(위) → Buffer → Buildings → OSM(아래)
```

#### Step 5: 렌더링 & 저장 (`burwood_3d_step5_render.py`) — Step 4보다 먼저 실행

```
3D 렌더러 임시 제거 (saveAsImage 크래시 방지):
    for layer in layers:
        if layer.renderer3D():
            saved_3d_renderers[layer_id] = r3d.clone()
            layer.setRenderer3D(None)
    ↓
iface.mapCanvas().saveAsImage("burwood_2d_map.png")
    → 2D 맵 PNG 렌더링 (2,657KB)
    ↓
3D 렌더러 복원
    ↓
QgsProject.instance().write("burwood_3d.qgz")
    → 프로젝트 파일 저장
```

#### Step 4: 3D 설정 (`burwood_3d_step4_3dview.py`) — 마지막에 실행

```
QgsPolygon3DSymbol() 생성:
    → height 속성 = QgsProperty("height")  (건물 높이만큼 돌출)
    → material = 밝은 회색-파랑 Phong shading
    ↓
QgsVectorLayer3DRenderer(symbol)
    → Buildings 레이어에 3D 렌더러 설정
    ↓
⚠️ createNewMapCanvas3D() → macOS segfault
    → 사용자에게 수동 열기 안내
    → 또는 웹 3D 뷰어 사용 권장
```

### 3.4 Step 실행 순서가 1→2→3→5→4인 이유

```
문제: setRenderer3D() 호출 후 QGIS 상태 오염
    ↓
Step 4 실행 → setRenderer3D() → QGIS 내부 상태 변경
    ↓
이후 어떤 exec() 명령이든 segfault 발생
    (심지어 project.write() 같은 단순 명령도 크래시)
    ↓
해결: Step 5(저장)를 Step 4(3D) 앞으로 이동
    → 모든 파일이 안전하게 저장된 후 3D 설정
    → Step 4에서 크래시되어도 결과물은 이미 확보
```

---

## 4. 3단계: 웹 3D 시각화

### 4.1 기술 선택 배경

| 후보 기술 | 장점 | 단점 | 선택 |
|----------|------|------|------|
| QGIS 3D Map View | QGIS 내장, 통합 | macOS segfault | ❌ |
| Three.js | 유연, 커스텀 자유 | GeoJSON 처리 직접 구현 | ❌ |
| CesiumJS | 지구본, 고정밀 지형 | 무겁고 복잡 | ❌ |
| **deck.gl** | **GeoJSON 네이티브, 경량, 인터랙티브** | CDN 의존 | ✅ |

### 4.2 deck.gl 렌더링 파이프라인

```
[1] HTML 로드
    ↓
[2] deck.gl + MapLibre CDN 로드
    ↓
[3] fetch('./burwood_buildings.geojson')
    → GeoJSON 데이터 로드 (HTTP 서버 필요)
    ↓
[4] GeoJsonLayer 생성
    ├── extruded: true                    → 폴리곤을 3D로 돌출
    ├── getElevation: height * 1.5        → 높이값으로 돌출 높이 결정
    ├── getFillColor: getColorByHeight()  → 높이별 6단계 색상
    ├── pickable: true                    → 마우스 인터랙션 활성화
    └── onHover: tooltip 업데이트         → 건물 정보 표시
    ↓
[5] DeckGL 인스턴스 생성
    ├── mapStyle: CARTO dark-matter       → 다크 테마 배경지도
    ├── initialViewState:
    │   ├── longitude/latitude: Burwood   → 초기 카메라 위치
    │   ├── zoom: 15.5                    → 확대 수준
    │   ├── pitch: 55°                    → 기울기 (3D 느낌)
    │   └── bearing: -30°                 → 회전각
    ├── controller: true                  → 마우스 조작 활성화
    └── effects: LightingEffect           → 조명 효과
    ↓
[6] WebGL 캔버스에 렌더링
    → 60fps 인터랙티브 3D 뷰 완성
```

### 4.3 높이→색상 매핑 함수

```javascript
function getColorByHeight(height) {
    if (height <= 6)  return [33, 102, 172];   // #2166ac 파랑
    if (height <= 12) return [103, 169, 207];  // #67a9cf 연파랑
    if (height <= 20) return [209, 229, 240];  // #d1e5f0 하늘
    if (height <= 35) return [253, 219, 199];  // #fddbc7 연주황
    if (height <= 60) return [239, 138, 98];   // #ef8a62 주황
    return [178, 24, 43];                       // #b2182b 빨강
}
```

QGIS Step 3의 `QgsGraduatedSymbolRenderer`와 동일한 RdBu(Red-Blue) 팔레트 사용.

### 4.4 HTTP 서버가 필요한 이유

```
file:///path/to/viewer.html
    ↓ fetch('./burwood_buildings.geojson')
    ❌ CORS 에러 (브라우저 보안 정책: file:// 에서 다른 file:// fetch 차단)

http://localhost:8080/burwood_3d_viewer.html
    ↓ fetch('./burwood_buildings.geojson')
    ✅ 같은 origin이므로 CORS 통과
```

### 4.5 UI 구성 요소

```
┌──────────────────────────────────────────────────────┐
│  ┌─────────────────────┐                             │
│  │ 🏙️ Burwood Station  │                             │
│  │ 3D Buildings        │          3D 건물 뷰         │
│  │ 📍 Sydney NSW       │       (deck.gl 캔버스)       │
│  │ 🏢 건물 513개       │                             │
│  └─────────────────────┘                             │
│                                                      │
│                    [ 건물들이 3D로                     │
│                      돌출되어 표시 ]                   │
│                                                      │
│                                   ┌────────────────┐ │
│  ┌──────────────────┐             │ 🏢 건물 높이    │ │
│  │ 🖱️ 조작법:       │             │ ■ 0~6m (1-2층) │ │
│  │ 왼쪽 드래그: 이동 │             │ ■ 6~12m        │ │
│  │ 오른쪽: 회전     │             │ ■ 12~20m       │ │
│  │ 스크롤: 확대     │             │ ■ 20~35m       │ │
│  │ Ctrl: 기울기     │             │ ■ 35~60m       │ │
│  └──────────────────┘             │ ■ 60m+         │ │
│                                   └────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 5. 트러블슈팅 이력

### 5.1 해결된 문제들

| # | 문제 | 원인 | 해결 방법 |
|---|------|------|----------|
| 1 | QGIS 반복 실행 시 크래시 | QTimer 재진입(reentrancy) | `self._processing` 플래그로 process_server() 보호 |
| 2 | 플러그인 수정 미반영 | 심볼릭 링크가 아닌 복사본 | 플러그인 디렉토리에 직접 복사 + `__pycache__` 삭제 |
| 3 | Step 5에서 항상 크래시 | setRenderer3D() 후 상태 오염 | Step 순서 변경: 1→2→3→5→4 |
| 4 | createNewMapCanvas3D() 크래시 | macOS Metal/OpenGL 충돌 | 웹 기반 deck.gl 3D 뷰어로 대체 |
| 5 | QAction 트리거로도 3D 뷰 크래시 | QGIS 내부 3D 엔진 문제 | AppleScript도 실패 → 웹 뷰어 확정 |
| 6 | Overpass API 504 타임아웃 | 서버 과부하 | 기존 GeoJSON 파일 재사용 |
| 7 | startup.py 미실행 | QGIS 프로필 설정 문제 | `--code` 플래그 방식으로 전환 |
| 8 | HTTP 서버 404 | 잘못된 디렉토리에서 실행 | QGIS_MCP 디렉토리에서 실행 |

### 5.2 알려진 미해결 이슈

| # | 이슈 | 영향 | 우회 방법 |
|---|------|------|----------|
| 1 | QGIS 3D Map View macOS 불가 | QGIS 내장 3D 사용 불가 | 웹 뷰어 사용 |
| 2 | setRenderer3D() 상태 오염 | Step 4 이후 MCP 통신 불가 | Step 4를 마지막에 실행 |
| 3 | CDN 오프라인 불가 | 인터넷 없으면 웹 뷰어 안 열림 | 로컬 번들링 필요 |

---

## 6. 재현 가이드

### 6.1 전체 파이프라인 실행

```bash
# 1. QGIS 자동 시작 + Step 1~5 실행
cd /Users/link4eeg/Desktop/QGIS_MCP
python3 run_all_steps.py

# 2. 웹 3D 뷰어 실행
python3 -m http.server 8080 --bind 127.0.0.1 &
open http://localhost:8080/burwood_3d_viewer.html
```

### 6.2 웹 뷰어만 실행 (GeoJSON이 이미 있을 때)

```bash
cd /Users/link4eeg/Desktop/QGIS_MCP
python3 -m http.server 8080 --bind 127.0.0.1 &
open http://localhost:8080/burwood_3d_viewer.html
```

### 6.3 QGIS 프로젝트만 열기

```bash
open /Users/link4eeg/Desktop/QGIS_MCP/burwood_3d.qgz
```

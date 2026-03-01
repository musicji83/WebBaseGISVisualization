# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QGIS MCP (Model Context Protocol) connects QGIS to Claude AI via socket-based communication. Based on the [BlenderMCP](https://github.com/ahujasid/blender-mcp) project.

## Architecture

Two-component system communicating over TCP sockets (JSON protocol, default port 9876):

```
Claude AI → MCP Server (FastMCP) → TCP Socket → QGIS Plugin (Qt timer-polled) → PyQGIS APIs
```

### Component 1: MCP Server (`qgis_mcp/src/qgis_mcp/`)
- `qgis_mcp_server.py` — FastMCP server with 15 `@mcp.tool()` endpoints. Uses a global persistent socket connection (`_qgis_connection`) with reconnection logic. All tools return `json.dumps(result)`.
- `qgis_socket_client.py` — Standalone socket client class (`QgisMCPClient`) for testing without MCP. Has a `main()` with hardcoded demo paths.

### Component 2: QGIS Plugin (`qgis_mcp/qgis_mcp_plugin/`)
- `qgis_mcp_plugin.py` — Three classes in one file:
  - `QgisMCPServer(QObject)` — Non-blocking socket server using `QTimer` (100ms polling). Command dispatch via `handlers` dict in `execute_command()`. All handlers accept `**kwargs`.
  - `QgisMCPDockWidget(QDockWidget)` — UI with port selector (1024-65535), start/stop buttons, status label.
  - `QgisMCPPlugin` — QGIS plugin interface (`initGui`/`unload`/`classFactory`).
- `__init__.py` — Just re-exports `classFactory`.
- `metadata.txt` — QGIS plugin registry metadata.

### Socket Protocol
```json
// Request
{"type": "command_name", "params": {"key": "value"}}
// Response
{"status": "success", "result": {...}}
{"status": "error", "message": "error text"}
```

Both sides buffer incomplete JSON and attempt parse on each chunk received.

## Commands

### Run MCP Server
```bash
cd qgis_mcp
uv run src/qgis_mcp/qgis_mcp_server.py
```

### Install Dependencies
```bash
cd qgis_mcp
uv sync
```

### Install QGIS Plugin (symlink)
Mac:
```bash
ln -s $(pwd)/qgis_mcp/qgis_mcp_plugin ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/qgis_mcp
```

### Claude Desktop Config (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "qgis": {
      "command": "uv",
      "args": ["--directory", "/ABSOLUTE/PATH/TO/qgis_mcp/src/qgis_mcp", "run", "qgis_mcp_server.py"]
    }
  }
}
```

## Key Constraints

- **Python >= 3.12** (specified in `pyproject.toml` and `.python-version`)
- **QGIS 3.X** required (tested on 3.22). Plugin code uses PyQGIS (`qgis.core`, `qgis.gui`, `qgis.PyQt`)
- **Single dependency**: `mcp[cli]>=1.3.0` (managed via `uv`)
- **No test suite** exists — validation is manual
- `get_project_info` limits layer listing to 10; `get_layer_features` defaults to 10 features
- `execute_code` tool runs arbitrary PyQGIS via `exec()` — powerful but unsafe
- The MCP server's `QgisMCPServer` class (confusingly same name as the plugin's server class) uses `self.sock` for connection health check but the actual attribute is `self.socket` — known bug in `get_qgis_connection()`

## Workspace Layout

- `qgis_mcp/` — The actual git repo (upstream: `jjsantos01/qgis_mcp`)
- `burwood_3d_step[1-5]_*.py` — PyQGIS scripts for a Burwood Station 3D buildings tutorial (run sequentially in QGIS Python console, Korean comments)
- `burwood_buildings.geojson`, `burwood_3d.qgz`, `burwood_2d_map.png` — Tutorial data files
- `burwood_3d_viewer.html` — deck.gl 기반 인터랙티브 3D 웹 뷰어
- `run_all_steps.py` — QGIS 자동 실행 + MCP 서버 대기 + Step 1~5 일괄 실행
- `auto_start_mcp.py` — QGIS `--code` 플래그로 실행되는 MCP 서버 자동 시작 스크립트
- `startup.py` — QGIS 프로필 startup 스크립트 (현재 미사용, `--code` 방식으로 대체)

## Burwood 3D 시각화 구축 프로세스

### 전체 흐름

```
📡 데이터 수집 (Overpass API)
    ↓
🗺️ QGIS 프로젝트 구성 (MCP 서버 경유)
    ↓
🌐 웹 3D 시각화 (deck.gl)
```

### 1단계: 건물 데이터 수집

```
OpenStreetMap Overpass API → burwood_buildings.geojson (221KB, 513개 건물)
```

- **데이터 소스**: OpenStreetMap의 Overpass API
- **검색 조건**: Burwood Station 반경 500m 내 `building=*` 태그가 있는 모든 건물
- **결과**: 513개 건물 폴리곤 + 속성 (height, levels, name, osm_id)
- **파일 형식**: GeoJSON (좌표 + 속성을 담는 지리 데이터 표준 포맷)

### 2단계: QGIS 프로젝트 구성 (MCP 서버 경유)

```
터미널 (run_all_steps.py)
    ↓ TCP 소켓 (localhost:9876)
QGIS MCP 플러그인 (QTimer 100ms 폴링)
    ↓ exec() 로 PyQGIS 코드 실행
QGIS 내부 엔진
```

| Step | 내용 | 핵심 API |
|------|------|----------|
| Step 1 | 프로젝트 초기 설정 (OSM 배경 + 핀 + 500m 버퍼) | QgsRasterLayer, QgsVectorLayer |
| Step 2 | 건물 레이어 로드 | QgsVectorLayer("ogr") |
| Step 3 | 높이별 6단계 그라데이션 스타일링 | QgsGraduatedSymbolRenderer |
| Step 5 | 2D PNG 렌더링 + .qgz 프로젝트 저장 | canvas.saveAsImage(), project.write() |
| Step 4 | 3D Extrusion 설정 | QgsVectorLayer3DRenderer, QgsPolygon3DSymbol |

**실행 순서**: 1→2→3→**5→4** (Step 4의 `setRenderer3D()`가 QGIS 내부 상태를 망가뜨려서 저장을 먼저 수행)

**자동 실행 방법**:
```bash
python3 run_all_steps.py
```
- QGIS가 꺼져있으면 `--code auto_start_mcp.py` 플래그로 자동 실행
- MCP 서버 연결 대기 (최대 30초) 후 Step 실행

### 3단계: 웹 3D 시각화 (deck.gl)

QGIS 3D Map View가 macOS에서 `createNewMapCanvas3D()` 호출 시 C++ segfault를 일으키는 문제 때문에 웹 기반 대안을 구축했다.

```
burwood_3d_viewer.html
├── deck.gl (CDN)           ← WebGL 기반 3D 렌더링 엔진
├── MapLibre GL (CDN)       ← 다크 테마 배경지도 타일 (CARTO)
├── burwood_buildings.geojson ← fetch()로 로드
└── Python HTTP 서버 (8080)  ← 로컬 파일 서빙
```

| 구성 요소 | 역할 | 출처 |
|-----------|------|------|
| **deck.gl** | GeoJSON 폴리곤을 height 값으로 3D 돌출(extrude) 렌더링 | CDN (unpkg.com) |
| **MapLibre GL** | 다크 테마 배경지도 타일 렌더링 | CARTO 타일 서버 |
| **GeoJSON** | 건물 폴리곤 좌표 + 높이/이름 속성 | 1단계에서 수집 |
| **HTTP 서버** | CORS 제약 우회, 로컬 파일 브라우저에 서빙 | `python3 -m http.server 8080` |

**deck.gl 3D 렌더링 원리**:
```
GeoJSON 2D 폴리곤 (건물 바닥 윤곽)
    ↓ GeoJsonLayer { extruded: true }
    ↓ getElevation: feature.properties.height
3D 입체 건물 (폴리곤을 높이만큼 위로 밀어올림)
    ↓ getFillColor: 높이별 6단계 색상 매핑
높이별 색상이 입혀진 인터랙티브 3D 건물
```

**실행 방법**:
```bash
cd /Users/link4eeg/Desktop/QGIS_MCP
python3 -m http.server 8080 --bind 127.0.0.1 &
open http://localhost:8080/burwood_3d_viewer.html
```

**마우스 조작**: 왼쪽 드래그(이동) | 오른쪽 드래그(회전) | 스크롤(확대/축소) | Ctrl+드래그(기울기)

### QGIS 3D 관련 알려진 제약사항

- `createNewMapCanvas3D()`: macOS에서 C++ segfault 발생 (API 호출, QAction 트리거, AppleScript 모두 동일)
- `setRenderer3D()`: 호출 후 QGIS MCP 통신이 불안정해짐 (이후 exec() 명령에서 segfault)
- QGIS 플러그인 디렉토리(`~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`)는 **복사본**이므로 수정 시 직접 복사 필요
- QTimer 재진입(reentrancy) 방지: `self._processing` 플래그로 `process_server()` 보호 필요

## Git Conventions

Commit messages follow: `feat:`, `fix:`, `docs:` prefixes.

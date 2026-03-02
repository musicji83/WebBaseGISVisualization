# PRD (Product Requirements Document)

## Burwood Station 3D Buildings Visualization

---

## 1. 제품 개요

| 항목 | 내용 |
|------|------|
| **제품명** | Sydney Stations 3D Buildings Visualization |
| **버전** | v1.0 (MVP) |
| **작성일** | 2026-03-02 |
| **목적** | Burwood & Ashfield Station 반경 500 m 건물 데이터를 듀얼 원형 프레임으로 3D 비교 시각화 |
| **대상 사용자** | GIS 분석가, 도시 계획 담당자, 데이터 시각화 학습자 |

## 2. 문제 정의

### 해결하려는 문제
- QGIS 단독으로는 3D 시각화가 macOS에서 불안정 (`createNewMapCanvas3D()` segfault)
- OpenStreetMap 건물 데이터를 수집부터 시각화까지 자동화된 파이프라인이 없음
- 비개발자도 건물 높이 데이터를 직관적으로 탐색할 수 있는 도구 필요

### 기존 대안의 한계
| 대안 | 한계 |
|------|------|
| QGIS 3D Map View | macOS에서 C++ segfault 발생 |
| Google Earth | 커스텀 데이터 로드 불편, 스타일 제한 |
| 수동 Python 스크립트 | 매번 QGIS를 수동으로 열고 코드를 붙여넣어야 함 |

## 3. 제품 요구사항

### 3.1 기능 요구사항 (Functional Requirements)

#### FR-01: 데이터 수집
| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-01-1 | Overpass API로 특정 좌표 반경 내 건물 데이터 자동 수집 | P0 |
| FR-01-2 | GeoJSON 형식으로 저장 (좌표, 높이, 층수, 이름 포함) | P0 |
| FR-01-3 | 기존 GeoJSON 파일 재사용 지원 (API 장애 대비) | P1 |
| FR-01-4 | 복수 지역 데이터 수집 (Burwood 513개 + Ashfield 840개) | P0 |

#### FR-02: QGIS 프로젝트 자동 구성
| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-02-1 | QGIS 자동 실행 및 MCP 서버 자동 시작 | P0 |
| FR-02-2 | OSM 배경지도 + 중심점 핀 + 버퍼 자동 추가 | P0 |
| FR-02-3 | 건물 레이어에 높이별 6단계 그라데이션 스타일 자동 적용 | P0 |
| FR-02-4 | 2D PNG 렌더링 및 .qgz 프로젝트 파일 저장 | P1 |
| FR-02-5 | 3D Extrusion 렌더러 자동 설정 | P1 |

#### FR-03: 웹 3D 시각화
| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| FR-03-1 | 브라우저에서 건물을 3D로 돌출(extrude) 렌더링 | P0 |
| FR-03-2 | Left-drag: Pan, Right-drag: Orbit, Scroll: Zoom 마우스 조작 | P0 |
| FR-03-3 | 높이별 색상 구분 (QGIS 스타일과 동일) | P0 |
| FR-03-4 | 건물 hover 시 이름, 높이, 층수 툴팁 표시 (Info) | P0 |
| FR-03-5 | 다크 테마 배경지도 | P2 |
| FR-03-6 | SVG 마우스 조작 다이어그램 UI | P1 |
| FR-03-7 | 두 지역 비교 듀얼 원형 프레임 뷰 (Burwood vs Ashfield) | P0 |

### 3.2 비기능 요구사항 (Non-Functional Requirements)

| ID | 요구사항 | 기준 |
|----|---------|------|
| NFR-01 | 전체 파이프라인 실행 시간 | 2분 이내 (QGIS 시작 포함) |
| NFR-02 | 웹 뷰어 초기 로딩 | 3초 이내 |
| NFR-03 | 웹 뷰어 FPS | 30fps 이상 (1,353개 건물, 듀얼 뷰 기준) |
| NFR-04 | 브라우저 호환성 | Chrome, Safari, Firefox (WebGL 지원) |
| NFR-05 | 외부 서버 의존성 | CDN(deck.gl, MapLibre) + CARTO 타일만 |

## 4. 기술 스택

| 계층 | 기술 | 용도 |
|------|------|------|
| 데이터 수집 | Overpass API (OSM) | 건물 GeoJSON 다운로드 |
| GIS 엔진 | QGIS 3.X + PyQGIS | 2D 렌더링, 프로젝트 관리 |
| 통신 | TCP Socket (JSON) | 터미널 ↔ QGIS 플러그인 |
| 자동화 | Python 3.12 + MCP 서버 | 스크립트 실행 파이프라인 |
| 3D 렌더링 | deck.gl (WebGL) | 브라우저 3D 건물 시각화 |
| 배경지도 | MapLibre GL + CARTO | 다크 테마 타일맵 |
| 서버 | Python http.server | 로컬 파일 서빙 |

## 5. 제약 조건

| 제약 | 설명 | 영향 |
|------|------|------|
| QGIS 3D 버그 | `createNewMapCanvas3D()` macOS segfault | 웹 뷰어로 대체 |
| `setRenderer3D()` 불안정 | 호출 후 MCP 통신 불가 | Step 실행 순서 조정 (5→4) |
| Overpass API 불안정 | 간헐적 504 타임아웃 | 기존 GeoJSON 재사용 지원 |
| 플러그인 복사본 | 심볼릭 링크 아닌 복사본 | 수동 복사 필요 |
| 로컬 HTTP 서버 필요 | file:// CORS 제약 | `python3 -m http.server` 실행 |

## 6. 성공 지표

| 지표 | 목표 | 현재 |
|------|------|------|
| 전체 자동화 성공률 | 100% (5개 Step 모두 완료) | 100% ✅ |
| 웹 3D 뷰어 렌더링 | 1,353개 건물 3D 표시 (듀얼 뷰) | Burwood 513 + Ashfield 840 ✅ |
| 마우스 인터랙션 | Left-drag: Pan, Right-drag: Orbit, Scroll: Zoom, Hover: Info | 모두 동작 ✅ |
| SVG 마우스 가이드 | 마우스 조작 다이어그램 표시 | 구현 완료 ✅ |
| 듀얼 원형 프레임 | 두 지역 동시 비교 | Burwood vs Ashfield ✅ |
| 생성 파일 | GeoJSON×2 + PNG + QGZ + HTML×2 | 6개 모두 생성 ✅ |

## 7. 향후 로드맵

| 단계 | 기능 | 우선순위 |
|------|------|---------|
| v1.1 | 좌표/반경 사용자 입력 지원 | P1 |
| v1.2 | 건물 검색 및 필터링 | P1 |
| v1.3 | 시간대별 그림자 시뮬레이션 | P2 |
| v1.4 | 추가 지역 비교 (3개 이상 원형 프레임) | P2 |
| v2.0 | 다른 도시 지원 (범용화) | P2 |
| v2.1 | 실시간 Overpass API 연동 | P3 |
